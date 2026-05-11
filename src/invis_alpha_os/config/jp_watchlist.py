"""Japan equity tickers from ``watchlist.yaml`` (Phase 1a Task 6)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .loader import load_yaml
from .paths import CONFIG_DIR


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


_JQ_DB4 = re.compile(r"^\d{4}$")


def jquants_daily_bars_ticker_kind(ticker: str) -> str:
    """Return ``ok`` for 4-digit numeric codes (sent as-is); else ``skipped_unsupported_code``."""

    t = (ticker or "").strip()
    if _JQ_DB4.fullmatch(t):
        return "ok"
    return "skipped_unsupported_code"
