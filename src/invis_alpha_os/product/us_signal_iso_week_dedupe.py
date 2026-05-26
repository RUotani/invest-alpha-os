"""Symbol × ISO week dedupe helpers for US observation_log (P3 forward; docs/161)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from invis_alpha_os.product.forward_event_resolution import parse_iso_date


def iso_week_key(d: date) -> tuple[int, int]:
    iso = d.isocalendar()
    return (iso[0], iso[1])


def symbol_iso_week_key(symbol: str, event_date: date) -> tuple[str, int, int]:
    return (str(symbol).strip().upper(), *iso_week_key(event_date))


def load_existing_symbol_iso_week_keys(observation_path: Path) -> set[tuple[str, int, int]]:
    """Keys already present in observation_log for US signal rows."""

    if not observation_path.is_file():
        return set()
    from invis_alpha_os.product.us_forward_return_validation import _iter_us_signal_rows

    obs_rows, _ = _iter_us_signal_rows(observation_path)
    keys: set[tuple[str, int, int]] = set()
    for row in obs_rows:
        keys.add(symbol_iso_week_key(str(row["symbol"]), row["event_date"]))
    return keys


def planned_item_iso_week_key(item: dict[str, Any]) -> tuple[str, int, int] | None:
    sym = item.get("symbol") or item.get("expect_symbol")
    raw = item.get("event_date") or item.get("last_date")
    if not sym or not raw:
        return None
    evt = parse_iso_date(raw)
    if evt is None:
        return None
    return symbol_iso_week_key(str(sym), evt)


def preview_iso_week_key(preview: dict[str, Any]) -> tuple[str, int, int] | None:
    return planned_item_iso_week_key(preview)


def is_duplicate_iso_week_key(
    key: tuple[str, int, int],
    existing_keys: set[tuple[str, int, int]],
) -> bool:
    return key in existing_keys


def build_p3_weekly_write_plan(
    *,
    observation_path: Path,
    planned_writes: list[dict[str, str]],
) -> dict[str, Any]:
    """Read-only split of planned writes into new ISO weeks vs duplicates."""

    existing = load_existing_symbol_iso_week_keys(observation_path)
    write_now: list[dict[str, str]] = []
    skip_duplicate: list[dict[str, str]] = []
    for item in planned_writes:
        key = planned_item_iso_week_key(item)
        sym = str(item.get("symbol") or item.get("expect_symbol") or "").strip().upper()
        raw = item.get("event_date") or item.get("last_date")
        if key is None:
            continue
        entry = {"symbol": sym, "last_date": str(raw)[:10]}
        if is_duplicate_iso_week_key(key, existing):
            skip_duplicate.append(entry)
        else:
            write_now.append(entry)
    return {
        "schema_version": 1,
        "observation_path": str(observation_path),
        "write_now_count": len(write_now),
        "skip_duplicate_count": len(skip_duplicate),
        "write_now": write_now[:25],
        "skip_duplicate": skip_duplicate[:25],
        "l1_hint": (
            "Use weekly --skip-duplicate-iso-week with --write-observation-log "
            "to log write_now symbols only (P3 effective rows)."
        ),
        "observation_only": True,
    }
