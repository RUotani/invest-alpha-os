"""R6.11-B: US cache-only signals pure helper (no HTTP)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from invis_alpha_os.data.us_cache_signals import (
    US_CACHE_SIGNAL_ROW_OK_KEYS,
    compute_us_cache_signal_row,
    load_us_cache_signal_row_from_json_file,
)
from invis_alpha_os.data.us_daily_bars_cache import load_us_daily_bars_json_file
from invis_alpha_os.signals.momentum import DailyBar

REPO = Path(__file__).resolve().parents[1]
FIX_MINIMAL = REPO / "tests" / "fixtures" / "us_equities" / "minimal_msft_envelope.json"
FIX_25 = REPO / "tests" / "fixtures" / "us_equities" / "msft_25bars_metrics_envelope.json"


def _synthetic_bars(n: int, *, base: float = 100.0, step: float = 1.0) -> list[DailyBar]:
    bars: list[DailyBar] = []
    d = date(2024, 1, 2)
    for i in range(n):
        c = base + step * i
        bars.append(
            {
                "date": d.isoformat(),
                "open": c,
                "high": c + 1.0,
                "low": c - 1.0,
                "close": c,
                "volume": 1000.0 + float(i),
            }
        )
        d += timedelta(days=1)
    return bars


@pytest.fixture(autouse=True)
def _block_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("US cache signals tests must not use live HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)


def test_empty_bars_invalid() -> None:
    row = compute_us_cache_signal_row([], symbol="MSFT")
    assert row["status"] == "invalid"
    assert row["reason"] == "empty_bars"
    assert row["live_http"] is False
    assert row["source"] == "cache_only"


def test_minimal_fixture_skipped_insufficient_bars() -> None:
    loaded = load_us_daily_bars_json_file(FIX_MINIMAL)
    assert loaded is not None
    bars, meta = loaded
    row = compute_us_cache_signal_row(bars, symbol=meta["symbol"])
    assert set(row.keys()) == US_CACHE_SIGNAL_ROW_OK_KEYS
    assert row["status"] == "skipped_insufficient_bars"
    assert row["reason"] == "insufficient_bars_for_5d"
    assert row["has_5d"] is False
    assert row["momentum_label"] is None


def test_25bar_fixture_uptrend_aligned() -> None:
    row = load_us_cache_signal_row_from_json_file(FIX_25)
    assert row is not None
    assert set(row.keys()) == US_CACHE_SIGNAL_ROW_OK_KEYS
    assert row["status"] == "ok"
    assert row["symbol"] == "MSFT"
    assert row["momentum_label"] == "uptrend_aligned"
    assert row["return_5d"] == pytest.approx(124.0 / 119.0 - 1.0)
    assert row["return_20d"] == pytest.approx(124.0 / 104.0 - 1.0)
    assert row["total_return"] == pytest.approx(0.24)


def test_pullback_short_label() -> None:
    bars = _synthetic_bars(10, base=100.0, step=1.0)
    bars[-1] = {**bars[-1], "close": 95.0}
    row = compute_us_cache_signal_row(bars, symbol="TEST")
    assert row["status"] == "ok"
    assert row["has_5d"] is True
    assert row["momentum_label"] == "pullback_short"


def test_load_from_file_symbol_mismatch_returns_none() -> None:
    assert load_us_cache_signal_row_from_json_file(FIX_25, expect_symbol="AAPL") is None
