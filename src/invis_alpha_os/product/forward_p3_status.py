"""Read-only combined forward P3 status (US + peer_sync; observation only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.product.peer_sync_forward_validation import compute_peer_sync_forward_join
from invis_alpha_os.product.post_p10_refresh_smoke import forward_p3_recommended_actions
from invis_alpha_os.product.us_forward_return_validation import (
    THIN_SAMPLE_THRESHOLD,
    classify_forward_skip_pattern,
    compute_us_forward_resolution_breakdown,
    compute_us_forward_returns,
    forward_p3_progress,
    observation_log_line_count,
    us_forward_matched_normal_for_p3,
)
from invis_alpha_os.product.us_universe_expansion import build_us_universe_expansion_report


def build_forward_p3_status_bundle(
    *,
    path_base: Path | None = None,
    observation_path: Path | None = None,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Aggregate US and peer_sync forward progress toward sample_quality=usable."""

    root = path_base or ROOT_DIR
    obs = observation_path or (OUTPUTS_DIR / "observation_log" / "observation_log.jsonl")
    cache = cache_dir or (OUTPUTS_DIR / "market_data" / "us_daily_bars")

    us_report: dict[str, Any] = {}
    try:
        us_report = compute_us_forward_returns(
            observation_path=obs,
            cache_dir=cache,
            path_base=root,
        )
    except (FileNotFoundError, ValueError):
        us_report = {}

    peer_report: dict[str, Any] = {}
    try:
        peer_report = compute_peer_sync_forward_join(observation_path=obs)
    except (FileNotFoundError, ValueError):
        peer_report = {}

    us_matched = int(us_report.get("rows_matched") or 0)
    peer_matched = int(peer_report.get("rows_matched") or 0)
    us_sq = us_report.get("sample_quality") or {}
    peer_sq = peer_report.get("sample_quality") or {}
    peer_status = str(peer_sq.get("status") or "")
    us_status = str(us_sq.get("status") or "")
    peer_usable = peer_status == "usable"
    us_usable = us_status == "usable"
    skipped = us_report.get("skipped_reasons") or {}
    signal_rows = int(us_report.get("rows_considered") or 0)
    skip_pattern = str(us_sq.get("skip_pattern") or "") or classify_forward_skip_pattern(
        skipped, signal_rows=signal_rows
    )
    stale_skips = int(skipped.get("cache_stale_event_after_cache_end") or 0)
    tier1_missing: list[str] = []
    try:
        expansion = build_us_universe_expansion_report(
            path_base=root,
            tier="1",
            missing_only=True,
        )
        tier1_missing = list(expansion.get("tier_1_missing_refresh_order") or [])
    except (FileNotFoundError, ValueError):
        tier1_missing = []
    log_lines = observation_log_line_count(obs)
    resolution_breakdown: dict[str, Any] = {}
    try:
        resolution_breakdown = compute_us_forward_resolution_breakdown(
            observation_path=obs,
            cache_dir=cache,
            path_base=root,
        )
    except (FileNotFoundError, ValueError):
        resolution_breakdown = {}
    p3_stall_diagnosis: dict[str, Any] = {}
    if resolution_breakdown.get("p3_stall_diagnosis"):
        p3_stall_diagnosis = resolution_breakdown["p3_stall_diagnosis"]
    else:
        try:
            from invis_alpha_os.product.us_forward_p3_stall_diagnosis import (
                compute_us_forward_p3_stall_diagnosis,
            )

            p3_stall_diagnosis = compute_us_forward_p3_stall_diagnosis(
                observation_path=obs,
                cache_dir=cache,
            )
        except (FileNotFoundError, ValueError):
            p3_stall_diagnosis = {}
    event_sources = resolution_breakdown.get("event_date_sources") or {}
    p3_us_forward_summary: dict[str, Any] = {}
    p3_weekly_write_plan: dict[str, Any] = {}
    if p3_stall_diagnosis:
        from invis_alpha_os.product.us_forward_p3_stall_diagnosis import (
            build_p3_us_forward_portfolio_summary,
            default_watchlist_cache_planned_writes,
        )
        from invis_alpha_os.product.us_signal_iso_week_dedupe import build_p3_weekly_write_plan

        p3_us_forward_summary = build_p3_us_forward_portfolio_summary(
            stall_diagnosis=p3_stall_diagnosis,
            us_matched=us_matched,
            thin_threshold=THIN_SAMPLE_THRESHOLD,
        )
        try:
            planned, _missing = default_watchlist_cache_planned_writes(path_base=root)
            will_match = int(
                (p3_stall_diagnosis.get("p3_bucket_counts") or {}).get(
                    "will_be_matchable_after_date", 0
                )
            )
            p3_weekly_write_plan = build_p3_weekly_write_plan(
                observation_path=obs,
                planned_writes=planned,
                will_be_matchable_after_date_rows=will_match,
            )
        except (FileNotFoundError, ValueError):
            p3_weekly_write_plan = {}
    l1_gate = (p3_weekly_write_plan.get("l1_gate") or {}) if p3_weekly_write_plan else {}
    recommended = forward_p3_recommended_actions(
        skip_pattern=skip_pattern,
        tier1_missing=tier1_missing,
        stale_skips=stale_skips,
        forward_matched=us_matched,
        stale_skip_by_symbol=list(us_report.get("stale_skip_by_symbol") or []),
        peer_sync_matched=peer_matched,
        resolution_outcomes=resolution_breakdown.get("outcomes"),
        insufficient_future_share=resolution_breakdown.get("insufficient_future_share"),
        event_date_source_as_of_share=event_sources.get("event_date_source_as_of_share"),
        l1_write_gate=l1_gate or None,
    )

    matched_normal = us_forward_matched_normal_for_p3(
        rows_matched=us_matched,
        stall_diagnosis=p3_stall_diagnosis or None,
        p3_summary=p3_us_forward_summary or None,
    )

    p3_path_to_usable: dict[str, Any] = {}
    if p3_stall_diagnosis or p3_us_forward_summary:
        from invis_alpha_os.product.p3_path_to_usable import build_p3_path_to_usable

        p3_path_to_usable = build_p3_path_to_usable(
            matched_normal=matched_normal,
            thin_threshold=THIN_SAMPLE_THRESHOLD,
            p3_us_forward_summary=p3_us_forward_summary,
            p3_weekly_write_plan=p3_weekly_write_plan,
            p3_horizon_timeline=p3_stall_diagnosis.get("p3_horizon_timeline") or {},
            stall_diagnosis=p3_stall_diagnosis,
        )
        for step in p3_path_to_usable.get("next_steps") or []:
            recommended = list(dict.fromkeys([*recommended, str(step)]))

    return {
        "schema_version": 1,
        "thin_threshold": THIN_SAMPLE_THRESHOLD,
        "observation_path": str(obs),
        "observation_log_lines": log_lines,
        "recommended_actions": recommended,
        "us_forward_resolution_breakdown": resolution_breakdown,
        "p3_stall_diagnosis": p3_stall_diagnosis,
        "p3_us_forward_summary": p3_us_forward_summary,
        "p3_weekly_write_plan": p3_weekly_write_plan,
        "p3_horizon_timeline": p3_stall_diagnosis.get("p3_horizon_timeline") or {},
        "p3_path_to_usable": p3_path_to_usable,
        "us_forward": {
            "rows_matched": us_matched,
            "matched_normal": matched_normal,
            "sample_quality_status": str(us_sq.get("status") or ""),
            "skip_pattern": str(us_sq.get("skip_pattern") or ""),
            "p3_progress": us_sq.get("p3_progress") or forward_p3_progress(us_matched),
            "stale_skip_by_symbol": list(us_report.get("stale_skip_by_symbol") or [])[:8],
        },
        "peer_sync_forward": {
            "rows_matched": peer_matched,
            "sample_quality_status": peer_status,
            "p3_progress": peer_sq.get("p3_progress") or forward_p3_progress(peer_matched),
            "p3_usable": peer_usable,
        },
        "us_p3_usable": us_usable,
        "peer_p3_usable": peer_usable,
        "milestone_note": (
            "peer_sync_forward P3 track: usable"
            if peer_usable and not us_usable
            else None
        ),
        "observation_only": True,
        "live_http": False,
    }


