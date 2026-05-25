"""Tests for weekly_trend P2 supplemental metrics."""

from __future__ import annotations

import json
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


def test_research_checklist_forward_fresh_log_category(tmp_path: Path) -> None:
    from invis_alpha_os.observation.us_signal_note import build_us_signal_observation_note
    from invis_alpha_os.product.weekly_us_observation import summarize_us_observation_log

    obs = tmp_path / "obs.jsonl"
    note = build_us_signal_observation_note(
        {"status": "ok", "momentum_label": "neutral", "last_date": "2026-05-24"}
    )
    obs.write_text(
        '{"id":"1","created_at":"2026-05-25T12:00:00+00:00","symbol":"MSFT","note":'
        + json.dumps(note)
        + ',"evidence_ids":[],"tags":[]}\n',
        encoding="utf-8",
    )
    summary = summarize_us_observation_log(
        obs,
        forward_sample_quality={
            "status": "empty",
            "reason": "observation events are too recent for forward windows",
            "skip_pattern": "fresh_log",
        },
    )
    categories = {c.get("category") for c in summary.get("research_checklist") or []}
    assert "forward_fresh_log" in categories


def test_post_refresh_hints_light(tmp_path: Path) -> None:
    from invis_alpha_os.product.post_p10_refresh_smoke import build_post_refresh_hints_light

    obs = tmp_path / "obs.jsonl"
    obs.write_text("", encoding="utf-8")
    hints = build_post_refresh_hints_light(path_base=tmp_path, observation_path=obs)
    assert "docs_163_hard_pass" in hints
    assert hints["observation_only"] is True
