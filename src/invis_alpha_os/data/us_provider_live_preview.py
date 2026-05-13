"""Gated one-symbol US Stooq path: shape preview (Main R3) + sanitized parse / cache (Main R4).

Performs at most one short HTTP GET when ``live=True`` and ``CONFIRM_US_LIVE_HTTP=YES``.
Optional ``save_us_daily_bars_cache`` when ``write_cache=True`` and ``CONFIRM_US_CACHE_WRITE=YES``.
Never prints or persists raw CSV/response bodies.
"""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path
from typing import Any

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from invis_alpha_os.config.loader import load_yaml
from invis_alpha_os.config.paths import CONFIG_DIR, ROOT_DIR
from invis_alpha_os.config.us_watchlist import normalize_us_symbol, us_symbol_asset_class_defaults
from invis_alpha_os.data.jquants_daily_bars_cache import utc_now_iso
from invis_alpha_os.data.us_daily_bars_cache import save_us_daily_bars_cache
from invis_alpha_os.data.us_provider_preview import build_stooq_daily_preview, us_cache_target_relpath
from invis_alpha_os.data.us_stooq_daily_csv import (
    classify_stooq_csv_text_safely,
    parse_stooq_daily_csv_to_rows,
)

CONFIRM_US_LIVE_HTTP_ENV = "CONFIRM_US_LIVE_HTTP"
CONFIRM_US_CACHE_WRITE_ENV = "CONFIRM_US_CACHE_WRITE"
STOOQ_TIMEOUT_SEC = 10


def _base_parse_error(
    *,
    norm: str,
    reason: str,
    live_http_performed: bool,
    http_status: int | None = None,
    response_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "status": "parse_error",
        "reason": reason,
        "symbol": norm,
        "provider": "stooq_preview",
        "live_http_performed": live_http_performed,
        "raw_response_included": False,
        "cache_write_performed": False,
    }
    if http_status is not None:
        out["http_status"] = http_status
    if response_diagnostics is not None:
        out["response_diagnostics"] = response_diagnostics
    return out


