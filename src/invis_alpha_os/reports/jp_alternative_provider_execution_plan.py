"""Dry-run execution plan for JP alternative provider data updates (no import/HTTP)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

REQUIRED_GATES: tuple[str, ...] = (
    "ALLOW_CACHE_WRITE",
    "CONFIRM_CACHE_WRITE",
    "CONFIRM_JP_CSV_IMPORT",
    "CONFIRM_TARGETS",
)

CSV_REQUIRED_COLUMNS: tuple[str, ...] = ("date", "open", "high", "low", "close", "volume")


@dataclass(frozen=True)
class JpAlternativeProviderExecutionPlanResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_jp_alternative_provider_execution_plan(
    *,
    report_date: str,
    readiness_json_payload: dict[str, Any] | None,
) -> JpAlternativeProviderExecutionPlanResult:
    readiness = readiness_json_payload if isinstance(readiness_json_payload, dict) else {}
    provider = str(readiness.get("recommended_provider", "manual_csv")).strip() or "manual_csv"
    targets = readiness.get("targets")
    target_list = [str(x).strip() for x in targets if str(x).strip()] if isinstance(targets, list) else []
    contract_limited = bool(readiness.get("jquants_contract_limited"))
    steps = [
        "Export JP daily bars CSV from broker (manual).",
        "Validate schema columns and ISO dates (dry-run validator; not executed here).",
        "Set cache write gates and run gated import in a follow-up PR (not this long-run).",
        "Regenerate Context Pack and run cache refresh postcheck.",
    ]
    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "provider_candidate": provider,
        "targets": target_list,
        "jquants_contract_limited": contract_limited,
        "input_file_schema": {
            "format": "csv",
            "required_columns": list(CSV_REQUIRED_COLUMNS),
            "date_format": "YYYY-MM-DD",
            "ticker_column": "optional (one file per ticker preferred)",
        },
        "dry_run_validation": {
            "enabled": True,
            "checks": [
                "header_columns_present",
                "date_parseable",
                "monotonic_dates",
                "no_future_dates_beyond_report_date",
            ],
            "executed": False,
        },
        "cache_write_gate": {
            "required_env": list(REQUIRED_GATES),
            "execute_import": False,
        },
        "postcheck_flow": [
            "weekly-candidate-brief-chatgpt-context",
            "weekly-candidate-brief-cache-refresh-readiness",
            "weekly-candidate-brief-cache-refresh-postcheck",
        ],
        "dry_run_only": True,
        "live_http_executed": False,
        "cache_write_executed": False,
        "actual_refresh_executed": False,
        "steps": steps,
    }
    lines = [
        "# JP Alternative Provider Execution Plan",
        "",
        "## メタ情報",
        f"- report_date: {report_date}",
        f"- generated_at: {payload['generated_at']}",
        f"- provider_candidate: {provider}",
        f"- targets: {', '.join(target_list) or '(none)'}",
        f"- jquants_contract_limited: {str(contract_limited).lower()}",
        "- dry_run_only: true",
        "- live_http_executed: false",
        "- cache_write_executed: false",
        "",
        "## 入力ファイル",
        f"- format: {payload['input_file_schema']['format']}",
        f"- required_columns: {', '.join(CSV_REQUIRED_COLUMNS)}",
        f"- date_format: {payload['input_file_schema']['date_format']}",
        "",
        "## Dry-run検証",
        "- executed: false",
        f"- checks: {', '.join(payload['dry_run_validation']['checks'])}",
        "",
        "## Cache writeゲート",
        f"- required_env: {', '.join(REQUIRED_GATES)}",
        "- execute_import: false",
        "",
        "## 手順",
        *[f"- {step}" for step in steps],
        "",
    ]
    return JpAlternativeProviderExecutionPlanResult(markdown_text="\n".join(lines), json_payload=payload)
