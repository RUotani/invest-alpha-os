"""Normalize broker-specific JP OHLCV CSV files to manual_csv canonical shape."""

from __future__ import annotations

import csv
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.manual_csv_pii_guard import run_manual_csv_pii_guard
from invis_alpha_os.reports.manual_csv_schema import (
    CANONICAL_COLUMNS,
    map_csv_headers,
    missing_required_columns,
    normalize_ticker,
    parse_bar_date,
    parse_float_cell,
)
from invis_alpha_os.reports.manual_csv_validation import load_manual_csv_rows

BROKER_FORMAT_GENERIC = "generic_ohlcv"
BROKER_FORMAT_MANUAL = "manual_csv"
BROKER_FORMAT_MOOMOO = "moomoo_jp"
BROKER_FORMAT_SBI = "sbi_jp"
BROKER_FORMAT_RAKUTEN = "rakuten_jp"
BROKER_FORMAT_AUTO = "auto"

SUPPORTED_BROKER_FORMATS: frozenset[str] = frozenset(
    {
        BROKER_FORMAT_GENERIC,
        BROKER_FORMAT_MANUAL,
        BROKER_FORMAT_MOOMOO,
        BROKER_FORMAT_SBI,
        BROKER_FORMAT_RAKUTEN,
        BROKER_FORMAT_AUTO,
    }
)

MOOMOO_HEADER_HINTS: frozenset[str] = frozenset({"symbol", "time", "open", "high", "low", "close", "volume"})
SBI_HEADER_HINTS: frozenset[str] = frozenset({"銘柄コード", "日付", "始値", "高値", "安値", "終値", "出来高"})
RAKUTEN_HEADER_HINTS: frozenset[str] = frozenset({"銘柄", "日付", "始値", "高値", "安値", "終値", "出来高"})


@dataclass(frozen=True)
class ManualCsvNormalizationResult:
    markdown_text: str
    json_payload: dict[str, Any]
    normalized_path: Path | None


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _header_tokens(headers: list[str]) -> set[str]:
    return {(h or "").strip().lstrip("\ufeff").lower() for h in headers if (h or "").strip()}


def detect_broker_format(headers: list[str]) -> str:
    tokens = _header_tokens(headers)
    if MOOMOO_HEADER_HINTS.issubset(tokens):
        return BROKER_FORMAT_MOOMOO
    lowered = {h.strip().lower() for h in headers}
    if SBI_HEADER_HINTS.issubset(lowered):
        return BROKER_FORMAT_SBI
    if RAKUTEN_HEADER_HINTS.issubset(lowered):
        return BROKER_FORMAT_RAKUTEN
    header_map = map_csv_headers(headers)
    if not missing_required_columns(header_map):
        return BROKER_FORMAT_GENERIC
    return "unknown"


def _row_value(row: dict[str, str], header_map: dict[str, str], canonical: str) -> str:
    source_header = header_map.get(canonical, "")
    return (row.get(source_header, "") if source_header else "").strip()


