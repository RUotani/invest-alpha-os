"""Render Observation-only momentum signal sections for daily reports (Main E / Main F / Main I)."""

from __future__ import annotations

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


def _risk_cell(m: MomentumBreakdown) -> str:
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
) -> None:
    lines.append(
        "**Momentum Score v2:** ranked by ``score_v2`` (desc), tie-break r20, r60, then wire code.",
    )
    lines.append("")
    lines.append("Legacy integer ``score`` still appears in CLI JSON next to ``score_v2``.")
    lines.append("")
    lines.append("| Rank | Code | Sv2 | Key | r5 | r20 | r60 | HiDist | VolR | Risk | Bars src |")
    lines.append("|------|------|-----|-----|-----|-----|-----|--------|------|------|----------|")
    for i, m in enumerate(ranked, start=1):
        key = _abbrev_labels(m)
        r5 = _fmt_pct(m.r5)
        r20 = _fmt_pct(m.r20)
        r60 = _fmt_pct(m.r60)
        bsrc = bars_source_for_code.get(m.code, "—")
        lines.append(
            f"| {i} | {m.code} | {m.score_v2} | {key} | {r5} | {r20} | {r60} | "
            f"{_hi_dist_cell(m)} | {_vol_r_cell(m)} | {_risk_cell(m)} | {bsrc} |",
        )
    lines.append("")

def render_momentum_signals_cache_only_section() -> str:
    """Build ``## Momentum Signals — Cache Only`` — cached bars only; no synthetic generation."""

    tickers = load_jp_watchlist_tickers()
    mapping: dict[str, list[DailyBar]] = {}
    skipped_no_cache: list[str] = []
    for raw in tickers:
        code = normalize_jquants_equity_code(str(raw))
        if code is None:
            continue
        got = try_load_cached_daily_bars(code)
        if got is not None:
            mapping[code] = got[0]
        else:
            skipped_no_cache.append(code)

    ranked = build_momentum_signals(mapping)
    bars_src = {c: "cache" for c in mapping}

    lines: list[str] = [
        "## Momentum Signals — Cache Only",
        "",
        "Observation only — not buy/sell advice. No automatic trading.",
        "",
        "**Bars source:** `cache` — local sanitized OHLCV files only "
        "(`outputs/market_data/jquants_daily_bars/{code}.json`). "
        "**No synthetic bars** are generated for this section.",
        "",
    ]
    if skipped_no_cache:
        codes = ", ".join(skipped_no_cache)
        lines.append(f"**Skipped (no local cache file):** {len(skipped_no_cache)} — {codes}.")
        lines.append("")
    lines.extend(
        [
            "**Momentum Score v2** adds dispersion beyond legacy labels. "
            "See CLI ``alpha-os signals`` JSON for ``score_v2_components`` and full fields.",
            "",
        ]
    )
    if not ranked:
        lines.append("- *(no tickers with local cache files in the JP watchlist)*")
        lines.append("")
        return "\n".join(lines)

    _append_ranking_table(lines, ranked, bars_src)
    return "\n".join(lines)


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
    lines: list[str] = [
        "## Momentum Signals — Mixed / System Validation",
        "",
        "Observation only — not buy/sell advice. No automatic trading.",
        "",
        "**Purpose:** Mixed ranking for **pipeline / system validation**. When a ticker lacks a local cache file, "
        "a **synthetic fallback** series is used so the mover still appears in the table. "
        "That is misleading for pure investment research because synthetic rows can outrank cached rows.",
        "",
        "**Synthetic fallback:** Deterministic placeholder OHLCV is inserted where no cache exists. "
        "**Synthetic rows are not actionable** and must not be treated like live or vendor-backed signals.",
        "",
        src_line,
        "**Momentum Score v2** ranking (legacy labels still listed under **Key** when present). "
        "**Synthetic fallback tickers:** treat **Key / Sv2 / Risk** as diagnostics only.",
        "",
    ]
    if not ranked:
        lines.append("- (no JP watchlist codes produced bar series)")
        lines.append("")
        return "\n".join(lines)

    _append_ranking_table(lines, ranked, sources)
    return "\n".join(lines)
