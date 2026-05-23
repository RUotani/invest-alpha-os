"""Observation-only US cache signals batch logging (no HTTP; no cache write)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from invis_alpha_os.data.us_cache_signals_batch_manifest import (
    build_us_cache_signals_previews_from_batch_manifest,
)
from invis_alpha_os.observation.service import ObservationService


def _observation_note_for_preview(preview: dict[str, Any]) -> str:
    status = str(preview.get("status") or "unknown")
    parts = [f"us_cache_signal observation_only status={status}"]
    label = preview.get("momentum_label")
    if label:
        parts.append(f"momentum_label={label}")
    reason = preview.get("reason")
    if reason and status != "ok":
        parts.append(f"reason={reason}")
    parts.append("not buy/sell advice")
    return " ".join(parts)


def log_us_signals_batch_observations(
    manifest_path: Path,
    *,
    path_base: Path,
    service: ObservationService,
) -> dict[str, Any]:
    """Append one observation_log row per manifest entry (read-only signal preview)."""

    result = build_us_cache_signals_previews_from_batch_manifest(manifest_path, path_base=path_base)
    manifest_status = str(result.get("status") or "unknown")
    if manifest_status != "ok":
        return {
            "manifest_status": manifest_status,
            "manifest_reason": result.get("reason"),
            "entry_count": result.get("entry_count", 0),
            "logged": 0,
            "skipped": 0,
            "observation_only": True,
            "live_http": False,
        }

    previews = list(result.get("previews") or [])
    logged = 0
    skipped = 0
    for preview in previews:
        sym = preview.get("symbol") or preview.get("expect_symbol")
        if not sym:
            skipped += 1
            continue
        service.log_observation(str(sym).strip().upper(), _observation_note_for_preview(preview))
        logged += 1
    return {
        "manifest_status": manifest_status,
        "entry_count": result.get("entry_count", 0),
        "logged": logged,
        "skipped": skipped,
        "observation_only": True,
        "live_http": False,
    }


def observation_batch_failed(result: dict[str, Any]) -> bool:
    """True when manifest invalid or zero rows logged despite entries."""

    if result.get("manifest_status") != "ok":
        return True
    entry_count = int(result.get("entry_count") or 0)
    logged = int(result.get("logged") or 0)
    return entry_count > 0 and logged == 0
