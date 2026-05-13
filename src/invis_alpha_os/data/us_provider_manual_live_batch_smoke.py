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
import re
import time
from pathlib import Path
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

# R6.5.7 execute-cache-write refusal reasons
_REASON_EXEC_CW_REQUIRES_LIVE = "manual_batch_execute_cache_write_requires_live"
_REASON_EXEC_CW_REQUIRES_PREFLIGHT = "manual_batch_execute_cache_write_requires_preflight"
_REASON_EXEC_CW_REQUIRES_EXECUTE_LIVE_HTTP = "manual_batch_execute_cache_write_requires_execute_live_http"
_REASON_EXEC_CW_REQUIRES_EVALUATE = "manual_batch_execute_cache_write_requires_evaluate_cache_write"


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
    execute_cache_write_requested: bool = False,
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

    if execute_cache_write_requested:
        # R6.5.7 — production cache write; all 9 conditions required
        _ecw_base: dict[str, Any] = {
            "status": "validation_error",
            "observation_only": True,
            "execute_cache_write_requested": True,
            "evaluate_cache_write_requested": evaluate_cache_write_requested,
            "live_requested": live_requested,
            "preflight_requested": preflight_requested,
            "execute_live_http_requested": execute_live_http_requested,
            "provider": prov,
            "live_http_performed": False,
            "cache_write_performed": False,
            "real_cache_write_performed": False,
            "raw_response_included": False,
            "provider_api_key_value_included": False,
            "scheduled_ingest_enabled": False,
            "manual_batch_smoke_enabled": False,
        }
        if not live_requested:
            return {**_ecw_base, "reason": _REASON_EXEC_CW_REQUIRES_LIVE}
        if not preflight_requested:
            return {**_ecw_base, "reason": _REASON_EXEC_CW_REQUIRES_PREFLIGHT}
        if not execute_live_http_requested:
            return {**_ecw_base, "reason": _REASON_EXEC_CW_REQUIRES_EXECUTE_LIVE_HTTP}
        if not evaluate_cache_write_requested:
            return {**_ecw_base, "reason": _REASON_EXEC_CW_REQUIRES_EVALUATE}
        ecw_live_ok = os.environ.get(CONFIRM_US_LIVE_HTTP_ENV) == "YES"
        ecw_batch_ok = os.environ.get(CONFIRM_US_MANUAL_BATCH_SMOKE_ENV) == "YES"
        if not (ecw_live_ok and ecw_batch_ok):
            return {**_ecw_base, "reason": _REASON_LIVE_GATE}
        ecw_cache_ok = os.environ.get(CONFIRM_US_CACHE_WRITE_ENV) == "YES"
        if not ecw_cache_ok:
            return {**_ecw_base, "reason": _REASON_CACHE_WRITE_REQUIRES_CACHE_GATE}
        if max_http == 0:
            return {**_ecw_base, "reason": _REASON_MAX_HTTP_ZERO}

        # All 9 conditions satisfied — execute production cache write
        ecw_src_block = {
            "from_watchlist": from_watchlist_used,
            "symbols_csv_provided": symbols_csv_provided,
            "limit": limit_param if isinstance(limit_param, int) and limit_param > 0 else None,
        }
        write_rows: list[dict[str, Any]] = []
        http_attempted = 0
        write_ok_count = 0
        write_fail_count = 0
        skipped_cap_count = 0

        for r in merged_plan_rows:
            if r.get("reason") == "invalid_symbol":
                write_rows.append(r)

        for norm in normed_acc:
            if http_attempted >= max_http:
                write_rows.append({
                    "symbol": norm,
                    "provider": prov,
                    "planned_action": "skipped_max_http_cap",
                    "live_http_performed": False,
                    "cache_write_performed": False,
                    "real_cache_write_performed": False,
                    "reason": "max_http_cap_reached",
                })
                skipped_cap_count += 1
                continue

            if http_attempted > 0 and min_sleep_val is not None and min_sleep_val > 0:
                time.sleep(min_sleep_val)

            result = stooq_live_preview_sanitized_bars(norm, live=True, write_cache=True)
            http_attempted += 1

            row_status = str(result.get("status") or "")
            row_cache_written = bool(result.get("cache_write_performed"))
            ecw_row: dict[str, Any] = {
                "symbol": norm,
                "provider": prov,
                "planned_action": "manual_cache_write_live_and_persist",
                "live_http_performed": bool(result.get("live_http_performed")),
                "cache_write_performed": row_cache_written,
                "real_cache_write_performed": row_cache_written,
                "raw_response_included": False,
                "provider_api_key_value_included": False,
                "status": row_status,
            }
            if "reason" in result:
                ecw_row["reason"] = result["reason"]
            if "cache_written_to" in result:
                ecw_row["cache_written_to"] = result["cache_written_to"]
            if row_status == "success" and row_cache_written:
                ecw_row["row_count"] = result.get("row_count", 0)
                write_ok_count += 1
            else:
                write_fail_count += 1
            write_rows.append(ecw_row)

        real_write_performed = write_ok_count > 0
        write_constraints = {**constraints_common, "actual_http_attempts": http_attempted}
        write_op_summary = {
            "dry_run_plan_count": valid_count,
            "planned_http_attempt_count": planned_http_attempts,
            "actual_http_attempt_count": http_attempted,
            "cache_write_success_count": write_ok_count,
            "cache_write_failure_count": write_fail_count,
            "skipped_max_http_cap_count": skipped_cap_count,
            "invalid_symbol_count": invalid_ct,
        }
        return {
            "status": "manual_cache_write_completed",
            "mode": "live_http_and_cache_write",
            "observation_only": True,
            "live_requested": True,
            "preflight_requested": True,
            "execute_live_http_requested": True,
            "evaluate_cache_write_requested": True,
            "execute_cache_write_requested": True,
            "live_http_performed": http_attempted > 0,
            "cache_write_performed": real_write_performed,
            "real_cache_write_performed": real_write_performed,
            "raw_response_included": False,
            "provider_api_key_env_name": STOOQ_API_KEY_ENV,
            "provider_api_key_value_included": False,
            "scheduled_ingest_enabled": False,
            "manual_batch_smoke_enabled": False,
            "provider": prov,
            "source": ecw_src_block,
            "constraints": write_constraints,
            "gate_status": gate_block,
            "symbol_count": len(write_rows),
            "symbols": list(normed_acc),
            "plan_rows": write_rows,
            "operator_summary": write_op_summary,
        }

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


