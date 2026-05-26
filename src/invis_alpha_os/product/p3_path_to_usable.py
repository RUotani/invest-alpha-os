"""Unified read-only P3 path to usable (US forward normal mode; docs/154/161)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import OUTPUTS_DIR, ROOT_DIR


def build_p3_path_to_usable(
    *,
    matched_normal: int,
    thin_threshold: int,
    p3_us_forward_summary: dict[str, Any] | None = None,
    p3_weekly_write_plan: dict[str, Any] | None = None,
    p3_horizon_timeline: dict[str, Any] | None = None,
    stall_diagnosis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Single machine-readable view of paths A (horizon) + B (new ISO week writes)."""

    summary = p3_us_forward_summary or {}
    plan = p3_weekly_write_plan or {}
    timeline = p3_horizon_timeline or {}
    stall = stall_diagnosis or {}
    needed = int(summary.get("samples_needed_for_usable") or max(0, thin_threshold - matched_normal))
    l1_gate = plan.get("l1_gate") or {}
    rollover = plan.get("iso_week_rollover") or l1_gate.get("iso_week_rollover") or {}
    dc = summary.get("dedupe_counterfactual") or stall.get("dedupe_counterfactual") or {}
    hm = stall.get("horizon_maturity") or summary.get("horizon_maturity") or {}

    path_a = {
        "label": "horizon_maturation_in_existing_log",
        "pending_rows": timeline.get("pending_horizon_rows", hm.get("will_be_matchable_after_date_rows", 0)),
        "min_sessions_until": timeline.get("min_sessions_until", hm.get("min_sessions_until")),
        "median_sessions_until": timeline.get("median_sessions_until", hm.get("median_sessions_until")),
        "projected_matched_at_min_sessions": timeline.get("projected_matched_at_min_sessions"),
        "projected_matched_at_median_sessions": timeline.get("projected_matched_at_median_sessions"),
        "sessions_until_histogram": timeline.get("sessions_until_histogram", {}),
        "requires_l1": False,
        "requires_cache_extension": True,
    }
    path_b = {
        "label": "new_symbol_iso_week_writes",
        "write_now_count": plan.get("write_now_count", 0),
        "skip_duplicate_count": plan.get("skip_duplicate_count", 0),
        "l1_status": l1_gate.get("status"),
        "l1_recommended": l1_gate.get("l1_recommended"),
        "days_until_earliest_rollover": rollover.get("days_until_earliest_rollover"),
        "earliest_next_iso_week_start": rollover.get("earliest_next_iso_week_start"),
        "projected_write_now_symbols_at_rollover": rollover.get("projected_write_now_symbols_at_rollover", 0),
        "requires_l1": bool(l1_gate.get("l1_recommended")),
        "requires_iso_week_rollover": (plan.get("write_now_count", 0) == 0 and plan.get("skip_duplicate_count", 0) > 0),
    }

    gaps: list[str] = []
    if path_a.get("projected_matched_at_median_sessions") is not None:
        gap_a = thin_threshold - int(path_a["projected_matched_at_median_sessions"])
        if gap_a > 0:
            gaps.append(f"horizon_path_short_by_{gap_a}_vs_usable_even_after_median_sessions")
    if path_b.get("write_now_count", 0) == 0:
        gaps.append("no_new_iso_week_rows_available_now")
    if int(dc.get("duplicate_rows_suppressed") or 0) > 0:
        gaps.append(f"duplicate_rows_in_log={dc.get('duplicate_rows_suppressed')} (ineffective for P3)")

    dominant = "horizon_maturation"
    if path_b.get("requires_iso_week_rollover") and not path_b.get("l1_recommended"):
        dominant = "iso_week_rollover_then_l1"
    elif path_a.get("pending_rows", 0) == 0 and path_b.get("write_now_count", 0) == 0:
        dominant = "blocked"

    headline = (
        f"P3 path: matched={matched_normal}/{thin_threshold} need={needed}; "
        f"dominant={dominant}; path_a_pending={path_a.get('pending_rows', 0)} "
        f"path_b_write_now={path_b.get('write_now_count', 0)}"
    )

    next_steps: list[str] = []
    if path_b.get("l1_recommended"):
        next_steps.append(str(l1_gate.get("next_action") or "Run L1 with --skip-duplicate-iso-week"))
    elif path_b.get("requires_iso_week_rollover") and rollover.get("l1_unblock_hint"):
        next_steps.append(str(rollover["l1_unblock_hint"]))
    if path_a.get("pending_rows", 0) > 0:
        next_steps.append(
            "Wait for cache horizon on existing log rows; re-run validate forward-p3-status weekly"
        )
    if not next_steps:
        next_steps.append("validate p3-path-to-usable --format markdown")

    return {
        "schema_version": 1,
        "matched_normal": matched_normal,
        "thin_threshold": thin_threshold,
        "samples_needed_for_usable": needed,
        "us_p3_usable": matched_normal >= thin_threshold,
        "dominant_path": dominant,
        "headline": headline,
        "path_a_horizon_maturation": path_a,
        "path_b_new_iso_week_writes": path_b,
        "gaps_to_usable": gaps,
        "dedupe_counterfactual_matched": dc.get("matched_first_per_week_only"),
        "why_matched_stuck_headline": summary.get("why_matched_stuck_headline")
        or (stall.get("why_matched_stuck") or {}).get("headline"),
        "next_steps": next_steps[:6],
        "observation_only": True,
    }


