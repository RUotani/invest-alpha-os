"""R6.17: Opt-in US cache-only preview section for daily report (read-only; no HTTP)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Final

from invis_alpha_os.config.paths import OUTPUTS_DIR
from invis_alpha_os.data.us_daily_bars_cache import load_us_daily_bars_json_file
from invis_alpha_os.data.us_daily_bars_cache_inventory import build_us_daily_bars_cache_inventory
from invis_alpha_os.data.us_daily_bars_metrics import compute_us_daily_bars_basic_metrics

_OPT_IN_HEADER: Final[str] = "### US Cache Preview (opt-in)"
_BENCHMARK_SYMBOLS: Final[frozenset[str]] = frozenset({"SPY", "QQQ", "TLT", "GLDM"})
_NOTE_STALE: Final[str] = "stale — returns not used"
_NOTE_FRESHNESS_UNKNOWN: Final[str] = "freshness unknown — returns not used"


def preview_note_for_freshness(freshness_status: str) -> str:
    """Map inventory freshness to preview note (no scoring semantics)."""

    st = str(freshness_status or "").strip()
    if st == "stale":
        return _NOTE_STALE
    if st == "freshness_unknown":
        return _NOTE_FRESHNESS_UNKNOWN
    return ""


def _fmt_num(value: object) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return ""


def build_us_cache_opt_in_preview_row(inv_row: dict[str, Any]) -> dict[str, Any]:
    """One preview table row from an inventory row (read-only)."""

    symbol = str(inv_row.get("symbol", ""))
    freshness = str(inv_row.get("freshness_status", ""))
    latest_date = inv_row.get("latest_date") or inv_row.get("last_date")
    inv_status = str(inv_row.get("status", ""))

    base: dict[str, Any] = {
        "symbol": symbol,
        "latest_date": latest_date,
        "freshness_status": freshness,
        "close": None,
        "return_1d": None,
        "return_5d": None,
        "return_20d": None,
        "volume_status": "unknown",
        "note": preview_note_for_freshness(freshness),
        "live_http": False,
    }

    if inv_status not in ("ok", "stale_unknown"):
        base["note"] = f"inventory {inv_status}"
        return base

    path_raw = inv_row.get("path")
    if not path_raw:
        base["note"] = "inventory ok — path missing"
        return base

    loaded = load_us_daily_bars_json_file(Path(str(path_raw)), expect_symbol=symbol)
    if loaded is None:
        base["note"] = "parse_failed"
        return base

    bars, _meta = loaded
    metrics = compute_us_daily_bars_basic_metrics(bars)
    if metrics.get("status") != "ok":
        base["note"] = str(metrics.get("reason") or "metrics_invalid")
        return base

    note = preview_note_for_freshness(freshness)
    base.update(
        {
            "latest_date": metrics.get("latest_date") or latest_date,
            "close": metrics.get("last_close"),
            "return_1d": metrics.get("return_1d"),
            "return_5d": metrics.get("return_5d"),
            "return_20d": metrics.get("return_20d"),
            "volume_status": metrics.get("volume_status", "unknown"),
            "note": note,
        }
    )
    return base


def build_us_cache_opt_in_preview(
    cache_root: Path | None = None,
    *,
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Build opt-in preview payload from cache inventory + metrics (read-only)."""

    root = (cache_root or (OUTPUTS_DIR / "market_data" / "us_daily_bars")).expanduser().resolve()
    inventory = build_us_daily_bars_cache_inventory(root, reference_date=reference_date)
    preview_rows = [build_us_cache_opt_in_preview_row(r) for r in inventory.get("rows") or []]

    benchmark_warnings: list[str] = []
    missing_symbols: list[str] = []
    stale_count = 0
    for row in preview_rows:
        sym = str(row.get("symbol", ""))
        if "inventory missing" in str(row.get("note", "")):
            missing_symbols.append(sym)
        fs = str(row.get("freshness_status", ""))
        if fs == "stale":
            stale_count += 1
        if sym in _BENCHMARK_SYMBOLS and fs in ("stale", "freshness_unknown"):
            benchmark_warnings.append(sym)

    return {
        "status": "ok",
        "source": "cache_only",
        "live_http": False,
        "cache_root": str(root),
        "rows": preview_rows,
        "benchmark_warnings": benchmark_warnings,
        "missing_symbols": missing_symbols,
        "stale_count": stale_count,
        "inventory_summary": inventory.get("summary"),
    }


def render_us_cache_opt_in_preview_markdown(preview: dict[str, Any]) -> str:
    """Markdown table for opt-in US cache preview (no trading advice)."""

    lines = [
        _OPT_IN_HEADER,
        "",
        "Observation only — cache-only preview. Not trading advice. No aggregate score.",
        "",
    ]
    if preview.get("stale_count", 0):
        lines.append(f"- **stale symbols**: {preview['stale_count']} (see note column)")
    if preview.get("missing_symbols"):
        miss = ", ".join(preview["missing_symbols"])
        lines.append(f"- **missing cache files**: {miss}")
    if preview.get("benchmark_warnings"):
        bw = ", ".join(preview["benchmark_warnings"])
        lines.append(f"- **benchmark warning**: {bw} (stale or unknown freshness; preview does not stop)")
    lines.extend(["", "| symbol | latest_date | freshness_status | close | return_1d | return_5d | return_20d | volume_status | note |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"])

    for row in preview.get("rows") or []:
        lines.append(
            "| {symbol} | {latest_date} | {freshness_status} | {close} | {return_1d} | {return_5d} | {return_20d} | {volume_status} | {note} |".format(
                symbol=row.get("symbol", ""),
                latest_date=row.get("latest_date") or "",
                freshness_status=row.get("freshness_status", ""),
                close=_fmt_num(row.get("close")),
                return_1d=_fmt_num(row.get("return_1d")),
                return_5d=_fmt_num(row.get("return_5d")),
                return_20d=_fmt_num(row.get("return_20d")),
                volume_status=row.get("volume_status", ""),
                note=row.get("note", ""),
            )
        )

    lines.extend(["", "- **live_http**: false", ""])
    return "\n".join(lines)


def append_us_cache_preview_section(
    base_markdown: str,
    *,
    cache_root: Path | None = None,
    reference_date: date | None = None,
) -> str:
    """Append US cache preview when CLI opt-in flag is set."""

    preview = build_us_cache_opt_in_preview(cache_root, reference_date=reference_date)
    section = render_us_cache_opt_in_preview_markdown(preview)
    return f"{base_markdown.rstrip()}\n\n{section}"
