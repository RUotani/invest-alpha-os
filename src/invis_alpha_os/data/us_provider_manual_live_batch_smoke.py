"""US provider **manual live batch smoke** — scaffold, preflight, bounded live preview, and cache-write refusal scaffold (**Main R6.5.1**).

**`debug us-provider-manual-live-batch-smoke`** milestone summary:

- **R6.3 dry-run scaffold** (`manual_live_batch_smoke_dry_run`): no vendor HTTP, no cache write.
- **R6.4.0 preflight** (`manual_live_batch_smoke_preflight_ready`): gate + cap validation only; no vendor HTTP.
- **R6.4.1 bounded live preview** (`manual_live_batch_smoke_live_preview_completed`):
  real HTTP under `--live --preflight --execute-live-http` + both gates + `--max-http > 0`;
  **no cache write**, **no raw response stored**, **no API key value in output**.
- **R6.5.1 cache-write refusal scaffold** (`--evaluate-cache-write`): always refuses with deterministic
  `validation_error`; **no HTTP**, **no cache write**, **no raw response**, **no API key value in output**.
"""

from __future__ import annotations

import os
import time
from typing import Any

from invis_alpha_os.config.us_watchlist import normalize_us_symbol
from invis_alpha_os.data.us_provider_live_preview import (
    CONFIRM_US_CACHE_WRITE_ENV,
    CONFIRM_US_LIVE_HTTP_ENV,
    stooq_live_preview_sanitized_bars,
)
from invis_alpha_os.data.us_provider_scheduled_ingest_plan import (
    ENV_MAX_SYMBOLS,
    ENV_MIN_SLEEP_SECONDS,
    _dedupe_preserve_order,
    _gate_literal,
    _parse_min_sleep_seconds,
    _parse_positive_int,
)

CONFIRM_US_MANUAL_BATCH_SMOKE_ENV = "CONFIRM_US_MANUAL_BATCH_SMOKE"
STOOQ_API_KEY_ENV = "STOOQ_APIKEY"

_REASON_SCAFFOLD = "r6_3_scaffold_no_http_no_write"
_REASON_LIVE_GATE = "manual_batch_smoke_live_http_not_confirmed"
_REASON_LIVE_NA = "manual_batch_smoke_live_execution_not_implemented_in_r6_3"
_REASON_MAX_HTTP_ZERO = "manual_batch_smoke_max_http_zero"
_REASON_PREFLIGHT_READY_ROW = "r6_4_0_preflight_ready_no_http"
_REASON_PREFLIGHT_REQUIRES_LIVE = "manual_batch_smoke_preflight_requires_live"
_REASON_EXECUTE_REQUIRES_LIVE = "manual_batch_smoke_execute_requires_live"
_REASON_EXECUTE_REQUIRES_PREFLIGHT = "manual_batch_smoke_execute_requires_preflight"

# R6.5.1 cache-write evaluation refusal reasons
_REASON_CACHE_WRITE_REQUIRES_LIVE = "manual_batch_cache_write_requires_live"
_REASON_CACHE_WRITE_REQUIRES_PREFLIGHT = "manual_batch_cache_write_requires_preflight"
_REASON_CACHE_WRITE_REQUIRES_EXECUTE = "manual_batch_cache_write_requires_execute_live_http"
_REASON_CACHE_WRITE_REQUIRES_CACHE_GATE = "manual_batch_cache_write_requires_cache_gate"
_REASON_CACHE_WRITE_NOT_ENABLED = "manual_batch_cache_write_not_enabled_in_r6_5_1"


def _symbol_merge_core(
    raw_tokens: list[str],
    *,
    prov: str,
    limit_param: int | None,
) -> tuple[list[dict[str, Any]], list[str], int, int]:
    """Return plan_rows (invalid first), normalized valid symbols, invalid count, constraints max_symbols."""
    plan_rows_partial: list[dict[str, Any]] = []
    normed_acc: list[str] = []

    for raw in raw_tokens:
        stripped = raw.strip()
        if not stripped:
            continue
        n = normalize_us_symbol(stripped)
        if n is None:
            plan_rows_partial.append(
                {
                    "symbol": stripped[:32],
                    "provider": prov,
                    "planned_action": "excluded_invalid_symbol",
                    "live_http_allowed": False,
                    "cache_write_allowed": False,
                    "reason": "invalid_symbol",
                },
            )
            continue
        normed_acc.append(n)

    normed_acc = _dedupe_preserve_order(normed_acc)

    env_symbol_cap = _parse_positive_int(ENV_MAX_SYMBOLS)
    caps: list[int] = []
    if isinstance(limit_param, int) and limit_param > 0:
        caps.append(limit_param)
    if env_symbol_cap is not None:
        caps.append(env_symbol_cap)

    universe_before_trim = len(normed_acc)
    effective_symbol_cap = min(caps) if caps else None
    if effective_symbol_cap is not None:
        normed_acc = normed_acc[:effective_symbol_cap]

    constraints_max_symbols: int = (
        effective_symbol_cap if effective_symbol_cap is not None else universe_before_trim
    )

    invalid_ct = sum(1 for r in plan_rows_partial if r.get("reason") == "invalid_symbol")

    rows_valid: list[dict[str, Any]] = []
    for norm in normed_acc:
        rows_valid.append(
            {
                "symbol": norm,
                "provider": prov,
                "planned_action": "dry_run_only",
                "live_http_allowed": False,
                "cache_write_allowed": False,
                "reason": _REASON_SCAFFOLD,
            },
        )

    invalid_rows = [r for r in plan_rows_partial if r.get("reason") == "invalid_symbol"]
    merged_plan_rows = invalid_rows + rows_valid

    return merged_plan_rows, list(normed_acc), invalid_ct, constraints_max_symbols


