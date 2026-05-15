"""US daily bars cache-only basic metrics (pure functions; no HTTP)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from invis_alpha_os.data.us_daily_bars_cache import load_us_daily_bars_json_file
from invis_alpha_os.signals.momentum import DailyBar, calculate_returns

METRICS_PREVIEW_INVALID_BASE_KEYS: Final[frozenset[str]] = frozenset(
    {"status", "reason", "path", "live_http"}
)

METRICS_PREVIEW_OK_KEYS: Final[frozenset[str]] = frozenset(
    {
        "status",
        "reason",
        "path",
        "symbol",
        "bar_count",
        "first_date",
        "last_date",
        "latest_date",
        "last_close",
        "last_volume",
        "total_return",
        "return_5d",
        "return_20d",
        "has_5d",
        "has_20d",
        "live_http",
    }
)


def compute_us_daily_bars_basic_metrics(bars: list[DailyBar]) -> dict[str, Any]:
    """Summarize validated oldest-first ``DailyBar`` rows (no disk I/O)."""

    if not bars:
        return {
            "status": "invalid",
            "reason": "empty_bars",
            "bar_count": 0,
            "has_5d": False,
            "has_20d": False,
        }

    closes = [float(b["close"]) for b in bars]
    volumes = [float(b["volume"]) for b in bars]
    rets = calculate_returns(closes, horizons=[5, 20])
    r5 = rets.get(5)
    r20 = rets.get(20)

    total_return: float | None = None
    if len(closes) >= 2 and closes[0] != 0:
        total_return = (closes[-1] / closes[0]) - 1.0

    return {
        "status": "ok",
        "reason": None,
        "bar_count": len(bars),
        "first_date": bars[0]["date"],
        "last_date": bars[-1]["date"],
        "latest_date": bars[-1]["date"],
        "last_close": closes[-1],
        "last_volume": volumes[-1],
        "total_return": total_return,
        "return_5d": r5,
        "return_20d": r20,
        "has_5d": r5 is not None,
        "has_20d": r20 is not None,
    }


def build_us_daily_bars_cache_metrics_preview(
    path: Path,
    *,
    expect_symbol: str | None = None,
) -> dict[str, Any]:
    """Load cache JSON and return basic metrics diagnostics (no HTTP, no disk write)."""

    rel_path = str(path)
    if not path.is_file():
        return {
            "status": "invalid",
            "reason": "path_not_found",
            "path": rel_path,
            "live_http": False,
        }

    loaded = load_us_daily_bars_json_file(path, expect_symbol=expect_symbol)
    if loaded is None:
        return {
            "status": "invalid",
            "reason": "parse_failed",
            "path": rel_path,
            "expect_symbol": expect_symbol,
            "live_http": False,
        }

    bars, meta = loaded
    metrics = compute_us_daily_bars_basic_metrics(bars)
    out = dict(metrics)
    out["path"] = rel_path
    out["symbol"] = meta.get("symbol", "")
    out["live_http"] = False
    return out


def format_us_daily_bars_cache_metrics_markdown(metrics: dict[str, Any]) -> str:
    lines = ["## US daily bars cache metrics", ""]
    status = metrics.get("status", "unknown")
    lines.append(f"- **status**: {status}")
    if status != "ok":
        reason = metrics.get("reason", "")
        if reason:
            lines.append(f"- **reason**: {reason}")
        path = metrics.get("path", "")
        if path:
            lines.append(f"- **path**: `{path}`")
        lines.append("- **live_http**: false")
        return "\n".join(lines) + "\n"

    sym = metrics.get("symbol", "")
    if sym:
        lines.append(f"- **symbol**: {sym}")
    lines.extend(
        [
            f"- **bar_count**: {metrics.get('bar_count', 0)}",
            f"- **first_date**: {metrics.get('first_date', '')}",
            f"- **last_date**: {metrics.get('last_date', '')}",
            f"- **last_close**: {metrics.get('last_close', '')}",
            f"- **last_volume**: {metrics.get('last_volume', '')}",
        ]
    )
    tr = metrics.get("total_return")
    if tr is not None:
        lines.append(f"- **total_return**: {tr}")
    r5 = metrics.get("return_5d")
    if r5 is not None:
        lines.append(f"- **return_5d**: {r5}")
    elif metrics.get("has_5d") is False:
        lines.append("- **return_5d**: (insufficient bars)")
    r20 = metrics.get("return_20d")
    if r20 is not None:
        lines.append(f"- **return_20d**: {r20}")
    elif metrics.get("has_20d") is False:
        lines.append("- **return_20d**: (insufficient bars)")
    lines.append(f"- **path**: `{metrics.get('path', '')}`")
    lines.append("- **live_http**: false")
    return "\n".join(lines) + "\n"


def format_us_daily_bars_cache_metrics_json(metrics: dict[str, Any]) -> str:
    return json.dumps(metrics, ensure_ascii=False, indent=2)