def _normalize_rows(
    rows: list[dict[str, str]],
    headers: list[str],
    *,
    broker_format: str,
) -> tuple[list[dict[str, str]], str, list[str], list[str]]:
    detected = broker_format
    if broker_format == BROKER_FORMAT_AUTO:
        detected = detect_broker_format(headers)
        if detected == "unknown":
            return [], detected, [], ["auto_detect_failed"]
    if broker_format not in SUPPORTED_BROKER_FORMATS - {BROKER_FORMAT_AUTO}:
        return [], broker_format, [], [f"unsupported_broker_format:{broker_format}"]
    if broker_format == BROKER_FORMAT_AUTO and detected == "unknown":
        return [], detected, [], ["auto_detect_failed_no_conversion"]

    effective = detected if broker_format == BROKER_FORMAT_AUTO else broker_format
    header_map = map_csv_headers(headers)
    if missing_required_columns(header_map) and effective == BROKER_FORMAT_MOOMOO:
        alt_map = {
            "ticker": "Symbol",
            "date": "Time",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
        header_map = {k: v for k, v in alt_map.items() if v in headers or v.lower() in _header_tokens(headers)}
        for canonical, aliases in (
            ("ticker", ("Symbol", "symbol")),
            ("date", ("Time", "time", "Date", "date")),
            ("open", ("Open", "open")),
            ("high", ("High", "high")),
            ("low", ("Low", "low")),
            ("close", ("Close", "close")),
            ("volume", ("Volume", "volume")),
        ):
            if canonical not in header_map:
                for alias in aliases:
                    if alias in rows[0] if rows else alias in headers:
                        header_map[canonical] = alias
                        break

    missing = missing_required_columns(header_map)
    if missing:
        return [], effective, [], [f"missing_required_columns:{','.join(missing)}"]

    ignored_headers = [h for h in headers if h not in set(header_map.values())]
    out_rows: list[dict[str, str]] = []
    for row in rows:
        ticker_raw = _row_value(row, header_map, "ticker")
        ticker, _warnings = normalize_ticker(ticker_raw)
        if ticker is None:
            continue
        date_raw = _row_value(row, header_map, "date")
        parsed_date = parse_bar_date(date_raw.split(" ")[0] if " " in date_raw else date_raw)
        if parsed_date is None:
            continue
        o = parse_float_cell(_row_value(row, header_map, "open"))
        h = parse_float_cell(_row_value(row, header_map, "high"))
        lo = parse_float_cell(_row_value(row, header_map, "low"))
        c = parse_float_cell(_row_value(row, header_map, "close"))
        v = parse_float_cell(_row_value(row, header_map, "volume"))
        if None in (o, h, lo, c, v):
            continue
        out_rows.append(
            {
                "ticker": ticker,
                "date": parsed_date.isoformat(),
                "open": str(o),
                "high": str(h),
                "low": str(lo),
                "close": str(c),
                "volume": str(v),
            }
        )
    return out_rows, effective, ignored_headers, []


def write_normalized_csv(rows: list[dict[str, str]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CANONICAL_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def build_manual_csv_normalization(
    *,
    csv_path: Path,
    report_date: str,
    broker_format: str = BROKER_FORMAT_GENERIC,
    output_path: Path | None = None,
) -> ManualCsvNormalizationResult:
    pii = run_manual_csv_pii_guard(csv_path)
    if pii.account_data_detected or pii.status == "rejected":
        payload = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "detected_format": broker_format,
            "ready_for_validation": False,
            "pii_guard_status": pii.status,
            "account_data_detected": pii.account_data_detected,
            "errors": ["pii_guard_failed"],
        }
        return ManualCsvNormalizationResult(
            markdown_text="# Manual CSV Normalization Refused\n\n- pii_guard_failed: true\n",
            json_payload=payload,
            normalized_path=None,
        )

    rows, load_errors = load_manual_csv_rows(csv_path)
    if load_errors or not rows:
        payload = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "detected_format": broker_format,
            "ready_for_validation": False,
            "errors": load_errors or ["csv_empty"],
        }
        return ManualCsvNormalizationResult(
            markdown_text="# Manual CSV Normalization Failed\n",
            json_payload=payload,
            normalized_path=None,
        )

    headers = list(rows[0].keys())
    normalized_rows, detected, ignored, errors = _normalize_rows(rows, headers, broker_format=broker_format)
    ready = bool(normalized_rows) and not errors
    out_path: Path | None = None
    if ready:
        target = output_path or Path(tempfile.gettempdir()) / f"manual_csv_normalized_{report_date}.csv"
        out_path = write_normalized_csv(normalized_rows, target)

    payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "requested_format": broker_format,
        "detected_format": detected,
        "normalized_columns": list(CANONICAL_COLUMNS),
        "unsupported_columns_ignored": ignored,
        "pii_columns_detected": pii.denied_columns,
        "normalized_row_count": len(normalized_rows),
        "ready_for_validation": ready,
        "errors": errors,
        "cache_write_executed": False,
        "actual_import_executed": False,
    }
    lines = [
        "# Manual CSV Normalization",
        "",
        f"- detected_format: {detected}",
        f"- ready_for_validation: {str(ready).lower()}",
        f"- normalized_row_count: {len(normalized_rows)}",
        "",
    ]
    return ManualCsvNormalizationResult(
        markdown_text="\n".join(lines),
        json_payload=payload,
        normalized_path=out_path,
    )
