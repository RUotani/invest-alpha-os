"""Tests for centralized P3 monitoring CLI hints."""

from __future__ import annotations

from invis_alpha_os.product.p3_path_to_usable import (
    build_weekly_p3_path_preflight,
    format_weekly_p3_path_preflight_markdown,
)
from invis_alpha_os.product.us_forward_return_validation import (
    forward_validation_next_commands,
    p3_monitoring_next_commands,
)


def test_p3_monitoring_next_commands_includes_horizon_export() -> None:
    cmds = p3_monitoring_next_commands(horizon_rows=50)
    assert any("p3-path-to-usable" in c for c in cmds)
    assert any("p3-horizon-timeline" in c and "50" in c for c in cmds)
    assert any("forward-p3-status" in c for c in cmds)


def test_forward_validation_includes_p3_monitoring() -> None:
    cmds = forward_validation_next_commands()
    for cmd in p3_monitoring_next_commands():
        assert cmd in cmds


def test_weekly_p3_path_preflight_missing_log_returns_none(tmp_path) -> None:
    assert (
        build_weekly_p3_path_preflight(
            path_base=tmp_path,
            observation_path=tmp_path / "missing.jsonl",
        )
        is None
    )


def test_format_weekly_p3_path_preflight_markdown() -> None:
    md = format_weekly_p3_path_preflight_markdown(
        {
            "headline": "P3 path: matched=1/10",
            "dominant_path": "iso_week_rollover_then_l1",
            "matched_normal": 1,
            "rows_matched_all": 20,
            "samples_needed_for_usable": 9,
            "pending_horizon_rows": 16,
            "write_now_count": 0,
            "l1_status": "blocked",
            "requires_iso_week_rollover": True,
            "next_steps": ["wait"],
        }
    )
    assert "## P3 path preflight" in md
    assert "matched_normal: 1" in md
