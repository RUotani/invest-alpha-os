"""Render Observation-only momentum signal sections for daily reports (Main E / Main F / Main I)."""

from __future__ import annotations

import statistics
from collections.abc import Callable, Sequence
from invis_alpha_os.config.jp_watchlist import load_jp_watchlist_tickers, normalize_jquants_equity_code
from invis_alpha_os.data.jquants_daily_bars_cache import try_load_cached_daily_bars
from invis_alpha_os.signals.momentum import (
    SCORE_V2_OVERHEAT_R20,
    SCORE_V2_OVERHEAT_R60,
    DailyBar,
    MomentumBreakdown,
    build_momentum_signals,
    synthetic_bars_for_code,
)


WATCH_NOTE_QUALITATIVE_TREND = "quality_trend"
WATCH_NOTE_OVERHEATED_TREND = "overheated_trend"
WATCH_NOTE_PULLBACK_UPTREND = "pullback_in_uptrend"
WATCH_NOTE_WEAK_MIXED = "weak_or_mixed"
WATCH_NOTE_LIMITED_HISTORY = "limited_history"


def momentum_score_v2_glossary_lines() -> list[str]:
    """Short table legend for daily markdown (Observation only — no advisory language)."""

    return [
        "**Momentum Score v2 table (concise legend):**",
        "- **Sv2:** Momentum Score v2 composite. Higher means stronger multi-horizon trend quality in this score.",
        "- **HiDist:** Distance versus the trailing ~252-session high excluding the latest bar — values closer to **0%** sit nearer the range top.",
        "- **VolR:** Latest volume divided by the prior **25**-session average (excluding the latest bar).",
        '- **Flag / Watch:** Observation-only condition flags (**overheat**, thin history); **Watch** is a coarse **prioritization tag** for follow-up scans.',
        '- **Overheat:** Very strong trailing strength — elevated **chase / giveback** caution in the mechanic (not predictive).',
        "- Observation only — not buy/sell advice. No automatic trading.",
        "",
    ]


def classify_watch_note(
    ranked: Sequence[MomentumBreakdown],
    m: MomentumBreakdown,
) -> str:
    """Single deterministic tag per ticker for skim-friendly grouping (prioritization, not recommendation)."""

    dq = dict(m.data_quality)
    if not dq.get("enough_120d", False):
        return WATCH_NOTE_LIMITED_HISTORY

    r5_down = m.r5 is not None and m.r5 < 0
    long_horizons_up = (
        m.r20 is not None
        and m.r20 > 0
        and m.r60 is not None
        and m.r60 > 0
        and m.r120 is not None
        and m.r120 > 0
    )
    if r5_down and long_horizons_up:
        return WATCH_NOTE_PULLBACK_UPTREND

    if m.overheat_flag:
        return WATCH_NOTE_OVERHEATED_TREND

    batch = [x.score_v2 for x in ranked]
    median_sv2 = statistics.median(batch) if batch else 0
    threshold = max(int(round(median_sv2)), 4)

    if m.trend_quality == "3_of_3_positive" and m.score_v2 >= threshold:
        return WATCH_NOTE_QUALITATIVE_TREND

    return WATCH_NOTE_WEAK_MIXED


def _codes_in_rank_order_for_note(
    ranked: Sequence[MomentumBreakdown],
    note_by_code: dict[str, str],
    wanted: str,
) -> list[str]:
    return [m.code for m in ranked if note_by_code.get(m.code) == wanted]


