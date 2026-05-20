"""R7.0-C: US universe scanner config validation."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from invis_alpha_os.discovery.us_universe_scanner import FORBIDDEN_OUTPUT_TERMS, load_us_universe_spec
from invis_alpha_os.reports.symbol_display_names import display_name

REPO = Path(__file__).resolve().parents[1]
CFG = REPO / "config" / "us_universe_scanner_mvp.yaml"


def test_us_universe_config_exists_and_has_symbols() -> None:
    assert CFG.is_file()
    scope, symbols = load_us_universe_spec(CFG)
    assert scope == "curated_us_watchlist"
    assert len(symbols) >= 10
    assert len(symbols) == len(set(symbols))


def test_symbols_are_normalized_and_not_full_market_claim() -> None:
    data = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    text = CFG.read_text(encoding="utf-8").lower()
    assert "not full-market" in text or "not full market" in text
    for item in data["symbols"]:
        assert isinstance(item, dict)
        symbol = str(item["symbol"]).strip().upper()
        assert re.fullmatch(r"[A-Z0-9._-]{1,12}", symbol)


def test_display_names_resolve_for_core_symbols() -> None:
    _, symbols = load_us_universe_spec(CFG)
    for sym in ("MSFT", "NVDA", "AAPL", "SPY"):
        assert sym in symbols
        name = display_name(sym, market="us")
        assert name


def test_us_universe_config_has_no_recommendation_language() -> None:
    text = CFG.read_text(encoding="utf-8").lower()
    for term in FORBIDDEN_OUTPUT_TERMS:
        assert not re.search(rf"\b{re.escape(term)}\b", text)
