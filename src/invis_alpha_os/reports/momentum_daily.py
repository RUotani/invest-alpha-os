"""Render Observation-only momentum signal section for daily reports (Main E / Main F)."""

from __future__ import annotations

from invis_alpha_os.config.jp_watchlist import load_jp_watchlist_tickers, normalize_jquants_equity_code
from invis_alpha_os.data.jquants_daily_bars_cache import try_load_cached_daily_bars
from invis_alpha_os.signals.momentum import DailyBar, build_momentum_signals, synthetic_bars_for_code


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


def render_momentum_signals_section() -> str:
    """Build ``## Momentum Signals`` markdown; prefers sanitized J-Quants cache when present."""

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
    lines = [
        "## Momentum Signals",
        "",
        "Observation only — not buy/sell advice.",
        src_line,
        "Labels: `high_52w_breakout`, `volume_25d_spike`, `positive_20d_60d_momentum`.",
        "",
    ]
    if not ranked:
        lines.append("- (no JP watchlist codes produced bar series)")
        lines.append("")
        return "\n".join(lines)

    lines.append("| Rank | Code | Score | Labels | r5 | r20 | r60 | Bars src |")
    lines.append("|------|------|-------|--------|-----|-----|-----|----------|")
    for i, m in enumerate(ranked, start=1):
        lbl = ", ".join(m.labels) if m.labels else "—"
        r5 = "—" if m.r5 is None else f"{m.r5 * 100:.2f}%"
        r20 = "—" if m.r20 is None else f"{m.r20 * 100:.2f}%"
        r60 = "—" if m.r60 is None else f"{m.r60 * 100:.2f}%"
        bsrc = sources.get(m.code, "—")
        lines.append(f"| {i} | {m.code} | {m.score} | {lbl} | {r5} | {r20} | {r60} | {bsrc} |")
    lines.append("")
    return "\n".join(lines)
