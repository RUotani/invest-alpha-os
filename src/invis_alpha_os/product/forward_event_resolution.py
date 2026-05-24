"""Resolve observation event dates for cache-only forward validation."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from invis_alpha_os.signals.momentum import DailyBar

AS_OF_NOTE_KEY = "as_of"


def parse_iso_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    if "T" in s:
        s = s.split("T", 1)[0]
    elif " " in s:
        s = s.split(" ", 1)[0]
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def parse_as_of_from_note(note: str) -> date | None:
    m = re.search(rf"{AS_OF_NOTE_KEY}=([^\s]+)", note)
    if not m:
        return None
    return parse_iso_date(m.group(1))


def append_as_of_to_note(note: str, as_of: str | date) -> str:
    """Insert ``as_of=`` after the observation-only prefix when absent."""

    if parse_as_of_from_note(note) is not None:
        return note
    token = f"{AS_OF_NOTE_KEY}={parse_iso_date(as_of) or as_of}"
    parts = note.split(" ", 2)
    if len(parts) >= 2 and parts[0]:
        return f"{parts[0]} {parts[1]} {token} {' '.join(parts[2:])}".strip()
    return f"{note} {token}".strip()


def resolve_observation_event_date(
    *,
    note: str,
    created_at: object,
) -> tuple[date | None, str]:
    as_of = parse_as_of_from_note(note)
    if as_of is not None:
        return as_of, "as_of"
    created = parse_iso_date(created_at)
    if created is not None:
        return created, "created_at"
    return None, "missing"


def bar_dates(bars: list[DailyBar]) -> list[date]:
    out: list[date] = []
    for b in bars:
        parsed = parse_iso_date(b.get("date"))
        if parsed is not None:
            out.append(parsed)
    return out


def event_bar_index(bars: list[DailyBar], event: date) -> int | None:
    dates = bar_dates(bars)
    if len(dates) != len(bars):
        return None
    idx: int | None = None
    for i, d in enumerate(dates):
        if d <= event:
            idx = i
        else:
            break
    return idx


def forward_return(bars: list[DailyBar], start_idx: int, horizon: int) -> float | None:
    end_idx = start_idx + horizon
    if end_idx >= len(bars):
        return None
    old = float(bars[start_idx]["close"])
    new = float(bars[end_idx]["close"])
    if old == 0:
        return None
    return (new / old) - 1.0


def compute_horizon_returns(
    bars: list[DailyBar],
    start_idx: int,
    horizons: tuple[int, ...],
) -> tuple[dict[str, float | None], bool]:
    horizon_returns: dict[str, float | None] = {}
    any_ok = False
    for h in horizons:
        fr = forward_return(bars, start_idx, int(h))
        horizon_returns[str(h)] = fr
        if fr is not None:
            any_ok = True
    return horizon_returns, any_ok


def resolve_forward_horizons(
    bars: list[DailyBar],
    event: date,
    horizons: tuple[int, ...],
    *,
    backtest_within_cache: bool = False,
) -> tuple[int, dict[str, float | None], str | None] | None:
    """Return start index, horizon returns, and optional event resolution tag."""

    idx = event_bar_index(bars, event)
    if idx is None:
        return None
    dates = bar_dates(bars)
    last_cache = dates[-1] if dates else None
    returns, ok = compute_horizon_returns(bars, idx, horizons)
    if ok:
        tag: str | None = None
        if last_cache is not None and event > last_cache:
            tag = "event_after_cache_end_clamped"
        return idx, returns, tag
    if backtest_within_cache:
        max_h = max(int(h) for h in horizons)
        shifted = len(bars) - max_h - 1
        if shifted >= 0:
            returns, ok = compute_horizon_returns(bars, shifted, horizons)
            if ok:
                return shifted, returns, "backtest_within_cache"
    if last_cache is not None and event > last_cache:
        return None
    return None


def cache_stale_skip_reason(event: date, bars: list[DailyBar]) -> str | None:
    dates = bar_dates(bars)
    if not dates:
        return None
    if event > dates[-1]:
        return "cache_stale_event_after_cache_end"
    return None
