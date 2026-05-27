"""Symbol × ISO week dedupe helpers for US observation_log (P3 forward; docs/161)."""

from __future__ import annotations

from datetime import date, timedelta
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


def next_iso_week_start(from_date: date) -> date:
    """First calendar date that falls in the ISO week after ``from_date``."""

    current = iso_week_key(from_date)
    probe = from_date + timedelta(days=1)
    while iso_week_key(probe) == current:
        probe += timedelta(days=1)
    return probe


def estimate_p3_iso_week_rollover(
    *,
    skip_duplicate: list[dict[str, str]],
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Read-only: when L1 may unblock if cache as_of advances to a new ISO week."""

    ref = reference_date or date.today()
    if not skip_duplicate:
        return {
            "schema_version": 1,
            "status": "not_applicable",
            "observation_only": True,
        }

    per_symbol: list[dict[str, Any]] = []
    earliest: date | None = None
    for item in skip_duplicate:
        sym = str(item.get("symbol") or "").strip().upper()
        raw = item.get("last_date")
        evt = parse_iso_date(raw)
        if not sym or evt is None:
            continue
        nxt = next_iso_week_start(evt)
        days = max(0, (nxt - ref).days)
        per_symbol.append(
            {
                "symbol": sym,
                "cache_as_of": evt.isoformat(),
                "current_iso_week": f"{iso_week_key(evt)[0]}-W{iso_week_key(evt)[1]:02d}",
                "next_iso_week_starts": nxt.isoformat(),
                "days_until_next_iso_week": days,
            }
        )
        if earliest is None or nxt < earliest:
            earliest = nxt

    if earliest is None:
        return {
            "schema_version": 1,
            "status": "unknown",
            "observation_only": True,
        }

    days_until = max(0, (earliest - ref).days)
    iso = earliest.isocalendar()
    rollover_passed = ref >= earliest
    days_until_note = (
        "0 = earliest_next_iso_week_start reached or passed (calendar rollover date elapsed; "
        "write_now may still be 0 if cache/as_of has not advanced)"
        if rollover_passed
        else f"{days_until} calendar day(s) until earliest_next_iso_week_start"
    )
    if rollover_passed:
        status = "rollover_passed_write_still_blocked"
        l1_unblock_hint = (
            "ISO week rollover date has passed but write_now_count=0: planned writes still "
            "duplicate existing symbol×ISO week rows or cache/as_of has not advanced; "
            "refresh P10 tier-1 cache and re-check write_now_count"
        )
    else:
        status = "waiting_for_iso_week_rollover"
        l1_unblock_hint = (
            f"Re-check write_now_count after {earliest.isoformat()} "
            f"(ISO week {iso[0]}-W{iso[1]:02d}) or after P10 extends cache into a new week"
        )
    return {
        "schema_version": 1,
        "status": status,
        "reference_date": ref.isoformat(),
        "earliest_next_iso_week_start": earliest.isoformat(),
        "earliest_next_iso_week": f"{iso[0]}-W{iso[1]:02d}",
        "days_until_earliest_rollover": days_until,
        "days_until_earliest_rollover_note": days_until_note,
        "rollover_passed": rollover_passed,
        "projected_write_now_symbols_at_rollover": len(per_symbol),
        "per_symbol_sample": per_symbol[:12],
        "l1_unblock_hint": l1_unblock_hint,
        "observation_only": True,
    }


def evaluate_p3_l1_write_gate(
    *,
    write_now_count: int,
    skip_duplicate_count: int,
    will_be_matchable_after_date_rows: int | None = None,
    iso_week_rollover: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read-only L1 batch gate from weekly write plan + horizon maturity (docs/161)."""

    will_match = int(will_be_matchable_after_date_rows or 0)
    rollover = iso_week_rollover or {}
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
        if rollover.get("rollover_passed"):
            msg = (
                "L1 blocked: ISO week rollover date has passed but write_now_count=0 — "
                "planned writes still duplicate existing symbol×ISO week rows or "
                "cache/as_of has not advanced; refresh P10 tier-1 cache and re-check write_now_count"
            )
        else:
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
    rollover = estimate_p3_iso_week_rollover(skip_duplicate=skip_duplicate)
    l1_gate = evaluate_p3_l1_write_gate(
        write_now_count=len(write_now),
        skip_duplicate_count=len(skip_duplicate),
        will_be_matchable_after_date_rows=will_be_matchable_after_date_rows,
        iso_week_rollover=rollover,
    )
    if rollover.get("l1_unblock_hint") and not l1_gate.get("l1_recommended"):
        l1_gate = {
            **l1_gate,
            "iso_week_rollover": {
                "earliest_next_iso_week_start": rollover.get("earliest_next_iso_week_start"),
                "days_until_earliest_rollover": rollover.get("days_until_earliest_rollover"),
                "days_until_earliest_rollover_note": rollover.get("days_until_earliest_rollover_note"),
                "rollover_passed": rollover.get("rollover_passed"),
                "projected_write_now_symbols_at_rollover": rollover.get(
                    "projected_write_now_symbols_at_rollover"
                ),
            },
            "next_action": (
                f"{l1_gate.get('next_action', '')}; {rollover['l1_unblock_hint']}"
                if not rollover.get("rollover_passed")
                else rollover["l1_unblock_hint"]
            ),
        }
    return {
        "schema_version": 1,
        "observation_path": str(observation_path),
        "write_now_count": len(write_now),
        "skip_duplicate_count": len(skip_duplicate),
        "write_now": write_now[:25],
        "skip_duplicate": skip_duplicate[:25],
        "l1_gate": l1_gate,
        "iso_week_rollover": rollover,
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