def observations_momentum_cache_only_lines(
    ranked: Sequence[MomentumBreakdown],
    note_by_code: dict[str, str],
    *,
    n_skipped_no_cache: int,
) -> list[str]:
    """Deterministic bullet block from tier groupings (typically 3–6 lines)."""

    ranked_list = list(ranked)
    if not ranked_list:
        return []

    lines: list[str] = [
        "### Observations — Momentum (cache-only)",
        "",
    ]
    bullets: list[str] = []

    ql = _codes_in_rank_order_for_note(ranked_list, note_by_code, WATCH_NOTE_QUALITATIVE_TREND)
    if ql:
        bullets.append(f"- **Top quality trend:** {', '.join(ql)}.")

    oh = _codes_in_rank_order_for_note(ranked_list, note_by_code, WATCH_NOTE_OVERHEATED_TREND)
    if oh:
        bullets.append(f"- **Overheat watch:** {', '.join(oh)}.")

    pb = _codes_in_rank_order_for_note(ranked_list, note_by_code, WATCH_NOTE_PULLBACK_UPTREND)
    if pb:
        bullets.append(f"- **Pullback within uptrend:** {', '.join(pb)}.")

    lk = _codes_in_rank_order_for_note(ranked_list, note_by_code, WATCH_NOTE_LIMITED_HISTORY)
    if lk:
        bullets.append(
            "- **Limited-history context:** "
            + ", ".join(lk)
            + " — Score v2 full window not met (~120 sessions).",
        )

    wm = _codes_in_rank_order_for_note(ranked_list, note_by_code, WATCH_NOTE_WEAK_MIXED)
    if wm:
        bullets.append(f"- **Weak / mixed trend:** {', '.join(wm)}.")

    if n_skipped_no_cache == 0:
        bullets.append(
            "- **Bars coverage:** **All rows are cache-backed** (displayed rankings); synthetic fallback **0**.",
        )
    else:
        bullets.append(
            "- **Bars coverage:** Ranked rows are cache-backed; synthetic fallback **0**; "
            + f"**{n_skipped_no_cache}** watchlist ticker(s) skipped locally (missing cache).",
        )

    lines.extend(bullets)
    lines.append("")
    return lines


_ACTION_WATCHLIST_BUCKETS: tuple[tuple[str, str, str], ...] = (
    (
        WATCH_NOTE_QUALITATIVE_TREND,
        "Monitor strength / quality trend",
        "Trend quality is broad across horizons. Next checks: valuation, catalyst, latest price/volume, earnings schedule.",
    ),
    (
        WATCH_NOTE_OVERHEATED_TREND,
        "Overheat / chase-risk watch",
        "Strong trailing returns but elevated chase/giveback risk. Next checks: pullback level, volume confirmation, news/event driver.",
    ),
    (
        WATCH_NOTE_PULLBACK_UPTREND,
        "Pullback within uptrend",
        "Short-term weakness inside positive medium/long trend. Next checks: support level, reversal volume, whether r20/r60 remains positive.",
    ),
    (
        WATCH_NOTE_WEAK_MIXED,
        "Weak or mixed trend",
        "Trend confirmation is incomplete. Next checks: whether r20 turns positive, sector relative strength, downside risk.",
    ),
    (
        WATCH_NOTE_LIMITED_HISTORY,
        "Limited history",
        "Score reliability is lower due to limited bars. Next checks: listing/date history, liquidity, structural reason for short history.",
    ),
)


def action_watchlist_momentum_cache_only_lines(
    ranked: Sequence[MomentumBreakdown],
    note_by_code: dict[str, str],
) -> list[str]:
    """Grouped next-check cues from ``watch_note`` tags — observation-only, rank order preserved."""

    ranked_list = list(ranked)
    if not ranked_list:
        return []

    lines: list[str] = [
        "### Action Watchlist — Momentum (observation only)",
        "",
        "Grouped from the **Watch** column above; for manual follow-up checks only.",
        "",
    ]
    wrote_any = False
    for watch_key, title, cue in _ACTION_WATCHLIST_BUCKETS:
        codes = _codes_in_rank_order_for_note(ranked_list, note_by_code, watch_key)
        if not codes:
            continue
        wrote_any = True
        joined = ", ".join(codes)
        lines.extend(
            [
                f"#### {title}",
                "",
                f"**Codes:** {joined}",
                "",
                cue,
                "",
            ],
        )
    if not wrote_any:
        return []
    return lines


def _bars_source_summary_line(sources: dict[str, str]) -> str:
    if not sources:
        return "**Bars source:** (no JP watchlist codes)."
    n_cache = sum(1 for s in sources.values() if s == "cache")
    n_synth = sum(1 for s in sources.values() if s == "synthetic")
    n = len(sources)
    if n_cache == n:
        return (
            "**Bars source:** `cache` — local files under `outputs/market_data/jquants_daily_bars/{code}.json` "
            "(sanitized OHLCV only)."
        )
    if n_synth == n:
        return (
            "**Bars source:** `synthetic` — deterministic placeholder OHLCV per ticker "
            "(no cache file). **Not actionable** as a live or vendor-data signal."
        )
    return (
        f"**Bars source:** **mixed** — `cache`: {n_cache} ticker(s), `synthetic` fallback: {n_synth} ticker(s). "
        "Synthetic portions are **not actionable** as live signals."
    )


def _fmt_pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.2f}%"