def _common_live_refusal_booleans() -> dict[str, Any]:
    return {
        "live_http_performed": False,
        "cache_write_performed": False,
        "raw_response_included": False,
        "provider_api_key_value_included": False,
        "scheduled_ingest_enabled": False,
    }


def _gate_status_block() -> dict[str, Any]:
    return {
        CONFIRM_US_LIVE_HTTP_ENV: _gate_literal(CONFIRM_US_LIVE_HTTP_ENV),
        CONFIRM_US_MANUAL_BATCH_SMOKE_ENV: _gate_literal(CONFIRM_US_MANUAL_BATCH_SMOKE_ENV),
        CONFIRM_US_CACHE_WRITE_ENV: _gate_literal(CONFIRM_US_CACHE_WRITE_ENV),
    }


def build_us_provider_manual_live_batch_smoke_payload(
    raw_tokens: list[str],
    *,
    provider: str = "stooq_preview",
    from_watchlist_used: bool = False,
    symbols_csv_provided: bool = False,
    limit_param: int | None = None,
    max_http: int = 0,
    live_requested: bool = False,
    preflight_requested: bool = False,
    execute_live_http_requested: bool = False,
    evaluate_cache_write_requested: bool = False,
) -> dict[str, Any]:
    """Build manual batch smoke envelope (**R6.5.1** — cache-write always refused; HTTP only under full gate set)."""

    prov = provider.strip()
    if prov != "stooq_preview":
        return {
            "status": "validation_error",
            "reason": "unsupported_provider",
            "provider": prov,
            "observation_only": True,
            "live_requested": live_requested,
            **_common_live_refusal_booleans(),
        }

    if max_http < 0:
        max_http = 0

    merged_plan_rows, normed_acc, invalid_ct, constraints_max_symbols = _symbol_merge_core(
        raw_tokens,
        prov=prov,
        limit_param=limit_param,
    )

    if not normed_acc and invalid_ct == 0:
        return {
            "status": "validation_error",
            "reason": "empty_symbol_batch",
            "provider": prov,
            "observation_only": True,
            "live_requested": live_requested,
            **_common_live_refusal_booleans(),
        }

    min_sleep_val = _parse_min_sleep_seconds()
    valid_count = len(normed_acc)
    planned_http_attempts = min(valid_count, max_http)

    operator_summary_base = {
        "dry_run_plan_count": valid_count,
        "planned_http_attempt_count": planned_http_attempts,
        "live_http_allowed_count": 0,
        "cache_write_allowed_count": 0,
        "invalid_symbol_count": invalid_ct,
    }

    constraints_common: dict[str, Any] = {
        "max_symbols": constraints_max_symbols,
        "max_http_per_run": max_http,
        "planned_http_attempts": planned_http_attempts,
        "min_sleep_seconds": min_sleep_val,
        "requires_operator_approval": True,
    }

    gate_block = _gate_status_block()

    if evaluate_cache_write_requested:
        # R6.5.1 — always refuses; no HTTP, no cache write
        _eval_base: dict[str, Any] = {
            "status": "validation_error",
            "observation_only": True,
            "evaluate_cache_write_requested": True,
            "live_requested": live_requested,
            "preflight_requested": preflight_requested,
            "execute_live_http_requested": execute_live_http_requested,
            "provider": prov,
            "live_http_performed": False,
            "cache_write_performed": False,
            "raw_response_included": False,
            "provider_api_key_value_included": False,
            "scheduled_ingest_enabled": False,
            "manual_batch_smoke_enabled": False,
        }
        if not live_requested:
            return {**_eval_base, "reason": _REASON_CACHE_WRITE_REQUIRES_LIVE}
        if not preflight_requested:
            return {**_eval_base, "reason": _REASON_CACHE_WRITE_REQUIRES_PREFLIGHT}
        if not execute_live_http_requested:
            return {**_eval_base, "reason": _REASON_CACHE_WRITE_REQUIRES_EXECUTE}
        live_ok = os.environ.get(CONFIRM_US_LIVE_HTTP_ENV) == "YES"
        batch_ok = os.environ.get(CONFIRM_US_MANUAL_BATCH_SMOKE_ENV) == "YES"
        if not (live_ok and batch_ok):
            return {**_eval_base, "reason": _REASON_LIVE_GATE}
        cache_ok = os.environ.get(CONFIRM_US_CACHE_WRITE_ENV) == "YES"
        if not cache_ok:
            return {**_eval_base, "reason": _REASON_CACHE_WRITE_REQUIRES_CACHE_GATE}
        # All gates set — still refuse in R6.5.1
        eval_rows: list[dict[str, Any]] = []
        for r in merged_plan_rows:
            if r.get("reason") == "invalid_symbol":
                eval_rows.append(r)
            else:
                eval_rows.append({
                    "symbol": r["symbol"],
                    "provider": prov,
                    "planned_action": "cache_write_evaluation_refused",
                    "live_http_allowed": False,
                    "cache_write_allowed": False,
                    "live_http_performed": False,
                    "cache_write_performed": False,
                    "raw_response_included": False,
                    "reason": "cache_write_evaluation_refused_no_write",
                })
        gate_block_eval = _gate_status_block()
        return {
            **_eval_base,
            "status": "validation_error",
            "reason": _REASON_CACHE_WRITE_NOT_ENABLED,
            "mode": "cache_write_evaluation_refusal_no_write",
            "gate_status": gate_block_eval,
            "constraints": {
                **constraints_common,
                "max_symbols": constraints_max_symbols,
            },
            "operator_summary": {
                "cache_write_allowed_count": 0,
                "cache_write_performed_count": 0,
                "invalid_symbol_count": invalid_ct,
            },
            "symbol_count": len(eval_rows),
            "symbols": list(normed_acc),
            "plan_rows": eval_rows,
            "next_required_approval": "R6.5.2 manual cache-write implementation candidate",
        }

    if execute_live_http_requested:
        if not live_requested:
            return {
                "status": "validation_error",
                "reason": _REASON_EXECUTE_REQUIRES_LIVE,
                "provider": prov,
                "observation_only": True,
                "live_requested": False,
                "preflight_requested": preflight_requested,
                "execute_live_http_requested": True,
                **_common_live_refusal_booleans(),
            }
        if not preflight_requested:
            return {
                "status": "validation_error",
                "reason": _REASON_EXECUTE_REQUIRES_PREFLIGHT,
                "provider": prov,
                "observation_only": True,
                "live_requested": True,
                "preflight_requested": False,
                "execute_live_http_requested": True,
                **_common_live_refusal_booleans(),
            }
        # --live --preflight --execute-live-http path
        live_ok = os.environ.get(CONFIRM_US_LIVE_HTTP_ENV) == "YES"
        batch_ok = os.environ.get(CONFIRM_US_MANUAL_BATCH_SMOKE_ENV) == "YES"
        if not (live_ok and batch_ok):
            return {
                "status": "validation_error",
                "reason": _REASON_LIVE_GATE,
                "provider": prov,
                "observation_only": True,
                "live_requested": True,
                "preflight_requested": True,
                "execute_live_http_requested": True,
                **_common_live_refusal_booleans(),
            }
        if max_http == 0:
            return {
                "status": "validation_error",
                "reason": _REASON_MAX_HTTP_ZERO,
                "provider": prov,
                "observation_only": True,
                "live_requested": True,
                "preflight_requested": True,
                "execute_live_http_requested": True,
                **_common_live_refusal_booleans(),
            }

        # Execute bounded live HTTP
        src_block = {
            "from_watchlist": from_watchlist_used,
            "symbols_csv_provided": symbols_csv_provided,
            "limit": limit_param if isinstance(limit_param, int) and limit_param > 0 else None,
        }
        exec_rows: list[dict[str, Any]] = []
        http_attempted = 0
        live_preview_ok_count = 0
        live_preview_fail_count = 0
        skipped_cap_count = 0

        # invalid symbol rows first
        for r in merged_plan_rows:
            if r.get("reason") == "invalid_symbol":
                exec_rows.append(r)

        for norm in normed_acc:
            if http_attempted >= max_http:
                exec_rows.append({
                    "symbol": norm,
                    "provider": prov,
                    "planned_action": "skipped_max_http_cap",
                    "live_http_allowed": False,
                    "cache_write_allowed": False,
                    "live_http_performed": False,
                    "cache_write_performed": False,
                    "reason": "max_http_cap_reached",
                })
                skipped_cap_count += 1
                continue

            if http_attempted > 0 and min_sleep_val is not None and min_sleep_val > 0:
                time.sleep(min_sleep_val)

            result = stooq_live_preview_sanitized_bars(norm, live=True, write_cache=False)
            http_attempted += 1

            row_status = str(result.get("status") or "")
            row_http_performed = bool(result.get("live_http_performed"))
            row: dict[str, Any] = {
                "symbol": norm,
                "provider": prov,
                "planned_action": "live_preview_http_get",
                "live_http_allowed": True,
                "cache_write_allowed": False,
                "live_http_performed": row_http_performed,
                "cache_write_performed": False,
                "raw_response_included": False,
                "status": "live_preview_ok" if row_status == "preview_ok" else row_status,
            }
            if "reason" in result:
                row["reason"] = result["reason"]
            if row_status == "preview_ok":
                row["sanitized_bar_count"] = result.get("row_count", 0)
                row["bars_source"] = "vendor_live_sanitized_preview"
                live_preview_ok_count += 1
            else:
                live_preview_fail_count += 1

            exec_rows.append(row)

        exec_constraints = {
            **constraints_common,
            "actual_http_attempts": http_attempted,
        }
        exec_op_summary = {
            "dry_run_plan_count": valid_count,
            "planned_http_attempt_count": planned_http_attempts,
            "actual_http_attempt_count": http_attempted,
            "live_preview_success_count": live_preview_ok_count,
            "live_preview_failure_count": live_preview_fail_count,
            "skipped_max_http_cap_count": skipped_cap_count,
            "live_http_allowed_count": http_attempted,
            "cache_write_allowed_count": 0,
            "invalid_symbol_count": invalid_ct,
        }
        return {
            "status": "manual_live_batch_smoke_live_preview_completed",
            "mode": "live_preview_http_no_cache_write",
            "observation_only": True,
            "live_requested": True,
            "preflight_requested": True,
            "execute_live_http_requested": True,
            "live_http_performed": http_attempted > 0,
            "cache_write_performed": False,
            "raw_response_included": False,
            "provider_api_key_env_name": STOOQ_API_KEY_ENV,
            "provider_api_key_value_included": False,
            "scheduled_ingest_enabled": False,
            "manual_batch_smoke_enabled": False,
            "provider": prov,
            "source": src_block,
            "constraints": exec_constraints,
            "gate_status": gate_block,
            "symbol_count": len(exec_rows),
            "symbols": list(normed_acc),
            "plan_rows": exec_rows,
            "operator_summary": exec_op_summary,
            "next_required_approval": "R6.5 manual live batch cache-write evaluation",
        }

    if preflight_requested:
        if not live_requested:
            return {
                "status": "validation_error",
                "reason": _REASON_PREFLIGHT_REQUIRES_LIVE,
                "provider": prov,
                "observation_only": True,
                "live_requested": False,
                "preflight_requested": True,
                **_common_live_refusal_booleans(),
            }
        live_ok = os.environ.get(CONFIRM_US_LIVE_HTTP_ENV) == "YES"
        batch_ok = os.environ.get(CONFIRM_US_MANUAL_BATCH_SMOKE_ENV) == "YES"
        if not (live_ok and batch_ok):
            return {
                "status": "validation_error",
                "reason": _REASON_LIVE_GATE,
                "provider": prov,
                "mode": "preflight_dry_run",
                "observation_only": True,
                "live_requested": live_requested,
                "preflight_requested": True,
                "live_http_performed": False,
                "cache_write_performed": False,
                "raw_response_included": False,
                "provider_api_key_env_name": STOOQ_API_KEY_ENV,
                "provider_api_key_value_included": False,
                "scheduled_ingest_enabled": False,
                "manual_batch_smoke_enabled": False,
                "source": {
                    "from_watchlist": from_watchlist_used,
                    "symbols_csv_provided": symbols_csv_provided,
                    "limit": limit_param if isinstance(limit_param, int) and limit_param > 0 else None,
                },
                "constraints": constraints_common,
                "gate_status": gate_block,
                "symbol_count": len(merged_plan_rows),
                "symbols": list(normed_acc),
                "plan_rows": merged_plan_rows,
                "operator_summary": operator_summary_base,
            }

        if max_http == 0:
            return {
                "status": "validation_error",
                "reason": _REASON_MAX_HTTP_ZERO,
                "provider": prov,
                "mode": "preflight_dry_run",
                "observation_only": True,
                "live_requested": live_requested,
                "preflight_requested": True,
                "live_http_performed": False,
                "cache_write_performed": False,
                "raw_response_included": False,
                "provider_api_key_env_name": STOOQ_API_KEY_ENV,
                "provider_api_key_value_included": False,
                "scheduled_ingest_enabled": False,
                "manual_batch_smoke_enabled": False,
                "source": {
                    "from_watchlist": from_watchlist_used,
                    "symbols_csv_provided": symbols_csv_provided,
                    "limit": limit_param if isinstance(limit_param, int) and limit_param > 0 else None,
                },
                "constraints": constraints_common,
                "gate_status": gate_block,
                "symbol_count": len(merged_plan_rows),
                "symbols": list(normed_acc),
                "plan_rows": merged_plan_rows,
                "operator_summary": operator_summary_base,
            }

        preflight_rows: list[dict[str, Any]] = []
        for r in merged_plan_rows:
            if r.get("reason") == "invalid_symbol":
                preflight_rows.append(r)
            else:
                preflight_rows.append(
                    {
                        "symbol": r["symbol"],
                        "provider": prov,
                        "planned_action": "preflight_ready_no_http",
                        "live_http_allowed": False,
                        "cache_write_allowed": False,
                        "reason": _REASON_PREFLIGHT_READY_ROW,
                    }
                )

        preflight_ready_count = sum(
            1 for r in preflight_rows if r.get("reason") == _REASON_PREFLIGHT_READY_ROW
        )
        preflight_op_summary = {
            **operator_summary_base,
            "preflight_ready_count": preflight_ready_count,
        }

        return {
            "status": "manual_live_batch_smoke_preflight_ready",
            "mode": "preflight_ready_no_http",
            "observation_only": True,
            "live_requested": live_requested,
            "preflight_requested": True,
            "live_http_performed": False,
            "cache_write_performed": False,
            "raw_response_included": False,
            "provider_api_key_env_name": STOOQ_API_KEY_ENV,
            "provider_api_key_value_included": False,
            "scheduled_ingest_enabled": False,
            "manual_batch_smoke_enabled": False,
            "provider": prov,
            "source": {
                "from_watchlist": from_watchlist_used,
                "symbols_csv_provided": symbols_csv_provided,
                "limit": limit_param if isinstance(limit_param, int) and limit_param > 0 else None,
            },
            "constraints": constraints_common,
            "gate_status": gate_block,
            "symbol_count": len(preflight_rows),
            "symbols": list(normed_acc),
            "plan_rows": preflight_rows,
            "operator_summary": preflight_op_summary,
            "next_required_approval": "R6.4.1 manual live batch smoke execution",
        }

    if live_requested:
        if max_http == 0:
            return {
                "status": "validation_error",
                "reason": _REASON_MAX_HTTP_ZERO,
                "provider": prov,
                "mode": "scaffold_dry_run",
                "observation_only": True,
                "live_requested": True,
                "live_http_performed": False,
                "cache_write_performed": False,
                "raw_response_included": False,
                "provider_api_key_env_name": STOOQ_API_KEY_ENV,
                "provider_api_key_value_included": False,
                "scheduled_ingest_enabled": False,
                "manual_batch_smoke_enabled": False,
                "source": {
                    "from_watchlist": from_watchlist_used,
                    "symbols_csv_provided": symbols_csv_provided,
                    "limit": limit_param if isinstance(limit_param, int) and limit_param > 0 else None,
                },
                "constraints": constraints_common,
                "gate_status": gate_block,
                "symbol_count": len(merged_plan_rows),
                "symbols": list(normed_acc),
                "plan_rows": merged_plan_rows,
                "operator_summary": operator_summary_base,
            }

        live_ok = os.environ.get(CONFIRM_US_LIVE_HTTP_ENV) == "YES"
        batch_ok = os.environ.get(CONFIRM_US_MANUAL_BATCH_SMOKE_ENV) == "YES"
        if not (live_ok and batch_ok):
            return {
                "status": "validation_error",
                "reason": _REASON_LIVE_GATE,
                "provider": prov,
                "mode": "scaffold_dry_run",
                "observation_only": True,
                "live_requested": True,
                "live_http_performed": False,
                "cache_write_performed": False,
                "raw_response_included": False,
                "provider_api_key_env_name": STOOQ_API_KEY_ENV,
                "provider_api_key_value_included": False,
                "scheduled_ingest_enabled": False,
                "manual_batch_smoke_enabled": False,
                "source": {
                    "from_watchlist": from_watchlist_used,
                    "symbols_csv_provided": symbols_csv_provided,
                    "limit": limit_param if isinstance(limit_param, int) and limit_param > 0 else None,
                },
                "constraints": constraints_common,
                "gate_status": gate_block,
                "symbol_count": len(merged_plan_rows),
                "symbols": list(normed_acc),
                "plan_rows": merged_plan_rows,
                "operator_summary": operator_summary_base,
            }

        return {
            "status": "validation_error",
            "reason": _REASON_LIVE_NA,
            "provider": prov,
            "mode": "scaffold_dry_run",
            "observation_only": True,
            "live_requested": True,
            "live_http_performed": False,
            "cache_write_performed": False,
            "raw_response_included": False,
            "provider_api_key_env_name": STOOQ_API_KEY_ENV,
            "provider_api_key_value_included": False,
            "scheduled_ingest_enabled": False,
            "manual_batch_smoke_enabled": False,
            "source": {
                "from_watchlist": from_watchlist_used,
                "symbols_csv_provided": symbols_csv_provided,
                "limit": limit_param if isinstance(limit_param, int) and limit_param > 0 else None,
            },
            "constraints": constraints_common,
            "gate_status": gate_block,
            "symbol_count": len(merged_plan_rows),
            "symbols": list(normed_acc),
            "plan_rows": merged_plan_rows,
            "operator_summary": operator_summary_base,
            "next_required_approval": "R6.4.1 manual live batch smoke execution",
        }

    return {
        "status": "manual_live_batch_smoke_dry_run",
        "mode": "scaffold_dry_run",
        "observation_only": True,
        "live_requested": False,
        "live_http_performed": False,
        "cache_write_performed": False,
        "raw_response_included": False,
        "provider_api_key_env_name": STOOQ_API_KEY_ENV,
        "provider_api_key_value_included": False,
        "scheduled_ingest_enabled": False,
        "manual_batch_smoke_enabled": False,
        "provider": prov,
        "source": {
            "from_watchlist": from_watchlist_used,
            "symbols_csv_provided": symbols_csv_provided,
            "limit": limit_param if isinstance(limit_param, int) and limit_param > 0 else None,
        },
        "constraints": constraints_common,
        "gate_status": gate_block,
        "symbol_count": len(merged_plan_rows),
        "symbols": list(normed_acc),
        "plan_rows": merged_plan_rows,
        "operator_summary": operator_summary_base,
        "next_required_approval": "R6.4.1 manual live batch smoke execution",
    }


