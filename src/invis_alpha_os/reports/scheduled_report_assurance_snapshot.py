"""Source-only scheduled report assurance snapshot and next-run readiness matrix."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from invis_alpha_os.reports.long_run_operator_preflight import build_long_run_operator_preflight_pack
from invis_alpha_os.reports.scheduled_report_observability import build_scheduled_report_observability
from invis_alpha_os.reports.weekly_report_local_dryrun_backfill_contract import (
    build_weekly_report_local_dryrun_backfill_contract,
)
from invis_alpha_os.reports.weekly_report_recovery_runbook import build_weekly_report_recovery_runbook
from invis_alpha_os.reports.weekly_report_workflow_approval_package import (
    build_weekly_report_workflow_approval_package,
)


def _next_weekday(source_date: date, *, weekday: int) -> date:
    days_ahead = (weekday - source_date.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return source_date + timedelta(days=days_ahead)


def _next_saturday_jst(report_date: str, *, target_local_hour: int) -> dict[str, Any]:
    local_date = date.fromisoformat(report_date)
    next_date = _next_weekday(local_date, weekday=5)
    jst = ZoneInfo("Asia/Tokyo")
    local_dt = datetime.combine(next_date, time(target_local_hour, 0), tzinfo=jst)
    utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
    return {
        "next_run_date_jst": next_date.isoformat(),
        "next_run_local_time": f"{target_local_hour:02d}:00",
        "timezone": "Asia/Tokyo",
        "next_run_utc_iso": utc_dt.isoformat().replace("+00:00", "Z"),
        "github_actions_cron_utc": "0 22 * * 5",
    }


def build_scheduled_report_assurance_snapshot(
    *,
    report_date: str,
    missed_report_date: str = "2026-05-30",
    target_local_hour: int = 7,
) -> dict[str, Any]:
    workflow = build_weekly_report_workflow_approval_package(
        report_date=report_date,
        target_local_hour=target_local_hour,
    )
    local_contract = build_weekly_report_local_dryrun_backfill_contract(
        report_date=report_date,
        missed_report_date=missed_report_date,
    )
    observability = build_scheduled_report_observability(as_of_date=report_date)
    recovery = build_weekly_report_recovery_runbook(missed_report_date=missed_report_date)
    preflight = build_long_run_operator_preflight_pack(report_date=report_date)
    next_run = _next_saturday_jst(report_date, target_local_hour=target_local_hour)
    readiness_rows = (
        {
            "item": "next_saturday_morning_jst_target",
            "status": "ready",
            "evidence": f"{next_run['next_run_date_jst']} {next_run['next_run_local_time']} {next_run['timezone']}",
        },
        {
            "item": "workflow_patch_required",
            "status": "requires_human_approval"
            if workflow["current_scheduler_assessment"]["workflow_patch_required"]
            else "ready",
            "evidence": f"workflow_patch_required={workflow['current_scheduler_assessment']['workflow_patch_required']}",
        },
        {
            "item": "local_dryrun_backfill_contract_exists",
            "status": "ready",
            "evidence": local_contract["readiness_verdict"],
        },
        {
            "item": "missing_report_sentinel_exists",
            "status": "ready",
            "evidence": observability["missing_report_verdict"],
        },
        {
            "item": "recovery_runbook_exists",
            "status": "ready",
            "evidence": f"manual_backfill_requires_human_choice={recovery['backfill_approval_boundary']['manual_backfill_requires_human_choice']}",
        },
        {
            "item": "sleep_prevention_instruction_present",
            "status": "ready",
            "evidence": preflight["sleep_prevention"]["recommended_command"],
        },
        {
            "item": "manual_approvals_remaining",
            "status": "not_ready",
            "evidence": "workflow patch approval and any recovery/backfill execution approval remain manual",
        },
    )
    workflow_required = workflow["current_scheduler_assessment"]["workflow_patch_required"]
    return {
        "pack_version": "v71D",
        "report_name": "scheduled_report_assurance_snapshot",
        "source_only": True,
        "report_date": report_date,
        "missed_report_date": missed_report_date,
        "next_run_target": next_run,
        "readiness_matrix": readiness_rows,
        "component_status": {
            "weekly_report_schedule_diagnostic_exists": True,
            "scheduled_report_observability_exists": True,
            "weekly_report_recovery_runbook_exists": True,
            "weekly_report_workflow_approval_package_exists": True,
            "weekly_report_local_dryrun_backfill_contract_exists": True,
            "long_run_operator_preflight_sleep_guard_exists": True,
        },
        "remaining_manual_approvals": (
            "explicit .github/workflows approval before applying the v71 workflow patch",
            "explicit local dry-run/backfill execution approval before any recovery execution",
            "explicit Gmail send approval before any notification send",
        ),
        "next_scheduled_report_confidence": (
            "medium_after_workflow_patch_approval" if workflow_required else "high_if_github_actions_enabled"
        ),
        "readiness_verdict": (
            "scheduled_report_not_ready_until_workflow_patch_approved"
            if workflow_required
            else "scheduled_report_ready_for_next_run_observation"
        ),
        "safety_summary": {
            "provider_live_access_executed": False,
            "live_http_executed": False,
            "tiingo_api_call_executed": False,
            "stooq_yahoo_polygon_live_fetch_executed": False,
            "cache_write_executed": False,
            "actual_refresh_import_executed": False,
            "manual_actual_import_executed": False,
            "raw_ohlcv_persistence_executed": False,
            "raw_api_response_persistence_executed": False,
            "reports_private_raw_data_written": False,
            "git_tracked_raw_data_written": False,
            "env_secret_displayed": False,
            "workflow_files_modified": False,
            "dependency_pyproject_changed": False,
            "gmail_send_executed": False,
            "trading_action_executed": False,
        },
    }


def format_scheduled_report_assurance_snapshot_markdown(payload: dict[str, Any]) -> str:
    next_run = payload["next_run_target"]
    lines = [
        "# Scheduled Report Assurance Snapshot / Next-Run Readiness Matrix v71D",
        "",
        "## Verdict",
        f"- readiness_verdict: {payload['readiness_verdict']}",
        f"- next_scheduled_report_confidence: {payload['next_scheduled_report_confidence']}",
        "",
        "## Next Run Target",
        f"- next_run_date_jst: {next_run['next_run_date_jst']}",
        f"- next_run_local_time: {next_run['next_run_local_time']} {next_run['timezone']}",
        f"- next_run_utc_iso: {next_run['next_run_utc_iso']}",
        f"- github_actions_cron_utc: `{next_run['github_actions_cron_utc']}`",
        "",
        "## Readiness Matrix",
        "| item | status | evidence |",
        "|---|---|---|",
    ]
    for row in payload["readiness_matrix"]:
        lines.append(f"| {row['item']} | {row['status']} | {row['evidence']} |")
    lines.extend(["", "## Component Status"])
    for key, value in payload["component_status"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(["", "## Remaining Manual Approvals"])
    lines.extend(f"- {item}" for item in payload["remaining_manual_approvals"])
    lines.extend(["", "## Safety Summary"])
    for key, value in payload["safety_summary"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def format_scheduled_report_assurance_snapshot_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_scheduled_report_assurance_snapshot_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "scheduled_report_assurance_snapshot.md"
        json_path = root / "scheduled_report_assurance_snapshot.json"
        md_path.write_text(markdown_text, encoding="utf-8")
        json_path.write_text(format_scheduled_report_assurance_snapshot_json(json_payload) + "\n", encoding="utf-8")
        paths[f"{label}_scheduled_report_assurance_snapshot_md"] = md_path
        paths[f"{label}_scheduled_report_assurance_snapshot_json"] = json_path
    return paths
