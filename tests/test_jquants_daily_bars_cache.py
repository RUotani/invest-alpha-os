"""Main F: sanitized J-Quants daily bars cache and report labeling (no live HTTP)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from invis_alpha_os.data.jquants_daily_bars_cache import (
    jquants_daily_bars_cache_path,
    load_jquants_daily_bars_cache,
    save_jquants_daily_bars_cache,
)
from invis_alpha_os.reports.momentum_daily import render_momentum_signals_mixed_section


def test_jquants_daily_bars_cache_roundtrip_no_secrets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    rows = [{"date": "2024-01-01", "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "volume": 100.0}]
    path = save_jquants_daily_bars_cache("7011", rows, source="unit", fetched_at="2026-01-01T00:00:00Z")
    text = path.read_text().lower()
    assert "api_key" not in text
    assert "raw_response" not in text
    assert "x-api-key" not in text
    loaded = load_jquants_daily_bars_cache("7011")
    assert loaded is not None
    bars, meta = loaded
    assert len(bars) == 1
    assert meta.get("source") == "unit"


def test_jquants_daily_bars_cache_path_rejects_unsafe_code() -> None:
    with pytest.raises(ValueError):
        jquants_daily_bars_cache_path("../7011")


def test_load_cache_invalid_code_returns_none() -> None:
    assert load_jquants_daily_bars_cache("BAD") is None


def test_jquants_daily_bars_cache_save_refuses_empty_list() -> None:
    with pytest.raises(ValueError, match="refuse to write empty"):
        save_jquants_daily_bars_cache("7011", [], source="x", fetched_at="2026-01-01T00:00:00Z")


def test_jquants_daily_bars_cache_file_has_no_secret_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    rows = [{"date": "2024-01-01", "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}]
    path = save_jquants_daily_bars_cache(
        "7011",
        rows,
        source="jquants_v2_equities_bars_daily",
        fetched_at="2026-01-01T00:00:00Z",
    )
    low = path.read_text().lower()
    assert "api_key" not in low
    assert "raw_response" not in low
    assert "x-api-key" not in low


def test_render_momentum_section_shows_cache_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(
        "invis_alpha_os.reports.momentum_daily.load_jp_watchlist_tickers",
        lambda: ["7011"],
    )
    cache_dir = tmp_path / "market_data" / "jquants_daily_bars"
    cache_dir.mkdir(parents=True)
    bars = []
    for i in range(80):
        c = 1000.0 + i * 0.1
        bars.append(
            {
                "date": f"2024-01-{(i % 28) + 1:02d}",
                "open": c,
                "high": c + 1.0,
                "low": c - 1.0,
                "close": c,
                "volume": 5000.0,
            }
        )
    payload = {
        "schema_version": 1,
        "code": "7011",
        "source": "jquants_v2_equities_bars_daily",
        "fetched_at": "2026-01-01T00:00:00+00:00",
        "generated_at": None,
        "bar_count": len(bars),
        "bars": bars,
    }
    (cache_dir / "7011.json").write_text(json.dumps(payload), encoding="utf-8")

    md = render_momentum_signals_mixed_section()
    assert "## Momentum Signals — Mixed / System Validation" in md
    assert "**Bars source:**" in md
    assert "cache" in md.lower()
    assert "| Bars src |" in md
    assert "| cache |" in md