def format_p3_path_to_usable_markdown(path: dict[str, Any]) -> str:
    lines = [
        "## P3 path to usable (read-only)",
        "",
        f"- {path.get('headline', '')}",
        f"- dominant_path: {path.get('dominant_path', '')}",
        f"- samples_needed_for_usable: {path.get('samples_needed_for_usable', 0)}",
    ]
    pa = path.get("path_a_horizon_maturation") or {}
    pb = path.get("path_b_new_iso_week_writes") or {}
    lines.extend(
        [
            "",
            "### Path A — horizon maturation (existing log)",
            f"- pending_rows: {pa.get('pending_rows', 0)}",
            f"- min_sessions_until: {pa.get('min_sessions_until')}",
            f"- projected_matched_at_median_sessions: {pa.get('projected_matched_at_median_sessions')}",
            f"- requires_l1: {pa.get('requires_l1')}",
        ]
    )
    hist = pa.get("sessions_until_histogram") or {}
    if hist:
        lines.append(f"- sessions_until_histogram: {hist}")
    lines.extend(
        [
            "",
            "### Path B — new ISO week writes",
            f"- write_now_count: {pb.get('write_now_count', 0)}",
            f"- skip_duplicate_count: {pb.get('skip_duplicate_count', 0)}",
            f"- l1_status: {pb.get('l1_status')}",
            f"- days_until_earliest_rollover: {pb.get('days_until_earliest_rollover')}",
            f"- requires_iso_week_rollover: {pb.get('requires_iso_week_rollover')}",
        ]
    )
    gaps = path.get("gaps_to_usable") or []
    if gaps:
        lines.append("")
        lines.append("### Gaps to usable")
        for g in gaps:
            lines.append(f"- {g}")
    steps = path.get("next_steps") or []
    if steps:
        lines.append("")
        lines.append("### Next steps")
        for step in steps:
            lines.append(f"- {step}")
    return "\n".join(lines)


def _slim_weekly_write_plan(plan: dict[str, Any] | None) -> dict[str, Any]:
    plan = plan or {}
    l1 = plan.get("l1_gate") or {}
    rollover = plan.get("iso_week_rollover") or l1.get("iso_week_rollover") or {}
    return {
        "write_now_count": plan.get("write_now_count", 0),
        "skip_duplicate_count": plan.get("skip_duplicate_count", 0),
        "l1_status": l1.get("status"),
        "l1_recommended": l1.get("l1_recommended"),
        "days_until_earliest_rollover": rollover.get("days_until_earliest_rollover"),
        "earliest_next_iso_week_start": rollover.get("earliest_next_iso_week_start"),
    }


