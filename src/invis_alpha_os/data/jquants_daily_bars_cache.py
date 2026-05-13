"""Sanitized on-disk daily OHLCV for J-Quants–derived bars (observation only; no secrets, no raw API).

* **JP J-Quants namespace** — filenames under ``market_data/jquants_daily_bars/`` MUST pass
  ``_jp_daily_bars_cache_wire_or_raise`` (``normalize_jquants_equity_code`` plus a guard rejecting
  all-alpha 4-char codes such as accidental US tickers) before hitting disk.
* **Slug-only namespace** — for cross-market **preflight** paths (no ingestion wired yet), use
  ``slug_daily_bars_cache_path`` → ``market_data/slug_daily_bars/``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.config.jp_watchlist import normalize_jquants_equity_code
from invis_alpha_os.config.paths import OUTPUTS_DIR
from invis_alpha_os.data.cache_wire_slug import sanitize_provider_wire_slug_for_cache_filename
from invis_alpha_os.signals.momentum import DailyBar, bars_from_rows

SCHEMA_VERSION = 1
REL_CACHE_ROOT = Path("market_data") / "jquants_daily_bars"
REL_SLUG_CACHE_ROOT = Path("market_data") / "slug_daily_bars"


def _jp_daily_bars_cache_wire_or_raise(raw: str) -> str:
    """J-Quants on-disk caches are JP-listed wire codes — not generic US OTC-style tickers."""

    n = normalize_jquants_equity_code(raw.strip())
    if n is None:
        raise ValueError("invalid equity code for J-Quants daily bars cache")
    # ``normalize_jquants_equity_code`` allows any 4-letter alnum bucket; forbid all-alpha equities
    # (covers accidental ``MSFT``-style IDs that are not JP file keys for this subtree).
    if len(n) == 4 and n.isalpha():
        raise ValueError("invalid JP equity wire code for J-Quants daily bars cache (all-alpha symbols are rejected)")
    slug = sanitize_provider_wire_slug_for_cache_filename(n)
    return slug


def slug_daily_bars_cache_path(raw_code: str) -> Path:
    """Cross-market slug path only — ``outputs/market_data/slug_daily_bars/{slug}.json`` (no JP semantics)."""

    slug = sanitize_provider_wire_slug_for_cache_filename(raw_code)
    return OUTPUTS_DIR / REL_SLUG_CACHE_ROOT / f"{slug}.json"


def jquants_daily_bars_cache_path(code: str) -> Path:
    """``outputs/market_data/jquants_daily_bars/{wire}.json`` — rejects non–JP-wire codes."""

    slug = _jp_daily_bars_cache_wire_or_raise(code)
    return OUTPUTS_DIR / REL_CACHE_ROOT / f"{slug}.json"


def save_jquants_daily_bars_cache(
    code: str,
    rows: list[dict[str, Any]],
    *,
    source: str,
    fetched_at: str | None = None,
    generated_at: str | None = None,
) -> Path:
    """Write sanitized cache JSON (no raw response, no API material)."""

    if not rows:
        raise ValueError("refuse to write empty J-Quants daily bars cache")

    path = jquants_daily_bars_cache_path(code)
    norm_wire = normalize_jquants_equity_code(code.strip())
    if norm_wire is None:  # defensive; path() should have raised
        raise ValueError("invalid equity code for J-Quants daily bars cache")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "code": norm_wire,
        "source": source,
        "fetched_at": fetched_at,
        "generated_at": generated_at,
        "bar_count": len(rows),
        "bars": rows,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_jquants_daily_bars_cache(code: str) -> tuple[list[DailyBar], dict[str, Any]] | None:
    """Load cache file if present and well-formed; else ``None``."""

    try:
        path = jquants_daily_bars_cache_path(code)
    except ValueError:
        return None
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    ver_raw = data.get("schema_version")
    try:
        ver = int(ver_raw) if ver_raw is not None else -1
    except (TypeError, ValueError):
        return None
    if ver != SCHEMA_VERSION:
        return None
    raw_bars = data.get("bars")
    if not isinstance(raw_bars, list) or not raw_bars:
        return None
    try:
        bars = bars_from_rows(raw_bars)
    except (TypeError, ValueError):
        return None
    meta = {
        "source": data.get("source", ""),
        "fetched_at": data.get("fetched_at"),
        "generated_at": data.get("generated_at"),
        "bar_count": data.get("bar_count", len(bars)),
    }
    return bars, meta


def try_load_cached_daily_bars(code: str) -> tuple[list[DailyBar], str] | None:
    """Return ``(bars, 'cache')`` when a non-empty valid cache exists."""

    loaded = load_jquants_daily_bars_cache(code)
    if loaded is None:
        return None
    bars, _meta = loaded
    if not bars:
        return None
    return bars, "cache"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
