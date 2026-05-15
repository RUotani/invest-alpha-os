"""R6.11-F: US asset universe fixture / loader (no HTTP)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from invis_alpha_os.data.us_asset_universe import (
    US_ASSET_ENTRY_OK_KEYS,
    enabled_us_asset_symbols,
    index_us_asset_universe_by_symbol,
    load_us_asset_universe_json_file,
    parse_us_asset_universe_payload,
)

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "tests" / "fixtures" / "us_equities" / "us_asset_universe_minimal.json"


@pytest.fixture(autouse=True)
def _block_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("US asset universe tests must not use live HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)


def test_fixture_loads_and_matches_watchlist_count() -> None:
    u = load_us_asset_universe_json_file(FIX)
    assert u is not None
    assert u["schema_version"] == 1
    assert u["asset_count"] == 16
    assert len(u["assets"]) == 16


def test_entry_keys_contract() -> None:
    u = load_us_asset_universe_json_file(FIX)
    assert u is not None
    for row in u["assets"]:
        assert set(row.keys()) == US_ASSET_ENTRY_OK_KEYS


def test_spy_gldm_roles() -> None:
    u = load_us_asset_universe_json_file(FIX)
    assert u is not None
    by_sym = index_us_asset_universe_by_symbol(u)
    assert by_sym["SPY"]["asset_class"] == "us_etf"
    assert by_sym["SPY"]["role"] == "market_proxy"
    assert by_sym["GLDM"]["role"] == "metals_bridge"
    assert by_sym["MSFT"]["asset_class"] == "us_equity"


def test_enabled_symbols_order() -> None:
    u = load_us_asset_universe_json_file(FIX)
    assert u is not None
    syms = enabled_us_asset_symbols(u)
    assert syms[0] == "MSFT"
    assert "SPY" in syms
    assert len(syms) == 16


def test_parse_rejects_duplicate_symbol() -> None:
    raw = json.loads(FIX.read_text(encoding="utf-8"))
    dup = dict(raw)
    dup["assets"] = list(raw["assets"]) + [dict(raw["assets"][0])]
    assert parse_us_asset_universe_payload(dup) is None


def test_missing_file_returns_none() -> None:
    assert load_us_asset_universe_json_file(Path("/no/universe.json")) is None
