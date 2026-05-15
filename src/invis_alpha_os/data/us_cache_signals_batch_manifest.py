"""Explicit US cache signals batch manifest (no HTTP; no directory scan)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from invis_alpha_os.data.us_cache_signals import (
    attach_us_asset_universe_metadata_to_signals_preview,
    build_us_cache_signals_preview,
)

US_CACHE_SIGNALS_BATCH_MANIFEST_ENTRY_KEYS: Final[frozenset[str]] = frozenset(
    {"symbol", "cache_path"}
)


def _validate_manifest_entry(row: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    if set(row.keys()) != US_CACHE_SIGNALS_BATCH_MANIFEST_ENTRY_KEYS:
        return None
    sym = str(row.get("symbol", "")).strip().upper()
    cache_path = str(row.get("cache_path", "")).strip()
    if not sym or not cache_path:
        return None
    return {"symbol": sym, "cache_path": cache_path}


def parse_us_cache_signals_batch_manifest_payload(data: Any) -> dict[str, Any] | None:
    """Validate batch manifest envelope; return normalized dict or ``None``."""

    if not isinstance(data, dict):
        return None
    if data.get("schema_version") != 1:
        return None
    rows = data.get("entries")
    if not isinstance(rows, list) or not rows:
        return None
    out_rows: list[dict[str, Any]] = []
    for raw in rows:
        entry = _validate_manifest_entry(raw)
        if entry is None:
            return None
        out_rows.append(entry)
    universe_path = data.get("universe_path")
    if universe_path is not None and not isinstance(universe_path, str):
        return None
    uni = str(universe_path).strip() if universe_path else None
    if universe_path is not None and not uni:
        return None
    source = data.get("source")
    if source is not None and not isinstance(source, str):
        return None
    return {
        "schema_version": 1,
        "source": str(source) if source is not None else None,
        "universe_path": uni,
        "entries": out_rows,
        "entry_count": len(out_rows),
    }


def load_us_cache_signals_batch_manifest_json_file(path: Path) -> dict[str, Any] | None:
    """Load and validate batch manifest JSON from ``path`` (no network)."""

    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return parse_us_cache_signals_batch_manifest_payload(data)


def _resolve_manifest_relative_path(path_base: Path, rel: str) -> Path:
    candidate = Path(rel)
    if candidate.is_absolute():
        return candidate
    return (path_base / candidate).resolve()


def build_us_cache_signals_previews_from_batch_manifest(
    manifest_path: Path,
    *,
    path_base: Path,
) -> dict[str, Any]:
    """Build signal preview rows from an explicit manifest (no auto scan)."""

    rel_manifest = str(manifest_path)
    manifest = load_us_cache_signals_batch_manifest_json_file(manifest_path)
    if manifest is None:
        return {
            "status": "invalid",
            "reason": "manifest_invalid",
            "manifest_path": rel_manifest,
            "previews": [],
            "entry_count": 0,
            "live_http": False,
        }

    universe_abs: Path | None = None
    uni_rel = manifest.get("universe_path")
    if uni_rel:
        universe_abs = _resolve_manifest_relative_path(path_base, uni_rel)

    previews: list[dict[str, Any]] = []
    for entry in manifest["entries"]:
        cache_abs = _resolve_manifest_relative_path(path_base, entry["cache_path"])
        preview = build_us_cache_signals_preview(cache_abs, expect_symbol=entry["symbol"])
        if universe_abs is not None:
            preview = attach_us_asset_universe_metadata_to_signals_preview(
                preview, universe_abs
            )
        previews.append(preview)

    return {
        "status": "ok",
        "reason": None,
        "manifest_path": rel_manifest,
        "universe_path": uni_rel,
        "previews": previews,
        "entry_count": len(previews),
        "live_http": False,
    }
