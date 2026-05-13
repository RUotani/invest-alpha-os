"""Main R: US watchlist normalization + ordering."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from invis_alpha_os.config.paths import CONFIG_DIR
from invis_alpha_os.config.us_watchlist import (
    extract_us_watchlist_symbols,
    load_us_watchlist_tickers,
    normalize_us_symbol,
)


def test_normalize_us_symbol_basic() -> None:
    assert normalize_us_symbol("  msft  ") == "MSFT"
    assert normalize_us_symbol("brk.b") == "BRK.B"
    assert normalize_us_symbol("GOOGL") == "GOOGL"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "../MSFT",
        "a/b",
        "MS\x00FT",
        "FOO-BAR-",  # trailing dash violates slug ends-alnum rule
        " TICK@ER ",
    ],
)
def test_normalize_us_symbol_rejects_unsafe(raw: str) -> None:
    assert normalize_us_symbol(raw) is None


def test_load_us_watchlist_order_normalize_dedupe(tmp_path: Path) -> None:
    payload = {
        "us_equities": [" msft ", "NVDA", "MSFT"],
        "us_etfs": ["SPY"],
        "crypto_proxy": [{"ticker": "mstr"}, {"symbol": ""}],
    }
    p = tmp_path / "uw.yaml"
    p.write_text(yaml.safe_dump(payload), encoding="utf-8")

    seq = extract_us_watchlist_symbols(payload)
    assert seq[:3] == ["msft", "NVDA", "MSFT"]

    tickers = load_us_watchlist_tickers(p)
    assert tickers == ["MSFT", "NVDA", "SPY", "MSTR"]


def test_repo_us_watchlist_file_loads() -> None:
    p = CONFIG_DIR / "us_watchlist.yaml"
    assert p.is_file()
    xs = load_us_watchlist_tickers()
    assert xs[0] == "MSFT"
    assert "GOOGL" in xs
    assert xs == sorted(set(xs), key=lambda s: xs.index(s))
