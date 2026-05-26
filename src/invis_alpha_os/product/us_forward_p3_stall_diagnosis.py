"""Read-only diagnosis for US forward P3 stall (3/10 thin → usable; docs/154/161)."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from typing import Any

from invis_alpha_os.product.forward_event_resolution import (
    bar_dates,
    cache_stale_skip_reason,
    event_bar_index,
    resolve_forward_horizons,
)
from invis_alpha_os.product.us_forward_return_validation import (
    DEFAULT_HORIZONS,
    THIN_SAMPLE_THRESHOLD,
    _iter_us_signal_rows,
    _load_bars_for_symbol,
    classify_us_signal_row_forward_outcome,
    forward_p3_progress,
)

# User-facing deficiency categories (task spec).
CATEGORY_INSUFFICIENT_FUTURE = "insufficient_future"
CATEGORY_STALE_CACHE = "stale_cache_horizon"
CATEGORY_DUPLICATE_WEEK = "duplicate_same_week_rows"
CATEGORY_UNMATCHABLE_AS_OF = "unmatchable_as_of"
CATEGORY_MISSING_CACHE = "missing_cache"
CATEGORY_PARSE_INVALID = "parse_invalid"

# P3 progress buckets (task spec).
BUCKET_MATCHABLE_NOW = "matchable_now"
BUCKET_WILL_MATCH_AFTER_DATE = "will_be_matchable_after_date"
BUCKET_NEEDS_NEW_CACHE = "needs_new_cache_after_date"
BUCKET_DEAD_OR_DUPLICATE = "dead_rows_or_duplicate_rows"

def _iso_week_key(d: date) -> tuple[int, int]:
    iso = d.isocalendar()
    return (iso[0], iso[1])


def _map_outcome_to_user_category(outcome: str, *, is_duplicate: bool) -> str:
    if is_duplicate:
        return CATEGORY_DUPLICATE_WEEK
    if outcome == "matched":
        return "matched"
    if outcome == "insufficient_future_bars":
        return CATEGORY_INSUFFICIENT_FUTURE
    if outcome == "cache_stale_event_after_cache_end":
        return CATEGORY_STALE_CACHE
    if outcome == "price_data_missing":
        return CATEGORY_MISSING_CACHE
    if outcome in {"event_date_outside_cache", "event_after_reference"}:
        return CATEGORY_UNMATCHABLE_AS_OF
    if outcome in {
        "missing_event_date",
        "missing_symbol",
        "invalid_jsonl",
        "invalid_row_type",
        "not_us_signal_row",
    }:
        return CATEGORY_PARSE_INVALID
    return "other"


def _sessions_until_matchable(
    bars: list[Any],
    event: date,
    horizons: tuple[int, ...],
) -> tuple[int | None, date | None]:
    """Sessions missing before max horizon fits; last cache date when known."""

    idx = event_bar_index(bars, event)
    if idx is None:
        return None, None
    dates = bar_dates(bars)
    if not dates:
        return None, None
    max_h = max(int(h) for h in horizons)
    need_idx = idx + max_h
    if need_idx < len(bars):
        return 0, dates[need_idx]
    sessions_short = need_idx - len(bars) + 1
    return sessions_short, dates[-1]


def _assign_p3_bucket(
    *,
    outcome: str,
    user_category: str,
    is_duplicate: bool,
    sessions_until: int | None,
    cache_last: date | None,
    event: date,
) -> str:
    if outcome == "matched":
        return BUCKET_MATCHABLE_NOW
    if is_duplicate:
        return BUCKET_DEAD_OR_DUPLICATE
    if user_category == CATEGORY_STALE_CACHE:
        return BUCKET_NEEDS_NEW_CACHE
    if user_category == CATEGORY_INSUFFICIENT_FUTURE:
        if sessions_until is not None and sessions_until > 0:
            return BUCKET_WILL_MATCH_AFTER_DATE
        return BUCKET_WILL_MATCH_AFTER_DATE
    if user_category in {
        CATEGORY_PARSE_INVALID,
        CATEGORY_MISSING_CACHE,
        CATEGORY_UNMATCHABLE_AS_OF,
    }:
        return BUCKET_DEAD_OR_DUPLICATE
    return BUCKET_DEAD_OR_DUPLICATE


def _weekly_write_effective(
    *,
    user_category: str,
    p3_bucket: str,
    event_date_source: str,
    is_duplicate: bool,
) -> bool:
    if is_duplicate:
        return False
    if p3_bucket == BUCKET_MATCHABLE_NOW:
        return False
    if user_category == CATEGORY_INSUFFICIENT_FUTURE and event_date_source == "as_of":
        return True
    if user_category == CATEGORY_INSUFFICIENT_FUTURE and event_date_source == "created_at":
        return True
    if p3_bucket == BUCKET_WILL_MATCH_AFTER_DATE:
        return True
    return False


def _classify_single_row(
    row: dict[str, Any],
    *,
    cache_dir: Any,
    horizons: tuple[int, ...],
    reference_date: date | None,
    is_duplicate: bool,
) -> dict[str, Any]:
    sym = row["symbol"]
    event: date = row["event_date"]
    if is_duplicate:
        outcome = "duplicate_same_week_row"
        user_category = CATEGORY_DUPLICATE_WEEK
        p3_bucket = BUCKET_DEAD_OR_DUPLICATE
        return {
            "symbol": sym,
            "event_date": event.isoformat(),
            "event_date_source": row.get("event_date_source"),
            "outcome": outcome,
            "user_category": user_category,
            "p3_bucket": p3_bucket,
            "sessions_until_matchable": None,
            "matchable_after_hint": None,
            "needs_new_cache_after_date": None,
            "cache_last_date": None,
            "weekly_write_effective": False,
            "is_duplicate_same_week": True,
        }
    outcome = classify_us_signal_row_forward_outcome(
        row,
        cache_dir=cache_dir,
        horizons=horizons,
        reference_date=reference_date,
        backtest_within_cache=False,
    )
    user_category = _map_outcome_to_user_category(outcome, is_duplicate=False)
    sessions_until: int | None = None
    cache_last: date | None = None
    matchable_after: str | None = None
    needs_cache_after: str | None = None

    loaded = _load_bars_for_symbol(sym, cache_dir=cache_dir)
    if loaded is not None:
        bars, _ = loaded
        dates = bar_dates(bars)
        if dates:
            cache_last = dates[-1]
        sessions_until, _proj = _sessions_until_matchable(bars, event, horizons)
        if user_category == CATEGORY_INSUFFICIENT_FUTURE and sessions_until and sessions_until > 0:
            matchable_after = (
                f"after ~{sessions_until} more US sessions from cache_end={cache_last.isoformat() if cache_last else '?'}"
            )
        if user_category == CATEGORY_STALE_CACHE and cache_last and event > cache_last:
            needs_cache_after = event.isoformat()

    p3_bucket = _assign_p3_bucket(
        outcome=outcome,
        user_category=user_category,
        is_duplicate=is_duplicate,
        sessions_until=sessions_until,
        cache_last=cache_last,
        event=event,
    )

    return {
        "symbol": sym,
        "event_date": event.isoformat(),
        "event_date_source": row.get("event_date_source"),
        "outcome": outcome,
        "user_category": user_category,
        "p3_bucket": p3_bucket,
        "sessions_until_matchable": sessions_until,
        "matchable_after_hint": matchable_after,
        "needs_new_cache_after_date": needs_cache_after,
        "cache_last_date": cache_last.isoformat() if cache_last else None,
        "weekly_write_effective": _weekly_write_effective(
            user_category=user_category,
            p3_bucket=p3_bucket,
            event_date_source=str(row.get("event_date_source") or ""),
            is_duplicate=is_duplicate,
        ),
        "is_duplicate_same_week": is_duplicate,
    }


def _duplicate_week_keys(rows: list[dict[str, Any]]) -> set[int]:
    """Mark row indices (0-based in rows list) that are duplicate same-week per symbol."""

    groups: dict[tuple[str, int, int], list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        key = (row["symbol"], *_iso_week_key(row["event_date"]))
        groups[key].append(i)
    dup_indices: set[int] = set()
    for indices in groups.values():
        if len(indices) <= 1:
            continue
        for j in indices[1:]:
            dup_indices.add(j)
    return dup_indices


def compute_us_forward_p3_stall_diagnosis(
    *,
    observation_path: Any,
    cache_dir: Any = None,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    reference_date: date | None = None,
    row_sample_limit: int = 24,
) -> dict[str, Any]:
    """Classify why normal-mode matched stays below P3 usable (read-only)."""

    from pathlib import Path

    obs_path = Path(observation_path)
    obs_rows, pre_skipped = _iter_us_signal_rows(obs_path)
    dup_indices = _duplicate_week_keys(obs_rows)

    row_details: list[dict[str, Any]] = []
    for i, row in enumerate(obs_rows):
        row_details.append(
            _classify_single_row(
                row,
                cache_dir=cache_dir,
                horizons=horizons,
                reference_date=reference_date,
                is_duplicate=i in dup_indices,
            )
        )

    user_cat_counts: Counter[str] = Counter()
    bucket_counts: Counter[str] = Counter()
    by_symbol: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "matched": 0,
            "user_category": Counter(),
            "p3_bucket": Counter(),
        }
    )
    weekly_effective_yes = 0
    weekly_effective_no = 0

    for detail in row_details:
        uc = detail["user_category"]
        bk = detail["p3_bucket"]
        user_cat_counts[uc] += 1
        bucket_counts[bk] += 1
        sym = detail["symbol"]
        by_symbol[sym]["user_category"][uc] += 1
        by_symbol[sym]["p3_bucket"][bk] += 1
        if detail["outcome"] == "matched":
            by_symbol[sym]["matched"] += 1
        if detail.get("weekly_write_effective"):
            weekly_effective_yes += 1
        else:
            weekly_effective_no += 1

    for k, v in pre_skipped.items():
        cat = _map_outcome_to_user_category(k, is_duplicate=False)
        user_cat_counts[cat] += int(v)
        bucket_counts[BUCKET_DEAD_OR_DUPLICATE] += int(v)

    matched = sum(
        1
        for d in row_details
        if d.get("outcome") == "matched" and not d.get("is_duplicate_same_week")
    )
    backtest_matched = 0
    try:
        from invis_alpha_os.product.us_forward_return_validation import (
            compute_us_forward_resolution_breakdown,
        )

        bt_bd = compute_us_forward_resolution_breakdown(
            observation_path=obs_path,
            cache_dir=cache_dir,
            horizons=horizons,
            reference_date=reference_date,
            backtest_within_cache=True,
            include_stall_diagnosis=False,
        )
        backtest_matched = int(bt_bd.get("matched_rows") or 0)
    except (FileNotFoundError, ValueError):
        backtest_matched = 0

    insuf = int(user_cat_counts.get(CATEGORY_INSUFFICIENT_FUTURE, 0))
    dup = int(user_cat_counts.get(CATEGORY_DUPLICATE_WEEK, 0))
    stale = int(user_cat_counts.get(CATEGORY_STALE_CACHE, 0))
    will_match = int(bucket_counts.get(BUCKET_WILL_MATCH_AFTER_DATE, 0))
    needs_cache = int(bucket_counts.get(BUCKET_NEEDS_NEW_CACHE, 0))
    dead = int(bucket_counts.get(BUCKET_DEAD_OR_DUPLICATE, 0))

    dominant = user_cat_counts.most_common(1)[0][0] if user_cat_counts else "none"
    samples_needed = max(0, THIN_SAMPLE_THRESHOLD - matched)

    why_stuck = {
        "headline": (
            f"normal matched={matched}/{THIN_SAMPLE_THRESHOLD}; "
            f"dominant_category={dominant}; "
            f"backtest_exploratory={backtest_matched} (not P3 milestone)"
        ),
        "normal_matched": matched,
        "backtest_within_cache_matched": backtest_matched,
        "gap_explained_by": (
            "backtest shifts events inside cache; normal mode requires future sessions after event"
        ),
        "dominant_user_category": dominant,
        "insufficient_future_rows": insuf,
        "duplicate_same_week_rows": dup,
        "stale_cache_horizon_rows": stale,
        "will_be_matchable_after_date_rows": will_match,
        "needs_new_cache_after_date_rows": needs_cache,
        "dead_or_duplicate_rows": dead,
    }

    next_actions: list[str] = [
        "Read-only: validate forward-p3-status --format markdown (P3 bucket summary)",
        f"P3 usable needs {samples_needed} more normal matched rows (not backtest count)",
    ]
    if insuf > stale and insuf > dup:
        next_actions.append(
            "Calendar wait: insufficient_future rows need more sessions after event in cache "
            "(weekly write with as_of= is effective; re-logging duplicates does not help)"
        )
        next_actions.append(
            "Optional L1 batch: weekly write only when will_be_matchable_after_date rows accumulate "
            "(not every week if bucket counts unchanged)"
        )
    if stale > 0:
        next_actions.append(
            "Gated P10 tier-1 refresh for stale_cache_horizon symbols (historical log lines stay stale)"
        )
    if dup > 0:
        next_actions.append(
            "Reduce duplicate_same_week_rows: one US signal log per symbol per ISO week"
        )
    if backtest_matched >= THIN_SAMPLE_THRESHOLD and matched < THIN_SAMPLE_THRESHOLD:
        next_actions.append(
            "Do not use --backtest-within-cache for P3 milestone; use bucket will_be_matchable_after_date"
        )

    by_symbol_out: dict[str, Any] = {}
    for sym, block in sorted(by_symbol.items()):
        by_symbol_out[sym] = {
            "matched": block["matched"],
            "user_category": dict(block["user_category"]),
            "p3_bucket": dict(block["p3_bucket"]),
        }

    return {
        "schema_version": 1,
        "observation_path": str(obs_path),
        "horizons": list(horizons),
        "matched_normal": matched,
        "samples_needed_for_usable": samples_needed,
        "p3_progress": forward_p3_progress(matched),
        "user_category_counts": dict(sorted(user_cat_counts.items(), key=lambda x: (-x[1], x[0]))),
        "p3_bucket_counts": dict(sorted(bucket_counts.items(), key=lambda x: (-x[1], x[0]))),
        "why_matched_stuck": why_stuck,
        "weekly_write_effectiveness": {
            "effective_rows": weekly_effective_yes,
            "ineffective_rows": weekly_effective_no,
            "note": (
                "effective = insufficient_future with as_of/created_at (time can add matched); "
                "ineffective = duplicate/stale/dead"
            ),
        },
        "by_symbol": by_symbol_out,
        "row_details_sample": row_details[:row_sample_limit],
        "rows_classified": len(row_details),
        "pre_skipped": dict(pre_skipped),
        "next_actions": next_actions,
        "observation_only": True,
    }


def format_p3_stall_diagnosis_markdown(diagnosis: dict[str, Any]) -> str:
    """Markdown section for P3 stall (embed in forward-p3 / us-forward reports)."""

    why = diagnosis.get("why_matched_stuck") or {}
    lines = [
        "## P3 stall diagnosis (normal mode)",
        "",
        f"- {why.get('headline', '')}",
        f"- gap: {why.get('gap_explained_by', '')}",
        "",
        "### P3 buckets",
    ]
    for key, count in (diagnosis.get("p3_bucket_counts") or {}).items():
        lines.append(f"- {key}: {count}")
    lines.extend(["", "### User categories"])
    for key, count in (diagnosis.get("user_category_counts") or {}).items():
        lines.append(f"- {key}: {count}")
    wk = diagnosis.get("weekly_write_effectiveness") or {}
    lines.extend(
        [
            "",
            "### Weekly write effectiveness",
            f"- effective_rows: {wk.get('effective_rows', 0)}",
            f"- ineffective_rows: {wk.get('ineffective_rows', 0)}",
            f"- note: {wk.get('note', '')}",
            "",
            "### Next actions (read-only)",
        ]
    )
    for action in diagnosis.get("next_actions") or []:
        lines.append(f"- {action}")
    sym_block = diagnosis.get("by_symbol") or {}
    if sym_block:
        lines.extend(["", "### By symbol (top)"])
        for sym in list(sym_block.keys())[:12]:
            block = sym_block[sym]
            lines.append(
                f"- {sym}: matched={block.get('matched', 0)} "
                f"categories={block.get('user_category', {})}"
            )
    return "\n".join(lines)
