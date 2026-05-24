"""Tests for repeat signal summary grouping."""

from __future__ import annotations

from invis_alpha_os.product.weekly_us_observation import compute_repeat_signal_summary


def test_compute_repeat_signal_summary_first_seen_last_seen() -> None:
    rows = [
        {"symbol": "MSFT", "created_at": "2026-05-10T12:00:00+00:00", "momentum_label": "uptrend"},
        {"symbol": "MSFT", "created_at": "2026-05-17T12:00:00+00:00", "momentum_label": "uptrend"},
        {"symbol": "AAPL", "created_at": "2026-05-17T12:00:00+00:00", "momentum_label": "pullback"},
    ]
    summary = compute_repeat_signal_summary(rows)
    assert summary["repeat_symbol_count"] == 1
    msft = summary["repeat_by_symbol"][0]
    assert msft["symbol"] == "MSFT"
    assert msft["count"] == 2
    assert msft["first_seen"].startswith("2026-05-10")
    assert msft["last_seen"].startswith("2026-05-17")
    assert msft["consecutive_weeks"] >= 1
    assert "uptrend" in summary["repeat_by_label"]
