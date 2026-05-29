"""Schema mapper and safety guard for manual JP bars (metadata/redacted only)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.manual_csv_pii_guard import read_csv_headers
from invis_alpha_os.reports.manual_csv_schema import CANONICAL_COLUMNS, map_csv_headers, missing_required_columns
from invis_alpha_os.reports.manual_csv_validation import validate_manual_csv_file

DEFAULT_TARGET_TICKERS_CSV = "5802,6645,5801,285A,5803"

PROHIBITED_COLUMN_TOKENS: tuple[str, ...] = (
    "account",
    "name",
    "address",
    "phone",
    "email",
    "quantity",
    "position",
    "pnl",
    "profit",
    "loss",
    "trade_id",
    "order_id",
    "broker_account",
    "口座",
    "氏名",
    "住所",
    "電話",
    "メール",
    "保有数量",
    "数量",
    "評価損益",
    "損益",
    "注文番号",
    "約定番号",
    "証券口座",
)

SUSPICIOUS_COLUMN_TOKENS: tuple[str, ...] = (
    "balance",
    "cash",
    "margin",
    "commission",
    "fee",
    "残高",
    "手数料",
)


@dataclass(frozen=True)
class ManualDataSchemaValidationResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_targets(targets_csv: str) -> list[str]:
    return [part.strip() for part in targets_csv.split(",") if part.strip()]


def redacted_header_summary(headers: list[str]) -> str:
    normalized = sorted(h.strip().lower() for h in headers if h and h.strip())
    if not normalized:
        return "cols=0"
    digest = hashlib.sha256(",".join(normalized).encode("utf-8")).hexdigest()[:12]
    return f"cols={len(normalized)};sha256_prefix={digest}"


def detect_prohibited_headers(headers: list[str]) -> list[str]:
    hits: list[str] = []
    for header in headers:
        norm = header.strip().lower()
        if not norm:
            continue
        for token in PROHIBITED_COLUMN_TOKENS:
            if token in norm:
                hits.append(header.strip())
                break
    return sorted(set(hits))


def detect_suspicious_headers(headers: list[str]) -> list[str]:
    hits: list[str] = []
    for header in headers:
        norm = header.strip().lower()
        if not norm:
            continue
        for token in SUSPICIOUS_COLUMN_TOKENS:
            if token in norm:
                hits.append(header.strip())
                break
    return sorted(set(hits))


def build_manual_data_schema_validation(
    *,
    input_path: Path,
    targets_csv: str = DEFAULT_TARGET_TICKERS_CSV,
    report_date: str,
) -> ManualDataSchemaValidationResult:
    allowed = _parse_targets(targets_csv)
    headers, header_errors = read_csv_headers(input_path)
    prohibited = detect_prohibited_headers(headers)
    suspicious = detect_suspicious_headers(headers)
    header_map = map_csv_headers(headers) if headers else {}
    missing = missing_required_columns(header_map)

    schema_valid = False
    validation_payload: dict[str, Any] = {}
    ticker_coverage: list[dict[str, Any]] = []

    if prohibited:
        overall = "prohibited_columns_detected"
    elif header_errors:
        overall = "header_read_failed"
    elif missing:
        overall = "missing_required_columns"
    else:
        validation = validate_manual_csv_file(
            csv_path=input_path,
            targets_csv=targets_csv,
            report_date=report_date,
        )
        validation_payload = validation.json_payload
        schema_valid = bool(validation.json_payload.get("validated"))
        overall = "pass" if schema_valid else "validation_failed"
        rows_by_ticker = validation.rows_by_ticker
        for ticker in allowed:
            bars = rows_by_ticker.get(ticker, [])
            dates = [str(b["date"]) for b in bars]
            ticker_coverage.append(
                {
                    "ticker": ticker,
                    "status": "present" if bars else "missing",
                    "row_count": len(bars),
                    "date_min": min(dates) if dates else None,
                    "date_max": max(dates) if dates else None,
                }
            )

    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "overall_status": overall,
        "schema_valid": schema_valid and not prohibited and not missing,
        "prohibited_columns_detected": bool(prohibited),
        "prohibited_columns_redacted": prohibited,
        "suspicious_columns_redacted": suspicious,
        "missing_required_columns": missing,
        "required_columns": list(CANONICAL_COLUMNS),
        "redacted_header_summary": redacted_header_summary(headers),
        "header_read_errors": header_errors,
        "target_ticker_coverage": ticker_coverage,
        "validation": validation_payload,
        "actual_import": False,
        "cache_write": False,
        "contents_printed": False,
    }
    lines = [
        "# Manual Data Schema Validation",
        "",
        f"- overall_status: {overall}",
        f"- schema_valid: {str(payload['schema_valid']).lower()}",
        f"- prohibited_columns_detected: {str(payload['prohibited_columns_detected']).lower()}",
        f"- redacted_header_summary: {payload['redacted_header_summary']}",
        "",
        "## Target ticker coverage",
        "",
        "| ticker | status | date_min | date_max | rows |",
        "| --- | --- | --- | --- | ---: |",
    ]
    if ticker_coverage:
        for row in ticker_coverage:
            lines.append(
                f"| {row['ticker']} | {row['status']} | {row.get('date_min') or '-'} | "
                f"{row.get('date_max') or '-'} | {row['row_count']} |"
            )
    else:
        lines.append("| (not evaluated) | - | - | - | - |")
    lines.append("")
    return ManualDataSchemaValidationResult(markdown_text="\n".join(lines), json_payload=payload)
