"""PII and account-data column guards for manual/broker CSV intake."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.manual_csv_schema import CANONICAL_COLUMNS, map_csv_headers

PII_DENY_SUBSTRINGS: tuple[str, ...] = (
    "account",
    "account_number",
    "口座",
    "氏名",
    "名前",
    "住所",
    "電話",
    "email",
    "mail",
    "取引",
    "約定",
    "注文",
    "取得単価",
    "保有数量",
    "評価額",
    "損益",
    "入出金",
)

ALLOWED_OHLCV_HINTS: tuple[str, ...] = (
    "ticker",
    "symbol",
    "code",
    "銘柄",
    "date",
    "日付",
    "datetime",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "始値",
    "高値",
    "安値",
    "終値",
    "出来高",
)


@dataclass(frozen=True)
class ManualCsvPiiGuardResult:
    status: str
    account_data_detected: bool
    denied_columns: list[str]
    warnings: list[str]
    json_payload: dict[str, Any]


def _normalize_header(cell: str) -> str:
    return (cell or "").strip().lstrip("\ufeff").lower()


def _delimiter_for_path(path: Path, first_line: str) -> str:
    suffix = path.suffix.lower()
    if suffix == ".tsv":
        return "\t"
    if suffix == ".txt" and "\t" in first_line:
        return "\t"
    return ","


def read_csv_headers(csv_path: Path) -> tuple[list[str], list[str]]:
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
    delimiter = _delimiter_for_path(csv_path, lines[0])
    reader = csv.reader([lines[0]], delimiter=delimiter)
    row = next(reader, [])
    return [cell for cell in row if cell.strip()], errors


def scan_csv_headers_for_pii(headers: list[str]) -> ManualCsvPiiGuardResult:
    denied: list[str] = []
    warnings: list[str] = []
    for header in headers:
        norm = _normalize_header(header)
        if not norm:
            continue
        for token in PII_DENY_SUBSTRINGS:
            if token.lower() in norm:
                denied.append(header)
                break
    header_map = map_csv_headers(headers)
    missing = [col for col in CANONICAL_COLUMNS if col not in header_map]
    if missing:
        warnings.append(f"missing_ohlcv_columns:{','.join(missing)}")
    account_data = bool(denied)
    if account_data:
        status = "rejected"
    elif missing:
        status = "warning"
    else:
        status = "passed"
    payload = {
        "pii_guard_status": status,
        "account_data_detected": account_data,
        "denied_columns": denied,
        "warnings": warnings,
        "header_count": len(headers),
    }
    return ManualCsvPiiGuardResult(
        status=status,
        account_data_detected=account_data,
        denied_columns=denied,
        warnings=warnings,
        json_payload=payload,
    )


def run_manual_csv_pii_guard(csv_path: Path) -> ManualCsvPiiGuardResult:
    headers, errors = read_csv_headers(csv_path)
    if errors:
        return ManualCsvPiiGuardResult(
            status="rejected",
            account_data_detected=False,
            denied_columns=[],
            warnings=errors,
            json_payload={
                "pii_guard_status": "rejected",
                "account_data_detected": False,
                "denied_columns": [],
                "warnings": errors,
            },
        )
    return scan_csv_headers_for_pii(headers)
