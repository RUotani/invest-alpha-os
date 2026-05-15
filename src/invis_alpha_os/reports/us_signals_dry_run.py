"""US cache signals report dry-run section (observation-only; not wired to daily report)."""

from __future__ import annotations

from typing import Any

_DRY_RUN_INTRO: list[str] = [
    "## US Signals Dry Run",
    "",
    "Observation only — dry-run section; not buy/sell advice. "
    "Not connected to the daily report pipeline.",
    "",
]

_TABLE_HEADER: list[str] = [
    "| Symbol | Asset | Role | Signal | 20d | 5d | Universe |",
    "|---|---|---|---|---:|---:|---|",
]


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


def _dry_run_table_row(preview: dict[str, Any]) -> str:
    sym = preview.get("symbol") or "—"
    ac = preview.get("asset_class") or "—"
    role = preview.get("role") or "—"
    signal = _signal_cell(preview)
    r20 = _fmt_return_pct(preview.get("return_20d"))
    r5 = _fmt_return_pct(preview.get("return_5d"))
    uni = preview.get("universe_status") or "—"
    return f"| {sym} | {ac} | {role} | {signal} | {r20} | {r5} | {uni} |"


def _append_preview_footnotes(
    lines: list[str],
    preview: dict[str, Any],
    *,
    sym_prefix: bool = False,
) -> None:
    sym = preview.get("symbol") or "—"
    lead = f"**{sym}** · " if sym_prefix else ""
    display = preview.get("display_name")
    if display:
        lines.append(f"- {lead}**display_name**: {display}")
    theme = preview.get("theme")
    if theme:
        lines.append(f"- {lead}**theme**: {theme}")
    status = preview.get("status")
    if status and status != "ok":
        lines.append(f"- {lead}**status**: {status}")
        reason = preview.get("reason")
        if reason:
            lines.append(f"- {lead}**reason**: {reason}")


def render_us_cache_signals_dry_run_section(preview: dict[str, Any]) -> str:
    """Render a single-symbol US signals dry-run Markdown section from a preview dict."""

    lines = [* _DRY_RUN_INTRO, *_TABLE_HEADER, _dry_run_table_row(preview), ""]
    _append_preview_footnotes(lines, preview, sym_prefix=False)
    lines.append("- **live_http**: false")
    lines.append("")
    return "\n".join(lines)


def render_us_cache_signals_multi_symbol_dry_run_section(
    previews: list[dict[str, Any]],
) -> str:
    """Render a multi-symbol US signals dry-run Markdown section from preview dicts."""

    lines = list(_DRY_RUN_INTRO)
    if not previews:
        lines.extend(["- *(no preview rows)*", "", "- **live_http**: false", ""])
        return "\n".join(lines)

    lines.extend(_TABLE_HEADER)
    for preview in previews:
        lines.append(_dry_run_table_row(preview))
    lines.append("")
    for preview in previews:
        _append_preview_footnotes(lines, preview, sym_prefix=True)
    lines.append("- **live_http**: false")
    lines.append("")
    return "\n".join(lines)