def format_forward_p3_status_markdown(report: dict[str, Any]) -> str:
    us = report.get("us_forward") or {}
    peer = report.get("peer_sync_forward") or {}
    us_p3 = us.get("p3_progress") or {}
    peer_p3 = peer.get("p3_progress") or {}
    lines = [
        "# Forward P3 status (read-only)",
        "",
        "Observation only — not buy/sell advice.",
        "",
        f"- thin_threshold: {report.get('thin_threshold', 10)}",
        "",
        "## US forward",
        f"- matched (all rows): {us.get('rows_matched', 0)}",
        f"- matched_normal (P3): {us.get('matched_normal', us.get('rows_matched', 0))}",
        f"- sample_quality: {us.get('sample_quality_status', '')}",
        f"- skip_pattern: {us.get('skip_pattern') or '(n/a)'}",
        f"- p3_progress: {us_p3.get('progress_label', '')}",
        "",
        "## Peer sync forward",
        f"- matched: {peer.get('rows_matched', 0)}",
        f"- sample_quality: {peer.get('sample_quality_status', '')}",
        f"- p3_progress: {peer_p3.get('progress_label', '')}",
    ]
    note = report.get("milestone_note")
    if note:
        lines.append(f"- milestone_note: {note}")
    lines.extend(
        [
            "",
            "## Next commands",
            "",
        ]
    )
    from invis_alpha_os.product.us_forward_return_validation import forward_validation_next_commands

    for cmd in forward_validation_next_commands():
        lines.append(f"- `{cmd}`")
    lines.extend(
        [
            "- `.venv/bin/python -m invis_alpha_os.cli.main validate peer-sync-forward-returns --format markdown`",
            "- `.venv/bin/python -m invis_alpha_os.cli.main validate post-refresh-smoke --format markdown`",
            "",
        ]
    )
    stale = us.get("stale_skip_by_symbol") or []
    if stale:
        preview = ", ".join(f"{x.get('symbol')}({x.get('count')})" for x in stale[:6])
        lines.insert(10, f"- stale_skip_symbols: {preview}")
    log_lines = report.get("observation_log_lines")
    if log_lines is not None:
        lines.insert(4, f"- observation_log_lines: {log_lines}")
    bd = report.get("us_forward_resolution_breakdown") or {}
    if bd.get("outcomes"):
        lines.extend(
            [
                "",
                "## US forward resolution breakdown",
                f"- {bd.get('path_to_usable_note', '')}",
            ]
        )
        share = bd.get("insufficient_future_share")
        if share is not None:
            lines.append(f"- insufficient_future_share: {share}")
        eds = bd.get("event_date_sources") or {}
        if eds.get("us_signal_rows"):
            lines.append(f"- event_date_sources: {eds.get('event_date_source_note', '')}")
            as_of_share = eds.get("event_date_source_as_of_share")
            if as_of_share is not None:
                lines.append(f"- event_date_source_as_of_share: {as_of_share}")
        outcome_items = bd.get("us_signal_outcomes") or bd.get("outcomes") or {}
        for key, count in list(outcome_items.items())[:10]:
            lines.append(f"- {key}: {count}")
        bt = bd.get("backtest_within_cache_matched")
        if bt is not None:
            lines.append(f"- backtest_within_cache_matched (exploratory): {bt}")
            note = bd.get("backtest_exploratory_note")
            if note:
                lines.append(f"- {note}")
    path_usable = report.get("p3_path_to_usable") or {}
    if path_usable.get("headline"):
        from invis_alpha_os.product.p3_path_to_usable import format_p3_path_to_usable_markdown

        lines.extend(["", format_p3_path_to_usable_markdown(path_usable)])
    summary = report.get("p3_us_forward_summary") or {}
    if summary:
        from invis_alpha_os.product.us_forward_p3_stall_diagnosis import (
            format_p3_us_forward_portfolio_summary_markdown,
        )

        lines.extend(["", format_p3_us_forward_portfolio_summary_markdown(summary)])
    plan = report.get("p3_weekly_write_plan") or {}
    if plan.get("write_now_count") is not None:
        lines.extend(
            [
                "",
                "## P3 weekly write plan (read-only)",
                f"- write_now_count: {plan.get('write_now_count', 0)}",
                f"- skip_duplicate_count: {plan.get('skip_duplicate_count', 0)}",
                f"- l1_hint: {plan.get('l1_hint', '')}",
            ]
        )
        gate = plan.get("l1_gate") or {}
        if gate:
            lines.extend(
                [
                    f"- l1_status: {gate.get('status', '')}",
                    f"- l1_recommended: {gate.get('l1_recommended')}",
                ]
            )
            if gate.get("blocked_reason"):
                lines.append(f"- l1_blocked_reason: {gate.get('blocked_reason')}")
            if gate.get("next_action"):
                lines.append(f"- l1_next_action: {gate.get('next_action')}")
            rollover = gate.get("iso_week_rollover") or plan.get("iso_week_rollover") or {}
            if rollover.get("earliest_next_iso_week_start"):
                lines.extend(
                    [
                        "",
                        "### ISO week rollover estimate",
                        f"- earliest_next_iso_week_start: {rollover.get('earliest_next_iso_week_start')}",
                        f"- days_until_earliest_rollover: {rollover.get('days_until_earliest_rollover')}",
                        f"- projected_write_now_symbols_at_rollover: "
                        f"{rollover.get('projected_write_now_symbols_at_rollover', 0)}",
                    ]
                )
                hint = rollover.get("l1_unblock_hint")
                if hint:
                    lines.append(f"- l1_unblock_hint: {hint}")
        write_now = plan.get("write_now") or []
        if write_now:
            preview = ", ".join(
                f"{x.get('symbol')}({x.get('last_date')})" for x in write_now[:8]
            )
            lines.append(f"- write_now: {preview}")
    timeline = report.get("p3_horizon_timeline") or {}
    if timeline.get("headline"):
        from invis_alpha_os.product.us_forward_p3_stall_diagnosis import (
            format_p3_horizon_match_timeline_markdown,
        )

        lines.extend(["", format_p3_horizon_match_timeline_markdown(timeline)])
    stall = report.get("p3_stall_diagnosis") or {}
    if stall.get("why_matched_stuck"):
        from invis_alpha_os.product.us_forward_p3_stall_diagnosis import format_p3_stall_diagnosis_markdown

        lines.extend(["", format_p3_stall_diagnosis_markdown(stall)])
    actions = report.get("recommended_actions") or []
    stall_actions = stall.get("next_actions") or []
    merged_actions = list(dict.fromkeys([*actions, *stall_actions]))
    if merged_actions:
        lines.extend(["", "## Recommended actions (read-only)"])
        for action in merged_actions[:12]:
            lines.append(f"- {action}")
    return "\n".join(lines)
