"""One-command manual CSV import flow: PII guard → normalize → validate → plan → execute."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.manual_csv_guards import ManualCsvPathError, resolve_manual_csv_path
from invis_alpha_os.reports.manual_csv_import_execute import build_manual_csv_import_execute
from invis_alpha_os.reports.manual_csv_import_plan import build_manual_csv_import_plan
from invis_alpha_os.reports.manual_csv_normalizer import BROKER_FORMAT_GENERIC, build_manual_csv_normalization
from invis_alpha_os.reports.manual_csv_pii_guard import run_manual_csv_pii_guard
from invis_alpha_os.reports.manual_csv_validation import validate_manual_csv_file


@dataclass(frozen=True)
class ManualCsvImportFlowResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_manual_csv_import_flow(
    *,
    csv_path: Path,
    targets_csv: str,
    report_date: str,
    provider: str,
    scope: str,
    broker_format: str = BROKER_FORMAT_GENERIC,
    execute_import: bool = False,
    env: dict[str, str] | None = None,
    repo_root: Path,
    working_dir: Path,
) -> ManualCsvImportFlowResult:
    env_map = env or {}
    steps: dict[str, Any] = {}
    next_action = "fix_csv_and_retry"

    try:
        resolved = resolve_manual_csv_path(str(csv_path), repo_root=repo_root)
    except ManualCsvPathError as exc:
        payload = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "overall_status": "path_refused",
            "next_required_action": "provide_untracked_csv_path",
            "error": str(exc),
        }
        return ManualCsvImportFlowResult(
            markdown_text="# Manual CSV Import Flow Refused\n\n- path_refused: true\n",
            json_payload=payload,
        )

    pii = run_manual_csv_pii_guard(resolved)
    steps["pii_guard"] = pii.json_payload
    if pii.account_data_detected or pii.status == "rejected":
        payload = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "overall_status": "pii_guard_failed",
            "steps": steps,
            "next_required_action": "remove_account_or_pii_columns",
            "actual_import_executed": False,
            "cache_write_executed": False,
        }
        return ManualCsvImportFlowResult(
            markdown_text="# Manual CSV Import Flow Refused\n\n- pii_guard_failed: true\n",
            json_payload=payload,
        )

    norm_out = working_dir / "manual_csv_normalized_working.csv"
    normalization = build_manual_csv_normalization(
        csv_path=resolved,
        report_date=report_date,
        broker_format=broker_format,
        output_path=norm_out,
    )
    steps["normalization"] = normalization.json_payload
    pipeline_csv = normalization.normalized_path or resolved
    if not normalization.json_payload.get("ready_for_validation"):
        payload = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "overall_status": "normalization_failed",
            "steps": steps,
            "next_required_action": "fix_broker_format_or_columns",
            "actual_import_executed": False,
            "cache_write_executed": False,
        }
        return ManualCsvImportFlowResult(
            markdown_text="# Manual CSV Import Flow Failed\n\n- normalization_failed: true\n",
            json_payload=payload,
        )

    validation = validate_manual_csv_file(
        csv_path=pipeline_csv,
        targets_csv=targets_csv,
        report_date=report_date,
    )
    steps["validation"] = {
        "validated": validation.json_payload.get("validated"),
        "errors": validation.json_payload.get("errors", []),
        "warnings": validation.json_payload.get("warnings", []),
    }
    if not validation.json_payload.get("validated"):
        payload = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "overall_status": "validation_failed",
            "steps": steps,
            "next_required_action": "fix_validation_errors",
            "actual_import_executed": False,
            "cache_write_executed": False,
        }
        return ManualCsvImportFlowResult(
            markdown_text="# Manual CSV Import Flow Failed\n\n- validation_failed: true\n",
            json_payload=payload,
        )

    plan = build_manual_csv_import_plan(
        csv_path=pipeline_csv,
        targets_csv=targets_csv,
        report_date=report_date,
    )
    steps["import_plan"] = {
        "importable": plan.json_payload.get("importable"),
        "rows_newer_than_cache_total": plan.json_payload.get("rows_newer_than_cache_total"),
    }

    dry_execute = build_manual_csv_import_execute(
        csv_path=pipeline_csv,
        targets_csv=targets_csv,
        report_date=report_date,
        provider=provider,
        scope=scope,
        execute_import=False,
        env=env_map,
    )
    steps["dry_run_execute"] = {
        "overall_status": dry_execute.json_payload.get("overall_status"),
        "importable": dry_execute.json_payload.get("importable"),
    }

    actual_result: dict[str, Any] | None = None
    overall_status = "dry_run_complete"
    cache_write = False
    actual_executed = False
    next_action = "review_dry_run_then_set_gates_for_execute_import"

    if execute_import:
        if not plan.json_payload.get("importable"):
            overall_status = "skipped_not_importable"
            next_action = "add_newer_rows_or_fix_targets"
        else:
            executed = build_manual_csv_import_execute(
                csv_path=pipeline_csv,
                targets_csv=targets_csv,
                report_date=report_date,
                provider=provider,
                scope=scope,
                execute_import=True,
                env=env_map,
            )
            actual_result = executed.json_payload
            steps["actual_import"] = actual_result
            overall_status = str(executed.json_payload.get("overall_status", "unknown"))
            cache_write = bool(executed.json_payload.get("cache_write_executed"))
            actual_executed = bool(executed.json_payload.get("actual_import_executed"))
            next_action = "regenerate_context_and_readiness" if actual_executed else "fix_gates_or_csv"

    postcheck_summary = "skipped_no_actual_import"
    if actual_executed:
        postcheck_summary = "run_weekly_candidate_brief_cache_refresh_postcheck_after_context_regen"

    payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "provider": provider,
        "scope": scope,
        "targets": validation.json_payload.get("targets", []),
        "overall_status": overall_status,
        "steps": steps,
        "importable": plan.json_payload.get("importable"),
        "rows_newer_than_cache_total": plan.json_payload.get("rows_newer_than_cache_total"),
        "dry_run_only": not execute_import,
        "cache_write_executed": cache_write,
        "actual_import_executed": actual_executed,
        "postcheck_summary": postcheck_summary,
        "next_required_action": next_action,
    }
    lines = [
        "# Manual CSV Import Flow",
        "",
        f"- overall_status: {overall_status}",
        f"- importable: {str(plan.json_payload.get('importable')).lower()}",
        f"- rows_newer_than_cache_total: {plan.json_payload.get('rows_newer_than_cache_total')}",
        f"- actual_import_executed: {str(actual_executed).lower()}",
        f"- cache_write_executed: {str(cache_write).lower()}",
        f"- next_required_action: {next_action}",
        "",
    ]
    return ManualCsvImportFlowResult(markdown_text="\n".join(lines), json_payload=payload)
