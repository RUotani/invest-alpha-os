"""US provider **manual live batch smoke** scaffold (**Main R6.3**).

Builds deterministic JSON / Markdown for the future **`debug us-provider-manual-live-batch-smoke`** command.

**Main R6.3:** **no vendor HTTP**, **no cache write**, **no scheduler** — even when **`--live`** and confirmation env vars are set.
"""

from __future__ import annotations

import os
from typing import Any

from invis_alpha_os.config.us_watchlist import normalize_us_symbol
from invis_alpha_os.data.us_provider_live_preview import (
    CONFIRM_US_CACHE_WRITE_ENV,
    CONFIRM_US_LIVE_HTTP_ENV,
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
) -> dict[str, Any]:
    """Build observation-only manual batch smoke envelope (**R6.3** — **never** HTTP / cache write)."""

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
            "next_required_approval": "R6.4 manual live batch smoke execution",
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
        "next_required_approval": "R6.4 manual live batch smoke execution",
    }


def render_manual_live_batch_smoke_markdown(payload: dict[str, Any]) -> str:
    """Copy-ready Markdown (**Main R6.3**) — **never** API key values / raw payloads."""

    st = str(payload.get("status") or "")
    if st == "validation_error":
        rs = payload.get("reason")
        rs_s = rs if isinstance(rs, str) else "validation_error"
        return (
            "# US Manual Live Batch Smoke (**R6.3 scaffold**)\n\n"
            f"> **Observation only.** JSON canonical. **status:** `validation_error` — **`{rs_s}`**.\n\n"
            "## Operator verdict\n\n"
            "Scaffold refusal — fix gates, **`--max-http`**, CLI inputs, or wait for **R6.4** execution.\n"
        )

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
        "# US Manual Live Batch Smoke (**R6.3 scaffold**)",
        "",
        "> **Copy-ready recap.** **`STOOQ_APIKEY` values are never printed.** JSON remains canonical.",
        "> **Main R6.3:** scaffold only — **no vendor HTTP**, **no cache write**.",
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
        "- Gate **`CONFIRM_US_MANUAL_BATCH_SMOKE`** is documented for **R6.4+** execution.",
        "- See **`docs/14_us_provider_manual_live_batch_smoke_design.md`**.",
        "",
    ]

    return "\n".join(lines)
