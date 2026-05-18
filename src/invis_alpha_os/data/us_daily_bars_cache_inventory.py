"""Read-only inventory of US daily bars on-disk cache files (no HTTP, no writes)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from invis_alpha_os.config.us_watchlist import load_us_watchlist_tickers, normalize_us_symbol
from invis_alpha_os.data.us_daily_bars_cache import (
    build_us_daily_bars_cache_preview,
    us_daily_bars_cache_path,
)

_MIN_BARS_FOR_OK: Final[int] = 5


def resolve_us_daily_bars_cache_file(cache_root: Path, symbol: str) -> Path:
    """``{cache_root}/{slug}.json`` (inventory root may differ from default outputs path)."""

    slug = normalize_us_symbol(symbol.strip())
    if slug is None:
        raise ValueError(f"invalid US symbol for cache inventory: {symbol!r}")
    return cache_root / f"{slug}.json"


def _inventory_symbols(
    *,
    symbols: list[str] | None,
    watchlist_path: Path | None,
) -> list[str]:
    if symbols:
        out: list[str] = []
        seen: set[str] = set()
        for raw in symbols:
            n = normalize_us_symbol(str(raw).strip())
            if n is None or n in seen:
                continue
            seen.add(n)
            out.append(n)
        return out
    return load_us_watchlist_tickers(watchlist_path)


def build_us_daily_bars_cache_inventory_row(
    symbol: str,
    cache_root: Path,
) -> dict[str, Any]:
    """Single-symbol cache inventory row (read-only)."""

    path = resolve_us_daily_bars_cache_file(cache_root, symbol)
    base: dict[str, Any] = {
        "symbol": normalize_us_symbol(symbol.strip()) or symbol.strip().upper(),
        "source": "cache_only",
        "live_http": False,
        "file_exists": path.is_file(),
        "path": str(path),
        "bar_count": None,
        "first_date": None,
        "last_date": None,
        "reason": None,
    }
    if not path.is_file():
        base["status"] = "missing"
        base["reason"] = "cache_file_absent"
        return base

    preview = build_us_daily_bars_cache_preview(path, expect_symbol=base["symbol"])
    if preview.get("validation_status") != "ok":
        base["status"] = "invalid"
        base["reason"] = str(preview.get("reason") or "parse_failed")
        return base

    bar_count = int(preview.get("bar_count") or 0)
    base["bar_count"] = bar_count
    base["first_date"] = preview.get("first_date")
    base["last_date"] = preview.get("last_date")

    if bar_count < _MIN_BARS_FOR_OK:
        base["status"] = "insufficient"
        base["reason"] = f"bars_below_minimum_{_MIN_BARS_FOR_OK}"
        return base

    fetched_at = preview.get("fetched_at")
    generated_at = preview.get("generated_at")
    if not fetched_at and not generated_at:
        base["status"] = "stale_unknown"
        base["reason"] = "no_freshness_metadata"
        return base

    base["status"] = "ok"
    base["reason"] = None
    return base


def build_us_daily_bars_cache_inventory(
    cache_root: Path,
    *,
    symbols: list[str] | None = None,
    watchlist_path: Path | None = None,
) -> dict[str, Any]:
    """Scan cache files under ``cache_root`` for watchlist symbols (read-only)."""

    root = cache_root.expanduser().resolve()
    tickers = _inventory_symbols(symbols=symbols, watchlist_path=watchlist_path)
    default_root = us_daily_bars_cache_path("MSFT").parent.resolve()
    rows = [build_us_daily_bars_cache_inventory_row(sym, root) for sym in tickers]
    counts: dict[str, int] = {}
    for row in rows:
        st = str(row.get("status", "unknown"))
        counts[st] = counts.get(st, 0) + 1
    return {
        "source": "cache_only",
        "live_http": False,
        "cache_root": str(root),
        "default_outputs_cache_root": str(default_root),
        "symbol_count": len(tickers),
        "status_counts": counts,
        "rows": rows,
    }


def format_us_daily_bars_cache_inventory_json(inventory: dict[str, Any]) -> str:
    return json.dumps(inventory, ensure_ascii=False, indent=2)


def format_us_daily_bars_cache_inventory_markdown(inventory: dict[str, Any]) -> str:
    lines = [
        "## US daily bars cache inventory",
        "",
        f"- **cache_root**: `{inventory.get('cache_root', '')}`",
        f"- **symbol_count**: {inventory.get('symbol_count', 0)}",
        f"- **live_http**: false",
        "",
    ]
    counts = inventory.get("status_counts") or {}
    if counts:
        lines.append("### status_counts")
        lines.append("")
        for key in sorted(counts):
            lines.append(f"- **{key}**: {counts[key]}")
        lines.append("")
    lines.append("### rows")
    lines.append("")
    lines.append("| symbol | status | file_exists | bar_count | first_date | last_date | reason |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for row in inventory.get("rows") or []:
        lines.append(
            "| {symbol} | {status} | {file_exists} | {bar_count} | {first_date} | {last_date} | {reason} |".format(
                symbol=row.get("symbol", ""),
                status=row.get("status", ""),
                file_exists=row.get("file_exists", False),
                bar_count=row.get("bar_count", ""),
                first_date=row.get("first_date") or "",
                last_date=row.get("last_date") or "",
                reason=row.get("reason") or "",
            )
        )
    return "\n".join(lines) + "\n"