def evaluate_manual_cache_write_eligibility_from_rows(
    plan_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Pure deterministic cache-write eligibility classifier (**Main R6.5.2**).

    Classifies each row as eligible or rejected.  **No cache write, no HTTP, no cache writer import.**
    """
    eligible_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []

    cnt_invalid = cnt_parse = cnt_transport = cnt_validation = 0
    cnt_cap = cnt_raw = cnt_other = 0

    for row in plan_rows:
        symbol = row.get("symbol", "")
        status = str(row.get("status") or "")
        reason = str(row.get("reason") or "")
        planned_action = str(row.get("planned_action") or "")
        raw_included = row.get("raw_response_included")

        def _reject(rej_reason: str) -> dict[str, Any]:
            return {
                "symbol": symbol,
                "cache_write_eligible": False,
                "reason": rej_reason,
            }

        # Reject: raw response present
        if raw_included is True:
            cnt_raw += 1
            rejected_rows.append(_reject("manual_batch_cache_write_rejects_raw_response"))
            continue

        # Reject: invalid symbol
        if reason == "invalid_symbol" or planned_action == "excluded_invalid_symbol":
            cnt_invalid += 1
            rejected_rows.append(_reject("manual_batch_cache_write_rejects_invalid_symbol"))
            continue

        # Reject: capped
        if reason == "max_http_cap_reached" or planned_action == "skipped_max_http_cap":
            cnt_cap += 1
            rejected_rows.append(_reject("manual_batch_cache_write_rejects_max_http_capped_row"))
            continue

        # Reject: known error statuses
        if status == "parse_error" or reason == "parse_error":
            cnt_parse += 1
            rejected_rows.append(_reject("manual_batch_cache_write_rejects_parse_error"))
            continue
        if status == "transport_error" or reason == "transport_error":
            cnt_transport += 1
            rejected_rows.append(_reject("manual_batch_cache_write_rejects_transport_error"))
            continue
        if status == "validation_error" or reason == "validation_error":
            cnt_validation += 1
            rejected_rows.append(_reject("manual_batch_cache_write_rejects_validation_error"))
            continue

        # Eligible check
        bar_count = row.get("sanitized_bar_count")
        eligible = (
            status == "live_preview_ok"
            and planned_action == "live_preview_http_get"
            and row.get("live_http_performed") is True
            and row.get("cache_write_performed") is False
            and raw_included is False
            and row.get("bars_source") == "vendor_live_sanitized_preview"
            and isinstance(bar_count, int)
            and bar_count > 0
            and isinstance(symbol, str)
            and len(symbol) > 0
        )
        if eligible:
            eligible_rows.append({
                "symbol": symbol,
                "cache_write_eligible": True,
                "reason": "manual_batch_cache_write_eligible_live_preview_ok",
                "sanitized_bar_count": bar_count,
            })
        else:
            cnt_other += 1
            rejected_rows.append(_reject("manual_batch_cache_write_rejects_unexpected_row_shape"))

    all_results = eligible_rows + rejected_rows
    return {
        "status": "manual_cache_write_eligibility_evaluated",
        "observation_only": True,
        "cache_write_performed": False,
        "live_http_performed": False,
        "raw_response_included": False,
        "provider_api_key_value_included": False,
        "eligible_count": len(eligible_rows),
        "rejected_count": len(rejected_rows),
        "rows": all_results,
        "summary": {
            "eligible_count": len(eligible_rows),
            "rejected_invalid_symbol_count": cnt_invalid,
            "rejected_parse_error_count": cnt_parse,
            "rejected_transport_error_count": cnt_transport,
            "rejected_validation_error_count": cnt_validation,
            "rejected_max_http_cap_count": cnt_cap,
            "rejected_raw_response_count": cnt_raw,
            "rejected_other_count": cnt_other,
        },
    }


def execute_manual_cache_write_for_eligible_rows(
    plan_rows: list[dict[str, Any]],
    *,
    writer: Any,
    cache_write_confirmed: bool = False,
    provider: str = "stooq_preview",
) -> dict[str, Any]:
    """Gated cache-write execution candidate (**Main R6.5.3** — injected writer only, no real FS writes here).

    Writer must be injected by the caller.  Production-like integration remains R6.5.4+.
    """
    eligibility = evaluate_manual_cache_write_eligibility_from_rows(plan_rows)
    eligible_rows = [r for r in eligibility["rows"] if r.get("cache_write_eligible") is True]

    _base: dict[str, Any] = {
        "observation_only": True,
        "live_http_performed": False,
        "cache_write_performed": False,
        "raw_response_included": False,
        "provider_api_key_value_included": False,
        "provider": provider,
        "eligibility_summary": eligibility["summary"],
    }

    if not cache_write_confirmed:
        return {
            **_base,
            "status": "validation_error",
            "reason": "manual_batch_cache_write_requires_cache_gate",
            "writer_invoked": False,
            "real_cache_write_performed": False,
            "writer_call_count": 0,
        }

    if not eligible_rows:
        return {
            **_base,
            "status": "manual_cache_write_no_eligible_rows",
            "writer_invoked": False,
            "real_cache_write_performed": False,
            "writer_call_count": 0,
            "written_count": 0,
            "skipped_count": eligibility["rejected_count"],
        }

    written: list[dict[str, Any]] = []
    row_results: list[dict[str, Any]] = []
    for row in eligible_rows:
        sym = row["symbol"]
        bar_count = row.get("sanitized_bar_count", 0)
        writer(sym, {"symbol": sym, "sanitized_bar_count": bar_count, "provider": provider})
        written.append({"symbol": sym, "write_status": "written", "sanitized_bar_count": bar_count})
        row_results.append({"symbol": sym, "written": True, "sanitized_bar_count": bar_count})

    # Rejected rows — not passed to writer
    for row in eligibility["rows"]:
        if not row.get("cache_write_eligible"):
            row_results.append({"symbol": row.get("symbol", ""), "written": False, "reason": row.get("reason")})

    return {
        **_base,
        "status": "manual_cache_write_mock_execution_completed",
        # R6.5.3 mock/injected writer only; real filesystem cache persistence remains false.
        "cache_write_performed": len(written) > 0,
        "writer_invoked": len(written) > 0,
        "real_cache_write_performed": False,
        "written_count": len(written),
        "skipped_count": eligibility["rejected_count"],
        "writer_call_count": len(written),
        "rows": row_results,
    }


_SAFE_SYMBOL_RE = re.compile(r"^[A-Z0-9.\-_]{1,32}$")


def _safe_filename_for_symbol(symbol: str) -> str | None:
    """Return uppercase symbol if safe for use as a filename component, else None."""
    upper = symbol.upper()
    if _SAFE_SYMBOL_RE.match(upper) and ".." not in upper and "/" not in upper and "\\" not in upper:
        return upper
    return None


def build_manual_cache_write_dry_run_plan(
    plan_rows: list[dict[str, Any]],
    *,
    output_root: str | Path = "outputs/market_data/us_daily_bars",
    provider: str = "stooq_preview",
) -> dict[str, Any]:
    """Dry-run filesystem path planning only (**Main R6.5.4**).

    No file writes, no writer calls, no HTTP.  Validates target path shape for future production use.
    """
    root = Path(output_root)
    # Index original rows by symbol so sanitized_bars can be carried forward after eligibility strip
    original_by_symbol: dict[str, dict[str, Any]] = {}
    for r in plan_rows:
        s = str(r.get("symbol") or "")
        if s and s not in original_by_symbol:
            original_by_symbol[s] = r

    eligibility = evaluate_manual_cache_write_eligibility_from_rows(plan_rows)
    eligible_rows = [r for r in eligibility["rows"] if r.get("cache_write_eligible") is True]

    rows_out: list[dict[str, Any]] = []
    planned_write_count = 0

    for row in eligible_rows:
        sym = str(row.get("symbol") or "")
        safe = _safe_filename_for_symbol(sym)
        if safe is None:
            rows_out.append({
                "symbol": sym,
                "provider": provider,
                "planned_action": "excluded_unsafe_target_path",
                "cache_write_eligible": False,
                "reason": "manual_batch_cache_write_rejects_unsafe_target_path",
                "writer_invoked": False,
                "real_cache_write_performed": False,
                "cache_write_performed": False,
                "live_http_performed": False,
                "raw_response_included": False,
                "provider_api_key_value_included": False,
            })
            continue
        target = root / f"{safe}.json"
        plan_row: dict[str, Any] = {
            "symbol": safe,
            "provider": provider,
            "planned_action": "manual_cache_write_dry_run_target",
            "cache_write_eligible": True,
            "target_path": str(target),
            "sanitized_bar_count": row.get("sanitized_bar_count", 0),
            "writer_invoked": False,
            "real_cache_write_performed": False,
            "cache_write_performed": False,
            "live_http_performed": False,
            "raw_response_included": False,
            "provider_api_key_value_included": False,
        }
        # Carry sanitized_bars from original input row (eligibility output strips them)
        orig = original_by_symbol.get(safe) or original_by_symbol.get(sym) or {}
        src_bars = orig.get("sanitized_bars")
        if isinstance(src_bars, list) and len(src_bars) > 0:
            plan_row["sanitized_bars"] = src_bars
        rows_out.append(plan_row)
        planned_write_count += 1

    for row in eligibility["rows"]:
        if not row.get("cache_write_eligible"):
            rows_out.append({
                "symbol": str(row.get("symbol") or ""),
                "provider": provider,
                "planned_action": "excluded_ineligible",
                "cache_write_eligible": False,
                "reason": row.get("reason"),
                "writer_invoked": False,
                "real_cache_write_performed": False,
                "cache_write_performed": False,
            })

    return {
        "status": "manual_cache_write_dry_run_plan_built",
        "observation_only": True,
        "dry_run_only": True,
        "live_http_performed": False,
        "cache_write_performed": False,
        "writer_invoked": False,
        "real_cache_write_performed": False,
        "raw_response_included": False,
        "provider_api_key_value_included": False,
        "provider": provider,
        "output_root": str(root),
        "eligible_count": eligibility["eligible_count"],
        "rejected_count": eligibility["rejected_count"],
        "planned_write_count": planned_write_count,
        "rows": rows_out,
        "summary": eligibility["summary"],
    }


def execute_manual_cache_write_dry_run_plan_with_injected_writer(
    dry_run_plan: dict[str, Any],
    *,
    writer: Any,
    cache_write_confirmed: bool = False,
) -> dict[str, Any]:
    """Injected-writer adapter contract (**Main R6.5.5**).

    Accepts a dry-run plan from build_manual_cache_write_dry_run_plan.
    No real filesystem writes; production-like writer remains R6.5.6+.
    """
    _refusal_base: dict[str, Any] = {
        "status": "validation_error",
        "observation_only": True,
        "dry_run_only": True,
        "live_http_performed": False,
        "writer_invoked": False,
        "cache_write_performed": False,
        "real_cache_write_performed": False,
        "raw_response_included": False,
        "provider_api_key_value_included": False,
        "writer_invocation_count": 0,
    }

    if not cache_write_confirmed:
        return {**_refusal_base, "reason": "manual_batch_cache_write_requires_confirmed_gate"}

    if writer is None or not callable(writer):
        return {**_refusal_base, "reason": "manual_batch_cache_write_requires_callable_injected_writer" if writer is not None else "manual_batch_cache_write_requires_injected_writer"}

    if not isinstance(dry_run_plan, dict) or dry_run_plan.get("dry_run_only") is not True:
        return {**_refusal_base, "reason": "manual_batch_cache_write_requires_dry_run_plan"}

    if dry_run_plan.get("observation_only") is not True:
        return {**_refusal_base, "reason": "manual_batch_cache_write_requires_dry_run_plan"}

    if dry_run_plan.get("real_cache_write_performed") is True:
        return {**_refusal_base, "reason": "manual_batch_cache_write_rejects_real_write_source"}

    if dry_run_plan.get("raw_response_included") is True:
        return {**_refusal_base, "reason": "manual_batch_cache_write_rejects_raw_response"}

    if dry_run_plan.get("provider_api_key_value_included") is True:
        return {**_refusal_base, "reason": "manual_batch_cache_write_rejects_provider_api_key_value"}

    provider = str(dry_run_plan.get("provider") or "stooq_preview")
    plan_rows = dry_run_plan.get("rows") or []
    safe_rows = [r for r in plan_rows if r.get("planned_action") == "manual_cache_write_dry_run_target" and r.get("cache_write_eligible") is True]

    row_results: list[dict[str, Any]] = []
    invoked = 0

    for row in safe_rows:
        sym = str(row.get("symbol") or "")
        target = str(row.get("target_path") or "")
        bar_count = row.get("sanitized_bar_count", 0)
        writer_payload: dict[str, Any] = {
            "symbol": sym,
            "provider": provider,
            "target_path": target,
            "sanitized_bar_count": bar_count,
            "planned_action": "manual_cache_write_injected_writer_payload",
            "dry_run_source": True,
            "cache_write_confirmed": True,
            "raw_response_included": False,
            "provider_api_key_value_included": False,
        }
        # Pass sanitized_bars if present in dry-run plan row (required by save-cache adapter)
        row_bars = row.get("sanitized_bars")
        if isinstance(row_bars, list) and len(row_bars) > 0:
            writer_payload["sanitized_bars"] = row_bars
        writer(writer_payload)
        invoked += 1
        row_results.append({"symbol": sym, "writer_invoked": True, "target_path": target, "sanitized_bar_count": bar_count})

    for row in plan_rows:
        if row.get("planned_action") != "manual_cache_write_dry_run_target" or not row.get("cache_write_eligible"):
            row_results.append({
                "symbol": str(row.get("symbol") or ""),
                "writer_invoked": False,
                "reason": row.get("reason"),
            })

    return {
        "status": "manual_cache_write_injected_writer_completed",
        "observation_only": True,
        "dry_run_only": True,
        "live_http_performed": False,
        "writer_invoked": invoked > 0,
        # R6.5.5 injected writer only; real filesystem cache persistence remains false.
        "cache_write_performed": invoked > 0,
        "real_cache_write_performed": False,
        "raw_response_included": False,
        "provider_api_key_value_included": False,
        "provider": provider,
        "planned_write_count": dry_run_plan.get("planned_write_count", 0),
        "writer_invocation_count": invoked,
        "rejected_count": dry_run_plan.get("rejected_count", 0),
        "rows": row_results,
        "summary": dry_run_plan.get("summary", {}),
    }


def build_manual_cache_write_save_cache_writer_adapter(
    save_cache_func: Any,
    *,
    cache_write_confirmed: bool = False,
    provider: str = "stooq_preview",
) -> dict[str, Any]:
    """Save-cache writer adapter boundary (**Main R6.5.6**).

    Returns a writer callable (under key ``writer``) for use with
    execute_manual_cache_write_dry_run_plan_with_injected_writer.
    No real save_us_daily_bars_cache call; production-like CLI integration remains R6.5.7+.
    """
    _refusal: dict[str, Any] = {
        "status": "validation_error",
        "observation_only": True,
        "dry_run_only": True,
        "live_http_performed": False,
        "writer_invoked": False,
        "save_cache_func_invoked": False,
        "cache_write_performed": False,
        "real_cache_write_performed": False,
        "raw_response_included": False,
        "provider_api_key_value_included": False,
    }

    if save_cache_func is None:
        return {**_refusal, "reason": "manual_batch_cache_write_requires_save_cache_func"}
    if not callable(save_cache_func):
        return {**_refusal, "reason": "manual_batch_cache_write_requires_callable_save_cache_func"}
    if not cache_write_confirmed:
        return {**_refusal, "reason": "manual_batch_cache_write_requires_confirmed_gate"}

    invocation_log: list[dict[str, Any]] = []

    def _writer(writer_payload: dict[str, Any]) -> None:
        sym = str(writer_payload.get("symbol") or "")
        if not sym:
            invocation_log.append({"symbol": sym, "status": "rejected", "reason": "manual_batch_cache_write_rejects_unexpected_writer_payload"})
            return
        if writer_payload.get("raw_response_included") is True:
            invocation_log.append({"symbol": sym, "status": "rejected", "reason": "manual_batch_cache_write_rejects_raw_response"})
            return
        if writer_payload.get("provider_api_key_value_included") is True:
            invocation_log.append({"symbol": sym, "status": "rejected", "reason": "manual_batch_cache_write_rejects_provider_api_key_value"})
            return
        bars = writer_payload.get("sanitized_bars")
        if bars is None:
            invocation_log.append({"symbol": sym, "status": "rejected", "reason": "manual_batch_cache_write_requires_sanitized_bars"})
            return
        if not isinstance(bars, list) or len(bars) == 0:
            invocation_log.append({"symbol": sym, "status": "rejected", "reason": "manual_batch_cache_write_rejects_empty_sanitized_bars"})
            return
        _FORBIDDEN_BAR_KEYS = frozenset({
            "raw_response", "raw_body", "raw_csv", "api_key", "authorization",
            "bearer", "token", "secret", "credential",
        })
        for bar in bars:
            if not isinstance(bar, dict):
                invocation_log.append({"symbol": sym, "status": "rejected", "reason": "manual_batch_cache_write_rejects_non_dict_sanitized_bar"})
                return
            bar_sym = bar.get("symbol")
            if bar_sym is not None and bar_sym != sym:
                invocation_log.append({"symbol": sym, "status": "rejected", "reason": "manual_batch_cache_write_rejects_symbol_mismatch"})
                return
            bar_keys_lower = {k.lower() for k in bar.keys()}
            if bar_keys_lower & _FORBIDDEN_BAR_KEYS:
                invocation_log.append({"symbol": sym, "status": "rejected", "reason": "manual_batch_cache_write_rejects_forbidden_sanitized_bar_field"})
                return
        save_cache_func(sym, bars)
        invocation_log.append({"symbol": sym, "status": "written"})

    return {
        "status": "manual_batch_cache_write_save_cache_adapter_ready",
        "observation_only": True,
        "dry_run_only": True,
        "live_http_performed": False,
        "cache_write_performed": False,
        "real_cache_write_performed": False,
        "raw_response_included": False,
        "provider_api_key_value_included": False,
        "provider": provider,
        "writer": _writer,
        "invocation_log": invocation_log,
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
