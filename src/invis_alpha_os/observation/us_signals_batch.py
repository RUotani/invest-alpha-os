"""Observation-only US cache signals batch logging (no HTTP; no cache write)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from invis_alpha_os.data.us_cache_signals_batch_manifest import (
    build_us_cache_signals_previews_from_batch_manifest,
)
from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.observation.us_signal_note import build_us_signal_observation_note

# Backward-compatible alias for existing tests/imports.
_observation_note_for_preview = build_us_signal_observation_note


def log_us_signals_batch_observations(
    manifest_path: Path,
    *,
    path_base: Path,
    service: ObservationService,
    quality_snapshot: dict[str, Any] | None = None,
    skip_duplicate_iso_week: bool = False,
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
            "skipped_duplicate_iso_week": 0,
            "observation_only": True,
            "live_http": False,
        }

    previews = list(result.get("previews") or [])
    veto_by_symbol: dict[str, dict[str, Any]] = {}
    if quality_snapshot:
        for row in quality_snapshot.get("rows") or []:
            sym = row.get("symbol")
            if sym:
                veto_by_symbol[str(sym).strip().upper()] = row
    existing_iso_weeks: set[tuple[str, int, int]] = set()
    if skip_duplicate_iso_week:
        from invis_alpha_os.product.us_signal_iso_week_dedupe import (
            is_duplicate_iso_week_key,
            load_existing_symbol_iso_week_keys,
            preview_iso_week_key,
        )

        existing_iso_weeks = load_existing_symbol_iso_week_keys(service.observation_path)
    logged = 0
    skipped = 0
    skipped_duplicate_iso_week = 0
    skipped_duplicate_symbols: list[str] = []
    for preview in previews:
        sym = preview.get("symbol") or preview.get("expect_symbol")
        if not sym:
            skipped += 1
            continue
        sym_u = str(sym).strip().upper()
        if skip_duplicate_iso_week:
            from invis_alpha_os.product.us_signal_iso_week_dedupe import (
                is_duplicate_iso_week_key,
                preview_iso_week_key,
            )

            week_key = preview_iso_week_key(preview)
            if week_key is not None and is_duplicate_iso_week_key(week_key, existing_iso_weeks):
                skipped_duplicate_iso_week += 1
                if sym_u not in skipped_duplicate_symbols:
                    skipped_duplicate_symbols.append(sym_u)
                continue
        veto_row = veto_by_symbol.get(sym_u)
        veto_triggered: bool | None = None
        veto_rules: list[str] | None = None
        if veto_row is not None:
            veto_triggered = bool(veto_row.get("veto_triggered"))
            veto_rules = list(veto_row.get("veto_rules") or [])
        note = build_us_signal_observation_note(
            preview,
            veto_triggered=veto_triggered,
            veto_rules=veto_rules,
        )
        service.log_observation(sym_u, note)
        logged += 1
        if skip_duplicate_iso_week:
            from invis_alpha_os.product.us_signal_iso_week_dedupe import preview_iso_week_key

            week_key = preview_iso_week_key(preview)
            if week_key is not None:
                existing_iso_weeks.add(week_key)
    return {
        "manifest_status": manifest_status,
        "entry_count": result.get("entry_count", 0),
        "logged": logged,
        "skipped": skipped,
        "skipped_duplicate_iso_week": skipped_duplicate_iso_week,
        "skipped_duplicate_symbols": skipped_duplicate_symbols[:16],
        "skip_duplicate_iso_week": skip_duplicate_iso_week,
        "observation_only": True,
        "live_http": False,
    }


def observation_batch_failed(result: dict[str, Any]) -> bool:
    """True when manifest invalid or zero rows logged despite entries."""

    if result.get("manifest_status") != "ok":
        return True
    entry_count = int(result.get("entry_count") or 0)
    logged = int(result.get("logged") or 0)
    if entry_count > 0 and logged == 0:
        dup_skipped = int(result.get("skipped_duplicate_iso_week") or 0)
        if dup_skipped >= entry_count:
            return False
        return True
    return False
