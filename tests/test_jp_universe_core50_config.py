"""R7.0-B2: JP Core50 universe config validation."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from invis_alpha_os.discovery.jp_universe_scanner import FORBIDDEN_OUTPUT_TERMS, load_universe_spec
from invis_alpha_os.reports.symbol_display_names import display_name

REPO = Path(__file__).resolve().parents[1]
CORE50 = REPO / "config" / "jp_universe_core50.yaml"


def test_core50_config_exists_and_has_fifty_symbols() -> None:
    assert CORE50.is_file()
    scope, codes = load_universe_spec(CORE50)
    assert scope == "curated_liquid_cross_sector_sample"
    assert len(codes) >= 50
    assert len(codes) == len(set(codes))


def test_core50_symbols_are_strings_and_not_full_market_claim() -> None:
    data = yaml.safe_load(CORE50.read_text(encoding="utf-8"))
    text = CORE50.read_text(encoding="utf-8").lower()
    assert "not full-market" in text or "not full market" in text
    scope = str(data.get("universe_scope", ""))
    assert "curated" in scope
    for item in data["symbols"]:
        assert isinstance(item, dict)
        code = str(item["code"]).strip().upper()
        assert re.fullmatch(r"[0-9A-Z]{4}", code)


def test_core50_display_names_resolve_for_key_symbols() -> None:
    _, codes = load_universe_spec(CORE50)
    for code in ("7203", "8035", "5802", "6501"):
        assert code in codes
        name = display_name(code, market="jp")
        assert name != code or code == "285A"


def test_core50_config_has_no_recommendation_language() -> None:
    text = CORE50.read_text(encoding="utf-8").lower()
    for term in FORBIDDEN_OUTPUT_TERMS:
        assert not re.search(rf"\b{re.escape(term)}\b", text)
