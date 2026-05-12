"""Japan equity tickers from ``watchlist.yaml`` (Phase 1a Task 6).

**Re-focus Task 1**: J-Quants daily-bars wire accepts **4-character ASCII alphanumeric** codes (e.g. ``285A``,
``7011``) with letters normalized to **uppercase** for HTTP query values. Symbols, whitespace, unicode
identifiers, wrong lengths, etc. remain ``skipped_unsupported_code``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .loader import load_yaml
from .paths import CONFIG_DIR

_jq_code4_ascii_alnum = re.compile(r"^[0-9A-Za-z]{4}$")


def extract_jp_watchlist_tickers(watchlist_data: dict[str, Any]) -> list[str]:
    """Return tickers in ``jp_watchlist`` order (strings or ``dict.ticker``)."""

    rows = watchlist_data.get("jp_watchlist")
    if not isinstance(rows, list):
        return []
    out: list[str] = []
    for row in rows:
        if isinstance(row, dict):
            t = str(row.get("ticker", "")).strip()
            if t:
                out.append(t)
        elif isinstance(row, str) and row.strip():
            out.append(row.strip())
    return out


def load_jp_watchlist_tickers(path: Path | None = None) -> list[str]:
    """Load and extract JP tickers from the repo watchlist file."""

    p = path if path is not None else CONFIG_DIR / "watchlist.yaml"
    data = load_yaml(p)
    return extract_jp_watchlist_tickers(data)


def normalize_jquants_equity_code(ticker: str) -> str | None:
    """Return uppercase 4-character ASCII alphanumeric wire code, or ``None`` if unsupported."""

    t = (ticker or "").strip()
    if not _jq_code4_ascii_alnum.fullmatch(t):
        return None
    return t.upper()


def jquants_daily_bars_ticker_kind(ticker: str) -> str:
    """Return ``ok`` for supported JPX-style 4-character codes (digits and/or ASCII letters).

    Anything else maps to ``skipped_unsupported_code`` (empty string, wrong length,
    ASCII symbols beyond ``[A-Za-z0-9]{4}``, non-ASCII, etc.).
    """

    return "ok" if normalize_jquants_equity_code(ticker) is not None else "skipped_unsupported_code"
