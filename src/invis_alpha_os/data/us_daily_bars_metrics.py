"""US daily bars cache-only basic metrics (pure functions; no HTTP)."""

from __future__ import annotations

from typing import Any

from invis_alpha_os.signals.momentum import DailyBar, calculate_returns


def compute_us_daily_bars_basic_metrics(bars: list[DailyBar]) -> dict[str, Any]:
    """Summarize validated oldest-first ``DailyBar`` rows (no disk I/O)."""

    if not bars:
        return {
            "status": "invalid",
            "reason": "empty_bars",
            "bar_count": 0,
            "has_5d": False,
            "has_20d": False,
        }

    closes = [float(b["close"]) for b in bars]
    volumes = [float(b["volume"]) for b in bars]
    rets = calculate_returns(closes, horizons=[5, 20])
    r5 = rets.get(5)
    r20 = rets.get(20)

    total_return: float | None = None
    if len(closes) >= 2 and closes[0] != 0:
        total_return = (closes[-1] / closes[0]) - 1.0

    return {
        "status": "ok",
        "reason": None,
        "bar_count": len(bars),
        "first_date": bars[0]["date"],
        "last_date": bars[-1]["date"],
        "latest_date": bars[-1]["date"],
        "last_close": closes[-1],
        "last_volume": volumes[-1],
        "total_return": total_return,
        "return_5d": r5,
        "return_20d": r20,
        "has_5d": r5 is not None,
        "has_20d": r20 is not None,
    }
