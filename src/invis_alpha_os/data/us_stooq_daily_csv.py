"""Strict in-memory parser for Stooq daily CSV → sanitized OHLCV row dicts (Main R4).

Raises ``ValueError`` with fixed opaque reason codes — never embedded raw CSV rows or vendor bodies.
"""

from __future__ import annotations

import csv
import io
import math
import re

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_REQUIRED_LOWER = frozenset({"date", "open", "high", "low", "close", "volume"})


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
