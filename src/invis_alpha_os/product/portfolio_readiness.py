"""Portfolio observation readiness rubric (docs/154; read-only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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


def _milestone(
    *,
    milestone_id: str,
    passed: bool,
    status: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "id": milestone_id,
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
            status="blocked",
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
    if trend_status == "growing":
        p2 = _milestone(
            milestone_id="P2",
            passed=True,
            status="passed",
            detail=f"weekly_trend={trend_status} delta={weekly_trend.get('delta')}",
        )
    elif trend_status in {"flat", "declining"}:
        p2 = _milestone(
            milestone_id="P2",
            passed=False,
            status="blocked",
            detail=f"weekly_trend={trend_status}; need week-over-week growth",
        )
    else:
        p2 = _milestone(
            milestone_id="P2",
            passed=False,
            status="blocked",
            detail="insufficient weekly history in observation_log",
        )

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
        p3 = _milestone(
            milestone_id="P3",
            passed=False,
            status="blocked",
            detail=f"sample_quality={sq_status or 'empty'} ({reason})",
        )

    milestones = [p0, p1, p2, p3]
    blockers = [m["detail"] for m in milestones if not m["passed"]]

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

    return {
        "milestones": milestones,
        "accepted_tier": tier,
        "suggested_percent": _SUGGESTED_PERCENT.get(tier),
        "state_percent_locked": True,
        "blockers": blockers,
        "weekly_trend": weekly_trend,
        "observation_only": True,
    }
