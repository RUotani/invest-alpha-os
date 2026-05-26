"""Portfolio observation readiness rubric (docs/154; read-only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from invis_alpha_os.config.loader import load_yaml
from invis_alpha_os.config.paths import OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.product.portfolio_observation_summary import build_portfolio_observation_summary
from invis_alpha_os.product.us_forward_return_validation import compute_us_forward_returns
from invis_alpha_os.product.weekly_us_observation import (
    compute_us_signal_weekly_trend,
    summarize_us_observation_log,
)

_SUGGESTED_PERCENT: dict[str, int | None] = {
    "P0": 25,
    "P0+P1": 40,
    "P0-P2": 55,
    "P0-P3": 70,
    "P4": None,
}

_MILESTONE_META: dict[str, dict[str, str]] = {
    "P0": {
        "label": "Shadow JSONL + CLI",
        "operator_hint": "snapshot portfolio-observation-summary exit 0",
    },
    "P1": {
        "label": "Observation linkage",
        "operator_hint": "shadow positions with resolved evidence links",
    },
    "P2": {
        "label": "Weekly log sustained",
        "operator_hint": "us_signal_rows grow week-over-week",
    },
    "P3": {
        "label": "Forward usable",
        "operator_hint": "validate us-forward-returns sample_quality=usable (normal mode)",
    },
}


def portfolio_p2_weekly_hint(weekly_trend: dict[str, Any]) -> str | None:
    """Read-only hint for P2 milestone when calendar week vs trailing_7d diverge."""

    status = str(weekly_trend.get("status") or "")
    supplemental = str(weekly_trend.get("p2_supplemental") or "")
    trailing = int(weekly_trend.get("trailing_7d_count") or 0)
    if status == "growing":
        return None
    if supplemental == "active" and trailing > 0:
        return (
            f"P2 supplemental: trailing_7d={trailing} active while calendar_week={status}; "
            "accumulate more ISO weeks (docs/150)"
        )
    if status == "insufficient_history":
        return "P2 blocked: insufficient ISO week history; approved weekly writes needed"
    if status in {"declining", "flat"}:
        return f"P2 blocked: weekly_trend={status} (latest vs prior ISO week)"
    return None


def _load_portfolio_human_acceptance(path_base: Path) -> dict[str, Any] | None:
    candidate = path_base / "config" / "portfolio_observation_acceptance.yaml"
    if not candidate.is_file():
        return None
    data = load_yaml(candidate)
    if isinstance(data, dict) and data.get("human_accepted_percent") is not None:
        return data
    return None


def _milestone(
    *,
    milestone_id: str,
    passed: bool,
    status: str,
    detail: str,
) -> dict[str, Any]:
    meta = _MILESTONE_META.get(milestone_id, {})
    return {
        "id": milestone_id,
        "label": meta.get("label", milestone_id),
        "operator_hint": meta.get("operator_hint", ""),
        "passed": passed,
        "status": status,
        "detail": detail,
    }


def evaluate_portfolio_readiness(
    *,
    path_base: Path | None = None,
    observation_path: Path | None = None,
    shadow_path: Path | None = None,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Evaluate docs/154 P0–P3 milestones (read-only; does not update STATE %)."""

    root = path_base or ROOT_DIR
    obs = observation_path or (OUTPUTS_DIR / "observation_log" / "observation_log.jsonl")
    cache = cache_dir or (OUTPUTS_DIR / "market_data" / "us_daily_bars")

    portfolio = build_portfolio_observation_summary(
        path_base=root,
        observation_path=obs,
        shadow_path=shadow_path,
    )
    us = summarize_us_observation_log(obs)
    weekly_trend = compute_us_signal_weekly_trend(list(us.get("rows") or []))

    forward: dict[str, Any] | None = None
    if obs.is_file() and int(us.get("us_signal_rows") or 0) > 0:
        try:
            forward = compute_us_forward_returns(
                observation_path=obs,
                cache_dir=cache,
                path_base=root,
            )
        except (FileNotFoundError, ValueError):
            forward = None

    shadow_count = portfolio.shadow_position_count
    with_evidence = portfolio.positions_with_evidence_ids
    with_links = portfolio.positions_with_resolved_links

    p0 = _milestone(
        milestone_id="P0",
        passed=True,
        status="passed",
        detail="portfolio-observation-summary builds successfully",
    )

    if shadow_count == 0:
        p1 = _milestone(
            milestone_id="P1",
            passed=False,
            status="not_applicable",
            detail="no shadow positions; linkage not applicable yet",
        )
    elif with_evidence > 0 and with_links > 0:
        p1 = _milestone(
            milestone_id="P1",
            passed=True,
            status="passed",
            detail=f"evidence_ids={with_evidence} resolved_links={with_links}",
        )
    else:
        p1 = _milestone(
            milestone_id="P1",
            passed=False,
            status="blocked",
            detail=f"shadow_positions={shadow_count} evidence={with_evidence} resolved={with_links}",
        )

    trend_status = str(weekly_trend.get("status") or "insufficient_history")
    trailing_7d = int(weekly_trend.get("trailing_7d_count") or 0)
    p2_supplemental = str(weekly_trend.get("p2_supplemental") or "")
    calendar_caveat = weekly_trend.get("calendar_week_caveat")
    if trend_status == "growing":
        p2 = _milestone(
            milestone_id="P2",
            passed=True,
            status="passed",
            detail=f"weekly_trend={trend_status} delta={weekly_trend.get('delta')}",
        )
    elif p2_supplemental == "active" and calendar_caveat == "prior_week_bulk":
        p2 = _milestone(
            milestone_id="P2",
            passed=False,
            status="blocked",
            detail=(
                f"calendar_week={trend_status} (prior bulk) but trailing_7d={trailing_7d} active; "
                "accumulate more ISO weeks"
            ),
        )
    elif trend_status in {"flat", "declining"}:
        p2 = _milestone(
            milestone_id="P2",
            passed=False,
            status="blocked",
            detail=f"weekly_trend={trend_status}; trailing_7d={trailing_7d}",
        )
    else:
        p2 = _milestone(
            milestone_id="P2",
            passed=False,
            status="blocked",
            detail="insufficient weekly history in observation_log",
        )

    peer_forward_matched = 0
    peer_forward_usable = False
    if forward:
        ps_fwd = forward.get("peer_sync_forward") or {}
        peer_forward_matched = int(ps_fwd.get("rows_matched") or 0)
        ps_sq = ps_fwd.get("sample_quality") or {}
        peer_forward_usable = str(ps_sq.get("status") or "") == "usable"

    sq_status = str((forward or {}).get("sample_quality", {}).get("status") or "")
    if sq_status == "usable":
        p3 = _milestone(
            milestone_id="P3",
            passed=True,
            status="passed",
            detail="forward sample_quality=usable (normal mode)",
        )
    elif forward is None:
        p3 = _milestone(
            milestone_id="P3",
            passed=False,
            status="blocked",
            detail="forward validation unavailable",
        )
    else:
        reason = str((forward.get("sample_quality") or {}).get("reason") or sq_status or "unknown")
        skip_pat = str((forward.get("sample_quality") or {}).get("skip_pattern") or "")
        detail = f"sample_quality={sq_status or 'empty'} ({reason})"
        if skip_pat:
            detail += f"; skip_pattern={skip_pat}"
        if peer_forward_usable:
            detail += (
                f"; peer_sync_forward usable ({peer_forward_matched} matched, "
                "US P3 milestone separate — docs/154)"
            )
        stall = forward.get("p3_stall_diagnosis") or {}
        why = stall.get("why_matched_stuck") or {}
        if why.get("headline"):
            detail += f"; {why['headline']}"
        p3 = _milestone(
            milestone_id="P3",
            passed=False,
            status="blocked",
            detail=detail,
        )

    milestones = [p0, p1, p2, p3]
    blockers = [f"{m['id']} {m['label']}: {m['detail']}" for m in milestones if not m["passed"]]
    next_milestone = next((m for m in milestones if not m["passed"]), None)

    if p0["passed"] and p1["passed"] and p2["passed"] and p3["passed"]:
        tier = "P0-P3"
    elif p0["passed"] and p1["passed"] and p2["passed"]:
        tier = "P0-P2"
    elif p0["passed"] and p1["passed"]:
        tier = "P0+P1"
    elif p0["passed"]:
        tier = "P0"
    else:
        tier = "none"

    suggested = _SUGGESTED_PERCENT.get(tier)
    example_shadow = root / "config" / "examples" / "shadow_portfolio_positions.example.jsonl"
    shadow_seed_hint: str | None = None
    if shadow_count == 0 and example_shadow.is_file():
        shadow_seed_hint = (
            "Copy config/examples/shadow_portfolio_positions.example.jsonl to "
            "outputs/shadow_portfolio/positions.jsonl (manual; see docs/165)"
        )

    p1_linkage_hint: str | None = None
    if shadow_count > 0 and with_links == 0:
        p1_linkage_hint = (
            "Set thesis_evidence_ids to observation_log row ids "
            "(see docs/165; snapshot portfolio-observation-summary)"
        )

    p2_weekly_hint = portfolio_p2_weekly_hint(weekly_trend)
    p3_forward_progress: dict[str, Any] | None = None
    p3_us_forward_summary: dict[str, Any] | None = None
    peer_forward_note: str | None = None
    if forward:
        sq = forward.get("sample_quality") or {}
        raw_p3 = sq.get("p3_progress")
        if isinstance(raw_p3, dict):
            p3_forward_progress = raw_p3
        stall = forward.get("p3_stall_diagnosis") or {}
        if stall:
            from invis_alpha_os.product.us_forward_p3_stall_diagnosis import (
                build_p3_us_forward_portfolio_summary,
            )
            from invis_alpha_os.product.us_forward_return_validation import THIN_SAMPLE_THRESHOLD

            p3_us_forward_summary = build_p3_us_forward_portfolio_summary(
                stall_diagnosis=stall,
                us_matched=int(forward.get("rows_matched") or 0),
                thin_threshold=THIN_SAMPLE_THRESHOLD,
            )
        if peer_forward_usable:
            peer_forward_note = (
                f"peer_sync_forward sample_quality=usable ({peer_forward_matched} matched); "
                "US forward P3 milestone remains separate (docs/154)"
            )

    acceptance = _load_portfolio_human_acceptance(root)
    human_pct: int | None = None
    human_tier_declared: str | None = None
    if acceptance is not None:
        raw = acceptance.get("human_accepted_percent")
        if isinstance(raw, int):
            human_pct = raw
        elif isinstance(raw, str) and raw.isdigit():
            human_pct = int(raw)
        declared = acceptance.get("accepted_tier")
        if declared is not None:
            human_tier_declared = str(declared)
    state_percent_matches_rubric = (
        human_pct is not None
        and suggested is not None
        and human_pct == suggested
        and (human_tier_declared is None or human_tier_declared == tier)
    )
    return {
        "milestones": milestones,
        "accepted_tier": tier,
        "accepted_tier_label": _tier_label(tier),
        "next_milestone": next_milestone,
        "suggested_percent": suggested,
        "state_percent_locked": human_pct is None,
        "state_percent_human_accepted": human_pct,
        "human_accepted_tier": human_tier_declared,
        "state_percent_matches_rubric": state_percent_matches_rubric,
        "human_acceptance_meta": acceptance,
        "shadow_seed_hint": shadow_seed_hint,
        "p1_linkage_hint": p1_linkage_hint,
        "p2_weekly_hint": p2_weekly_hint,
        "p3_forward_progress": p3_forward_progress,
        "p3_us_forward_summary": p3_us_forward_summary,
        "peer_forward_usable": peer_forward_usable,
        "peer_forward_matched": peer_forward_matched,
        "peer_forward_note": peer_forward_note,
        "p3_stall_diagnosis": forward.get("p3_stall_diagnosis") if forward else None,
        "blockers": blockers,
        "weekly_trend": weekly_trend,
        "observation_only": True,
    }


def _tier_label(tier: str) -> str:
    labels = {
        "P0-P3": "P0 through P3 (forward usable)",
        "P0-P2": "P0 through P2 (weekly sustained)",
        "P0+P1": "P0 + P1 (linkage)",
        "P0": "P0 only (CLI ready)",
        "none": "none",
    }
    return labels.get(tier, tier)
