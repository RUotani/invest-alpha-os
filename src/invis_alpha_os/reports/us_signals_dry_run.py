"""US cache signals report dry-run section (observation-only; not wired to daily report)."""

from __future__ import annotations

from typing import Any


def _fmt_return_pct(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value) * 100:+.1f}%"
    except (TypeError, ValueError):
        return "—"


def _signal_cell(preview: dict[str, Any]) -> str:
    status = str(preview.get("status", ""))
    if status == "ok":
        label = preview.get("momentum_label")
        return str(label) if label else "—"
    if status == "skipped_insufficient_bars":
        return "skipped"
    reason = preview.get("reason")
    return str(reason) if reason else status or "—"


def render_us_cache_signals_dry_run_section(preview: dict[str, Any]) -> str:
    """Render a single-symbol US signals dry-run Markdown section from a preview dict."""

    lines = [
        "## US Signals Dry Run",
        "",
        "Observation only — dry-run section; not buy/sell advice. "
        "Not connected to the daily report pipeline.",
        "",
        "| Symbol | Asset | Role | Signal | 20d | 5d | Universe |",
        "|---|---|---|---|---:|---:|---|",
    ]
    sym = preview.get("symbol") or "—"
    ac = preview.get("asset_class") or "—"
    role = preview.get("role") or "—"
    signal = _signal_cell(preview)
    r20 = _fmt_return_pct(preview.get("return_20d"))
    r5 = _fmt_return_pct(preview.get("return_5d"))
    uni = preview.get("universe_status") or "—"
    lines.append(f"| {sym} | {ac} | {role} | {signal} | {r20} | {r5} | {uni} |")
    lines.append("")
    display = preview.get("display_name")
    if display:
        lines.append(f"- **display_name**: {display}")
    theme = preview.get("theme")
    if theme:
        lines.append(f"- **theme**: {theme}")
    status = preview.get("status")
    if status and status != "ok":
        lines.append(f"- **status**: {status}")
        reason = preview.get("reason")
        if reason:
            lines.append(f"- **reason**: {reason}")
    lines.append("- **live_http**: false")
    lines.append("")
    return "\n".join(lines)