def _abbrev_labels(m: MomentumBreakdown) -> str:
    """Concise momentum-style tags for Markdown width."""

    chips: list[str] = []
    if m.labels:
        chips.append(", ".join(m.labels))
    chips.append(m.trend_quality.replace("_", " "))
    if m.overheat_flag:
        chips.append("overheat")
    return "; ".join(chips) if chips else "—"


def _flag_cell(m: MomentumBreakdown) -> str:
    if m.overheat_flag:
        parts = []
        if m.r20 is not None and m.r20 > SCORE_V2_OVERHEAT_R20:
            parts.append("hot_r20")
        if m.r60 is not None and m.r60 > SCORE_V2_OVERHEAT_R60:
            parts.append("hot_r60")
        return "overheat (" + ",".join(parts) + ")"
    if not dict(m.data_quality).get("enough_120d", False):
        return "thin_hist"
    return "—"


def _hi_dist_cell(m: MomentumBreakdown) -> str:
    """HiDist — distance to prior-window high (+ breakout hint)."""

    if m.high_52w_breakout:
        tag = "brk"
    else:
        tag = ""
    d = _fmt_pct(m.high_52w_distance_pct)
    if tag and d != "—":
        return f"{d} ({tag})"
    if tag:
        return tag
    return d


def _vol_r_cell(m: MomentumBreakdown) -> str:
    if m.volume_ratio_25d is None:
        return "—"
    return f"{m.volume_ratio_25d:.2f}x"


def _append_ranking_table(
    lines: list[str],
    ranked: list[MomentumBreakdown],
    bars_source_for_code: dict[str, str],
) -> dict[str, str]:
    """Append ranking markdown; return ``code -> watch_note`` for observations."""

    note_by = {m.code: classify_watch_note(ranked, m) for m in ranked}
    lines.extend(momentum_score_v2_glossary_lines())
    lines.append(
        "**Momentum Score v2:** ranked by ``score_v2`` (desc), tie-break r20, r60, then wire code.",
    )
    lines.append("")
    lines.append("Legacy integer ``score`` still appears in CLI JSON next to ``score_v2``.")
    lines.append("")
    lines.append(
        "| Rank | Code | Sv2 | Key | r5 | r20 | r60 | HiDist | VolR | Flag | Watch | Bars src |",
    )
    lines.append(
        "|------|------|-----|-----|-----|-----|-----|--------|------|------|-------|----------|",
    )
    for i, m in enumerate(ranked, start=1):
        key = _abbrev_labels(m)
        r5 = _fmt_pct(m.r5)
        r20 = _fmt_pct(m.r20)
        r60 = _fmt_pct(m.r60)
        bsrc = bars_source_for_code.get(m.code, "—")
        watch = note_by[m.code]
        lines.append(
            f"| {i} | {m.code} | {m.score_v2} | {key} | {r5} | {r20} | {r60} | "
            f"{_hi_dist_cell(m)} | {_vol_r_cell(m)} | {_flag_cell(m)} | {watch} | {bsrc} |",
        )
    lines.append("")
    return note_by


def _default_jp_cache_only_intro_lines() -> list[str]:
    return [
        "Observation only — not buy/sell advice. No automatic trading.",
        "",
        "**Bars source:** `cache` — local sanitized OHLCV files only "
        "(`outputs/market_data/jquants_daily_bars/{code}.json`). "
        "**No synthetic bars** are generated for this section.",
        "",
    ]


def _tail_pointer_signals_json_lines() -> list[str]:
    return [
        "Full per-ticker fields (`score_v2_components`, `data_quality`, horizons) are available from "
        "``alpha-os signals`` JSON output.",
        "",
    ]


