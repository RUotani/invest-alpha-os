"""US daily OHLCV on-disk cache (sanitized skeleton; observation only).

No vendor HTTP adapters here — ``source`` defaults to ``manual_or_future_provider`` until Main R1+ ingestion exists.

Persisted payloads must never carry raw API envelopes, secrets, or auth headers — only sanitized bars + metadata keys.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from invis_alpha_os.config.paths import OUTPUTS_DIR
from invis_alpha_os.config.us_watchlist import normalize_us_symbol
from invis_alpha_os.data.jquants_daily_bars_cache import utc_now_iso
from invis_alpha_os.signals.momentum import DailyBar, bars_from_rows

SCHEMA_VERSION: Final[int] = 1
REL_US_CACHE_ROOT = Path("market_data") / "us_daily_bars"

_ALLOWED_PAYLOAD_KEYS_AT_ROOT: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "symbol",
        "asset_class",
        "source",
        "fetched_at",
        "generated_at",
        "bar_count",
        "bars",
    }
)


def _symbol_slug_or_raise(raw: str) -> str:
    s = normalize_us_symbol(raw.strip())
    if s is None:
        raise ValueError("invalid US symbol for daily bars cache")
    return s


def us_daily_bars_cache_path(symbol: str) -> Path:
    """``outputs/market_data/us_daily_bars/{slug}.json``."""

    slug = _symbol_slug_or_raise(symbol)
    return OUTPUTS_DIR / REL_US_CACHE_ROOT / f"{slug}.json"


def save_us_daily_bars_cache(
    symbol: str,
    rows: list[dict[str, Any]],
    *,
    asset_class: str | None = None,
    source: str = "manual_or_future_provider",
    fetched_at: str | None = None,
    generated_at: str | None = None,
) -> Path:
    """Write sanitized OHLCV JSON."""

    if not rows:
        raise ValueError("refuse to write empty US daily bars cache")

    slug = _symbol_slug_or_raise(symbol)

    forb = ("raw_response", "api_key", "authorization", "bearer")
    sl = source.lower()
    if any(x in sl for x in forb):
        raise ValueError("refuse ambiguous source metadata")

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "symbol": slug,
        "source": source,
        "fetched_at": fetched_at,
        "generated_at": generated_at if generated_at is not None else utc_now_iso(),
        "bar_count": len(rows),
        "bars": rows,
    }
    if asset_class is not None and str(asset_class).strip():
        payload["asset_class"] = str(asset_class).strip()

    txt = json.dumps(payload, ensure_ascii=False, indent=2)
    low = txt.lower()
    if any(tok in low for tok in forb):
        raise ValueError("refuse persisted cache blob with forbidden substring")

    path = us_daily_bars_cache_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(txt, encoding="utf-8")
    return path


def load_us_daily_bars_cache(symbol: str) -> tuple[list[DailyBar], dict[str, Any]] | None:
    """Load cache when present and well-formed."""

    try:
        path = us_daily_bars_cache_path(symbol)
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

    extras = set(data.keys()) - _ALLOWED_PAYLOAD_KEYS_AT_ROOT
    if extras:
        return None

    low = json.dumps(data, ensure_ascii=False).lower()
    for needle in ('"raw_response"', '"api_key"', "authorization:", "x-api-key", " bearer "):
        if needle.lower() in low:
            return None

    try:
        ver = int(data["schema_version"])
    except (KeyError, TypeError, ValueError):
        return None
    if ver != SCHEMA_VERSION:
        return None

    stored = data.get("symbol")
    if not isinstance(stored, str):
        return None
    norm_stored = normalize_us_symbol(stored)
    if norm_stored is None:
        return None

    requested: str | None
    try:
        requested = _symbol_slug_or_raise(symbol)
    except ValueError:
        requested = None
    if requested is not None and norm_stored != requested:
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
        "asset_class": data.get("asset_class"),
        "fetched_at": data.get("fetched_at"),
        "generated_at": data.get("generated_at"),
        "bar_count": data.get("bar_count", len(bars)),
        "symbol": norm_stored,
    }
    return bars, meta


def try_load_cached_us_daily_bars(symbol: str) -> tuple[list[DailyBar], str] | None:
    loaded = load_us_daily_bars_cache(symbol)
    if loaded is None:
        return None
    bars, _meta = loaded
    if not bars:
        return None
    return bars, "cache"
