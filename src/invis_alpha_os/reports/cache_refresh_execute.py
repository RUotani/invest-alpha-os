"""Dry-run only cache refresh execute skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from invis_alpha_os.reports.cache_refresh_execution_plan import REQUIRED_GATES


@dataclass(frozen=True)
class CacheRefreshExecuteResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _required_gates_status(env: dict[str, str] | None) -> dict[str, str]:
    values = env or {}
    return {
        "ALLOW_LIVE_HTTP": "1" if values.get("ALLOW_LIVE_HTTP") == "1" else "",
        "CONFIRM_LIVE_HTTP": "YES" if values.get("CONFIRM_LIVE_HTTP") == "YES" else "",
        "ALLOW_CACHE_WRITE": "1" if values.get("ALLOW_CACHE_WRITE") == "1" else "",
        "CONFIRM_CACHE_WRITE": "YES" if values.get("CONFIRM_CACHE_WRITE") == "YES" else "",
        "CONFIRM_CACHE_REFRESH": "YES" if values.get("CONFIRM_CACHE_REFRESH") == "YES" else "",
    }


def build_cache_refresh_execute_dry_run(
    *,
    report_date: str,
    plan_json_payload: dict[str, Any] | None,
    execute_refresh: bool,
    env: dict[str, str] | None = None,
) -> CacheRefreshExecuteResult:
    plan = plan_json_payload if isinstance(plan_json_payload, dict) else {}
    targets = plan.get("targets")
    target_rows = [x for x in targets if isinstance(x, dict)] if isinstance(targets, list) else []
    gate_status = _required_gates_status(env)
    missing_gates = [k for k, v in gate_status.items() if not v]
    status = "planned_dry_run_only"
    error = ""
    if execute_refresh:
        status = "actual_refresh_not_enabled"
        error = "actual_refresh_not_enabled"
    payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "dry_run_only": True,
        "live_http_executed": False,
        "cache_write_executed": False,
        "actual_refresh_executed": False,
        "status": status,
        "error": error,
        "required_gates": list(REQUIRED_GATES),
        "gate_status": gate_status,
        "missing_gates": missing_gates,
        "targets": target_rows,
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
        f"- status: {status}",
    ]
    if error:
        lines.append(f"- error: {error}")
    lines.extend(
        [
            "",
            "## 対象",
            "| ticker | market | provider | priority | plan_status |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    if not target_rows:
        lines.append("| (none) | - | - | - | planned_dry_run_only |")
    for row in target_rows:
        lines.append(
            "| {ticker} | {market} | {provider} | {priority} | {plan_status} |".format(
                ticker=row.get("ticker", ""),
                market=row.get("market", ""),
                provider=row.get("provider", ""),
                priority=row.get("priority", ""),
                plan_status=row.get("plan_status", "planned_dry_run_only"),
            )
        )
    lines.extend(
        [
            "",
            "## Gate確認",
            f"- required_gates: {', '.join(REQUIRED_GATES)}",
            f"- missing_gates: {', '.join(missing_gates) if missing_gates else '(none)'}",
            "- 実refresh: 未実装 (このPRでは常時無効)",
            "",
        ]
    )
    return CacheRefreshExecuteResult(markdown_text="\n".join(lines), json_payload=payload)