def render_momentum_cache_only_for_wire_codes(
    wire_codes_ordered: Sequence[str],
    *,
    section_heading: str = "## Momentum Signals — Cache Only",
    load_cached_bars: Callable[[str], tuple[list[DailyBar], str] | None] | None = None,
    intro_banner_lines: Sequence[str] | None = None,
    trailing_note_before_table_lines: Sequence[str] | None = None,
    empty_ranked_fallback_line: str = "- *(no tickers with local cache files in the JP watchlist)*",
) -> str:
    """Cache-only momentum block for explicit wire codes — no watchlist imports.

    ``load_cached_bars`` defaults to ``try_load_cached_daily_bars`` (local JSON under jquants tree).
    JP callers should supply codes already validated via ``normalize_jquants_equity_code``.
    """

    loader = load_cached_bars or try_load_cached_daily_bars
    mapping: dict[str, list[DailyBar]] = {}
    skipped_no_cache: list[str] = []
    for w in wire_codes_ordered:
        got = loader(w)
        if got is not None:
            mapping[w] = got[0]
        else:
            skipped_no_cache.append(w)

    ranked = build_momentum_signals(mapping)
    bars_src = {c: "cache" for c in mapping}

    preamble = list(intro_banner_lines) if intro_banner_lines is not None else _default_jp_cache_only_intro_lines()
    before_table = (
        list(trailing_note_before_table_lines)
        if trailing_note_before_table_lines is not None
        else _tail_pointer_signals_json_lines()
    )

    lines: list[str] = [section_heading, "", *preamble]
    if skipped_no_cache:
        codes = ", ".join(skipped_no_cache)
        lines.append(f"**Skipped (no local cache file):** {len(skipped_no_cache)} — {codes}.")
        lines.append("")
    lines.extend(before_table)
    if not ranked:
        lines.append(empty_ranked_fallback_line)
        lines.append("")
        return "\n".join(lines)

    note_by = _append_ranking_table(lines, ranked, bars_src)
    lines.extend(
        observations_momentum_cache_only_lines(
            ranked,
            note_by,
            n_skipped_no_cache=len(skipped_no_cache),
        ),
    )
    lines.extend(action_watchlist_momentum_cache_only_lines(ranked, note_by))
    return "\n".join(lines)


def render_momentum_signals_cache_only_section() -> str:
    """Build ``## Momentum Signals — Cache Only`` — JP watchlist + local cache-only rows."""

    tickers = load_jp_watchlist_tickers()
    wire_codes: list[str] = []
    for raw in tickers:
        code = normalize_jquants_equity_code(str(raw))
        if code is not None:
            wire_codes.append(code)
    return render_momentum_cache_only_for_wire_codes(wire_codes)


def render_momentum_signals_mixed_section() -> str:
    """Build mixed cache + synthetic fallback section for system validation (not clean research ranking)."""

    tickers = load_jp_watchlist_tickers()
    mapping: dict[str, list[DailyBar]] = {}
    sources: dict[str, str] = {}
    for raw in tickers:
        code = normalize_jquants_equity_code(str(raw))
        if code is None:
            continue
        got = try_load_cached_daily_bars(code)
        if got is not None:
            mapping[code] = got[0]
            sources[code] = "cache"
        else:
            mapping[code] = synthetic_bars_for_code(code)
            sources[code] = "synthetic"

    ranked = build_momentum_signals(mapping)
    src_line = _bars_source_summary_line(sources)

    head = [
        "## Momentum Signals — Mixed / System Validation",
        "",
        "Observation only — not buy/sell advice. No automatic trading.",
        "",
    ]

    if not ranked:
        lines = [*head, "- (no JP watchlist codes produced bar series)", ""]
        return "\n".join(lines)

    n_synth = sum(1 for s in sources.values() if s == "synthetic")
    all_cached_snapshot = bool(sources) and n_synth == 0

    if all_cached_snapshot:
        purpose = [
            "**Purpose:** Mixed **pipeline / system validation** block — for this JP watchlist snapshot **every row "
            "uses local cache** (synthetic fallback **0**), so the ranking matches the cache-backed dataset while "
            "keeping the mixed renderer path exercised.",
            "",
            "**All rows are cache-backed.**",
            "Synthetic OHLCV fallback remains **not actionable** when present; **this snapshot has none**.",
            "",
            src_line,
            "**Momentum Score v2** ranking (legacy labels still listed under **Key** when present).",
            "",
        ]
    else:
        purpose = [
            "**Purpose:** Mixed ranking for **pipeline / system validation**. When a ticker lacks a local cache file, "
            "a **synthetic fallback** series is used so the mover still appears in the table. "
            "That is misleading for pure investment research because synthetic rows can outrank cached rows.",
            "",
            "**Synthetic fallback:** Deterministic placeholder OHLCV is inserted where no cache exists. "
            "**Synthetic rows are not actionable** and must not be treated like live or vendor-backed signals.",
            "",
            src_line,
            "**Momentum Score v2** ranking (legacy labels still listed under **Key** when present). "
            "**Synthetic fallback tickers:** treat **Key / Sv2 / Flag / Watch** as diagnostics only.",
            "",
        ]
    lines = [*head, *purpose]

    _ = _append_ranking_table(lines, ranked, sources)
    return "\n".join(lines)
