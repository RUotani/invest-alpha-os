"""Read-only diagnosis for US forward P3 stall (3/10 thin → usable; docs/154/161)."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from statistics import median
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


def _sessions_bin(sessions: int) -> str:
    if sessions <= 5:
        return "1-5"
    if sessions <= 20:
        return "6-20"
    if sessions <= 60:
        return "21-60"
    return "61+"


def _horizon_maturity_estimate(
    row_details: list[dict[str, Any]],
    *,
    horizons: tuple[int, ...],
    matched: int,
) -> dict[str, Any]:
    """Trading-session estimate for rows that can mature into normal matched (read-only)."""

    max_h = max(int(h) for h in horizons) if horizons else 60
    pending: list[dict[str, Any]] = [
        d
        for d in row_details
        if not d.get("is_duplicate_same_week")
        and d.get("p3_bucket") == BUCKET_WILL_MATCH_AFTER_DATE
        and isinstance(d.get("sessions_until_matchable"), int)
        and int(d["sessions_until_matchable"]) > 0
    ]
    sessions_list = [int(d["sessions_until_matchable"]) for d in pending]
    hist: Counter[str] = Counter()
    for s in sessions_list:
        hist[_sessions_bin(s)] += 1

    flip_if_sessions: dict[str, int] = {}
    for milestone in (5, 20, max_h):
        flip_if_sessions[str(milestone)] = sum(
            1 for s in sessions_list if s <= milestone
        )

    dup_rows = sum(1 for d in row_details if d.get("is_duplicate_same_week"))
    unique_weekly_candidates = len(pending)

    return {
        "max_horizon_sessions": max_h,
        "will_be_matchable_after_date_rows": len(pending),
        "duplicate_same_week_rows": dup_rows,
        "sessions_until_histogram": dict(sorted(hist.items())),
        "min_sessions_until": min(sessions_list) if sessions_list else None,
        "median_sessions_until": int(median(sessions_list)) if sessions_list else None,
        "p90_sessions_until": (
            int(sorted(sessions_list)[int(0.9 * (len(sessions_list) - 1))])
            if len(sessions_list) >= 2
            else (sessions_list[0] if sessions_list else None)
        ),
        "projected_normal_matched_if_cache_extends_sessions": flip_if_sessions,
        "note": (
            "Uses US daily bars as trading sessions; dates after cache_end are session counts only "
            "(not calendar holidays)"
        ),
        "l1_gate": {
            "frequency": "monthly 1-2 times",
            "run_l1_when": (
                "will_be_matchable_after_date_rows increases vs prior forward-p3-status JSON "
                "OR median_sessions_until decreases"
            ),
            "skip_l1_when": (
                "only duplicate_same_week_rows grows (same ISO week re-logs); "
                f"current duplicate_rows={dup_rows}"
            ),
            "current_will_match_rows": len(pending),
            "current_matched_normal": matched,
            "unique_horizon_candidates": unique_weekly_candidates,
        },
    }


def build_p3_horizon_match_timeline(
    *,
    row_details: list[dict[str, Any]],
    matched_normal: int,
    thin_threshold: int = THIN_SAMPLE_THRESHOLD,
    max_rows: int = 16,
) -> dict[str, Any]:
    """Read-only: rows in log that can mature to normal matched via cache horizon (docs/161)."""

    pending = [
        d
        for d in row_details
        if not d.get("is_duplicate_same_week")
        and d.get("p3_bucket") == BUCKET_WILL_MATCH_AFTER_DATE
        and isinstance(d.get("sessions_until_matchable"), int)
        and int(d["sessions_until_matchable"]) > 0
    ]
    pending.sort(key=lambda d: int(d["sessions_until_matchable"]))
    sessions_list = [int(d["sessions_until_matchable"]) for d in pending]
    needed = max(0, thin_threshold - matched_normal)

    def cumulative_matched_at(max_sessions: int) -> int:
        flip = sum(1 for s in sessions_list if s <= max_sessions)
        return matched_normal + flip

    min_s = min(sessions_list) if sessions_list else None
    timeline_rows: list[dict[str, Any]] = []
    for d in pending[:max_rows]:
        timeline_rows.append(
            {
                "symbol": d.get("symbol"),
                "event_date": d.get("event_date"),
                "sessions_until_matchable": d.get("sessions_until_matchable"),
                "matchable_after_hint": d.get("matchable_after_hint"),
                "cache_last_date": d.get("cache_last_date"),
                "weekly_write_effective": d.get("weekly_write_effective"),
            }
        )

    headline = (
        f"{len(pending)} log row(s) await cache horizon (normal matched={matched_normal}/{thin_threshold})"
    )
    if min_s is not None:
        headline += (
            f"; +{cumulative_matched_at(min_s) - matched_normal} at min_sessions={min_s} "
            f"(projected total {cumulative_matched_at(min_s)})"
        )

    return {
        "schema_version": 1,
        "matched_normal": matched_normal,
        "thin_threshold": thin_threshold,
        "samples_needed_for_usable": needed,
        "pending_horizon_rows": len(pending),
        "min_sessions_until": min_s,
        "median_sessions_until": int(median(sessions_list)) if sessions_list else None,
        "projected_matched_at_min_sessions": cumulative_matched_at(min_s) if min_s is not None else None,
        "projected_matched_at_median_sessions": (
            cumulative_matched_at(int(median(sessions_list)))
            if sessions_list
            else None
        ),
        "headline": headline,
        "timeline_rows": timeline_rows,
        "note": (
            "Rows already in observation_log — they mature when US daily cache extends; "
            "weekly L1 does not add these rows. ISO-week rollover unlocks new write_now rows separately."
        ),
        "observation_only": True,
    }


def format_p3_horizon_match_timeline_markdown(timeline: dict[str, Any]) -> str:
    lines = [
        "## P3 horizon match timeline (read-only)",
        "",
        f"- {timeline.get('headline', '')}",
        f"- samples_needed_for_usable: {timeline.get('samples_needed_for_usable', 0)}",
        f"- note: {timeline.get('note', '')}",
    ]
    if timeline.get("min_sessions_until") is not None:
        lines.append(f"- min_sessions_until: {timeline['min_sessions_until']}")
    if timeline.get("projected_matched_at_min_sessions") is not None:
        lines.append(
            f"- projected_matched_at_min_sessions: {timeline['projected_matched_at_min_sessions']}"
        )
    rows = timeline.get("timeline_rows") or []
    if rows:
        lines.append("")
        lines.append("### Soonest horizon rows")
        for row in rows[:12]:
            lines.append(
                f"- {row.get('symbol')} event={row.get('event_date')} "
                f"sessions_until={row.get('sessions_until_matchable')} "
                f"after={row.get('matchable_after_hint') or row.get('cache_last_date')}"
            )
    return "\n".join(lines)


def _symbol_week_groups(rows: list[dict[str, Any]]) -> dict[tuple[str, int, int], list[int]]:
    groups: dict[tuple[str, int, int], list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        key = (row["symbol"], *_iso_week_key(row["event_date"]))
        groups[key].append(i)
    return groups


def _duplicate_week_keys(rows: list[dict[str, Any]]) -> set[int]:
    """Mark row indices (0-based in rows list) that are duplicate same-week per symbol."""

    dup_indices: set[int] = set()
    for indices in _symbol_week_groups(rows).values():
        if len(indices) <= 1:
            continue
        for j in indices[1:]:
            dup_indices.add(j)
    return dup_indices


def _first_per_week_indices(rows: list[dict[str, Any]]) -> set[int]:
    """Earliest row index per (symbol, ISO week) — counterfactual dedupe set."""

    return {indices[0] for indices in _symbol_week_groups(rows).values() if indices}


def _dedupe_counterfactual(
    obs_rows: list[dict[str, Any]],
    *,
    cache_dir: Any,
    horizons: tuple[int, ...],
    reference_date: date | None,
    matched_with_duplicate_policy: int,
) -> dict[str, Any]:
    """Read-only: P3 counts if only first row per symbol+ISO week is considered."""

    groups = _symbol_week_groups(obs_rows)
    first = _first_per_week_indices(obs_rows)
    cf_buckets: Counter[str] = Counter()
    cf_cats: Counter[str] = Counter()
    cf_matched = 0
    cf_will_match = 0
    for i, row in enumerate(obs_rows):
        if i not in first:
            continue
        detail = _classify_single_row(
            row,
            cache_dir=cache_dir,
            horizons=horizons,
            reference_date=reference_date,
            is_duplicate=False,
        )
        cf_buckets[detail["p3_bucket"]] += 1
        cf_cats[detail["user_category"]] += 1
        if detail["outcome"] == "matched":
            cf_matched += 1
        if detail["p3_bucket"] == BUCKET_WILL_MATCH_AFTER_DATE:
            cf_will_match += 1

    multi_groups = [(k, len(v)) for k, v in groups.items() if len(v) > 1]
    multi_groups.sort(key=lambda item: (-item[1], item[0][0], item[0][1], item[0][2]))
    top_dupes = [
        {
            "symbol": sym,
            "iso_year": yr,
            "iso_week": wk,
            "row_count": count,
            "extras_suppressed": count - 1,
        }
        for (sym, yr, wk), count in multi_groups[:10]
    ]

    suppressed = len(obs_rows) - len(first)
    return {
        "unique_symbol_weeks": len(first),
        "duplicate_rows_suppressed": suppressed,
        "multi_log_week_groups": len(multi_groups),
        "matched_with_current_policy": matched_with_duplicate_policy,
        "matched_first_per_week_only": cf_matched,
        "matched_delta_if_counted_first_only": cf_matched - matched_with_duplicate_policy,
        "will_be_matchable_first_per_week": cf_will_match,
        "samples_needed_counterfactual": max(0, THIN_SAMPLE_THRESHOLD - cf_matched),
        "p3_bucket_counts_first_per_week": dict(sorted(cf_buckets.items(), key=lambda x: (-x[1], x[0]))),
        "user_category_counts_first_per_week": dict(sorted(cf_cats.items(), key=lambda x: (-x[1], x[0]))),
        "top_duplicate_week_groups": top_dupes,
        "note": (
            "Counterfactual only — does not delete observation_log lines. "
            "Use to see P3 path if weekly write logs once per symbol per ISO week."
        ),
    }


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
            "Reduce duplicate_same_week_rows: one US signal log per symbol per ISO week "
            "(see dedupe_counterfactual — re-logging same week does not increase matched)"
        )
        next_actions.append(
            "Defer L1 until will_be_matchable_first_per_week rises; duplicates inflate row count only"
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

    horizon_maturity = _horizon_maturity_estimate(
        row_details, horizons=horizons, matched=matched
    )
    p3_horizon_timeline = build_p3_horizon_match_timeline(
        row_details=row_details,
        matched_normal=matched,
        thin_threshold=THIN_SAMPLE_THRESHOLD,
    )
    dedupe_counterfactual = _dedupe_counterfactual(
        obs_rows,
        cache_dir=cache_dir,
        horizons=horizons,
        reference_date=reference_date,
        matched_with_duplicate_policy=matched,
    )
    if dedupe_counterfactual.get("matched_first_per_week_only", 0) != matched:
        why_stuck["counterfactual_matched_first_per_week"] = dedupe_counterfactual[
            "matched_first_per_week_only"
        ]

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
        "horizon_maturity": horizon_maturity,
        "p3_horizon_timeline": p3_horizon_timeline,
        "dedupe_counterfactual": dedupe_counterfactual,
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


def planned_writes_from_batch_previews(batch_previews: dict[str, Any]) -> list[dict[str, str]]:
    """Extract symbol + cache as_of (last_date) from weekly batch preview payload."""

    out: list[dict[str, str]] = []
    for preview in batch_previews.get("previews") or []:
        if not isinstance(preview, dict):
            continue
        sym = preview.get("symbol")
        last_date = preview.get("last_date")
        if sym and last_date:
            out.append({"symbol": str(sym), "last_date": str(last_date)})
    return out


def default_watchlist_cache_planned_writes(*, path_base: Path | None = None) -> tuple[list[dict[str, str]], int]:
    """Planned as_of writes from on-disk tier watchlist caches (read-only)."""

    from invis_alpha_os.config.paths import ROOT_DIR
    from invis_alpha_os.config.us_watchlist import load_us_watchlist_tickers
    from invis_alpha_os.data.us_daily_bars_cache import load_us_daily_bars_json_file

    root = path_base or ROOT_DIR
    cache_dir = root / "outputs" / "market_data" / "us_daily_bars"
    planned: list[dict[str, str]] = []
    missing_cache = 0
    for sym in load_us_watchlist_tickers():
        cache_path = cache_dir / f"{sym}.json"
        if not cache_path.is_file():
            missing_cache += 1
            continue
        loaded = load_us_daily_bars_json_file(cache_path, expect_symbol=sym)
        if loaded is None:
            missing_cache += 1
            continue
        bars, _meta = loaded
        dates = bar_dates(bars)
        if not dates:
            missing_cache += 1
            continue
        planned.append({"symbol": sym, "last_date": dates[-1].isoformat()})
    return planned, missing_cache


def build_duplicate_week_write_preflight(
    *,
    observation_path: Path,
    planned_writes: list[dict[str, str]] | None = None,
    path_base: Path | None = None,
) -> dict[str, Any]:
    """Read-only: planned cache-as_of writes that would duplicate an existing symbol+ISO week."""

    if not observation_path.is_file():
        return {
            "schema_version": 1,
            "status": "missing_log",
            "observation_path": str(observation_path),
            "would_duplicate_count": 0,
            "would_new_symbol_week_count": 0,
            "warnings": [],
            "observation_only": True,
        }

    obs_rows, _ = _iter_us_signal_rows(observation_path)
    groups = _symbol_week_groups(obs_rows)

    warnings: list[dict[str, Any]] = []
    new_week_writes = 0
    missing_cache = 0
    planned = list(planned_writes or [])

    if not planned:
        planned, missing_cache = default_watchlist_cache_planned_writes(path_base=path_base)

    for item in planned:
        sym = str(item.get("symbol") or "").strip().upper()
        raw = item.get("event_date") or item.get("last_date")
        if not sym or not raw:
            continue
        try:
            evt = date.fromisoformat(str(raw)[:10])
        except ValueError:
            continue
        key = (sym, *_iso_week_key(evt))
        existing = groups.get(key, [])
        if existing:
            warnings.append(
                {
                    "symbol": sym,
                    "iso_year": key[1],
                    "iso_week": key[2],
                    "event_date": evt.isoformat(),
                    "existing_rows_in_log": len(existing),
                    "p3_effect": "duplicate_same_week_rows (ineffective for P3)",
                }
            )
        else:
            new_week_writes += 1

    skip_items = [
        {"symbol": w["symbol"], "last_date": w["event_date"]} for w in warnings
    ]
    from invis_alpha_os.product.us_signal_iso_week_dedupe import estimate_p3_iso_week_rollover

    rollover = estimate_p3_iso_week_rollover(skip_duplicate=skip_items)

    return {
        "schema_version": 1,
        "status": "ok",
        "observation_path": str(observation_path),
        "planned_symbol_count": len(planned),
        "would_duplicate_count": len(warnings),
        "would_new_symbol_week_count": new_week_writes,
        "missing_cache_symbols": missing_cache,
        "warnings": warnings[:25],
        "iso_week_rollover": rollover,
        "recommendation": (
            "Skip re-logging symbols whose ISO week already exists in observation_log; "
            "prefer one row per symbol per ISO week for P3 forward validation."
        ),
        "observation_only": True,
    }


def build_p3_us_forward_portfolio_summary(
    *,
    stall_diagnosis: dict[str, Any],
    us_matched: int,
    thin_threshold: int = THIN_SAMPLE_THRESHOLD,
) -> dict[str, Any]:
    """Compact machine-readable block for forward-p3-status / portfolio readiness."""

    buckets = stall_diagnosis.get("p3_bucket_counts") or {}
    hm = stall_diagnosis.get("horizon_maturity") or {}
    dc = stall_diagnosis.get("dedupe_counterfactual") or {}
    matched = int(stall_diagnosis.get("matched_normal", us_matched))
    needed = stall_diagnosis.get("samples_needed_for_usable")
    if needed is None:
        needed = max(0, thin_threshold - matched)
    p3_prog = stall_diagnosis.get("p3_progress") or forward_p3_progress(matched)
    return {
        "schema_version": 1,
        "matched_normal": matched,
        "thin_threshold": thin_threshold,
        "samples_needed_for_usable": needed,
        "p3_progress_label": p3_prog.get("progress_label"),
        "p3_buckets": {
            "matchable_now": buckets.get(BUCKET_MATCHABLE_NOW, 0),
            "will_be_matchable_after_date": buckets.get(BUCKET_WILL_MATCH_AFTER_DATE, 0),
            "needs_new_cache_after_date": buckets.get(BUCKET_NEEDS_NEW_CACHE, 0),
            "dead_rows_or_duplicate_rows": buckets.get(BUCKET_DEAD_OR_DUPLICATE, 0),
        },
        "user_category_counts": dict(stall_diagnosis.get("user_category_counts") or {}),
        "why_matched_stuck_headline": (stall_diagnosis.get("why_matched_stuck") or {}).get(
            "headline"
        ),
        "horizon_maturity": {
            "will_be_matchable_after_date_rows": hm.get("will_be_matchable_after_date_rows"),
            "median_sessions_until": hm.get("median_sessions_until"),
            "l1_batch_recommended": (hm.get("l1_gate") or {}).get("run_l1_when"),
        },
        "horizon_timeline_headline": (stall_diagnosis.get("p3_horizon_timeline") or {}).get(
            "headline"
        ),
        "dedupe_counterfactual": {
            "matched_first_per_week_only": dc.get("matched_first_per_week_only"),
            "duplicate_rows_suppressed": dc.get("duplicate_rows_suppressed"),
            "unique_symbol_weeks": dc.get("unique_symbol_weeks"),
            "will_be_matchable_first_per_week": dc.get("will_be_matchable_first_per_week"),
            "samples_needed_counterfactual": dc.get("samples_needed_counterfactual"),
        },
        "observation_only": True,
    }


def format_duplicate_week_preflight_markdown(preflight: dict[str, Any]) -> str:
    lines = [
        "## Duplicate ISO-week write preflight (read-only)",
        "",
        f"- would_duplicate_count: {preflight.get('would_duplicate_count', 0)}",
        f"- would_new_symbol_week_count: {preflight.get('would_new_symbol_week_count', 0)}",
        f"- recommendation: {preflight.get('recommendation', '')}",
    ]
    for warn in preflight.get("warnings") or []:
        lines.append(
            f"- {warn.get('symbol')} {warn.get('iso_year')}-W{int(warn.get('iso_week', 0)):02d}: "
            f"{warn.get('existing_rows_in_log')} existing rows (event={warn.get('event_date')})"
        )
    rollover = preflight.get("iso_week_rollover") or {}
    if rollover.get("earliest_next_iso_week_start"):
        lines.extend(
            [
                "",
                f"- earliest_next_iso_week_start: {rollover.get('earliest_next_iso_week_start')}",
                f"- days_until_earliest_rollover: {rollover.get('days_until_earliest_rollover')}",
                f"- l1_unblock_hint: {rollover.get('l1_unblock_hint', '')}",
            ]
        )
    return "\n".join(lines)


def format_p3_us_forward_portfolio_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "## P3 US forward portfolio summary",
        "",
        f"- matched_normal: {summary.get('matched_normal', 0)} / thin_threshold: {summary.get('thin_threshold', 10)}",
        f"- samples_needed_for_usable: {summary.get('samples_needed_for_usable', 0)}",
        f"- p3_progress: {summary.get('p3_progress_label', '')}",
    ]
    if summary.get("why_matched_stuck_headline"):
        lines.append(f"- stall: {summary['why_matched_stuck_headline']}")
    buckets = summary.get("p3_buckets") or {}
    if buckets:
        lines.append("")
        lines.append("### P3 buckets")
        for key, count in buckets.items():
            lines.append(f"- {key}: {count}")
    dc = summary.get("dedupe_counterfactual") or {}
    if dc:
        lines.extend(
            [
                "",
                "### Dedupe counterfactual",
                f"- matched_first_per_week_only: {dc.get('matched_first_per_week_only', 0)}",
                f"- duplicate_rows_suppressed: {dc.get('duplicate_rows_suppressed', 0)}",
                f"- will_be_matchable_first_per_week: {dc.get('will_be_matchable_first_per_week', 0)}",
            ]
        )
    return "\n".join(lines)


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
        ]
    )
    hm = diagnosis.get("horizon_maturity") or {}
    if hm:
        lines.extend(
            [
                "",
                "### Horizon maturity estimate (trading sessions)",
                f"- will_be_matchable_after_date_rows: {hm.get('will_be_matchable_after_date_rows', 0)}",
                f"- duplicate_same_week_rows: {hm.get('duplicate_same_week_rows', 0)}",
                f"- median_sessions_until: {hm.get('median_sessions_until')}",
                f"- sessions_until_histogram: {hm.get('sessions_until_histogram', {})}",
                f"- projected_normal_matched_if_cache_extends_sessions: "
                f"{hm.get('projected_normal_matched_if_cache_extends_sessions', {})}",
                f"- note: {hm.get('note', '')}",
            ]
        )
        gate = hm.get("l1_gate") or {}
        if gate:
            lines.extend(
                [
                    "",
                    "### L1 batch gate (monthly 1-2x)",
                    f"- run_l1_when: {gate.get('run_l1_when', '')}",
                    f"- skip_l1_when: {gate.get('skip_l1_when', '')}",
                    f"- current_will_match_rows: {gate.get('current_will_match_rows', 0)}",
                ]
            )
    dc = diagnosis.get("dedupe_counterfactual") or {}
    if dc:
        lines.extend(
            [
                "",
                "### Dedupe counterfactual (first row per symbol+ISO week)",
                f"- unique_symbol_weeks: {dc.get('unique_symbol_weeks', 0)}",
                f"- duplicate_rows_suppressed: {dc.get('duplicate_rows_suppressed', 0)}",
                f"- matched_first_per_week_only: {dc.get('matched_first_per_week_only', 0)}",
                f"- will_be_matchable_first_per_week: {dc.get('will_be_matchable_first_per_week', 0)}",
                f"- samples_needed_counterfactual: {dc.get('samples_needed_counterfactual', 0)}",
                f"- note: {dc.get('note', '')}",
            ]
        )
        top = dc.get("top_duplicate_week_groups") or []
        if top:
            lines.append("")
            lines.append("Top duplicate week groups (symbol, ISO week, rows):")
            for item in top[:6]:
                lines.append(
                    f"- {item.get('symbol')} {item.get('iso_year')}-W{item.get('iso_week'):02d}: "
                    f"{item.get('row_count')} rows ({item.get('extras_suppressed')} extras)"
                )
    lines.extend(["", "### Next actions (read-only)"])
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
