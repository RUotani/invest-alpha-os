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


def _us_daily_bar_rows_valid(raw_bars: list[Any]) -> bool:
    """Bar list must be non-empty dict rows with unique dates in ascending order."""

    if not raw_bars:
        return False
    seen_dates: set[str] = set()
    prior = ""
    for row in raw_bars:
        if not isinstance(row, dict):
            return False
        d = str(row.get("date", "")).strip()
        if not d or d in seen_dates:
            return False
        if prior and d < prior:
            return False
        prior = d
        seen_dates.add(d)
    return True


def parse_us_daily_bars_payload(
    data: dict[str, Any], *, expect_symbol: str | None
) -> tuple[list[DailyBar], dict[str, Any]] | None:
    """Validate a US daily bars JSON object and return bars + meta (no disk I/O)."""

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

    if expect_symbol is not None:
        try:
            requested = _symbol_slug_or_raise(expect_symbol)
        except ValueError:
            return None
        if norm_stored != requested:
            return None

    raw_bars = data.get("bars")
    if not isinstance(raw_bars, list) or not _us_daily_bar_rows_valid(raw_bars):
        return None
    bar_count = data.get("bar_count")
    if bar_count is not None:
        try:
            if int(bar_count) != len(raw_bars):
                return None
        except (TypeError, ValueError):
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


def load_us_daily_bars_json_file(
    path: Path, *, expect_symbol: str | None = None
) -> tuple[list[DailyBar], dict[str, Any]] | None:
    """Load US daily bars from an explicit JSON path (fixture or offline file; no HTTP)."""

    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return parse_us_daily_bars_payload(data, expect_symbol=expect_symbol)


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
    return parse_us_daily_bars_payload(data, expect_symbol=symbol)


def try_load_cached_us_daily_bars(symbol: str) -> tuple[list[DailyBar], str] | None:
    loaded = load_us_daily_bars_cache(symbol)
    if loaded is None:
        return None
    bars, _meta = loaded
    if not bars:
        return None
    return bars, "cache"


def build_us_daily_bars_cache_preview(
    path: Path,
    *,
    expect_symbol: str | None = None,
) -> dict[str, Any]:
    """Build a short diagnostics dict from a cache JSON path (no HTTP, no disk write)."""

    rel_path = str(path)
    if not path.is_file():
        return {
            "validation_status": "invalid",
            "reason": "path_not_found",
            "path": rel_path,
            "live_http": False,
        }

    loaded = load_us_daily_bars_json_file(path, expect_symbol=expect_symbol)
    if loaded is None:
        return {
            "validation_status": "invalid",
            "reason": "parse_failed",
            "path": rel_path,
            "expect_symbol": expect_symbol,
            "live_http": False,
        }

    bars, meta = loaded
    if not bars:
        return {
            "validation_status": "invalid",
            "reason": "empty_bars",
            "path": rel_path,
            "live_http": False,
        }

    first = bars[0]
    last = bars[-1]
    return {
        "validation_status": "ok",
        "path": rel_path,
        "symbol": meta.get("symbol", ""),
        "bar_count": len(bars),
        "first_date": first["date"],
        "last_date": last["date"],
        "last_close": last["close"],
        "last_volume": last["volume"],
        "source": meta.get("source", ""),
        "asset_class": meta.get("asset_class"),
        "fetched_at": meta.get("fetched_at"),
        "generated_at": meta.get("generated_at"),
        "live_http": False,
    }


def format_us_daily_bars_cache_preview_markdown(preview: dict[str, Any]) -> str:
    """Human-readable preview (cache-only diagnostics)."""

    lines = ["## US daily bars cache preview", ""]
    status = preview.get("validation_status", "unknown")
    lines.append(f"- **validation_status**: {status}")
    if status != "ok":
        reason = preview.get("reason", "")
        if reason:
            lines.append(f"- **reason**: {reason}")
        path = preview.get("path", "")
        if path:
            lines.append(f"- **path**: `{path}`")
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            f"- **symbol**: {preview.get('symbol', '')}",
            f"- **bar_count**: {preview.get('bar_count', 0)}",
            f"- **first_date**: {preview.get('first_date', '')}",
            f"- **last_date**: {preview.get('last_date', '')}",
            f"- **last_close**: {preview.get('last_close', '')}",
            f"- **last_volume**: {preview.get('last_volume', '')}",
            f"- **source**: {preview.get('source', '')}",
        ]
    )
    ac = preview.get("asset_class")
    if ac:
        lines.append(f"- **asset_class**: {ac}")
    lines.append(f"- **path**: `{preview.get('path', '')}`")
    return "\n".join(lines) + "\n"


def format_us_daily_bars_cache_preview_json(preview: dict[str, Any]) -> str:
    return json.dumps(preview, ensure_ascii=False, indent=2)
