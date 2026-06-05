"""Manual CSV schema definitions and column/ticker normalization for JP daily bars."""

from __future__ import annotations

import re
from datetime import date, datetime

from invis_alpha_os.config.jp_watchlist import normalize_jquants_equity_code

CANONICAL_COLUMNS: tuple[str, ...] = ("ticker", "date", "open", "high", "low", "close", "volume")

COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "ticker": ("ticker", "symbol", "code", "銘柄コード"),
    "date": ("date", "日付", "datetime"),
    "open": ("open", "始値"),
    "high": ("high", "高値"),
    "low": ("low", "安値"),
    "close": ("close", "終値"),
    "volume": ("volume", "出来高"),
}

_TICKER_SUFFIX_RE = re.compile(r"^(.+?)\.(T|JP)$", re.IGNORECASE)


def _normalize_header(cell: str) -> str:
    return (cell or "").strip().lstrip("\ufeff")


def map_csv_headers(headers: list[str]) -> dict[str, str]:
    """Map canonical column names to actual header names in the file."""
    normalized_headers = {_normalize_header(h): h for h in headers if _normalize_header(h)}
    out: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = _normalize_header(alias)
            if key in normalized_headers:
                out[canonical] = normalized_headers[key]
                break
    return out


def missing_required_columns(header_map: dict[str, str]) -> list[str]:
    return [col for col in CANONICAL_COLUMNS if col not in header_map]


def normalize_ticker(raw: str) -> tuple[str | None, list[str]]:
    warnings: list[str] = []
    token = (raw or "").strip().upper()
    if not token:
        return None, ["empty_ticker"]
    match = _TICKER_SUFFIX_RE.match(token)
    if match:
        token = match.group(1).upper()
        warnings.append("ticker_suffix_stripped")
    if len(token) == 5 and token.endswith("0") and token[:4].isdigit():
        candidate = token[:4]
        if normalize_jquants_equity_code(candidate):
            warnings.append("ticker_truncated_from_5digit")
            token = candidate
    wire = normalize_jquants_equity_code(token)
    if wire is None:
        return None, warnings + ["unsupported_ticker_format"]
    return wire, warnings


def parse_bar_date(raw: str) -> date | None:
    text = (raw or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_float_cell(raw: str) -> float | None:
    text = (raw or "").strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None
