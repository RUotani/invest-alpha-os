"""Render Observation-only momentum signal section for daily reports (Main E)."""

from __future__ import annotations

from invis_alpha_os.config.jp_watchlist import load_jp_watchlist_tickers, normalize_jquants_equity_code
from invis_alpha_os.signals.momentum import DailyBar, build_momentum_signals, synthetic_bars_for_code


def render_momentum_signals_section() -> str:
    """Build ``## Momentum Signals`` markdown using deterministic synthetic bars (no HTTP)."""

    tickers = load_jp_watchlist_tickers()
    mapping: dict[str, list[DailyBar]] = {}
    for raw in tickers:
        code = normalize_jquants_equity_code(str(raw))
        if code is None:
            continue
        mapping[code] = synthetic_bars_for_code(code)
    ranked = build_momentum_signals(mapping)
    lines = [
        "## Momentum Signals",
        "",
        "Observation only — not buy/sell advice. Below uses **deterministic synthetic OHLCV** per ticker",
        "(no live HTTP; no API keys). **Not** live or cached vendor market data; not actionable as an investment signal.",
        "Labels: `high_52w_breakout`, `volume_25d_spike`, `positive_20d_60d_momentum`.",
        "",
    ]
    if not ranked:
        lines.append("- (no JP watchlist codes produced bar series)")
        lines.append("")
        return "\n".join(lines)

    lines.append("| Rank | Code | Score | Labels | r5 | r20 | r60 |")
    lines.append("|------|------|-------|--------|-----|-----|-----|")
    for i, m in enumerate(ranked, start=1):
        lbl = ", ".join(m.labels) if m.labels else "—"
        r5 = "—" if m.r5 is None else f"{m.r5 * 100:.2f}%"
        r20 = "—" if m.r20 is None else f"{m.r20 * 100:.2f}%"
        r60 = "—" if m.r60 is None else f"{m.r60 * 100:.2f}%"
        lines.append(f"| {i} | {m.code} | {m.score} | {lbl} | {r5} | {r20} | {r60} |")
    lines.append("")
    return "\n".join(lines)
