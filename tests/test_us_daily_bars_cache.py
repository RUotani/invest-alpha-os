"""Main R: US daily bars cache skeleton (sanitized OHLCV only)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from invis_alpha_os.data import us_daily_bars_cache as usc
from invis_alpha_os.data.us_daily_bars_cache import (
    load_us_daily_bars_cache,
    save_us_daily_bars_cache,
    try_load_cached_us_daily_bars,
    us_daily_bars_cache_path,
)


@pytest.fixture()
def uc_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(usc, "OUTPUTS_DIR", tmp_path)
    return tmp_path


def test_us_daily_bars_cache_paths_accept_tickers(uc_root: Path) -> None:
    for sym in ("MSFT", "GOOGL", "BRK.B"):
        assert "us_daily_bars" in str(us_daily_bars_cache_path(sym))


def test_us_daily_bars_cache_rejects_unsafe_symbol(uc_root: Path) -> None:
    with pytest.raises(ValueError, match="invalid US symbol"):
        us_daily_bars_cache_path("../x")


def test_us_daily_bars_roundtrip_and_refuse_empty(uc_root: Path) -> None:
    rows = [{"date": "2024-01-02", "open": 1, "high": 1.1, "low": 0.9, "close": 1.02, "volume": 1000}]
    save_us_daily_bars_cache(
        "msft",
        rows,
        asset_class="us_equity",
        source="manual_or_future_provider",
        fetched_at="2026-01-01T00:00:00+00:00",
    )

    got = load_us_daily_bars_cache("MSFT")
    assert got is not None
    bars, meta = got
    assert len(bars) == 1
    assert meta["asset_class"] == "us_equity"

    assert try_load_cached_us_daily_bars("GOOGL") is None

    with pytest.raises(ValueError, match="empty"):
        save_us_daily_bars_cache("NVDA", [])


def test_save_rejects_raw_response_literal_in_source(uc_root: Path) -> None:
    rows = [{"date": "2024-01-02", "open": 1, "high": 1.1, "low": 0.9, "close": 1, "volume": 1}]
    with pytest.raises(ValueError, match="ambiguous|forbidden"):
        save_us_daily_bars_cache(
            "AAPL",
            rows,
            source="upstream raw_response stripped",
            asset_class="us_equity",
        )


def test_load_rejects_extra_root_keys(uc_root: Path) -> None:
    p = us_daily_bars_cache_path("COIN")
    p.parent.mkdir(parents=True)
    blob = {
        "schema_version": 1,
        "symbol": "COIN",
        "source": "manual_or_future_provider",
        "fetched_at": None,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "bar_count": 1,
        "bars": [{"date": "2024-01-02", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}],
        "api_key": "***",
    }
    p.write_text(json.dumps(blob), encoding="utf-8")
    assert load_us_daily_bars_cache("COIN") is None