def build_p3_path_to_usable_bundle(
    *,
    path_base: Path | None = None,
    observation_path: Path | None = None,
    cache_dir: Path | None = None,
    horizon_timeline_max_rows: int = 50,
) -> dict[str, Any]:
    """Focused read-only bundle: path + expanded horizon timeline (no full P3 aggregate)."""

    from invis_alpha_os.product.forward_p3_status import build_forward_p3_status_bundle
    from invis_alpha_os.product.us_forward_p3_stall_diagnosis import (
        compute_us_forward_p3_stall_diagnosis,
    )

    root = path_base or ROOT_DIR
    obs = observation_path or (OUTPUTS_DIR / "observation_log" / "observation_log.jsonl")
    cache = cache_dir or (OUTPUTS_DIR / "market_data" / "us_daily_bars")
    export_limit = max(16, int(horizon_timeline_max_rows))

    full = build_forward_p3_status_bundle(
        path_base=root,
        observation_path=obs,
        cache_dir=cache,
    )
    path = dict(full.get("p3_path_to_usable") or {})
    us_forward = full.get("us_forward") or {}
    us_matched = int(us_forward.get("rows_matched") or 0)
    if not path:
        from invis_alpha_os.product.us_forward_return_validation import THIN_SAMPLE_THRESHOLD

        path = build_p3_path_to_usable(
            matched_normal=us_matched,
            thin_threshold=THIN_SAMPLE_THRESHOLD,
            p3_us_forward_summary=full.get("p3_us_forward_summary"),
            p3_weekly_write_plan=full.get("p3_weekly_write_plan"),
            p3_horizon_timeline=full.get("p3_horizon_timeline"),
            stall_diagnosis=full.get("p3_stall_diagnosis"),
        )
    timeline = dict(full.get("p3_horizon_timeline") or {})
    existing_rows = len(timeline.get("timeline_rows") or [])
    if export_limit > existing_rows:
        try:
            stall = compute_us_forward_p3_stall_diagnosis(
                observation_path=obs,
                cache_dir=cache,
                horizon_timeline_max_rows=export_limit,
            )
            timeline = dict(stall.get("p3_horizon_timeline") or timeline)
        except (FileNotFoundError, ValueError):
            pass

    return {
        "schema_version": 1,
        "observation_only": True,
        "p3_path_to_usable": path,
        "p3_horizon_timeline": timeline,
        "p3_weekly_write_plan_summary": _slim_weekly_write_plan(
            full.get("p3_weekly_write_plan")
        ),
        "us_forward_matched_normal": int(
            us_forward.get("rows_matched") or path.get("matched_normal") or 0
        ),
        "us_forward_sample_quality": us_forward.get("sample_quality"),
        "horizon_timeline_max_rows": export_limit,
        "related_commands": [
            ".venv/bin/python -m invis_alpha_os.cli.main validate forward-p3-status --format markdown",
            ".venv/bin/python -m invis_alpha_os.cli.main validate post-refresh-smoke --format markdown",
        ],
    }


def format_p3_path_to_usable_bundle_markdown(bundle: dict[str, Any]) -> str:
    path = bundle.get("p3_path_to_usable") or {}
    parts = [format_p3_path_to_usable_markdown(path)]
    timeline = bundle.get("p3_horizon_timeline") or {}
    if timeline:
        from invis_alpha_os.product.us_forward_p3_stall_diagnosis import (
            format_p3_horizon_match_timeline_markdown,
        )

        parts.extend(["", format_p3_horizon_match_timeline_markdown(timeline)])
    return "\n".join(parts)
