"""Strict in-memory parser for Stooq daily CSV → sanitized OHLCV row dicts (Main R4).

Raises ``ValueError`` with fixed opaque reason codes — never embedded raw CSV rows or vendor bodies.

``classify_stooq_csv_text_safely`` (Main R4.1, **R4.3 refine**) returns only capped, redacted structural metadata —
never full lines, OHLC cells, or raw bodies.
"""

from __future__ import annotations

import csv
import io
import math
import re
from typing import Any

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_REQUIRED_LOWER = frozenset({"date", "open", "high", "low", "close", "volume"})

_HTML_HINT_RE = re.compile(
    r"<\s*html\b|<\s*!doctype\b|<\s*head\b|<\s*body\b|<\s*table\b",
    re.I,
)

_NO_DATA_HINT_RE = re.compile(
    r"(no\s*data|data\s+not\s+available|not\s+found|brak\s+danych|invalid\s+symbol|unknown\s+symbol|"
    r"symbol\s+not\s+found|nie\s+znaleziono)",
    re.I,
)

_API_KEY_HINT_RE = re.compile(
    r"(get\s+your\s+apikey|api\s+key|\bapikey\b)",
    re.I,
)

_HEADER_SAFE_CHAR_RE = re.compile(r"[^0-9A-Za-z_.\- ]")


def _sanitize_header_cell(cell: str) -> str:
    t = str(cell).strip()
    if len(t) > 40:
        t = t[:40]
    return _HEADER_SAFE_CHAR_RE.sub("?", t)


def _looks_like_number_token(token: str) -> bool:
    t = str(token).strip().replace(",", "")
    if not t or t in "-—":
        return False
    try:
        float(t)
    except (TypeError, ValueError):
        return False
    return True


def _first_line_probable_data_row(cells: list[str]) -> bool:
    """True if the split first line looks like an OHLC row, not a textual header."""

    if len(cells) < 2:
        return False

    any_letter = any(any(ch.isalpha() for ch in str(c)) for c in cells)
    if not any_letter:
        return True

    if _DATE_RE.match(str(cells[0]).strip()):
        if len(cells) >= 5 and all(_looks_like_number_token(cells[i]) for i in range(1, min(6, len(cells)))):
            return True

    return False


def _delimiter_drift_suspected(
    nonempty_lines: list[str],
    delim_char: str,
    delimiter_guess: str,
) -> bool:
    """Heuristic: header line delimiter does not match following data rows (tabular drift)."""

    if delimiter_guess == "unknown" or len(nonempty_lines) < 2:
        return False
    for raw in nonempty_lines[1:5]:
        ln = raw.strip()
        if not ln:
            continue
        tabs, commas, semis = ln.count("\t"), ln.count(","), ln.count(";")
        if delim_char == ",":
            if tabs >= 2 and tabs > commas + 1:
                return True
        elif delim_char == "\t":
            if commas >= 4 and commas > tabs + 1:
                return True
        elif delim_char == ";":
            if (tabs >= 2 and tabs > semis + 1) or (commas >= 4 and commas > semis + 1):
                return True
    return False


