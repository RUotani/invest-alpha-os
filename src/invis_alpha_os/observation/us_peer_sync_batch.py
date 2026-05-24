"""Append peer_sync pair snapshots to observation_log (cache-only; explicit opt-in)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.observation.us_peer_sync_note import build_us_peer_sync_observation_note
from invis_alpha_os.product.forward_event_resolution import bar_dates
from invis_alpha_os.product.jp_peer_sync_loader import try_load_bars_for_peer_sync
from invis_alpha_os.product.peer_sync_cache_only import build_peer_sync_cache_only_report


def log_peer_sync_snapshot_observations(
    *,
    path_base: Path,
    service: ObservationService,
    peer_map_path: Path | None = None,
    window_days: int = 20,
    divergence_threshold: float = 0.05,
    skip_statuses: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Append one observation_log row per evaluated peer pair (anchor symbol)."""

    skip = skip_statuses or frozenset()
    report = build_peer_sync_cache_only_report(
        path_base=path_base,
        peer_map_path=peer_map_path,
        window_days=window_days,
        divergence_threshold=divergence_threshold,
    )
    pairs = list(report.pairs)
    logged = 0
    skipped = 0
    for row in pairs:
        if not isinstance(row, dict):
            skipped += 1
            continue
        status = str(row.get("status") or "")
        if status in skip:
            skipped += 1
            continue
        anchor = str(row.get("anchor_symbol") or "").strip().upper()
        if not anchor:
            skipped += 1
            continue
        pair_row = dict(row)
        loaded = try_load_bars_for_peer_sync(anchor)
        if loaded is not None:
            dates = bar_dates(loaded[0])
            if dates:
                pair_row["as_of"] = dates[-1].isoformat()
        note = build_us_peer_sync_observation_note(pair_row)
        service.log_observation(anchor, note)
        logged += 1
    return {
        "pair_count": len(pairs),
        "logged": logged,
        "skipped": skipped,
        "summary": report.summary,
        "observation_only": True,
        "live_http": False,
    }


def peer_sync_log_failed(result: dict[str, Any]) -> bool:
    pair_count = int(result.get("pair_count") or 0)
    logged = int(result.get("logged") or 0)
    return pair_count > 0 and logged == 0
