"""Dry-run preview of planned US OHLCV provider requests (Main R2).

No HTTP. No env/.env reads for API keys. Output is suitable for CLI JSON only —
never persists ``raw_response`` or vendor envelopes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from invis_alpha_os.config.loader import load_yaml
from invis_alpha_os.config.paths import CONFIG_DIR
from invis_alpha_os.config.us_watchlist import normalize_us_symbol

_PREVIEW_DETAIL = (
    "Main R2 preview only; provider HTTP fetch is not implemented. "
    "Use sanitized OHLCV + save_us_daily_bars_cache after future gated ingest."
)

_STOOQ_NOTE = (
    "Stooq daily CSV uses suffix `.us` and maps dots to hyphens for class‑B style tickers "
    "(e.g. BRK.B → brk-b.us). Venue-specific failures are possible — validate per symbol "
    "before any future live fetch."
)


def _us_market_yaml_path(cfg_path: Path | None = None) -> Path:
    return (CONFIG_DIR / "us_market_data.yaml") if cfg_path is None else Path(cfg_path)


def load_us_market_data_config(cfg_path: Path | None = None) -> dict[str, Any]:
    data = load_yaml(_us_market_yaml_path(cfg_path))
    return data if isinstance(data, dict) else {}


def us_cache_target_relpath(symbol_normalized: str) -> str:
    """Relative JSON path under repo ``outputs/`` convention (machine-local)."""

    return f"outputs/market_data/us_daily_bars/{symbol_normalized}.json"


def _norm_or_error(symbol: str) -> tuple[str | None, dict[str, Any] | None]:
    n = normalize_us_symbol(symbol.strip())
    if n is None:
        return None, {
            "status": "validation_error",
            "reason": "invalid_symbol",
            "live_http": False,
            "raw_response_included": False,
        }
    return n, None


def stooq_daily_symbol_wire(normalized_upper: str) -> str:
    """Map normalized US ticker to Stooq-style daily CSV ``s`` parameter (heuristic)."""

    return f"{normalized_upper.lower().replace('.', '-')}.us"


def build_alpha_vantage_daily_preview(symbol: str, cfg_path: Path | None = None) -> dict[str, Any]:
    norm, err = _norm_or_error(symbol)
    if err is not None:
        err["detail"] = _PREVIEW_DETAIL
        return err

    cfg = load_us_market_data_config(cfg_path)
    pv = cfg.get("providers") or {}
    blk = pv.get("alpha_vantage_preview") if isinstance(pv, dict) else None
    if not isinstance(blk, dict):
        blk = {}

    base = str(blk.get("base_url") or "https://www.alphavantage.co/query").strip()
    fn = str(blk.get("function") or "TIME_SERIES_DAILY_ADJUSTED").strip()
    out_sz = str(blk.get("outputsize") or "compact").strip()

    q: dict[str, str] = {
        "function": fn,
        "symbol": norm,
        "outputsize": out_sz,
        "datatype": "json",
        "apikey": "<redacted_required_later>",
    }
    return {
        "status": "preview_ok",
        "symbol": norm,
        "provider": "alpha_vantage_preview",
        "live_http": False,
        "raw_response_included": False,
        "base_url_without_secrets": base,
        "query_params_without_secrets": q,
        "cache_target": us_cache_target_relpath(norm),
        "adjusted": True,
        "detail": _PREVIEW_DETAIL,
    }


def build_stooq_daily_preview(symbol: str, cfg_path: Path | None = None) -> dict[str, Any]:
    norm, err = _norm_or_error(symbol)
    if err is not None:
        err["detail"] = _PREVIEW_DETAIL
        return err

    cfg = load_us_market_data_config(cfg_path)
    pv = cfg.get("providers") or {}
    blk = pv.get("stooq_preview") if isinstance(pv, dict) else None
    base = (
        str(blk.get("base_url")).strip()
        if isinstance(blk, dict) and blk.get("base_url")
        else "https://stooq.com/q/d/l/"
    )

    wire = stooq_daily_symbol_wire(norm)
    qp: dict[str, str] = {
        "s": wire,
        "i": "d",
        "apikey": "<redacted_required_later>",
    }
    full_preview = f"{base}?{urlencode(qp)}"
    return {
        "status": "preview_ok",
        "symbol": norm,
        "provider": "stooq_preview",
        "live_http": False,
        "raw_response_included": False,
        "base_url_without_secrets": base,
        "query_params_without_secrets": qp,
        "cache_target": us_cache_target_relpath(norm),
        "adjusted": False,
        "detail": _PREVIEW_DETAIL,
        "note": _STOOQ_NOTE,
        "preview_url_without_secrets": full_preview,
    }


def build_manual_file_preview(symbol: str) -> dict[str, Any]:
    norm, err = _norm_or_error(symbol)
    if err is not None:
        err["detail"] = _PREVIEW_DETAIL
        return err
    return {
        "status": "preview_ok",
        "symbol": norm,
        "provider": "manual_file",
        "live_http": False,
        "raw_response_included": False,
        "cache_target": us_cache_target_relpath(norm),
        "detail": _PREVIEW_DETAIL,
        "note": "Populate cache via committed fixtures or debug us-daily-bars-cache-import (no vendor HTTP).",
    }


_PREVIEW_BUILDERS: dict[str, Any] = {
    "alpha_vantage_preview": build_alpha_vantage_daily_preview,
    "stooq_preview": build_stooq_daily_preview,
    "manual_file": build_manual_file_preview,
}


def build_us_provider_preview_plan(
    symbol: str,
    provider: str | None = None,
    *,
    cfg_path: Path | None = None,
) -> dict[str, Any]:
    """Return a structured preview dict for CLI (no HTTP, no secrets)."""

    cfg = load_us_market_data_config(cfg_path)
    key = (provider or "").strip() if provider is not None else ""
    if not key:
        def_key = cfg.get("provider_default")
        key = str(def_key).strip() if isinstance(def_key, str) else ""

    if not key:
        return {
            "status": "validation_error",
            "reason": "unknown_provider",
            "provider_input": "",
            "live_http": False,
            "raw_response_included": False,
            "detail": _PREVIEW_DETAIL,
        }

    if key not in _PREVIEW_BUILDERS:
        return {
            "status": "validation_error",
            "reason": "unknown_provider",
            "provider_input": key,
            "live_http": False,
            "raw_response_included": False,
            "detail": _PREVIEW_DETAIL,
        }

    builder = _PREVIEW_BUILDERS[key]
    if key == "manual_file":
        return builder(symbol)
    return builder(symbol, cfg_path)
