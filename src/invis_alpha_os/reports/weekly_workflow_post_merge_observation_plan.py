"""Source-only post-merge observation plan for the weekly candidate brief workflow."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from invis_alpha_os.config.paths import ROOT_DIR


WORKFLOW_PATH = Path(".github/workflows/weekly_candidate_brief.yml")
EXPECTED_CRON_UTC = "0 22 * * 5"
EXPECTED_ARTIFACT_NAME = "weekly-candidate-brief"


def _next_weekday(source_date: date, *, weekday: int) -> date:
    days_ahead = (weekday - source_date.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return source_date + timedelta(days=days_ahead)


def _next_saturday_jst(report_date: str, *, target_local_hour: int) -> dict[str, str]:
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
        "github_actions_cron_utc": EXPECTED_CRON_UTC,
    }


def _workflow_source_status(repo_root: Path) -> dict[str, Any]:
    workflow_file = repo_root / WORKFLOW_PATH
    text = workflow_file.read_text(encoding="utf-8") if workflow_file.is_file() else ""
    return {
        "workflow_path": str(WORKFLOW_PATH),
        "workflow_exists": workflow_file.is_file(),
        "expected_cron_found": f'cron: "{EXPECTED_CRON_UTC}"' in text,
        "workflow_dispatch_found": "workflow_dispatch:" in text,
        "artifact_name_found": EXPECTED_ARTIFACT_NAME in text,
        "artifact_paths_found": all(
            needle in text
            for needle in (
                "reports/*/weekly_candidate_brief_v0_1.md",
                "reports/*/weekly_candidate_brief_copy.md",
                "reports/*/email/*",
                "outputs/operator/weekly_candidate_brief/*/status.json",
            )
        ),
    }


def build_weekly_workflow_post_merge_observation_plan(
    *,
    report_date: str,
    target_local_hour: int = 7,
    repo_root: Path = ROOT_DIR,
) -> dict[str, Any]:
    next_run = _next_saturday_jst(report_date, target_local_hour=target_local_hour)
    source_status = _workflow_source_status(repo_root)
    source_ready = all(
        (
            source_status["workflow_exists"],
            source_status["expected_cron_found"],
            source_status["workflow_dispatch_found"],
            source_status["artifact_name_found"],
            source_status["artifact_paths_found"],
        )
    )
    return {
        "pack_version": "v73B",
        "report_name": "weekly_workflow_post_merge_observation_plan",
        "source_only": True,
        "report_date": report_date,
        "next_run_target": next_run,
        "workflow_source_status": source_status,
        "github_actions_ui_checks": (
            {
                "step": "open_actions_workflow",
                "expected": "Actions tab shows weekly-candidate-brief workflow for main",
                "manual_url": "https://github.com/RUotani/invest-alpha-os/actions/workflows/weekly_candidate_brief.yml",
            },
            {
                "step": "confirm_scheduled_run_exists",
                "expected": f"run appears after {next_run['next_run_utc_iso']} / Saturday 07:00 JST",
                "failure_class_if_missing": "scheduler_failure",
            },
            {
                "step": "confirm_run_status",
                "expected": "run conclusion is success",
                "failure_class_if_failed": "workflow_failure",
            },
            {
                "step": "confirm_no_manual_dispatch",
                "expected": "do not press Run workflow unless separately approved",
                "failure_class_if_needed": "manual_approval_missing",
            },
        ),
        "artifact_verification_checklist": (
            {
                "item": "artifact_container",
                "expected": EXPECTED_ARTIFACT_NAME,
                "required": True,
            },
            {
                "item": "markdown_report",
                "expected": "weekly_candidate_brief_v0_1.md is present in artifact",
                "required": True,
            },
            {
                "item": "copy_ready_report",
                "expected": "weekly_candidate_brief_copy.md is present in artifact",
                "required": True,
            },
            {
                "item": "email_preview",
                "expected": "reports/*/email/* preview files are present if generated",
                "required": False,
            },
            {
                "item": "operator_status",
                "expected": "outputs/operator/weekly_candidate_brief/*/status.json is present",
                "required": True,
            },
        ),
        "failure_triage_path": {
            "primary_pack": "v72C Scheduled Report Failure Triage Matrix",
            "cli": "weekly-candidate-brief-scheduled-report-failure-triage --report-date <YYYY-MM-DD> --format markdown",
            "classes": (
                "scheduler_failure",
                "workflow_failure",
                "report_generation_failure",
                "delivery_export_failure",
                "timezone_mismatch",
                "missing_secret",
                "permission_failure",
                "silent_failure",
            ),
        },
        "manual_backfill_decision_path": {
            "command_contract_pack": "v72B Weekly Report Manual Backfill Command Pack",
            "recovery_runbook_pack": "v70F Weekly Report Recovery Runbook",
            "dry_run_cli": (
                "weekly-candidate-brief-manual-backfill-command-pack "
                "--report-date <YYYY-MM-DD> --missed-report-date <YYYY-MM-DD> --format markdown"
            ),
            "manual_backfill_execution_approved_by_this_pack": False,
            "gmail_send_approved_by_this_pack": False,
        },
        "readiness_verdict": (
            "ready_to_observe_next_scheduled_run_source_verified"
            if source_ready
            else "not_ready_workflow_source_mismatch"
        ),
        "next_task": "observe_next_saturday_0700_jst_run_without_manual_dispatch",
        "safety_summary": {
            "provider_live_access_executed": False,
            "live_http_executed": False,
            "tiingo_api_call_executed": False,
            "stooq_yahoo_polygon_live_fetch_executed": False,
            "cache_write_executed": False,
            "actual_refresh_import_executed": False,
            "manual_actual_import_executed": False,
            "manual_workflow_dispatch_executed": False,
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


def format_weekly_workflow_post_merge_observation_plan_markdown(payload: dict[str, Any]) -> str:
    next_run = payload["next_run_target"]
    source = payload["workflow_source_status"]
    lines = [
        "# Weekly Workflow Post-Merge Observation Plan / Next Saturday Assurance Pack v73B",
        "",
        "## Verdict",
        f"- readiness_verdict: {payload['readiness_verdict']}",
        f"- next_task: {payload['next_task']}",
        "",
        "## Next Scheduled Run",
        f"- JST: {next_run['next_run_date_jst']} {next_run['next_run_local_time']} {next_run['timezone']}",
        f"- UTC: {next_run['next_run_utc_iso']}",
        f"- cron: `{next_run['github_actions_cron_utc']}`",
        "",
        "## Workflow Source Status",
    ]
    for key, value in source.items():
        lines.append(f"- {key}: {str(value).lower() if isinstance(value, bool) else value}")
    lines.extend(["", "## GitHub Actions UI Checks", "| step | expected |", "|---|---|"])
    for row in payload["github_actions_ui_checks"]:
        lines.append(f"| {row['step']} | {row['expected']} |")
    lines.extend(["", "## Artifact Verification Checklist", "| item | expected | required |", "|---|---|---|"])
    for row in payload["artifact_verification_checklist"]:
        lines.append(f"| {row['item']} | {row['expected']} | {str(row['required']).lower()} |")
    triage = payload["failure_triage_path"]
    backfill = payload["manual_backfill_decision_path"]
    lines.extend(
        [
            "",
            "## Failure Triage Path",
            f"- primary_pack: {triage['primary_pack']}",
            f"- cli: `{triage['cli']}`",
            f"- classes: {', '.join(triage['classes'])}",
            "",
            "## Manual Backfill Decision Path",
            f"- command_contract_pack: {backfill['command_contract_pack']}",
            f"- recovery_runbook_pack: {backfill['recovery_runbook_pack']}",
            f"- dry_run_cli: `{backfill['dry_run_cli']}`",
            f"- manual_backfill_execution_approved_by_this_pack: {str(backfill['manual_backfill_execution_approved_by_this_pack']).lower()}",
            f"- gmail_send_approved_by_this_pack: {str(backfill['gmail_send_approved_by_this_pack']).lower()}",
            "",
            "## Safety Summary",
        ]
    )
    for key, value in payload["safety_summary"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def format_weekly_workflow_post_merge_observation_plan_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_weekly_workflow_post_merge_observation_plan_outputs(
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
        md_path = root / "weekly_workflow_post_merge_observation_plan.md"
        json_path = root / "weekly_workflow_post_merge_observation_plan.json"
        md_path.write_text(markdown_text, encoding="utf-8")
        json_path.write_text(format_weekly_workflow_post_merge_observation_plan_json(json_payload) + "\n", encoding="utf-8")
        paths[f"{label}_weekly_workflow_post_merge_observation_plan_md"] = md_path
        paths[f"{label}_weekly_workflow_post_merge_observation_plan_json"] = json_path
    return paths
