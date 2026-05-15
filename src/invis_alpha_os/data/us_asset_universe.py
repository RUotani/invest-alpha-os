"""US asset universe metadata from fixture JSON (no HTTP; observation-only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

US_ASSET_CLASS_VALUES: Final[frozenset[str]] = frozenset(
    {"us_equity", "us_etf", "crypto_proxy"}
)
US_ASSET_ROLE_VALUES: Final[frozenset[str]] = frozenset(
    {
        "single_stock",
        "market_proxy",
        "growth_proxy",
        "metals_bridge",
        "rates_proxy",
        "crypto_proxy",
        "cash_like_proxy",
        "watch_only",
    }
)
US_ASSET_ENTRY_OK_KEYS: Final[frozenset[str]] = frozenset(
    {
        "symbol",
        "asset_class",
        "role",
        "theme",
        "display_name",
        "enabled",
    }
)


def _validate_entry(row: dict[str, Any], *, index: int) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    if set(row.keys()) != US_ASSET_ENTRY_OK_KEYS:
        return None
    sym = str(row.get("symbol", "")).strip().upper()
    if not sym:
        return None
    ac = str(row.get("asset_class", "")).strip()
    role = str(row.get("role", "")).strip()
    if ac not in US_ASSET_CLASS_VALUES or role not in US_ASSET_ROLE_VALUES:
        return None
    theme = str(row.get("theme", "")).strip()
    display = str(row.get("display_name", "")).strip()
    enabled = row.get("enabled")
    if not isinstance(enabled, bool):
        return None
    if not theme or not display:
        return None
    return {
        "symbol": sym,
        "asset_class": ac,
        "role": role,
        "theme": theme,
        "display_name": display,
        "enabled": enabled,
    }


def parse_us_asset_universe_payload(data: Any) -> dict[str, Any] | None:
    """Validate universe envelope; return normalized dict or ``None``."""

    if not isinstance(data, dict):
        return None
    if data.get("schema_version") != 1:
        return None
    rows = data.get("assets")
    if not isinstance(rows, list) or not rows:
        return None
    out_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, raw in enumerate(rows):
        entry = _validate_entry(raw, index=i)
        if entry is None:
            return None
        if entry["symbol"] in seen:
            return None
        seen.add(entry["symbol"])
        out_rows.append(entry)
    source = data.get("source")
    if source is not None and not isinstance(source, str):
        return None
    return {
        "schema_version": 1,
        "source": str(source) if source is not None else None,
        "assets": out_rows,
        "asset_count": len(out_rows),
    }


def load_us_asset_universe_json_file(path: Path) -> dict[str, Any] | None:
    """Load and validate universe JSON from ``path`` (no network)."""

    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return parse_us_asset_universe_payload(data)


def index_us_asset_universe_by_symbol(universe: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build symbol → entry map from a validated universe payload."""

    rows = universe.get("assets") or []
    return {str(r["symbol"]): dict(r) for r in rows if isinstance(r, dict) and r.get("symbol")}


def enabled_us_asset_symbols(universe: dict[str, Any]) -> list[str]:
    """Symbols with ``enabled: true`` in declaration order."""

    out: list[str] = []
    for row in universe.get("assets") or []:
        if isinstance(row, dict) and row.get("enabled") is True:
            out.append(str(row["symbol"]))
    return out