def render_manual_live_batch_smoke_markdown(payload: dict[str, Any]) -> str:
    """Copy-ready Markdown (**Main R6.4.1**) — **never** API key values / raw payloads."""

    st = str(payload.get("status") or "")
    if st == "validation_error":
        rs = payload.get("reason")
        rs_s = rs if isinstance(rs, str) else "validation_error"
        if payload.get("evaluate_cache_write_requested"):
            return (
                "# US Manual Live Batch Smoke (**R6.5.1 cache-write refusal scaffold**)\n\n"
                f"> **Observation only.** JSON canonical. **status:** `validation_error` — **`{rs_s}`**.\n"
                "> **R6.5.1 refusal scaffold** — **no cache write**, **no live HTTP consumed**.\n\n"
                "## Operator verdict\n\n"
                "Cache-write evaluation refused in R6.5.1. "
                "Fix gate combination or await R6.5.2 implementation.\n\n"
                "## Notes\n\n"
                "- **`--evaluate-cache-write`** is R6.5.1 scaffold only — always refuses.\n"
                "- **JSON remains canonical.** Use `--markdown` for human recap.\n"
            )
        return (
            "# US Manual Live Batch Smoke (**R6.4.1**)\n\n"
            f"> **Observation only.** JSON canonical. **status:** `validation_error` — **`{rs_s}`**.\n\n"
            "## Operator verdict\n\n"
            "Refusal — fix gates, **`--max-http`**, CLI inputs, or flag combination.\n"
        )

    if st == "manual_live_batch_smoke_live_preview_completed":
        gates = payload.get("gate_status")
        gates_lines = ""
        if isinstance(gates, dict):
            gates_lines = "\n".join(f"| `{k}` | `{gates[k]}` |" for k in sorted(gates.keys()))

        cons = payload.get("constraints") if isinstance(payload.get("constraints"), dict) else {}
        op_sum = payload.get("operator_summary") if isinstance(payload.get("operator_summary"), dict) else {}
        plan_rows_raw = payload.get("plan_rows")
        plan_rows: list[dict[str, Any]] = plan_rows_raw if isinstance(plan_rows_raw, list) else []
        ok_rows = [r for r in plan_rows if r.get("status") == "live_preview_ok"]

        lines = [
            "# US Manual Live Batch Smoke (**R6.4.1 live preview completed**)",
            "",
            "> **R6.4.1 live preview completed.** JSON canonical.",
            "> **no cache write**, **raw response not included**.",
            "",
            "## Operator verdict",
            "",
            f"**Live preview completed.** Attempted: {op_sum.get('actual_http_attempt_count', 0)}, "
            f"ok: {op_sum.get('live_preview_success_count', 0)}, "
            f"failed: {op_sum.get('live_preview_failure_count', 0)}.",
            "",
            "## Safety flags",
            "",
            "| flag | value |",
            "|---|---:|",
            f"| live_http_performed | {str(bool(payload.get('live_http_performed'))).lower()} |",
            f"| cache_write_performed | {str(bool(payload.get('cache_write_performed'))).lower()} |",
            f"| raw_response_included | {str(bool(payload.get('raw_response_included'))).lower()} |",
            f"| provider_api_key_value_included | {str(bool(payload.get('provider_api_key_value_included'))).lower()} |",
            f"| observation_only | {str(bool(payload.get('observation_only'))).lower()} |",
            f"| scheduled_ingest_enabled | {str(bool(payload.get('scheduled_ingest_enabled'))).lower()} |",
            "",
            "## Gate status",
            "",
            "| env gate | literal |",
            "|---|---|",
            gates_lines if gates_lines else "| — | — |",
            "",
            "## Results",
            "",
            f"- actual_http_attempts: `{op_sum.get('actual_http_attempt_count', 0)}`",
            f"- live_preview_success_count: `{op_sum.get('live_preview_success_count', 0)}`",
            f"- live_preview_failure_count: `{op_sum.get('live_preview_failure_count', 0)}`",
            f"- skipped_max_http_cap_count: `{op_sum.get('skipped_max_http_cap_count', 0)}`",
            f"- cache_write_allowed_count: `0`",
            "",
        ]
        for r in ok_rows:
            lines.append(
                f"- `{r.get('symbol')}`: {r.get('sanitized_bar_count', '?')} bars "
                f"({r.get('bars_source', '')})"
            )
        lines += [
            "",
            "## Next milestone",
            "",
            f"`{payload.get('next_required_approval')}`",
            "",
            "## Notes",
            "",
            "- **R6.4.1** — bounded live preview only; **no cache write**, **no raw response**.",
            "- This output is **not** scheduled ingest. See **`docs/13`** for R6.6+ scope.",
            "",
        ]
        return "\n".join(lines)

    if st == "manual_live_batch_smoke_preflight_ready":
        gates = payload.get("gate_status")
        gates_lines = ""
        if isinstance(gates, dict):
            gates_lines = "\n".join(f"| `{k}` | `{gates[k]}` |" for k in sorted(gates.keys()))

        cons = payload.get("constraints") if isinstance(payload.get("constraints"), dict) else {}
        src = payload.get("source") if isinstance(payload.get("source"), dict) else {}
        op_sum = payload.get("operator_summary") if isinstance(payload.get("operator_summary"), dict) else {}
        plan_rows_raw = payload.get("plan_rows")
        plan_rows: list[dict[str, Any]] = plan_rows_raw if isinstance(plan_rows_raw, list) else []
        symbols_display = [str(r["symbol"]) for r in plan_rows if isinstance(r.get("symbol"), str)]

        lines = [
            "# US Manual Live Batch Smoke (**R6.4.0 preflight**)",
            "",
            "> **R6.4.0 preflight-ready.** All gates confirmed. **No vendor HTTP performed.** JSON canonical.",
            "> **no vendor HTTP**, **no cache write** — preflight only.",
            "",
            "## Operator verdict",
            "",
            "**Preflight ready.** Gates confirmed. Awaiting R6.4.1 execution approval.",
            "",
            "## Safety flags",
            "",
            "| flag | value |",
            "|---|---:|",
            f"| manual_batch_smoke_enabled | {str(bool(payload.get('manual_batch_smoke_enabled'))).lower()} |",
            f"| scheduled_ingest_enabled | {str(bool(payload.get('scheduled_ingest_enabled'))).lower()} |",
            f"| live_requested | {str(bool(payload.get('live_requested'))).lower()} |",
            f"| preflight_requested | {str(bool(payload.get('preflight_requested'))).lower()} |",
            f"| live_http_performed | {str(bool(payload.get('live_http_performed'))).lower()} |",
            f"| cache_write_performed | {str(bool(payload.get('cache_write_performed'))).lower()} |",
            f"| raw_response_included | {str(bool(payload.get('raw_response_included'))).lower()} |",
            f"| observation_only | {str(bool(payload.get('observation_only'))).lower()} |",
            f"| provider_api_key_value_included | {str(bool(payload.get('provider_api_key_value_included'))).lower()} |",
            "",
            "## Source",
            "",
            f"- from_watchlist: `{src.get('from_watchlist')}`",
            f"- symbols_csv_provided: `{src.get('symbols_csv_provided')}`",
            f"- limit (CLI): `{src.get('limit')}`",
            "",
            "## Constraints",
            "",
            f"- max_symbols (reported): `{cons.get('max_symbols')}`",
            f"- max_http_per_run: `{cons.get('max_http_per_run')}`",
            f"- planned_http_attempts: `{cons.get('planned_http_attempts')}`",
            f"- min_sleep_seconds (`{ENV_MIN_SLEEP_SECONDS}`): `{cons.get('min_sleep_seconds')}`",
            f"- requires_operator_approval: `{cons.get('requires_operator_approval')}`",
            "",
            "## Gate status",
            "",
            "| env gate | literal |",
            "|---|---|",
            gates_lines if gates_lines else "| — | — |",
            "",
            "## Symbols",
            "",
            f"- count (plan_rows): **{payload.get('symbol_count', 0)}**",
            f"- row order: {', '.join(symbols_display) or '—'}",
            "",
            "## Operator summary",
            "",
            f"- dry_run_plan_count: `{op_sum.get('dry_run_plan_count', 0)}`",
            f"- preflight_ready_count: `{op_sum.get('preflight_ready_count', 0)}`",
            f"- planned_http_attempt_count: `{op_sum.get('planned_http_attempt_count', 0)}`",
            f"- live_http_allowed_count: `{op_sum.get('live_http_allowed_count', 0)}`",
            f"- cache_write_allowed_count: `{op_sum.get('cache_write_allowed_count', 0)}`",
            f"- invalid_symbol_count: `{op_sum.get('invalid_symbol_count', 0)}`",
            "",
            "## Next milestone",
            "",
            f"`{payload.get('next_required_approval')}`",
            "",
            "## Notes",
            "",
            "- **R6.4.0 preflight only** — **no vendor HTTP**, **no cache write**.",
            "- Gate **`CONFIRM_US_MANUAL_BATCH_SMOKE`** confirmed for preflight.",
            "- See **`docs/14_us_provider_manual_live_batch_smoke_design.md`**.",
            "",
        ]
        return "\n".join(lines)

    gates = payload.get("gate_status")
    gates_lines = ""
    if isinstance(gates, dict):
        gates_lines = "\n".join(f"| `{k}` | `{gates[k]}` |" for k in sorted(gates.keys()))

    cons = payload.get("constraints") if isinstance(payload.get("constraints"), dict) else {}
    src = payload.get("source") if isinstance(payload.get("source"), dict) else {}

    plan_rows_raw = payload.get("plan_rows")
    plan_rows: list[dict[str, Any]] = plan_rows_raw if isinstance(plan_rows_raw, list) else []
    symbols_display = [str(r["symbol"]) for r in plan_rows if isinstance(r.get("symbol"), str)]

    op_sum = payload.get("operator_summary") if isinstance(payload.get("operator_summary"), dict) else {}

    lines = [
        "# US Manual Live Batch Smoke (**R6.3 scaffold / R6.4.0**)",
        "",
        "> **Copy-ready recap.** **`STOOQ_APIKEY` values are never printed.** JSON remains canonical.",
        "> **R6.3 scaffold only** — **no vendor HTTP**, **no cache write**.",
        "",
        "## Operator verdict",
        "",
        "**Scaffold dry-run.** This output does not perform live vendor work.",
        "",
        "## Safety flags",
        "",
        "| flag | value |",
        "|---|---:|",
        f"| manual_batch_smoke_enabled | {str(bool(payload.get('manual_batch_smoke_enabled'))).lower()} |",
        f"| scheduled_ingest_enabled | {str(bool(payload.get('scheduled_ingest_enabled'))).lower()} |",
        f"| live_requested | {str(bool(payload.get('live_requested'))).lower()} |",
        f"| live_http_performed | {str(bool(payload.get('live_http_performed'))).lower()} |",
        f"| cache_write_performed | {str(bool(payload.get('cache_write_performed'))).lower()} |",
        f"| raw_response_included | {str(bool(payload.get('raw_response_included'))).lower()} |",
        f"| observation_only | {str(bool(payload.get('observation_only'))).lower()} |",
        f"| provider_api_key_value_included | {str(bool(payload.get('provider_api_key_value_included'))).lower()} |",
        "",
        "## Source",
        "",
        f"- from_watchlist: `{src.get('from_watchlist')}`",
        f"- symbols_csv_provided: `{src.get('symbols_csv_provided')}`",
        f"- limit (CLI): `{src.get('limit')}`",
        "",
        "## Constraints",
        "",
        f"- max_symbols (reported): `{cons.get('max_symbols')}`",
        f"- max_http_per_run: `{cons.get('max_http_per_run')}`",
        f"- planned_http_attempts: `{cons.get('planned_http_attempts')}`",
        f"- min_sleep_seconds (`{ENV_MIN_SLEEP_SECONDS}`): `{cons.get('min_sleep_seconds')}`",
        f"- requires_operator_approval: `{cons.get('requires_operator_approval')}`",
        "",
        "## Gate status",
        "",
        "| env gate | literal |",
        "|---|---|",
        gates_lines if gates_lines else "| — | — |",
        "",
        "## Symbols",
        "",
        f"- count (plan_rows): **{payload.get('symbol_count', 0)}**",
        f"- row order: {', '.join(symbols_display) or '—'}",
        "",
        "## Operator summary",
        "",
        f"- dry_run_plan_count: `{op_sum.get('dry_run_plan_count', 0)}`",
        f"- planned_http_attempt_count: `{op_sum.get('planned_http_attempt_count', 0)}`",
        f"- live_http_allowed_count: `{op_sum.get('live_http_allowed_count', 0)}`",
        f"- cache_write_allowed_count: `{op_sum.get('cache_write_allowed_count', 0)}`",
        f"- invalid_symbol_count: `{op_sum.get('invalid_symbol_count', 0)}`",
        "",
        "## Next milestone",
        "",
        f"`{payload.get('next_required_approval')}`",
        "",
        "## Notes",
        "",
        "- **R6.3 scaffold only** — **no vendor HTTP**, **no cache write**.",
        "- Gate **`CONFIRM_US_MANUAL_BATCH_SMOKE`** is documented for **R6.4.1+** execution.",
        "- See **`docs/14_us_provider_manual_live_batch_smoke_design.md`**.",
        "",
    ]

    return "\n".join(lines)
