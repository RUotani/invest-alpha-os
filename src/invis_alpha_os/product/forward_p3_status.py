"""Read-only combined forward P3 status (US + peer_sync; observation only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.product.peer_sync_forward_validation import compute_peer_sync_forward_join
from invis_alpha_os.product.us_forward_return_validation import (
    THIN_SAMPLE_THRESHOLD,
    compute_us_forward_returns,
    forward_p3_progress,
)


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

    return {
        "schema_version": 1,
        "thin_threshold": THIN_SAMPLE_THRESHOLD,
        "observation_path": str(obs),
        "us_forward": {
            "rows_matched": us_matched,
            "sample_quality_status": str(us_sq.get("status") or ""),
            "skip_pattern": str(us_sq.get("skip_pattern") or ""),
            "p3_progress": us_sq.get("p3_progress") or forward_p3_progress(us_matched),
            "stale_skip_by_symbol": list(us_report.get("stale_skip_by_symbol") or [])[:8],
        },
        "peer_sync_forward": {
            "rows_matched": peer_matched,
            "sample_quality_status": str(peer_sq.get("status") or ""),
            "p3_progress": peer_sq.get("p3_progress") or forward_p3_progress(peer_matched),
        },
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
        "",
        "## Next commands",
        "",
        "- `.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --format markdown`",
        "- `.venv/bin/python -m invis_alpha_os.cli.main validate peer-sync-forward-returns --format markdown`",
        "- `.venv/bin/python -m invis_alpha_os.cli.main validate post-refresh-smoke --format markdown`",
        "",
    ]
    stale = us.get("stale_skip_by_symbol") or []
    if stale:
        preview = ", ".join(f"{x.get('symbol')}({x.get('count')})" for x in stale[:6])
        lines.insert(10, f"- stale_skip_symbols: {preview}")
    return "\n".join(lines)
