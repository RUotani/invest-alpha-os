"""Source-only weekly report workflow approval package."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import ROOT_DIR
from invis_alpha_os.reports.weekly_report_schedule_diagnostic import (
    DEFAULT_EXPECTED_HOUR_JST,
    DEFAULT_EXPECTED_WEEKDAY,
    github_actions_cron_for_jst,
    proposed_weekly_github_actions_patch,
    build_weekly_report_schedule_diagnostic,
)


WORKFLOW_GLOB_PATTERNS = ("*.yml", "*.yaml")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _workflow_files(repo_root: Path) -> list[Path]:
    workflow_dir = repo_root / ".github" / "workflows"
    if not workflow_dir.is_dir():
        return []
    files: list[Path] = []
    for pattern in WORKFLOW_GLOB_PATTERNS:
        files.extend(sorted(workflow_dir.glob(pattern)))
    return files


def _scheduled_workflow_rows(repo_root: Path, expected_cron: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cron_pattern = re.compile(r"cron:\s*[\"']([^\"']+)[\"']")
    for path in _workflow_files(repo_root):
        text = _read_text(path)
        cron_values = cron_pattern.findall(text)
        has_weekly_command = "run_weekly_candidate_brief.sh" in text or "weekly-candidate-brief" in text
        rows.append(
            {
                "path": str(path.relative_to(repo_root)),
                "has_schedule": "schedule:" in text,
                "cron_values": cron_values,
                "has_weekly_candidate_command": has_weekly_command,
                "matches_expected_cron": expected_cron in cron_values,
                "wrong_cron_detected": bool(cron_values) and expected_cron not in cron_values and has_weekly_command,
            }
        )
    return rows


def build_weekly_report_workflow_approval_package(
    *,
    report_date: str,
    target_timezone: str = "Asia/Tokyo",
    target_weekday: str = DEFAULT_EXPECTED_WEEKDAY,
    target_local_hour: int = DEFAULT_EXPECTED_HOUR_JST,
    repo_root: Path = ROOT_DIR,
) -> dict[str, Any]:
    mapping = github_actions_cron_for_jst(
        expected_weekday=target_weekday,
        expected_hour_jst=target_local_hour,
        timezone_name=target_timezone,
    )
    diagnostic = build_weekly_report_schedule_diagnostic(
        observed_missing_date="2026-05-30",
        timezone_name=target_timezone,
        expected_weekday=target_weekday,
        expected_hour_jst=target_local_hour,
        repo_root=repo_root,
    )
    rows = _scheduled_workflow_rows(repo_root, mapping.github_actions_cron_utc)
    matching = any(row["has_weekly_candidate_command"] and row["matches_expected_cron"] for row in rows)
    wrong_cron = any(row["wrong_cron_detected"] for row in rows)
    workflow_required = not matching
    verdict = "workflow_patch_human_approval_required" if workflow_required else "tracked_workflow_schedule_sufficient"
    if wrong_cron:
        verdict = "workflow_patch_human_approval_required_wrong_cron_detected"
    return {
        "pack_version": "v71",
        "report_name": "weekly_report_workflow_approval_package",
        "source_only": True,
        "report_date": report_date,
        "target_schedule": {
            "timezone": target_timezone,
            "target_weekday": mapping.expected_weekday,
            "target_local_hour": target_local_hour,
            "target_local_minute": mapping.expected_minute_jst,
            "github_actions_cron_utc": mapping.github_actions_cron_utc,
            "utc_weekday": mapping.utc_weekday,
            "utc_hour": mapping.utc_hour,
        },
        "current_scheduler_assessment": {
            "tracked_weekly_workflow_schedule_sufficient": matching,
            "wrong_cron_detected": wrong_cron,
            "workflow_patch_required": workflow_required,
            "workflow_files": rows,
            "launchd_template_exists": diagnostic["detected_scheduler_wiring"]["launchd_template"]["exists"],
            "launchd_runtime_installation_proven": False,
            "github_weekly_schedule_found": diagnostic["detected_scheduler_wiring"]["github_actions"][
                "github_weekly_schedule_found"
            ],
        },
        "approval_checklist": (
            {
                "item": "workflow_schedule_targets_saturday_morning_jst",
                "status": "pass" if matching else "requires_human_approval",
            },
            {
                "item": "workflow_invokes_weekly_candidate_brief_script",
                "status": "pass" if matching else "requires_human_approval",
            },
            {
                "item": "workflow_uploads_report_artifacts",
                "status": "pass" if matching else "requires_human_approval",
            },
            {
                "item": "workflow_change_not_applied_by_agent",
                "status": "pass",
            },
        ),
        "required_workflow_change": (
            "add weekly_candidate_brief workflow with workflow_dispatch, Saturday 07:00 JST schedule, "
            "script invocation, and artifact upload"
        ),
        "exact_proposed_workflow_patch": proposed_weekly_github_actions_patch(mapping),
        "why_human_approval_required": (
            "RULES.md forbids direct .github/workflows changes without explicit human approval; "
            "this patch changes unattended scheduled automation behavior."
        ),
        "readiness_verdict": verdict,
        "context_summary": {
            "workflow_approval_package_exists": True,
            "workflow_patch_required": workflow_required,
            "workflow_patch_applied": False,
            "next_task": "local_dryrun_backfill_verification_contract_source_only",
        },
        "safety_summary": {
            "provider_live_access_executed": False,
            "live_http_executed": False,
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
            "trading_action_executed": False,
        },
    }


def format_weekly_report_workflow_approval_package_markdown(payload: dict[str, Any]) -> str:
    schedule = payload["target_schedule"]
    assessment = payload["current_scheduler_assessment"]
    lines = [
        "# Weekly Report Workflow Approval Patch Package v71",
        "",
        "## Verdict",
        f"- readiness_verdict: {payload['readiness_verdict']}",
        f"- workflow_patch_required: {str(assessment['workflow_patch_required']).lower()}",
        f"- workflow_files_modified: {str(payload['safety_summary']['workflow_files_modified']).lower()}",
        "",
        "## Target Schedule",
        f"- target: {schedule['target_weekday']} {schedule['target_local_hour']:02d}:00 {schedule['timezone']}",
        f"- github_actions_cron_utc: `{schedule['github_actions_cron_utc']}`",
        f"- utc: {schedule['utc_weekday']} {schedule['utc_hour']:02d}:00",
        "",
        "## Current Scheduler Assessment",
        f"- tracked_weekly_workflow_schedule_sufficient: {str(assessment['tracked_weekly_workflow_schedule_sufficient']).lower()}",
        f"- wrong_cron_detected: {str(assessment['wrong_cron_detected']).lower()}",
        f"- launchd_template_exists: {str(assessment['launchd_template_exists']).lower()}",
        f"- launchd_runtime_installation_proven: {str(assessment['launchd_runtime_installation_proven']).lower()}",
        f"- github_weekly_schedule_found: {str(assessment['github_weekly_schedule_found']).lower()}",
        "",
        "## Workflow Files",
        "| path | has_schedule | cron_values | has_weekly_candidate_command | matches_expected_cron | wrong_cron_detected |",
        "|---|---|---|---|---|---|",
    ]
    for row in assessment["workflow_files"]:
        lines.append(
            f"| {row['path']} | {str(row['has_schedule']).lower()} | {', '.join(row['cron_values']) or '(none)'} | "
            f"{str(row['has_weekly_candidate_command']).lower()} | {str(row['matches_expected_cron']).lower()} | "
            f"{str(row['wrong_cron_detected']).lower()} |"
        )
    lines.extend(["", "## Approval Checklist", "| item | status |", "|---|---|"])
    for row in payload["approval_checklist"]:
        lines.append(f"| {row['item']} | {row['status']} |")
    lines.extend(
        [
            "",
            "## Required Workflow Change",
            f"- {payload['required_workflow_change']}",
            f"- why_human_approval_required: {payload['why_human_approval_required']}",
            "",
            "## Exact Proposed Workflow Patch",
            "```diff",
            payload["exact_proposed_workflow_patch"],
            "```",
            "",
            "## Safety Summary",
        ]
    )
    for key, value in payload["safety_summary"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def format_weekly_report_workflow_approval_package_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_weekly_report_workflow_approval_package_outputs(
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
        md_path = root / "weekly_report_workflow_approval_package.md"
        json_path = root / "weekly_report_workflow_approval_package.json"
        md_path.write_text(markdown_text, encoding="utf-8")
        json_path.write_text(format_weekly_report_workflow_approval_package_json(json_payload) + "\n", encoding="utf-8")
        paths[f"{label}_weekly_report_workflow_approval_package_md"] = md_path
        paths[f"{label}_weekly_report_workflow_approval_package_json"] = json_path
    return paths
