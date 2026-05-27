"""Tests for unified P3 path to usable (read-only)."""

from __future__ import annotations

from invis_alpha_os.product.p3_path_to_usable import (
    build_p3_path_to_usable,
    format_p3_path_to_usable_markdown,
)


def test_format_p3_path_weekly_one_liner() -> None:
    from invis_alpha_os.product.p3_path_to_usable import format_p3_path_weekly_one_liner

    line = format_p3_path_weekly_one_liner(
        {
            "matched_normal": 1,
            "samples_needed_for_usable": 9,
            "dominant_path": "iso_week_rollover_then_l1",
            "write_now_count": 0,
            "rows_matched_all": 20,
        }
    )
    assert line.startswith("- p3_path:")
    assert "matched_normal=1/10" in line
    assert "rows_matched_all=20" in line


def test_build_p3_path_to_usable_iso_week_blocked() -> None:
    path = build_p3_path_to_usable(
        matched_normal=1,
        thin_threshold=10,
        p3_us_forward_summary={"samples_needed_for_usable": 9, "why_matched_stuck_headline": "stuck"},
        p3_weekly_write_plan={
            "write_now_count": 0,
            "skip_duplicate_count": 16,
            "l1_gate": {
                "status": "blocked_duplicate_iso_week",
                "l1_recommended": False,
            },
            "iso_week_rollover": {
                "days_until_earliest_rollover": 3,
                "earliest_next_iso_week_start": "2026-05-29",
                "l1_unblock_hint": "wait for rollover",
            },
        },
        p3_horizon_timeline={
            "pending_horizon_rows": 16,
            "projected_matched_at_median_sessions": 5,
            "sessions_until_histogram": {"1-5": 2, "6-20": 14},
        },
    )
    assert path["samples_needed_for_usable"] == 9
    assert path["dominant_path"] == "iso_week_rollover_then_l1"
    assert path["path_a_horizon_maturation"]["pending_rows"] == 16
    assert path["path_b_new_iso_week_writes"]["write_now_count"] == 0
    md = format_p3_path_to_usable_markdown(path)
    assert "## P3 path to usable" in md
    assert "Path A" in md
    assert "Path B" in md


def test_build_p3_path_to_usable_l1_ready() -> None:
    path = build_p3_path_to_usable(
        matched_normal=1,
        thin_threshold=10,
        p3_weekly_write_plan={
            "write_now_count": 4,
            "skip_duplicate_count": 12,
            "l1_gate": {"status": "ready", "l1_recommended": True, "next_action": "run L1"},
        },
        p3_horizon_timeline={"pending_horizon_rows": 0},
    )
    assert path["dominant_path"] == "horizon_maturation"
    assert path["path_b_new_iso_week_writes"]["requires_l1"] is True


def test_build_p3_path_to_usable_rollover_passed_still_blocked() -> None:
    path = build_p3_path_to_usable(
        matched_normal=1,
        thin_threshold=10,
        p3_weekly_write_plan={
            "write_now_count": 0,
            "skip_duplicate_count": 16,
            "l1_gate": {
                "status": "blocked_duplicate_iso_week",
                "l1_recommended": False,
            },
            "iso_week_rollover": {
                "days_until_earliest_rollover": 0,
                "days_until_earliest_rollover_note": "0 = earliest_next_iso_week_start reached or passed",
                "rollover_passed": True,
                "earliest_next_iso_week_start": "2024-04-15",
                "l1_unblock_hint": (
                    "ISO week rollover date has passed but write_now_count=0: planned writes still "
                    "duplicate existing symbol×ISO week rows or cache/as_of has not advanced"
                ),
            },
        },
        p3_horizon_timeline={"pending_horizon_rows": 16},
    )
    assert path["dominant_path"] == "rollover_passed_cache_or_duplicate_blocked"
    pb = path["path_b_new_iso_week_writes"]
    assert pb["rollover_passed_write_still_blocked"] is True
    assert pb["requires_iso_week_rollover"] is False
    md = format_p3_path_to_usable_markdown(path)
    assert "rollover_passed_write_still_blocked" in md
    assert "days_until_earliest_rollover_note" in md
