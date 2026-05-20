"""R6.10-E: US daily bars cache-only basic metrics (no HTTP)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from invis_alpha_os.data.us_daily_bars_cache import load_us_daily_bars_json_file
from invis_alpha_os.data.us_daily_bars_metrics import (
    compute_us_daily_bars_basic_metrics,
    compute_volume_status,
)
from invis_alpha_os.signals.momentum import DailyBar

REPO = Path(__file__).resolve().parents[1]
FIX_MINIMAL = REPO / "tests" / "fixtures" / "us_equities" / "minimal_msft_envelope.json"


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
        raise AssertionError("US metrics tests must not use live HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)


def test_empty_bars_invalid() -> None:
    m = compute_us_daily_bars_basic_metrics([])
    assert m["status"] == "invalid"
    assert m["reason"] == "empty_bars"
    assert m["has_5d"] is False
    assert m["has_20d"] is False


def test_minimal_fixture_insufficient_horizons() -> None:
    loaded = load_us_daily_bars_json_file(FIX_MINIMAL)
    assert loaded is not None
    bars, _meta = loaded
    m = compute_us_daily_bars_basic_metrics(bars)
    assert m["status"] == "ok"
    assert m["bar_count"] == 2
    assert m["has_5d"] is False
    assert m["has_20d"] is False
    assert m["return_5d"] is None
    assert m["total_return"] is not None


def test_25_bars_return_5d_and_20d() -> None:
    bars = _synthetic_bars(25, base=100.0, step=1.0)
    m = compute_us_daily_bars_basic_metrics(bars)
    assert m["status"] == "ok"
    assert m["has_5d"] is True
    assert m["has_20d"] is True
    assert m["return_5d"] == pytest.approx(124.0 / 119.0 - 1.0)
    assert m["return_20d"] == pytest.approx(124.0 / 104.0 - 1.0)
    assert m["total_return"] == pytest.approx(0.24)


def test_zero_first_close_total_return_none() -> None:
    bars = _synthetic_bars(10)
    bars[0] = {**bars[0], "close": 0.0}
    m = compute_us_daily_bars_basic_metrics(bars)
    assert m["status"] == "ok"
    assert m["total_return"] is None


def test_metrics_from_loaded_fixture_file() -> None:
    loaded = load_us_daily_bars_json_file(FIX_MINIMAL)
    assert loaded is not None
    bars, meta = loaded
    m = compute_us_daily_bars_basic_metrics(bars)
    assert m["status"] == "ok"
    assert m["first_date"] == "2024-01-02"
    assert m["last_date"] == "2024-01-03"
    assert meta["symbol"] == "MSFT"


def test_return_1d_present_with_two_bars() -> None:
    bars = _synthetic_bars(2, base=100.0, step=1.0)
    m = compute_us_daily_bars_basic_metrics(bars)
    assert m["has_1d"] is True
    assert m["return_1d"] == pytest.approx(101.0 / 100.0 - 1.0)


def test_return_1d_none_with_one_bar() -> None:
    bars = _synthetic_bars(1)
    m = compute_us_daily_bars_basic_metrics(bars)
    assert m["has_1d"] is False
    assert m["return_1d"] is None


def test_volume_status_high() -> None:
    bars = _synthetic_bars(10, base=100.0, step=0.0)
    for i in range(9):
        bars[i] = {**bars[i], "volume": 1000.0}
    bars[-1] = {**bars[-1], "volume": 5000.0}
    assert compute_volume_status([float(b["volume"]) for b in bars]) == "high"


def test_volume_status_low() -> None:
    bars = _synthetic_bars(10, base=100.0, step=0.0)
    for i in range(9):
        bars[i] = {**bars[i], "volume": 1000.0}
    bars[-1] = {**bars[-1], "volume": 100.0}
    assert compute_volume_status([float(b["volume"]) for b in bars]) == "low"


def test_volume_status_normal() -> None:
    bars = _synthetic_bars(10, base=100.0, step=0.0)
    for i in range(9):
        bars[i] = {**bars[i], "volume": 1000.0}
    bars[-1] = {**bars[-1], "volume": 1000.0}
    assert compute_volume_status([float(b["volume"]) for b in bars]) == "normal"


def test_volume_status_unknown_insufficient_prior() -> None:
    bars = _synthetic_bars(5)
    assert compute_volume_status([float(b["volume"]) for b in bars]) == "unknown"


def test_volume_status_unknown_zero_average() -> None:
    bars = _synthetic_bars(8)
    for b in bars:
        b["volume"] = 0.0
    bars[-1]["volume"] = 100.0
    assert compute_volume_status([float(b["volume"]) for b in bars]) == "unknown"
