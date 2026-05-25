"""Tests for weekly_trend P2 supplemental metrics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from invis_alpha_os.product.weekly_us_observation import compute_us_signal_weekly_trend


def test_weekly_trend_prior_week_bulk_caveat() -> None:
    now = datetime.now(timezone.utc)
    prior_week = now - timedelta(days=10)
    latest_week = now - timedelta(days=2)
    rows = []
    for _ in range(40):
        rows.append({"created_at": prior_week.isoformat()})
    for _ in range(8):
        rows.append({"created_at": latest_week.isoformat()})
    trend = compute_us_signal_weekly_trend(rows)
    assert trend["status"] == "declining"
    assert trend.get("calendar_week_caveat") == "prior_week_bulk"
    assert trend.get("p2_supplemental") == "active"
    assert trend.get("trailing_7d_count", 0) >= 4


def test_post_refresh_hints_light(tmp_path: Path) -> None:
    from invis_alpha_os.product.post_p10_refresh_smoke import build_post_refresh_hints_light

    obs = tmp_path / "obs.jsonl"
    obs.write_text("", encoding="utf-8")
    hints = build_post_refresh_hints_light(path_base=tmp_path, observation_path=obs)
    assert "docs_163_hard_pass" in hints
    assert hints["observation_only"] is True
