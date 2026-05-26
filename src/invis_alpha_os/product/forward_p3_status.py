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
    recommended = forward_p3_recommended_actions(
        skip_pattern=skip_pattern,
        tier1_missing=tier1_missing,
        stale_skips=stale_skips,
        forward_matched=us_matched,
        stale_skip_by_symbol=list(us_report.get("stale_skip_by_symbol") or []),
        peer_sync_matched=peer_matched,
        resolution_outcomes=resolution_breakdown.get("outcomes"),
    )

    return {
        "schema_version": 1,
        "thin_threshold": THIN_SAMPLE_THRESHOLD,
        "observation_path": str(obs),
        "observation_log_lines": log_lines,
        "recommended_actions": recommended,
        "us_forward_resolution_breakdown": resolution_breakdown,
        "us_forward": {
            "rows_matched": us_matched,
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
        f"- matched: {us.get('rows_matched', 0)}",
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
            "- `.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --format markdown`",
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
        for key, count in list((bd.get("outcomes") or {}).items())[:10]:
            lines.append(f"- {key}: {count}")
    actions = report.get("recommended_actions") or []
    if actions:
        lines.extend(["", "## Recommended actions (read-only)"])
        for action in actions[:8]:
            lines.append(f"- {action}")
    return "\n".join(lines)
