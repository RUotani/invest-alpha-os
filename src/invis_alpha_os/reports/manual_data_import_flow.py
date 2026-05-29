"""Unified manual data import flow for CSV/TSV/TXT/XLSX inputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.manual_csv_guards import ManualCsvPathError, resolve_manual_data_path
from invis_alpha_os.reports.manual_csv_import_execute import build_manual_csv_import_execute
from invis_alpha_os.reports.manual_csv_import_plan import build_manual_csv_import_plan
from invis_alpha_os.reports.manual_csv_normalizer import BROKER_FORMAT_AUTO
from invis_alpha_os.reports.manual_csv_validation import validate_manual_csv_file
from invis_alpha_os.reports.manual_file_security import scan_manual_file_security
from invis_alpha_os.reports.manual_data_normalizer import build_manual_data_normalization


@dataclass(frozen=True)
class ManualDataImportFlowResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_manual_data_import_flow(
    *,
    input_path: Path,
    targets_csv: str,
    report_date: str,
    provider: str,
    scope: str,
    broker_format: str = BROKER_FORMAT_AUTO,
    execute_import: bool = False,
    env: dict[str, str] | None = None,
    repo_root: Path,
    working_dir: Path,
) -> ManualDataImportFlowResult:
    env_map = env or {}
    steps: dict[str, Any] = {}

    try:
        resolved = resolve_manual_data_path(str(input_path), repo_root=repo_root)
    except ManualCsvPathError as exc:
        payload = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "overall_status": "path_refused",
            "next_required_action": "provide_untracked_data_file",
            "error": str(exc),
        }
        return ManualDataImportFlowResult(
            markdown_text="# Manual Data Import Flow Refused\n\n- path_refused: true\n",
            json_payload=payload,
        )

    security = scan_manual_file_security(resolved)
    steps["file_security"] = security.json_payload
    if security.status != "passed":
        payload = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "overall_status": "security_rejected",
            "steps": steps,
            "next_required_action": "fix_file_security_issues",
            "contents_printed": False,
            "actual_import_executed": False,
            "cache_write_executed": False,
        }
        return ManualDataImportFlowResult(
            markdown_text="# Manual Data Import Flow Refused\n\n- security_rejected: true\n",
            json_payload=payload,
        )

    normalization = build_manual_data_normalization(
        input_path=resolved,
        report_date=report_date,
        broker_format=broker_format,
        output_path=working_dir / "manual_data_normalized_working.csv",
    )
    steps["normalization"] = normalization.json_payload
    pipeline_path = normalization.normalized_path
    if not pipeline_path or not normalization.json_payload.get("ready_for_validation"):
        payload = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "overall_status": "normalization_failed",
            "steps": steps,
            "next_required_action": "fix_file_format_or_columns",
            "actual_import_executed": False,
            "cache_write_executed": False,
        }
        return ManualDataImportFlowResult(
            markdown_text="# Manual Data Import Flow Failed\n\n- normalization_failed: true\n",
            json_payload=payload,
        )

    validation = validate_manual_csv_file(
        csv_path=pipeline_path,
        targets_csv=targets_csv,
        report_date=report_date,
    )
    steps["validation"] = {
        "validated": validation.json_payload.get("validated"),
        "errors": validation.json_payload.get("errors", []),
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
        return ManualDataImportFlowResult(
            markdown_text="# Manual Data Import Flow Failed\n\n- validation_failed: true\n",
            json_payload=payload,
        )

    plan = build_manual_csv_import_plan(
        csv_path=pipeline_path,
        targets_csv=targets_csv,
        report_date=report_date,
    )
    steps["import_plan"] = {
        "importable": plan.json_payload.get("importable"),
        "rows_newer_than_cache_total": plan.json_payload.get("rows_newer_than_cache_total"),
    }

    dry_execute = build_manual_csv_import_execute(
        csv_path=pipeline_path,
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

    actual_executed = False
    cache_write = False
    overall_status = "dry_run_complete"
    next_action = "review_dry_run_then_set_gates_for_execute_import"

    if execute_import:
        if not plan.json_payload.get("importable"):
            overall_status = "skipped_not_importable"
            next_action = "add_newer_rows_or_fix_targets"
        else:
            executed = build_manual_csv_import_execute(
                csv_path=pipeline_path,
                targets_csv=targets_csv,
                report_date=report_date,
                provider=provider,
                scope=scope,
                execute_import=True,
                env=env_map,
            )
            steps["actual_import"] = executed.json_payload
            overall_status = str(executed.json_payload.get("overall_status", "unknown"))
            actual_executed = bool(executed.json_payload.get("actual_import_executed"))
            cache_write = bool(executed.json_payload.get("cache_write_executed"))
            next_action = "regenerate_context_and_readiness" if actual_executed else "fix_gates_or_data"

    payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "input_type": normalization.json_payload.get("input_type"),
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
        "postcheck_summary": "skipped_no_actual_import"
        if not actual_executed
        else "run_cache_refresh_postcheck_after_context_regen",
        "next_required_action": next_action,
        "contents_printed": False,
    }
    lines = [
        "# Manual Data Import Flow",
        "",
        f"- overall_status: {overall_status}",
        f"- input_type: {payload.get('input_type', '-')}",
        f"- importable: {str(plan.json_payload.get('importable')).lower()}",
        f"- rows_newer_than_cache_total: {plan.json_payload.get('rows_newer_than_cache_total')}",
        f"- actual_import_executed: {str(actual_executed).lower()}",
        f"- next_required_action: {next_action}",
        "",
    ]
    return ManualDataImportFlowResult(markdown_text="\n".join(lines), json_payload=payload)