def classify_stooq_csv_text_safely(csv_text: str) -> dict[str, Any]:
    """Structural-only summary of vendor text for operator debugging (**no OHLC**, **no rows**, **no raw body**)."""

    raw = csv_text if isinstance(csv_text, str) else ""
    stripped = raw.strip()
    if not stripped:
        return {
            "body_kind": "empty",
            "header_columns_sanitized": [],
            "header_column_count": 0,
            "line_count_limited": 0,
            "has_required_columns": False,
            "required_columns_missing": sorted(_REQUIRED_LOWER),
            "delimiter_guess": "unknown",
        }

    lines = stripped.splitlines()
    line_nl = len(lines)
    line_count_limited = min(line_nl, 200)

    nonempty_lines = [ln for ln in lines if ln.strip()]
    first_line = nonempty_lines[0] if nonempty_lines else ""

    c_cnt, s_cnt, t_cnt = (
        first_line.count(","),
        first_line.count(";"),
        first_line.count("\t"),
    )
    if t_cnt > c_cnt and t_cnt > s_cnt and t_cnt > 0:
        delim_char = "\t"
        delimiter_guess: str = "tab"
    elif s_cnt > c_cnt and s_cnt > 0:
        delim_char = ";"
        delimiter_guess = "semicolon"
    elif c_cnt > 0:
        delim_char = ","
        delimiter_guess = "comma"
    else:
        delim_char = ","
        delimiter_guess = "unknown"

    header_cells: list[str] = []
    if first_line:
        if delimiter_guess == "unknown" and "\t" in first_line:
            delim_char = "\t"
            delimiter_guess = "tab"
        try:
            row = next(csv.reader(io.StringIO(first_line), delimiter=delim_char))
            header_cells = [str(x) for x in row]
        except (csv.Error, StopIteration):
            header_cells = [first_line]

    header_column_count = len(header_cells)
    probable_data = _first_line_probable_data_row(header_cells)
    if probable_data:
        header_columns_sanitized: list[str] = []
        names_lower: list[str] = []
    else:
        header_columns_sanitized = [_sanitize_header_cell(cell) for cell in header_cells[:12]]
        names_lower = [str(x or "").strip().lower() for x in header_cells]

    req_missing = sorted(_REQUIRED_LOWER - frozenset(names_lower))
    has_required = not bool(req_missing)

    head_sample = stripped[:8192]
    if _HTML_HINT_RE.search(head_sample):
        body_kind: str = "html_like"
    elif _NO_DATA_HINT_RE.search(stripped[:1600]):
        body_kind = "no_data_like"
    elif header_column_count >= 2 and delimiter_guess != "unknown":
        body_kind = "csv_like"
    elif header_column_count >= 2:
        body_kind = "csv_like"
    elif header_column_count == 1 and delimiter_guess == "unknown":
        lone = names_lower[0] if names_lower else ""
        snip_low = stripped[:400].lower()
        if (lone and ("error" in lone or "sorry" in lone)) or ("sorry" in snip_low):
            body_kind = "no_data_like"
        else:
            body_kind = "unknown"
    else:
        body_kind = "unknown"

    if body_kind == "csv_like" and _delimiter_drift_suspected(nonempty_lines, delim_char, delimiter_guess):
        body_kind = "delimiter_drift"

    joined_san = " ".join(header_columns_sanitized).lower()
    hint_region = stripped[:8192]
    api_in_header = bool(_API_KEY_HINT_RE.search(joined_san))
    api_in_body = bool(_API_KEY_HINT_RE.search(hint_region))
    if api_in_header or api_in_body:
        body_kind = "api_key_required"

    if body_kind == "no_data_like":
        header_columns_sanitized = []
        header_column_count = 0
        has_required = False
        req_missing = sorted(_REQUIRED_LOWER)

    if _HTML_HINT_RE.search(head_sample):
        header_columns_sanitized = []
        header_column_count = 0
        has_required = False
        req_missing = sorted(_REQUIRED_LOWER)

    return {
        "body_kind": body_kind,
        "header_columns_sanitized": header_columns_sanitized,
        "header_column_count": header_column_count,
        "line_count_limited": line_count_limited,
        "has_required_columns": has_required,
        "required_columns_missing": req_missing,
        "delimiter_guess": delimiter_guess,
    }


def _reject_parse() -> None:
    raise ValueError("stooq_csv_parse_failed")


def _float_ohlc(token: str) -> float:
    t = token.strip()
    if not t or t in "-—":
        _reject_parse()
    try:
        v = float(t)
    except (TypeError, ValueError):
        _reject_parse()
    if not math.isfinite(v) or v <= 0:
        _reject_parse()
    return float(v)


def _float_vol(token: str) -> float:
    t = token.strip()
    if not t or t in "-—":
        _reject_parse()
    try:
        v = float(t)
    except (TypeError, ValueError):
        _reject_parse()
    if not math.isfinite(v) or v < 0:
        _reject_parse()
    return float(v)


def parse_stooq_daily_csv_to_rows(csv_text: str) -> list[dict[str, object]]:
    """Parse classic Stooq header ``Date,Open,High,Low,Close,Volume`` CSV text.

    Returned rows match ``bars_from_rows`` keys: ``date``, ``open``, ``high``, ``low``, ``close``, ``volume``.

    Raises:
        ValueError: ``stooq_csv_no_rows`` | ``stooq_csv_missing_required_columns`` |
            ``stooq_csv_parse_failed``
    """

    stripped = csv_text.strip()
    if not stripped:
        raise ValueError("stooq_csv_no_rows")

    reader = csv.reader(io.StringIO(stripped))
    try:
        header = next(reader)
    except StopIteration:
        raise ValueError("stooq_csv_no_rows") from None

    names = [str(c or "").strip().lower() for c in header]
    if len(names) < len(header):
        _reject_parse()
    if not names or names[0] == "":
        raise ValueError("stooq_csv_missing_required_columns")

    missing = _REQUIRED_LOWER - frozenset(names)
    if missing:
        raise ValueError("stooq_csv_missing_required_columns")

    col_ix = {n: names.index(n) for n in _REQUIRED_LOWER}

    out: list[dict[str, object]] = []
    for raw in reader:
        if raw is None or not any(str(c).strip() for c in raw):
            continue

        max_ix = max(col_ix.values())
        if len(raw) <= max_ix:
            _reject_parse()

        ds = str(raw[col_ix["date"]]).strip()
        if not _DATE_RE.match(ds):
            _reject_parse()

        row_obj: dict[str, object] = {
            "date": ds,
            "open": _float_ohlc(str(raw[col_ix["open"]])),
            "high": _float_ohlc(str(raw[col_ix["high"]])),
            "low": _float_ohlc(str(raw[col_ix["low"]])),
            "close": _float_ohlc(str(raw[col_ix["close"]])),
            "volume": _float_vol(str(raw[col_ix["volume"]])),
        }
        out.append(row_obj)

    if not out:
        raise ValueError("stooq_csv_no_rows")

    out.sort(key=lambda r: str(r["date"]))
    dates = [str(r["date"]) for r in out]
    if len(set(dates)) != len(dates):
        _reject_parse()

    return out
