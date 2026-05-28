"""JP-only cache refresh dry-run wiring report."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from invis_alpha_os.reports.cache_refresh_execution_plan import REQUIRED_GATES


@dataclass(frozen=True)
class JPCacheRefreshDryRunResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_jp_cache_refresh_dry_run(
    *,
    report_date: str,
    plan_json_payload: dict[str, Any] | None,
) -> JPCacheRefreshDryRunResult:
    plan = plan_json_payload if isinstance(plan_json_payload, dict) else {}
    rows = plan.get("targets")
    targets = [x for x in rows if isinstance(x, dict)] if isinstance(rows, list) else []
    jp_targets: list[dict[str, Any]] = []
    for row in targets:
        provider = str(row.get("provider", "")).strip()
        priority = str(row.get("priority", "")).strip().lower()
        ticker = str(row.get("ticker", "")).strip()
        if provider != "jquants" or priority != "high" or not ticker:
            continue
        jp_targets.append(
            {
                "ticker": ticker,
                "market": str(row.get("market", "")).strip().upper() or "JP",
                "provider": "jquants",
                "priority": "high",
                "planned_command": f"refresh_jquants_daily_bars --symbol {ticker}",
                "live_http_executed": False,
                "cache_write_executed": False,
                "actual_refresh_executed": False,
            }
        )
    payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "dry_run_only": True,
        "provider": "jquants",
        "filter": {"priority": "high"},
        "required_gates": list(REQUIRED_GATES),
        "live_http_executed": False,
        "cache_write_executed": False,
        "actual_refresh_executed": False,
        "targets": jp_targets,
    }
    lines = [
        "# JP Cache Refresh Dry-Run",
        "",
        "## メタ情報",
        f"- report_date: {report_date}",
        f"- generated_at: {payload['generated_at']}",
        "- provider: jquants",
        "- filter: high priority only",
        "- dry_run_only: true",
        "- live_http_executed: false",
        "- cache_write_executed: false",
        "- actual_refresh_executed: false",
        "",
        "## 対象",
        "| ticker | provider | priority | planned_command |",
        "| --- | --- | --- | --- |",
    ]
    if not jp_targets:
        lines.append("| (none) | jquants | high | (no planned command) |")
    for row in jp_targets:
        lines.append(f"| {row['ticker']} | jquants | high | {row['planned_command']} |")
    lines.extend(
        [
            "",
            "## Gate",
            f"- required_gates: {', '.join(REQUIRED_GATES)}",
            "- 実refresh: 未実行",
            "",
        ]
    )
    return JPCacheRefreshDryRunResult(markdown_text="\n".join(lines), json_payload=payload)
