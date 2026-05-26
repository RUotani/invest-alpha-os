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


def evaluate_p3_l1_write_gate(
    *,
    write_now_count: int,
    skip_duplicate_count: int,
    will_be_matchable_after_date_rows: int | None = None,
) -> dict[str, Any]:
    """Read-only L1 batch gate from weekly write plan + horizon maturity (docs/161)."""

    will_match = int(will_be_matchable_after_date_rows or 0)
    base = {
        "write_now_count": write_now_count,
        "skip_duplicate_count": skip_duplicate_count,
        "will_be_matchable_after_date_rows": will_match,
        "observation_only": True,
    }
    if write_now_count > 0:
        return {
            **base,
            "status": "ready",
            "l1_recommended": True,
            "blocked_reason": None,
            "next_action": (
                f"L1 ready: {write_now_count} new symbol×ISO week row(s); "
                "weekly --write-observation-log --skip-duplicate-iso-week"
            ),
        }
    if skip_duplicate_count > 0:
        msg = (
            "L1 blocked: all planned cache as_of dates fall in ISO weeks already logged; "
            "wait for ISO week rollover, then re-check write_now_count"
        )
        if will_match > 0:
            msg += f" ({will_match} row(s) will_be_matchable_after_date in log)"
        return {
            **base,
            "status": "blocked_duplicate_iso_week",
            "l1_recommended": False,
            "blocked_reason": "all_planned_writes_duplicate_iso_week",
            "next_action": msg,
        }
    return {
        **base,
        "status": "blocked",
        "l1_recommended": False,
        "blocked_reason": "no_planned_writes",
        "next_action": "No watchlist cache planned writes; check tier-1 cache coverage",
    }


def build_p3_weekly_write_plan(
    *,
    observation_path: Path,
    planned_writes: list[dict[str, str]],
    will_be_matchable_after_date_rows: int | None = None,
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
    l1_gate = evaluate_p3_l1_write_gate(
        write_now_count=len(write_now),
        skip_duplicate_count=len(skip_duplicate),
        will_be_matchable_after_date_rows=will_be_matchable_after_date_rows,
    )
    return {
        "schema_version": 1,
        "observation_path": str(observation_path),
        "write_now_count": len(write_now),
        "skip_duplicate_count": len(skip_duplicate),
        "write_now": write_now[:25],
        "skip_duplicate": skip_duplicate[:25],
        "l1_gate": l1_gate,
        "l1_hint": (
            "Use weekly --skip-duplicate-iso-week with --write-observation-log "
            "to log write_now symbols only (P3 effective rows)."
        ),
        "observation_only": True,
    }


def build_p3_l1_write_gate_for_observation(
    *,
    observation_path: Path,
    stall_diagnosis: dict[str, Any] | None,
    path_base: Path | None = None,
) -> dict[str, Any] | None:
    """Convenience: L1 gate from stall diagnosis + watchlist planned writes."""

    if not stall_diagnosis or not observation_path.is_file():
        return None
    from invis_alpha_os.product.us_forward_p3_stall_diagnosis import (
        default_watchlist_cache_planned_writes,
    )

    try:
        planned, _missing = default_watchlist_cache_planned_writes(path_base=path_base)
        will_match = int(
            (stall_diagnosis.get("p3_bucket_counts") or {}).get(
                "will_be_matchable_after_date", 0
            )
        )
        plan = build_p3_weekly_write_plan(
            observation_path=observation_path,
            planned_writes=planned,
            will_be_matchable_after_date_rows=will_match,
        )
    except (FileNotFoundError, ValueError):
        return None
    gate = plan.get("l1_gate")
    return gate if isinstance(gate, dict) else None