def stooq_live_preview_shape_digest(symbol: str, *, live: bool = False) -> dict[str, Any]:
    """Return dry-run, validation, or live Stooq daily CSV **shape** summary (no OHLCV values)."""

    norm = normalize_us_symbol(symbol.strip())
    if norm is None:
        return {
            "status": "validation_error",
            "reason": "invalid_symbol",
            "live_http_performed": False,
            "raw_response_included": False,
            "cache_write_performed": False,
        }

    if not live:
        return {
            "status": "dry_run",
            "provider": "stooq_preview",
            "symbol": norm,
            "live_http_performed": False,
            "raw_response_included": False,
            "cache_write_performed": False,
            "detail": "Pass --live and CONFIRM_US_LIVE_HTTP=YES to perform gated live preview.",
        }

    if os.environ.get(CONFIRM_US_LIVE_HTTP_ENV) != "YES":
        return {
            "status": "validation_error",
            "reason": "live_http_not_confirmed",
            "live_http_performed": False,
            "raw_response_included": False,
            "cache_write_performed": False,
        }

    plan = build_stooq_daily_preview(symbol)
    if plan.get("status") != "preview_ok":
        return {
            "status": "validation_error",
            "reason": "preview_plan_failed",
            "symbol": norm,
            "provider": "stooq_preview",
            "live_http_performed": False,
            "raw_response_included": False,
            "cache_write_performed": False,
        }

    url = str(plan.get("preview_url_without_secrets") or "").strip()
    if not url:
        return {
            "status": "validation_error",
            "reason": "missing_preview_url",
            "symbol": norm,
            "provider": "stooq_preview",
            "live_http_performed": False,
            "raw_response_included": False,
            "cache_write_performed": False,
        }

    req = Request(
        url,
        headers={"User-Agent": "invest-alpha-os/observation-only (Main R3 Stooq preview)"},
        method="GET",
    )

    http_status: int | None = None
    try:
        with urlopen(req, timeout=STOOQ_TIMEOUT_SEC) as resp:  # noqa: S310 — gated; tests monkeypatch
            http_status = int(resp.getcode())
            raw = resp.read()
    except HTTPError as e:
        code = int(e.code) if e.code is not None else None
        return {
            "status": "http_error",
            "reason": f"http_status_{code}" if code is not None else "http_error",
            "http_status": code,
            "symbol": norm,
            "provider": "stooq_preview",
            "live_http_performed": True,
            "raw_response_included": False,
            "cache_write_performed": False,
        }
    except (URLError, TimeoutError, OSError):
        return {
            "status": "http_error",
            "reason": "network_or_timeout",
            "symbol": norm,
            "provider": "stooq_preview",
            "live_http_performed": True,
            "raw_response_included": False,
            "cache_write_performed": False,
        }

    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        return _base_parse_error(
            norm=norm,
            reason="csv_decode_failed",
            live_http_performed=True,
            http_status=http_status,
        )

    reader = csv.reader(io.StringIO(text))
    try:
        rows = list(reader)
    except csv.Error:
        return _base_parse_error(
            norm=norm,
            reason="csv_parse_failed",
            live_http_performed=True,
            http_status=http_status,
        )

    if not rows:
        return _base_parse_error(
            norm=norm,
            reason="empty_csv",
            live_http_performed=True,
            http_status=http_status,
        )

    header = [c.strip() for c in rows[0]]
    data_rows = [r for r in rows[1:] if r and any(str(c).strip() for c in r)]
    if not header or not data_rows:
        return _base_parse_error(
            norm=norm,
            reason="csv_parse_failed",
            live_http_performed=True,
            http_status=http_status,
        )

    try:
        first_date = str(data_rows[0][0]).strip()
        last_date = str(data_rows[-1][0]).strip()
    except (IndexError, TypeError):
        return _base_parse_error(
            norm=norm,
            reason="csv_parse_failed",
            live_http_performed=True,
            http_status=http_status,
        )

    return {
        "status": "live_preview_ok",
        "symbol": norm,
        "provider": "stooq_preview",
        "row_count": len(data_rows),
        "first_date": first_date,
        "last_date": last_date,
        "columns": header,
        "live_http_performed": True,
        "raw_response_included": False,
        "cache_write_performed": False,
        "http_status": http_status,
    }


