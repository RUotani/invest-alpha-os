"""US cache-only observation signals from validated daily bars (no HTTP)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from invis_alpha_os.data.us_asset_universe import (
    index_us_asset_universe_by_symbol,
    load_us_asset_universe_json_file,
)
from invis_alpha_os.data.us_daily_bars_cache import load_us_daily_bars_json_file
from invis_alpha_os.data.us_daily_bars_metrics import compute_us_daily_bars_basic_metrics
from invis_alpha_os.signals.momentum import DailyBar

US_CACHE_SIGNALS_PREVIEW_INVALID_BASE_KEYS: Final[frozenset[str]] = frozenset(
    {"status", "reason", "path", "live_http", "expect_symbol", "universe_path"}
)

US_CACHE_SIGNALS_UNIVERSE_EXTRA_KEYS: Final[frozenset[str]] = frozenset(
    {
        "universe_status",
        "universe_path",
        "role",
        "theme",
        "display_name",
    }
)

US_CACHE_SIGNAL_ROW_OK_KEYS: Final[frozenset[str]] = frozenset(
    {
        "status",
        "reason",
        "symbol",
        "asset_class",
        "bar_count",
        "first_date",
        "last_date",
        "last_close",
        "last_volume",
        "total_return",
        "return_5d",
        "return_20d",
        "has_5d",
        "has_20d",
        "momentum_label",
        "source",
        "live_http",
    }
)

_SOURCE_CACHE_ONLY = "cache_only"


def _momentum_label_from_metrics(metrics: dict[str, Any]) -> str | None:
    if not metrics.get("has_5d"):
        return None
    r5 = metrics.get("return_5d")
    r20 = metrics.get("return_20d")
    if r5 is None:
        return None
    if metrics.get("has_20d") and r20 is not None and r5 > 0 and r20 > 0:
        return "uptrend_aligned"
    if r5 > 0:
        return "uptrend_short"
    if r5 < 0:
        return "pullback_short"
    return "neutral"


def compute_us_cache_signal_row(
    bars: list[DailyBar],
    *,
    symbol: str,
    asset_class: str | None = None,
) -> dict[str, Any]:
    """Build one cache-only US signal observation row (no disk I/O)."""

    base: dict[str, Any] = {
        "symbol": symbol,
        "asset_class": asset_class,
        "source": _SOURCE_CACHE_ONLY,
        "live_http": False,
    }

    if not bars:
        return {
            **base,
            "status": "invalid",
            "reason": "empty_bars",
            "bar_count": 0,
            "has_5d": False,
            "has_20d": False,
            "momentum_label": None,
        }

    metrics = compute_us_daily_bars_basic_metrics(bars)
    if metrics.get("status") != "ok":
        return {
            **base,
            "status": "invalid",
            "reason": metrics.get("reason") or "metrics_invalid",
            "bar_count": metrics.get("bar_count", 0),
            "has_5d": metrics.get("has_5d", False),
            "has_20d": metrics.get("has_20d", False),
            "momentum_label": None,
        }

    row: dict[str, Any] = {
        **base,
        "status": "ok",
        "reason": None,
        "bar_count": metrics["bar_count"],
        "first_date": metrics["first_date"],
        "last_date": metrics["last_date"],
        "last_close": metrics["last_close"],
        "last_volume": metrics["last_volume"],
        "total_return": metrics["total_return"],
        "return_5d": metrics["return_5d"],
        "return_20d": metrics["return_20d"],
        "has_5d": metrics["has_5d"],
        "has_20d": metrics["has_20d"],
    }

    if not metrics["has_5d"]:
        row["status"] = "skipped_insufficient_bars"
        row["reason"] = "insufficient_bars_for_5d"
        row["momentum_label"] = None
        return row

    row["momentum_label"] = _momentum_label_from_metrics(metrics)
    return row


def load_us_cache_signal_row_from_json_file(
    path: Path,
    *,
    expect_symbol: str | None = None,
    asset_class: str | None = None,
) -> dict[str, Any] | None:
    """Load envelope JSON and return a signal row, or ``None`` if parse fails."""

    loaded = load_us_daily_bars_json_file(path, expect_symbol=expect_symbol)
    if loaded is None:
        return None
    bars, meta = loaded
    sym = str(meta.get("symbol", ""))
    return compute_us_cache_signal_row(bars, symbol=sym, asset_class=asset_class)


def build_us_cache_signals_preview(
    path: Path,
    *,
    expect_symbol: str | None = None,
    asset_class: str | None = None,
) -> dict[str, Any]:
    """Load cache JSON and return US signals diagnostics (no HTTP, no disk write)."""

    rel_path = str(path)
    if not path.is_file():
        return {
            "status": "invalid",
            "reason": "path_not_found",
            "path": rel_path,
            "live_http": False,
        }

    row = load_us_cache_signal_row_from_json_file(
        path, expect_symbol=expect_symbol, asset_class=asset_class
    )
    if row is None:
        return {
            "status": "invalid",
            "reason": "parse_failed",
            "path": rel_path,
            "expect_symbol": expect_symbol,
            "live_http": False,
        }

    out = dict(row)
    out["path"] = rel_path
    return out


def attach_us_asset_universe_metadata_to_signals_preview(
    preview: dict[str, Any],
    universe_path: Path,
) -> dict[str, Any]:
    """Merge optional universe metadata into a signals preview (no HTTP; no disk write)."""

    rel_uni = str(universe_path)
    universe = load_us_asset_universe_json_file(universe_path)
    if universe is None:
        out: dict[str, Any] = {
            "status": "invalid",
            "reason": "universe_invalid",
            "live_http": False,
            "universe_path": rel_uni,
        }
        if preview.get("path"):
            out["path"] = preview["path"]
        return out

    out = dict(preview)
    out["universe_path"] = rel_uni
    sym = str(out.get("symbol", "")).strip().upper()
    if not sym:
        out["universe_status"] = "not_found"
        return out

    entry = index_us_asset_universe_by_symbol(universe).get(sym)
    if entry is None:
        out["universe_status"] = "not_found"
        return out

    out["universe_status"] = "disabled" if not entry.get("enabled") else "matched"
    out["asset_class"] = entry["asset_class"]
    out["role"] = entry["role"]
    out["theme"] = entry["theme"]
    out["display_name"] = entry["display_name"]
    return out


def format_us_cache_signals_preview_markdown(preview: dict[str, Any]) -> str:
    lines = ["## US cache signals preview", ""]
    status = preview.get("status", "unknown")
    lines.append(f"- **status**: {status}")
    if status not in ("ok", "skipped_insufficient_bars"):
        reason = preview.get("reason", "")
        if reason:
            lines.append(f"- **reason**: {reason}")
        path = preview.get("path", "")
        if path:
            lines.append(f"- **path**: `{path}`")
        lines.append("- **live_http**: false")
        return "\n".join(lines) + "\n"

    sym = preview.get("symbol", "")
    if sym:
        lines.append(f"- **symbol**: {sym}")
    uni_status = preview.get("universe_status")
    if uni_status:
        lines.append(f"- **universe_status**: {uni_status}")
        role = preview.get("role")
        if role:
            lines.append(f"- **role**: {role}")
        theme = preview.get("theme")
        if theme:
            lines.append(f"- **theme**: {theme}")
        display = preview.get("display_name")
        if display:
            lines.append(f"- **display_name**: {display}")
        ac = preview.get("asset_class")
        if ac and uni_status in ("matched", "disabled"):
            lines.append(f"- **asset_class**: {ac}")
    label = preview.get("momentum_label")
    if label:
        lines.append(f"- **momentum_label**: {label}")
    elif status == "skipped_insufficient_bars":
        lines.append("- **momentum_label**: (insufficient bars)")
    lines.extend(
        [
            f"- **bar_count**: {preview.get('bar_count', 0)}",
            f"- **first_date**: {preview.get('first_date', '')}",
            f"- **last_date**: {preview.get('last_date', '')}",
            f"- **last_close**: {preview.get('last_close', '')}",
        ]
    )
    tr = preview.get("total_return")
    if tr is not None:
        lines.append(f"- **total_return**: {tr}")
    r5 = preview.get("return_5d")
    if r5 is not None:
        lines.append(f"- **return_5d**: {r5}")
    elif preview.get("has_5d") is False:
        lines.append("- **return_5d**: (insufficient bars)")
    r20 = preview.get("return_20d")
    if r20 is not None:
        lines.append(f"- **return_20d**: {r20}")
    elif preview.get("has_20d") is False:
        lines.append("- **return_20d**: (insufficient bars)")
    lines.append(f"- **path**: `{preview.get('path', '')}`")
    lines.append("- **live_http**: false")
    return "\n".join(lines) + "\n"


def format_us_cache_signals_preview_json(preview: dict[str, Any]) -> str:
    return json.dumps(preview, ensure_ascii=False, indent=2)
