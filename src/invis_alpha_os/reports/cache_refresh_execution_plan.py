"""Dry-run only cache refresh execution planner."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

REQUIRED_GATES: tuple[str, ...] = (
    "ALLOW_LIVE_HTTP",
    "CONFIRM_LIVE_HTTP",
    "ALLOW_CACHE_WRITE",
    "CONFIRM_CACHE_WRITE",
    "CONFIRM_CACHE_REFRESH",
)


@dataclass(frozen=True)
class CacheRefreshExecutionPlanResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_cache_refresh_execution_plan(
    *,
    report_date: str,
    readiness_json_payload: dict[str, Any] | None,
) -> CacheRefreshExecutionPlanResult:
    readiness = readiness_json_payload if isinstance(readiness_json_payload, dict) else {}
    rows = readiness.get("stale_candidates")
    targets = [x for x in rows if isinstance(x, dict)] if isinstance(rows, list) else []
    normalized: list[dict[str, Any]] = []
    provider_groups: dict[str, dict[str, Any]] = {}
    for row in targets:
        ticker = str(row.get("ticker", "")).strip()
        if not ticker:
            continue
        provider = str(row.get("provider_candidate", "")).strip() or "unknown"
        item = {
            "ticker": ticker,
            "market": str(row.get("market", "")).strip().upper() or "UNKNOWN",
            "provider": provider,
            "priority": str(row.get("refresh_priority", "")).strip() or "unknown",
            "stale_days": row.get("stale_days"),
            "latest_bar_date": row.get("latest_bar_date"),
            "plan_status": "planned_dry_run_only",
            "reason": str(row.get("reason", "")).strip() or "stale candidate",
            "data_contract_limited": bool(row.get("data_contract_limited")),
            "provider_plan_upgrade_required": bool(row.get("provider_plan_upgrade_required")),
            "alternative_provider_required": bool(row.get("alternative_provider_required")),
            "data_contract_limit_reason": row.get("data_contract_limit_reason"),
        }
        normalized.append(item)
        grp = provider_groups.setdefault(provider, {"tickers": [], "required_gates": list(REQUIRED_GATES), "execute_refresh": False})
        if ticker not in grp["tickers"]:
            grp["tickers"].append(ticker)
    contract_limited = [x["ticker"] for x in normalized if x.get("data_contract_limited")]
    payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "dry_run_only": True,
        "live_http_executed": False,
        "cache_write_executed": False,
        "actual_refresh_executed": False,
        "targets": normalized,
        "provider_groups": provider_groups,
        "data_contract_limited_targets": contract_limited,
    }
    lines = [
        "# Cache Refresh Execution Plan",
        "",
        "## メタ情報",
        f"- report_date: {report_date}",
        f"- generated_at: {payload['generated_at']}",
        "- dry_run_only: true",
        "- live_http_executed: false",
        "- cache_write_executed: false",
        "- actual_refresh_executed: false",
        "",
        "## 対象",
        "| ticker | market | provider | priority | stale_days | data_contract_limited | plan_status | reason |",
        "| --- | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    if not normalized:
        lines.append("| (none) | - | - | - | - | - | planned_dry_run_only | readinessに対象なし |")
    for item in normalized:
        lines.append(
            f"| {item['ticker']} | {item['market']} | {item['provider']} | {item['priority']} | {item['stale_days']} | "
            f"{str(item.get('data_contract_limited', False)).lower()} | {item['plan_status']} | {item['reason']} |"
        )
    if contract_limited:
        lines.extend(["", "## 契約上限", f"- data_contract_limited_targets: {', '.join(contract_limited)}", ""])
    lines.append("")
    lines.append("## Provider別計画")
    for provider, grp in provider_groups.items():
        lines.extend(
            [
                f"### {provider}",
                f"- 対象: {', '.join(grp['tickers']) or '(none)'}",
                f"- 必要ゲート: {', '.join(grp['required_gates'])}",
                "- 実refresh: 未実行",
                "",
            ]
        )
    lines.extend(
        [
            "## 次に人間が決めること",
            "- JP high優先度を先行するか",
            "- US/ETF staleを同時に更新するか",
            "- 実refreshは別PRで明示ゲートを満たした上で対象限定実行するか",
            "",
        ]
    )
    return CacheRefreshExecutionPlanResult(markdown_text="\n".join(lines), json_payload=payload)
