"""Header-only probes for OHLCV-shaped manual files (no row content in reports)."""

from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.manual_csv_pii_guard import read_csv_headers
from invis_alpha_os.reports.manual_csv_schema import map_csv_headers, missing_required_columns
from invis_alpha_os.reports.manual_data_schema_guard import detect_prohibited_headers


def headers_look_like_ohlcv(headers: list[str]) -> bool:
    if not headers:
        return False
    if detect_prohibited_headers(headers):
        return False
    header_map = map_csv_headers(headers)
    return len(missing_required_columns(header_map)) == 0


def probe_path_ohlcv_schema(path: Path) -> tuple[bool, str]:
    suffix = path.suffix.lower()
    if suffix not in {".csv", ".tsv", ".txt"}:
        return False, "unsupported_extension"
    headers, errors = read_csv_headers(path)
    if errors:
        return False, "header_read_failed"
    if detect_prohibited_headers(headers):
        return False, "prohibited_columns"
    if headers_look_like_ohlcv(headers):
        return True, "ohlcv_schema_match"
    return False, "missing_required_columns"
