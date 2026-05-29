"""JP-only gated cache refresh execute (dry-run default; one-shot live when gates match)."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from invis_alpha_os.config.jp_watchlist import normalize_jquants_equity_code
from invis_alpha_os.data.jquants_daily_bars_cache import save_jquants_daily_bars_cache, utc_now_iso
from invis_alpha_os.reports.cache_refresh_execution_plan import REQUIRED_GATES
from invis_alpha_os.reports.jquants_preflight import assess_jquants_credentials
from invis_alpha_os.reports.provider_error_diagnostics import (
    ENDPOINT_CATEGORY_DAILY_BARS,
    REQUEST_PHASE_DAILY_QUOTES_FETCH,
    build_redacted_provider_diagnostics,
)

JP_ALLOWED_TARGETS: frozenset[str] = frozenset({"5802", "6645", "5801"})
REQUIRED_PROVIDER = "jquants"
REQUIRED_SCOPE = "JP_ONLY"
REFRESH_LOOKBACK_DAYS = 400

RefreshSymbolFn = Callable[[str, str, str], dict[str, Any]]


@dataclass(frozen=True)
class CacheRefreshExecuteResult:
    markdown_text: str
    json_payload: dict[str, Any]
    is_result: bool = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_targets_csv(targets_csv: str) -> list[str]:
    out: list[str] = []
    for part in targets_csv.split(","):
        token = part.strip()
        if token:
            out.append(token)
    return out


def _truthy_env(env: dict[str, str], key: str, expected: str) -> bool:
    return env.get(key, "").strip() == expected


def validate_jp_only_gates(
    *,
    env: dict[str, str],
    targets: list[str],
    provider: str,
    scope: str,
    execute_refresh: bool,
) -> tuple[str, list[str]]:
    """Return (status, missing_or_reason_tokens). status: ok | refused_*."""
    missing: list[str] = []
    target_set = frozenset(targets)
    if provider.strip().lower() != REQUIRED_PROVIDER:
        return "refused_provider_mismatch", [f"provider={provider}"]
    if scope.strip().upper() != REQUIRED_SCOPE:
        return "refused_scope_mismatch", [f"scope={scope}"]
    if target_set != JP_ALLOWED_TARGETS:
        return "refused_target_mismatch", [f"targets={sorted(target_set)}"]
    for t in targets:
        if normalize_jquants_equity_code(t) is None:
            return "refused_invalid_target", [t]
    if not execute_refresh:
        return "planned_dry_run_only", []
    for gate in REQUIRED_GATES:
        if gate == "ALLOW_LIVE_HTTP" and not _truthy_env(env, gate, "1"):
            missing.append(gate)
        elif gate.startswith("CONFIRM_") and not _truthy_env(env, gate, "YES"):
            missing.append(gate)
    if not _truthy_env(env, "CONFIRM_TARGETS", "5802,6645,5801"):
        missing.append("CONFIRM_TARGETS")
    if env.get("CONFIRM_PROVIDER", "").strip().lower() != REQUIRED_PROVIDER:
        missing.append("CONFIRM_PROVIDER")
    if env.get("CONFIRM_SCOPE", "").strip().upper() != REQUIRED_SCOPE:
        missing.append("CONFIRM_SCOPE")
    jq_live = env.get("JQUANTS_ALLOW_LIVE_HTTP", "").strip().lower()
    if jq_live not in {"true", "1"}:
        missing.append("JQUANTS_ALLOW_LIVE_HTTP")
    if missing:
        return "refused_missing_gates", missing
    return "ok", []


def default_refresh_date_range() -> tuple[str, str]:
    to_d = date.today()
    from_d = to_d - timedelta(days=REFRESH_LOOKBACK_DAYS)
    return from_d.strftime("%Y-%m-%d"), to_d.strftime("%Y-%m-%d")


def _map_gate_status(gate_status: str) -> str:
    if gate_status == "refused_target_mismatch" or gate_status == "refused_invalid_target":
        return "target_mismatch"
    if gate_status == "refused_provider_mismatch":
        return "target_mismatch"
    if gate_status.startswith("refused_"):
        return "gate_refused"
    return gate_status


def normalize_target_status(raw: dict[str, Any]) -> dict[str, Any]:
    raw_status = str(raw.get("status", ""))
    reason = str(raw.get("reason", raw.get("hint", "")))
    if raw_status in {"disabled", "not_configured", "api_key_missing", "base_url_missing"}:
        normalized = "auth_missing"
        live = False
    elif raw_status == "success" and raw.get("cache_write_executed"):
        normalized = "success"
        live = bool(raw.get("live_http_executed"))
    elif raw_status == "success":
        normalized = "partial_failure"
        live = bool(raw.get("live_http_executed"))
    elif raw_status in {"live_blocked"}:
        normalized = "gate_refused"
        live = False
    elif raw_status in {"validation_error"}:
        normalized = "target_mismatch"
        live = False
    else:
        normalized = "provider_error"
        live = bool(raw.get("live_http_executed"))
    row: dict[str, Any] = {
        "ticker": raw.get("ticker", ""),
        "status": normalized,
        "raw_status": raw_status,
        "reason": reason,
        "live_http_executed": live,
        "cache_write_executed": bool(raw.get("cache_write_executed")),
        "sanitized_bar_count": raw.get("sanitized_bar_count"),
    }
    if normalized == "provider_error":
        row.update(
            build_redacted_provider_diagnostics(
                {
                    **raw,
                    "request_phase": raw.get("request_phase", REQUEST_PHASE_DAILY_QUOTES_FETCH),
                    "endpoint_category": raw.get("endpoint_category", ENDPOINT_CATEGORY_DAILY_BARS),
                }
            )
        )
    return row


def normalize_overall_status(
    *,
    gate_status: str,
    execute_refresh: bool,
    per_target: list[dict[str, Any]],
    auth_ready: bool,
) -> str:
    if not execute_refresh:
        return "planned_dry_run_only"
    if gate_status != "ok":
        return _map_gate_status(gate_status)
    if not auth_ready:
        return "auth_missing"
    if not per_target:
        return "no_targets"
    statuses = [str(x.get("status", "")) for x in per_target]
    if all(s == "success" for s in statuses):
        return "success"
    if any(s == "auth_missing" for s in statuses):
        return "auth_missing"
    if any(s == "provider_error" for s in statuses):
        return "provider_error"
    return "partial_failure"


def next_required_action(overall_status: str) -> str:
    mapping = {
        "auth_missing": "Set J-Quants credentials and rerun once",
        "gate_refused": "Set required CONFIRM/ALLOW gates and rerun once",
        "target_mismatch": "Fix targets/provider/scope to exact JP-only set",
        "provider_error": "Inspect provider error and retry once after fix",
        "partial_failure": "Review per-target results and rerun once if needed",
        "success": "Run postcheck and regenerate Context Pack",
        "planned_dry_run_only": "Review dry-run output then execute once with gates",
    }
    return mapping.get(overall_status, "Review execute result")


def retry_safe(overall_status: str) -> bool:
    return overall_status in {
        "auth_missing",
        "gate_refused",
        "provider_error",
        "partial_failure",
        "planned_dry_run_only",
    }


def refresh_jp_symbol_live(
    code: str,
    from_date: str,
    to_date: str,
) -> dict[str, Any]:
    """Fetch J-Quants daily bars and write cache (live HTTP + cache write)."""
    from invis_alpha_os.data.adapters.jquants_client import JQuantsClient

    wire = normalize_jquants_equity_code(code.strip())
    if wire is None:
        return {"ticker": code, "status": "validation_error", "reason": "invalid_equity_code"}
    if os.environ.get("CONFIRM_LIVE_HTTP") != "YES":
        return {"ticker": wire, "status": "live_blocked", "reason": "confirm_live_http_required"}
    client = JQuantsClient.from_env()
    if not client.is_enabled():
        return {
            "ticker": wire,
            "status": "disabled",
            "hint": "JQUANTS_ENABLED=false",
            "live_http_executed": False,
            "cache_write_executed": False,
        }
    result = client.get_daily_quotes(
        wire,
        from_date=from_date,
        to_date=to_date,
        attempt_live=True,
        return_sanitized_bars=True,
    )
    st = str(result.get("status", ""))
    if st != "success":
        attempted_live = st not in {"disabled", "not_configured", "api_key_missing", "base_url_missing", "dry_run"}
        return {
            "ticker": wire,
            "status": st,
            "reason": str(result.get("reason", result.get("hint", st))),
            "live_http_executed": attempted_live,
            "cache_write_executed": False,
            "http_status": result.get("http_status"),
            "endpoint_path": result.get("endpoint_path"),
            "endpoint_url_without_query": result.get("endpoint_url_without_query"),
            "error_body_preview": result.get("error_body_preview"),
            "request_phase": REQUEST_PHASE_DAILY_QUOTES_FETCH,
            "endpoint_category": ENDPOINT_CATEGORY_DAILY_BARS,
        }
    bars = result.get("sanitized_bars")
    if not isinstance(bars, list) or not bars:
        return {
            "ticker": wire,
            "status": "success",
            "sanitized_bar_count": 0,
            "cache_written_to": None,
            "live_http_executed": True,
            "cache_write_executed": False,
        }
    path = save_jquants_daily_bars_cache(
        wire,
        bars,
        source="jquants_v2_equities_bars_daily",
        fetched_at=utc_now_iso(),
    )
    return {
        "ticker": wire,
        "status": "success",
        "sanitized_bar_count": len(bars),
        "cache_written_to": str(path),
        "live_http_executed": True,
        "cache_write_executed": True,
    }


def execute_jp_targets(
    targets: list[str],
    *,
    from_date: str,
    to_date: str,
    refresh_fn: RefreshSymbolFn | None = None,
) -> list[dict[str, Any]]:
    fn = refresh_fn or refresh_jp_symbol_live
    ordered = [t for t in ("5802", "6645", "5801") if t in targets]
    return [fn(t, from_date, to_date) for t in ordered]


def build_cache_refresh_execute(
    *,
    report_date: str,
    plan_json_payload: dict[str, Any] | None,
    execute_refresh: bool,
    provider: str = REQUIRED_PROVIDER,
    targets_csv: str = "5802,6645,5801",
    scope: str = REQUIRED_SCOPE,
    env: dict[str, str] | None = None,
    refresh_fn: RefreshSymbolFn | None = None,
) -> CacheRefreshExecuteResult:
    env_map = env or {}
    targets = parse_targets_csv(targets_csv)
    gate_status, gate_detail = validate_jp_only_gates(
        env=env_map,
        targets=targets,
        provider=provider,
        scope=scope,
        execute_refresh=execute_refresh,
    )
    plan = plan_json_payload if isinstance(plan_json_payload, dict) else {}
    plan_targets = plan.get("targets")
    plan_rows = [x for x in plan_targets if isinstance(x, dict)] if isinstance(plan_targets, list) else []
    filtered_rows = [
        row
        for row in plan_rows
        if str(row.get("provider", "")).strip() == REQUIRED_PROVIDER
        and str(row.get("ticker", "")).strip() in JP_ALLOWED_TARGETS
    ]
    from_date, to_date = default_refresh_date_range()
    if gate_status != "ok":
        overall = _map_gate_status(gate_status)
        payload: dict[str, Any] = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "dry_run_only": not execute_refresh,
            "live_http_executed": False,
            "cache_write_executed": False,
            "actual_refresh_executed": False,
            "status": gate_status,
            "overall_status": overall,
            "provider": provider,
            "scope": scope,
            "targets": targets,
            "required_gates": list(REQUIRED_GATES)
            + ["CONFIRM_TARGETS", "CONFIRM_PROVIDER", "CONFIRM_SCOPE", "JQUANTS_ALLOW_LIVE_HTTP"],
            "gate_detail": gate_detail,
            "plan_targets": filtered_rows,
            "per_target_results": [],
            "retry_safe": retry_safe(overall),
            "next_required_action": next_required_action(overall),
            "secrets_printed": False,
        }
        title = "# Cache Refresh Execute Dry-Run"
        if execute_refresh:
            title = "# Cache Refresh Execute Refused"
        lines = [
            title,
            "",
            "## メタ情報",
            f"- report_date: {report_date}",
            f"- generated_at: {payload['generated_at']}",
            f"- status: {gate_status}",
            "- dry_run_only: true" if not execute_refresh else "- dry_run_only: false",
            "- live_http_executed: false",
            "- cache_write_executed: false",
            "- actual_refresh_executed: false",
            f"- provider: {provider}",
            f"- scope: {scope}",
            f"- targets: {', '.join(targets)}",
            "",
        ]
        if gate_detail:
            lines.append(f"- gate_detail: {', '.join(gate_detail)}")
        lines.append("")
        return CacheRefreshExecuteResult(markdown_text="\n".join(lines), json_payload=payload, is_result=False)

    if not execute_refresh:
        return build_cache_refresh_execute_dry_run(
            report_date=report_date,
            plan_json_payload=plan,
            execute_refresh=False,
            env=env_map,
            targets=targets,
            provider=provider,
            scope=scope,
            filtered_rows=filtered_rows,
        )

    auth_diag = assess_jquants_credentials(env_map)
    if not auth_diag.get("refresh_allowed"):
        per_target = [
            {
                "ticker": t,
                "status": "auth_missing",
                "live_http_executed": False,
                "cache_write_executed": False,
            }
            for t in targets
        ]
        overall = "auth_missing"
        payload = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "dry_run_only": False,
            "live_http_executed": False,
            "cache_write_executed": False,
            "actual_refresh_executed": False,
            "status": overall,
            "overall_status": overall,
            "provider": provider,
            "scope": scope,
            "targets": targets,
            "from_date": from_date,
            "to_date": to_date,
            "symbol_results": [],
            "per_target_results": per_target,
            "missing_env": auth_diag.get("missing_env", []),
            "retry_safe": True,
            "next_required_action": next_required_action(overall),
            "secrets_printed": False,
        }
    else:
        symbol_results = execute_jp_targets(targets, from_date=from_date, to_date=to_date, refresh_fn=refresh_fn)
        per_target = [normalize_target_status(row) for row in symbol_results]
        overall = normalize_overall_status(
            gate_status=gate_status,
            execute_refresh=True,
            per_target=per_target,
            auth_ready=True,
        )
        payload = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "dry_run_only": False,
            "live_http_executed": any(bool(r.get("live_http_executed")) for r in per_target),
            "cache_write_executed": any(bool(r.get("cache_write_executed")) for r in per_target),
            "actual_refresh_executed": overall == "success",
            "status": overall,
            "overall_status": overall,
            "provider": provider,
            "scope": scope,
            "targets": targets,
            "from_date": from_date,
            "to_date": to_date,
            "symbol_results": symbol_results,
            "per_target_results": per_target,
            "retry_safe": retry_safe(overall),
            "next_required_action": next_required_action(overall),
            "secrets_printed": False,
        }
    lines = [
        "# Cache Refresh Execute Result",
        "",
        "## メタ情報",
        f"- report_date: {report_date}",
        f"- generated_at: {payload['generated_at']}",
        "- dry_run_only: false",
        f"- live_http_executed: {str(payload['live_http_executed']).lower()}",
        f"- cache_write_executed: {str(payload['cache_write_executed']).lower()}",
        f"- actual_refresh_executed: {str(payload['actual_refresh_executed']).lower()}",
        f"- status: {payload['status']}",
        f"- overall_status: {payload.get('overall_status', payload['status'])}",
        f"- retry_safe: {str(payload.get('retry_safe', False)).lower()}",
        f"- next_required_action: {payload.get('next_required_action', '')}",
        f"- provider: {provider}",
        f"- scope: {scope}",
        "",
        "## 対象結果",
        "| ticker | status | provider_error_class | http_status | sanitized_bar_count | cache_written |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for row in payload.get("per_target_results") or []:
        lines.append(
            f"| {row.get('ticker', '')} | {row.get('status', '')} | "
            f"{row.get('provider_error_class', '-')} | {row.get('http_status', '-')} | "
            f"{row.get('sanitized_bar_count', '-')} | "
            f"{'yes' if row.get('cache_write_executed') else 'no'} |"
        )
    lines.extend(["", "## Provider diagnostics"])
    for row in payload.get("per_target_results") or []:
        if row.get("status") != "provider_error":
            continue
        lines.extend(
            [
                f"### {row.get('ticker', '')}",
                f"- provider_error_class: {row.get('provider_error_class', '-')}",
                f"- http_status: {row.get('http_status', '-')}",
                f"- request_phase: {row.get('request_phase', '-')}",
                f"- endpoint_category: {row.get('endpoint_category', '-')}",
                f"- retry_safe: {str(row.get('retry_safe', False)).lower()}",
                f"- next_required_action: {row.get('next_required_action', '-')}",
                "- response_body_redacted: true",
                "- secrets_printed: false",
                "",
            ]
        )
    return CacheRefreshExecuteResult(markdown_text="\n".join(lines), json_payload=payload, is_result=True)


def build_cache_refresh_execute_dry_run(
    *,
    report_date: str,
    plan_json_payload: dict[str, Any] | None,
    execute_refresh: bool,
    env: dict[str, str] | None = None,
    targets: list[str] | None = None,
    provider: str = REQUIRED_PROVIDER,
    scope: str = REQUIRED_SCOPE,
    filtered_rows: list[dict[str, Any]] | None = None,
) -> CacheRefreshExecuteResult:
    plan = plan_json_payload if isinstance(plan_json_payload, dict) else {}
    rows = filtered_rows
    if rows is None:
        plan_targets = plan.get("targets")
        all_rows = [x for x in plan_targets if isinstance(x, dict)] if isinstance(plan_targets, list) else []
        rows = all_rows
    target_list = targets or [str(r.get("ticker", "")) for r in rows if r.get("ticker")]
    gate_status, gate_detail = validate_jp_only_gates(
        env=env or {},
        targets=target_list,
        provider=provider,
        scope=scope,
        execute_refresh=False,
    )
    from_date, to_date = default_refresh_date_range()
    payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "dry_run_only": True,
        "live_http_executed": False,
        "cache_write_executed": False,
        "actual_refresh_executed": False,
        "status": gate_status,
        "provider": provider,
        "scope": scope,
        "targets": target_list,
        "from_date": from_date,
        "to_date": to_date,
        "gate_detail": gate_detail,
        "plan_targets": rows,
        "secrets_printed": False,
    }
    lines = [
        "# Cache Refresh Execute Dry-Run",
        "",
        "## メタ情報",
        f"- report_date: {report_date}",
        f"- generated_at: {payload['generated_at']}",
        "- dry_run_only: true",
        "- live_http_executed: false",
        "- cache_write_executed: false",
        "- actual_refresh_executed: false",
        f"- status: {gate_status}",
        f"- provider: {provider}",
        f"- scope: {scope}",
        f"- targets: {', '.join(target_list)}",
        f"- from_date: {from_date}",
        f"- to_date: {to_date}",
        "",
        "## 対象",
        "| ticker | market | provider | priority | plan_status |",
        "| --- | --- | --- | --- | --- |",
    ]
    if not rows:
        lines.append("| (none) | - | - | - | planned_dry_run_only |")
    for item in rows:
        lines.append(
            f"| {item.get('ticker', '')} | {item.get('market', 'JP')} | {item.get('provider', '')} | "
            f"{item.get('priority', '')} | {item.get('plan_status', 'planned_dry_run_only')} |"
        )
    lines.extend(["", "## Gate確認", "- 実refresh: 未実行 (dry-run)", ""])
    return CacheRefreshExecuteResult(markdown_text="\n".join(lines), json_payload=payload, is_result=False)
