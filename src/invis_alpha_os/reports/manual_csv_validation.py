"""Validate manual CSV files for JP daily bars import (no cache write)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.manual_csv_schema import (
    CANONICAL_COLUMNS,
    map_csv_headers,
    missing_required_columns,
    normalize_ticker,
    parse_bar_date,
    parse_float_cell,
)


@dataclass(frozen=True)
class ManualCsvValidationResult:
    markdown_text: str
    json_payload: dict[str, Any]
    rows_by_ticker: dict[str, list[dict[str, Any]]]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_targets_csv(targets_csv: str) -> list[str]:
    return [part.strip() for part in targets_csv.split(",") if part.strip()]


def _validate_ohlc_row(
    *,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float,
) -> list[str]:
    issues: list[str] = []
    if close <= 0:
        issues.append("close_not_positive")
    if volume < 0:
        issues.append("volume_negative")
    hi_bound = max(open_, close, low)
    lo_bound = min(open_, close, high)
    if high < hi_bound - 1e-9:
        issues.append("high_below_ohlc")
    if low > lo_bound + 1e-9:
        issues.append("low_above_ohlc")
    return issues


def load_manual_csv_rows(csv_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    errors: list[str] = []
    if not csv_path.is_file():
        return [], [f"csv_not_found:{csv_path.name}"]
    try:
        text = csv_path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return [], [f"csv_read_failed:{exc.__class__.__name__}"]
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return [], ["csv_empty"]
    reader = csv.DictReader(lines)
    if reader.fieldnames is None:
        return [], ["csv_missing_header"]
    return list(reader), errors


def validate_manual_csv_file(
    *,
    csv_path: Path,
    targets_csv: str,
    report_date: str,
) -> ManualCsvValidationResult:
    allowed_targets = set(_parse_targets_csv(targets_csv))
    raw_rows, load_errors = load_manual_csv_rows(csv_path)
    errors: list[str] = list(load_errors)
    warnings: list[str] = []
    parsed_rows: list[dict[str, Any]] = []
    rows_by_ticker: dict[str, list[dict[str, Any]]] = {}

    if not raw_rows and not load_errors:
        errors.append("no_data_rows")

    header_map: dict[str, str] = {}
    if raw_rows:
        header_map = map_csv_headers(list(raw_rows[0].keys()))
        missing = missing_required_columns(header_map)
        if missing:
            errors.append(f"missing_columns:{','.join(missing)}")

    report_d = date.fromisoformat(report_date)
    seen_keys: set[tuple[str, str]] = set()
    tickers_in_file: set[str] = set()

    for idx, row in enumerate(raw_rows, start=2):
        if not header_map:
            break
        raw_ticker = row.get(header_map["ticker"], "")
        wire, ticker_warnings = normalize_ticker(raw_ticker)
        if wire is None:
            errors.append(f"row_{idx}:invalid_ticker")
            continue
        warnings.extend(f"row_{idx}:{w}" for w in ticker_warnings)
        tickers_in_file.add(wire)
        if allowed_targets and wire not in allowed_targets:
            errors.append(f"row_{idx}:target_out_of_scope:{wire}")
            continue

        raw_date = row.get(header_map["date"], "")
        bar_date = parse_bar_date(raw_date)
        if bar_date is None:
            errors.append(f"row_{idx}:invalid_date")
            continue
        if bar_date > report_d:
            errors.append(f"row_{idx}:future_date:{bar_date.isoformat()}")
            continue

        open_ = parse_float_cell(row.get(header_map["open"], ""))
        high = parse_float_cell(row.get(header_map["high"], ""))
        low = parse_float_cell(row.get(header_map["low"], ""))
        close = parse_float_cell(row.get(header_map["close"], ""))
        volume = parse_float_cell(row.get(header_map["volume"], ""))
        if None in (open_, high, low, close, volume):
            errors.append(f"row_{idx}:non_numeric_ohlcv")
            continue
        assert open_ is not None and high is not None and low is not None and close is not None and volume is not None
        ohlc_issues = _validate_ohlc_row(open_=open_, high=high, low=low, close=close, volume=volume)
        if ohlc_issues:
            errors.append(f"row_{idx}:{'|'.join(ohlc_issues)}")

        iso_date = bar_date.isoformat()
        key = (wire, iso_date)
        if key in seen_keys:
            errors.append(f"row_{idx}:duplicate_ticker_date:{wire}:{iso_date}")
            continue
        seen_keys.add(key)

        bar = {
            "ticker": wire,
            "date": iso_date,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
        parsed_rows.append(bar)
        rows_by_ticker.setdefault(wire, []).append(bar)

    for ticker, bars in rows_by_ticker.items():
        bars.sort(key=lambda x: x["date"])
        dates = [date.fromisoformat(b["date"]) for b in bars]
        for prev, cur in zip(dates, dates[1:]):
            gap = (cur - prev).days
            if gap > 5:
                warnings.append(f"{ticker}:data_gap_{gap}_days_between_{prev.isoformat()}_and_{cur.isoformat()}")

    missing_targets = sorted(allowed_targets - tickers_in_file) if allowed_targets else []
    if missing_targets:
        warnings.append(f"missing_targets_in_csv:{','.join(missing_targets)}")

    all_dates = [r["date"] for r in parsed_rows]
    payload: dict[str, Any] = {
        "provider": "manual_csv",
        "validated": not errors,
        "cache_write_executed": False,
        "actual_import_executed": False,
        "targets": sorted(tickers_in_file & allowed_targets) if allowed_targets else sorted(tickers_in_file),
        "row_count": len(parsed_rows),
        "date_min": min(all_dates) if all_dates else None,
        "date_max": max(all_dates) if all_dates else None,
        "latest_date": max(all_dates) if all_dates else None,
        "errors": errors,
        "warnings": warnings,
        "required_columns": list(CANONICAL_COLUMNS),
    }

    lines = [
        "# Manual CSV Validation",
        "",
        "## メタ情報",
        f"- provider: manual_csv",
        f"- validated: {str(payload['validated']).lower()}",
        f"- row_count: {payload['row_count']}",
        f"- date_min: {payload['date_min']}",
        f"- date_max: {payload['date_max']}",
        f"- targets: {', '.join(payload['targets']) or '(none)'}",
        "- cache_write_executed: false",
        "- actual_import_executed: false",
        "",
        "## エラー",
    ]
    if errors:
        lines.extend(f"- {e}" for e in errors[:80])
    else:
        lines.append("- (none)")
    lines.extend(["", "## 警告"])
    if warnings:
        lines.extend(f"- {w}" for w in warnings[:80])
    else:
        lines.append("- (none)")
    lines.append("")
    return ManualCsvValidationResult(
        markdown_text="\n".join(lines),
        json_payload=payload,
        rows_by_ticker=rows_by_ticker,
    )