def _resolved_us_asset_class(norm: str) -> str | None:
    try:
        data = load_yaml(CONFIG_DIR / "us_watchlist.yaml")
    except (OSError, TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return us_symbol_asset_class_defaults(data).get(norm)


def _rel_under_root(path: Path) -> str:
    try:
        return path.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def _stooq_live_fetch_csv_text(norm: str) -> dict[str, Any] | tuple[int, str]:
    """Return an error payload dict, or ``(http_status, decoded_text)`` on success."""

    plan = build_stooq_daily_preview(norm)
    if plan.get("status") != "preview_ok":
        return {
            "status": "validation_error",
            "reason": "preview_plan_failed",
            "symbol": norm,
            "provider": "stooq_preview",
            "live_http_performed": False,
            "raw_response_included": False,
            "cache_write_performed": False,
        }

    url = str(plan.get("preview_url_without_secrets") or "").strip()
    if not url:
        return {
            "status": "validation_error",
            "reason": "missing_preview_url",
            "symbol": norm,
            "provider": "stooq_preview",
            "live_http_performed": False,
            "raw_response_included": False,
            "cache_write_performed": False,
        }

    req = Request(
        url,
        headers={"User-Agent": "invest-alpha-os/observation-only (Main R4 Stooq ingest)"},
        method="GET",
    )

    http_status: int | None = None
    try:
        with urlopen(req, timeout=STOOQ_TIMEOUT_SEC) as resp:  # noqa: S310
            http_status = int(resp.getcode())
            raw = resp.read()
    except HTTPError as e:
        code = int(e.code) if e.code is not None else None
        return {
            "status": "http_error",
            "reason": f"http_status_{code}" if code is not None else "http_error",
            "http_status": code,
            "symbol": norm,
            "provider": "stooq_preview",
            "live_http_performed": True,
            "raw_response_included": False,
            "cache_write_performed": False,
        }
    except (URLError, TimeoutError, OSError):
        return {
            "status": "http_error",
            "reason": "network_or_timeout",
            "symbol": norm,
            "provider": "stooq_preview",
            "live_http_performed": True,
            "raw_response_included": False,
            "cache_write_performed": False,
        }

    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        return _base_parse_error(
            norm=norm,
            reason="csv_decode_failed",
            live_http_performed=True,
            http_status=http_status,
        )

    assert http_status is not None
    return (http_status, text)


def stooq_live_preview_sanitized_bars(
    symbol: str,
    *,
    live: bool = False,
    write_cache: bool = False,
) -> dict[str, Any]:
    """Gated Stooq fetch → strict sanitized OHLC rows; optional on-disk cache (Main R4)."""

    norm = normalize_us_symbol(symbol.strip())
    if norm is None:
        return {
            "status": "validation_error",
            "reason": "invalid_symbol",
            "live_http_performed": False,
            "cache_write_performed": False,
            "raw_response_included": False,
        }

    canonical_cols = ["date", "open", "high", "low", "close", "volume"]
    cache_target = us_cache_target_relpath(norm)

    if not live:
        return {
            "status": "dry_run",
            "provider": "stooq_preview",
            "symbol": norm,
            "live_http_performed": False,
            "cache_write_performed": False,
            "raw_response_included": False,
            "detail": (
                "Pass --live and CONFIRM_US_LIVE_HTTP=YES to fetch; pass --write-cache "
                "and CONFIRM_US_CACHE_WRITE=YES to write cache."
            ),
        }

    if os.environ.get(CONFIRM_US_LIVE_HTTP_ENV) != "YES":
        return {
            "status": "validation_error",
            "reason": "live_http_not_confirmed",
            "live_http_performed": False,
            "cache_write_performed": False,
            "raw_response_included": False,
        }

    if write_cache and os.environ.get(CONFIRM_US_CACHE_WRITE_ENV) != "YES":
        return {
            "status": "validation_error",
            "reason": "cache_write_not_confirmed",
            "live_http_performed": False,
            "cache_write_performed": False,
            "raw_response_included": False,
        }

    got = _stooq_live_fetch_csv_text(norm)
    if isinstance(got, dict):
        return got

    http_status, text = got

    try:
        rows = parse_stooq_daily_csv_to_rows(text)
    except ValueError as e:
        code = str(e)
        if code not in (
            "stooq_csv_no_rows",
            "stooq_csv_missing_required_columns",
            "stooq_csv_parse_failed",
        ):
            code = "stooq_csv_parse_failed"
        diagnostics = classify_stooq_csv_text_safely(text)
        return _base_parse_error(
            norm=norm,
            reason=code,
            live_http_performed=True,
            http_status=http_status,
            response_diagnostics=diagnostics,
        )

    first_date = str(rows[0]["date"])
    last_date = str(rows[-1]["date"])

    if not write_cache:
        return {
            "status": "preview_ok",
            "provider": "stooq_preview",
            "symbol": norm,
            "row_count": len(rows),
            "first_date": first_date,
            "last_date": last_date,
            "columns": canonical_cols,
            "live_http_performed": True,
            "cache_write_performed": False,
            "raw_response_included": False,
            "cache_target": cache_target,
        }

    ac = _resolved_us_asset_class(norm)
    fetched = utc_now_iso()
    try:
        written = save_us_daily_bars_cache(
            norm,
            list(rows),
            asset_class=ac,
            source="stooq_preview_gated_live",
            fetched_at=fetched,
            generated_at=fetched,
        )
    except ValueError:
        return {
            "status": "parse_error",
            "reason": "cache_persist_refused",
            "symbol": norm,
            "provider": "stooq_preview",
            "live_http_performed": True,
            "cache_write_performed": False,
            "raw_response_included": False,
            "http_status": http_status,
        }

    return {
        "status": "success",
        "provider": "stooq_preview",
        "symbol": norm,
        "row_count": len(rows),
        "cache_written_to": _rel_under_root(written),
        "live_http_performed": True,
        "cache_write_performed": True,
        "raw_response_included": False,
    }
