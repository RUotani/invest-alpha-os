"""US provider scheduled-ingest **dry-run plan** (**Main R6.1**).

Emits JSON / Markdown describing a **planned** universe and constraints **without** vendor HTTP,
**without** disk cache writes, and **without** any raw vendor payload surface.

Scheduling, cron, and GitHub Actions are **not** implemented here — this module is a **plan renderer only**.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from invis_alpha_os.config.us_watchlist import normalize_us_symbol
from invis_alpha_os.data.us_provider_cache_preview_batch import symbols_from_us_watchlist_file
from invis_alpha_os.data.us_provider_live_preview import (
    CONFIRM_US_CACHE_WRITE_ENV,
    CONFIRM_US_LIVE_HTTP_ENV,
)

CONFIRM_US_SCHEDULED_INGEST_ENV = "CONFIRM_US_SCHEDULED_INGEST"
ENV_MAX_SYMBOLS = "US_PROVIDER_MAX_SYMBOLS"
ENV_MAX_HTTP_PER_RUN = "US_PROVIDER_MAX_HTTP_PER_RUN"
ENV_MIN_SLEEP_SECONDS = "US_PROVIDER_MIN_SLEEP_SECONDS"
STOOQ_API_KEY_ENV = "STOOQ_APIKEY"


_PLAN_REASON = "r6_1_plan_only_no_http_no_write"


def _dedupe_preserve_order(normals: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for n in normals:
        if n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out


def _parse_positive_int(name: str) -> int | None:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        v = int(str(raw).strip(), 10)
    except ValueError:
        return None
    return v if v > 0 else None


def _parse_non_negative_int(name: str) -> int | None:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        v = int(str(raw).strip(), 10)
    except ValueError:
        return None
    return v if v >= 0 else None


def _parse_min_sleep_seconds() -> float | None:
    raw = os.environ.get(ENV_MIN_SLEEP_SECONDS)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return float(str(raw).strip())
    except ValueError:
        return None


def _gate_literal(env_name: str) -> str:
    v = os.environ.get(env_name)
    if v == "YES":
        return "YES"
    if v is None or str(v).strip() == "":
        return "not_set"
    return "set_not_yes"


def build_us_provider_scheduled_ingest_plan(
    symbols: list[str],
    *,
    provider: str = "stooq_preview",
    from_watchlist_used: bool = False,
    symbols_csv_provided: bool = False,
    limit_param: int | None = None,
) -> dict[str, Any]:
    """Build observation-only ingest plan (**no HTTP**, **no cache write**, **never** exposes API keys)."""

    prov = provider.strip()
    if prov != "stooq_preview":
        return {
            "status": "validation_error",
            "reason": "unsupported_provider",
            "provider": prov,
            "observation_only": True,
            "scheduled_ingest_enabled": False,
        }

    plan_rows_out: list[dict[str, Any]] = []
    normed_acc: list[str] = []

    for raw in symbols:
        stripped = raw.strip()
        if not stripped:
            continue
        n = normalize_us_symbol(stripped)
        if n is None:
            plan_rows_out.append(
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

    invalid_ct = sum(1 for r in plan_rows_out if r.get("reason") == "invalid_symbol")
    dry_ct = len(normed_acc)

    if not normed_acc and invalid_ct == 0:
        return {
            "status": "validation_error",
            "reason": "empty_symbol_batch",
            "provider": prov,
            "observation_only": True,
            "scheduled_ingest_enabled": False,
        }

    min_sleep_parsed = _parse_min_sleep_seconds()
    max_http_env = _parse_non_negative_int(ENV_MAX_HTTP_PER_RUN)

    constraints_max_symbols: int = (
        effective_symbol_cap if effective_symbol_cap is not None else universe_before_trim
    )

    rows_valid: list[dict[str, Any]] = []
    for norm in normed_acc:
        row = {
            "symbol": norm,
            "provider": prov,
            "planned_action": "dry_run_only",
            "live_http_allowed": False,
            "cache_write_allowed": False,
            "reason": _PLAN_REASON,
        }
        plan_rows_out.append(row)
        rows_valid.append(row)

    invalid_rows = [r for r in plan_rows_out if r.get("reason") == "invalid_symbol"]
    merged_plan_rows = invalid_rows + rows_valid

    return {
        "status": "scheduled_plan_dry_run",
        "provider": prov,
        "mode": "dry_run_plan",
        "observation_only": True,
        "live_http_performed": False,
        "cache_write_performed": False,
        "raw_response_included": False,
        "scheduled_ingest_enabled": False,
        "schedule_config_present": False,
        "provider_api_key_env_name": STOOQ_API_KEY_ENV,
        "provider_api_key_value_included": False,
        "source": {
            "from_watchlist": from_watchlist_used,
            "symbols_csv_provided": symbols_csv_provided,
            "limit": limit_param if isinstance(limit_param, int) and limit_param > 0 else None,
        },
        "constraints": {
            "max_symbols": constraints_max_symbols,
            "max_http_per_run": int(max_http_env) if max_http_env is not None else 0,
            "min_sleep_seconds": min_sleep_parsed,
            "requires_operator_approval": True,
        },
        "gate_status": {
            CONFIRM_US_SCHEDULED_INGEST_ENV: _gate_literal(CONFIRM_US_SCHEDULED_INGEST_ENV),
            CONFIRM_US_LIVE_HTTP_ENV: _gate_literal(CONFIRM_US_LIVE_HTTP_ENV),
            CONFIRM_US_CACHE_WRITE_ENV: _gate_literal(CONFIRM_US_CACHE_WRITE_ENV),
        },
        "symbol_count": len(merged_plan_rows),
        "symbols": list(normed_acc),
        "plan_rows": merged_plan_rows,
        "operator_summary": {
            "dry_run_plan_count": dry_ct,
            "live_http_allowed_count": 0,
            "cache_write_allowed_count": 0,
            "invalid_symbol_count": invalid_ct,
        },
        "next_required_approval": "R6.2 manual live batch smoke design",
    }


def render_us_provider_scheduled_ingest_plan_markdown(payload: dict[str, Any]) -> str:
    """Copy-ready Markdown (**Main R6.1**) — envelope + constraints; **never** emits API keys or raw payloads."""

    if str(payload.get("status") or "") == "validation_error":
        rs = payload.get("reason")
        rs_s = rs if isinstance(rs, str) else "validation_error"
        return (
            "# US Scheduled Ingest Plan (dry-run)\n\n"
            f"> **Observation only.** JSON canonical. **status:** `validation_error` — **`{rs_s}`**.\n\n"
            "## Operator verdict\n\n"
            "Fix CLI inputs (**`unsupported_provider`** or **`empty_symbol_batch`**) — no plan rows emitted.\n"
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
        "# US Scheduled Ingest Plan (dry-run)",
        "",
        "> **Copy-ready plan recap.** **`STOOQ_APIKEY` values are never printed.** JSON remains canonical.",
        "> **Main R6.1:** no vendor HTTP, no cache write, no scheduler execution.",
        "",
        "## Operator verdict",
        "",
        "**Dry-run plan only.** This output is not a substitute for JSON and does not perform live work.",
        "",
        "## Safety flags",
        "",
        "| flag | value |",
        "|---|---:|",
        f"| scheduled_ingest_enabled | {str(bool(payload.get('scheduled_ingest_enabled'))).lower()} |",
        f"| live_http_performed | {str(bool(payload.get('live_http_performed'))).lower()} |",
        f"| cache_write_performed | {str(bool(payload.get('cache_write_performed'))).lower()} |",
        f"| raw_response_included | {str(bool(payload.get('raw_response_included'))).lower()} |",
        f"| observation_only | {str(bool(payload.get('observation_only'))).lower()} |",
        f"| schedule_config_present | {str(bool(payload.get('schedule_config_present'))).lower()} |",
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
        f"- max_symbols (applied ceiling / reported): `{cons.get('max_symbols')}`",
        f"- max_http_per_run (configured for future runs): `{cons.get('max_http_per_run')}`",
        f"- min_sleep_seconds: `{cons.get('min_sleep_seconds')}`",
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
        f"- count: **{payload.get('symbol_count', 0)}**",
        f"- plan row order: {', '.join(symbols_display) or '—'}",
        "",
        "## Operator summary (plan)",
        "",
        f"- dry_run_plan_count: `{op_sum.get('dry_run_plan_count', 0)}`",
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
        "- This renderer **never** performs HTTP or filesystem cache writes.",
        "- Use JSON output for **`plan_rows`** and machine checks.",
        "- See **`docs/13_us_provider_scheduled_ingest_design.md`** for R6 phased gates.",
        "",
    ]

    return "\n".join(lines)


def merged_symbols_for_scheduled_ingest_plan(
    *,
    from_watchlist: bool,
    symbols_csv: str | None,
    path_override: Path | None = None,
) -> tuple[list[str], bool, bool]:
    """Merge watchlist symbols with CSV (**matches batch CLI**: full watchlist, then CSV).

    **`limit`** is applied only in **`build_us_provider_scheduled_ingest_plan`** on the merged tokens.
    """

    merged: list[str] = []
    if from_watchlist:
        merged.extend(symbols_from_us_watchlist_file(path_override=path_override))
    csv_provided = bool(symbols_csv and symbols_csv.strip())
    if csv_provided:
        merged.extend([p.strip() for p in str(symbols_csv).split(",") if p.strip()])
    return merged, from_watchlist, csv_provided
