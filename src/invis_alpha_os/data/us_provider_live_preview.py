"""Gated one-symbol live preview for US provider wiring (Main R3: Stooq only).

Performs at most one short HTTP GET when ``live=True`` and ``CONFIRM_US_LIVE_HTTP=YES``.
Never prints or persists raw CSV/response bodies; output is a shape digest only.
Does not write ``us_daily_bars`` cache.
"""

from __future__ import annotations

import csv
import io
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from invis_alpha_os.config.us_watchlist import normalize_us_symbol
from invis_alpha_os.data.us_provider_preview import build_stooq_daily_preview

CONFIRM_US_LIVE_HTTP_ENV = "CONFIRM_US_LIVE_HTTP"
STOOQ_TIMEOUT_SEC = 10


def _base_parse_error(
    *,
    norm: str,
    reason: str,
    live_http_performed: bool,
    http_status: int | None = None,
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
