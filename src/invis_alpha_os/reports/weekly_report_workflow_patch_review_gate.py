"""Source-only weekly report workflow patch review and human approval gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import ROOT_DIR
from invis_alpha_os.reports.weekly_report_workflow_approval_package import (
    build_weekly_report_workflow_approval_package,
)


def build_weekly_report_workflow_patch_review_gate(
    *,
    report_date: str,
    target_timezone: str = "Asia/Tokyo",
    target_weekday: str = "Saturday",
    target_local_hour: int = 7,
    repo_root: Path = ROOT_DIR,
) -> dict[str, Any]:
    approval = build_weekly_report_workflow_approval_package(
        report_date=report_date,
        target_timezone=target_timezone,
        target_weekday=target_weekday,
        target_local_hour=target_local_hour,
        repo_root=repo_root,
    )
    schedule = approval["target_schedule"]
    workflow_required = approval["current_scheduler_assessment"]["workflow_patch_required"]
    return {
        "pack_version": "v72",
        "report_name": "weekly_report_workflow_patch_review_gate",
        "source_only": True,
        "report_date": report_date,
        "root_cause": (
            "Tracked GitHub Actions weekly workflow is missing or does not match the Saturday morning JST "
            "weekly report target."
        ),
        "required_workflow_change": approval["required_workflow_change"],
        "schedule": {
            "utc_cron_expression": schedule["github_actions_cron_utc"],
            "corresponding_jst_schedule": (
                f"{schedule['target_weekday']} {schedule['target_local_hour']:02d}:00 {schedule['timezone']}"
            ),
            "utc_schedule": f"{schedule['utc_weekday']} {schedule['utc_hour']:02d}:00 UTC",
            "manual_workflow_dispatch_required": True,
        },
        "manual_workflow_dispatch_proposal": {
            "included_in_patch": True,
            "yaml_key": "workflow_dispatch",
            "purpose": "Allow a human to trigger the weekly candidate brief workflow after approval without changing cron.",
        },
        "failure_detection": (
            {
                "failure_class": "scheduler_failure",
                "detection": "scheduled GitHub Actions run absent after expected UTC cron window",
                "next_check": "scheduled report observability sentinel",
            },
            {
                "failure_class": "workflow_failure",
                "detection": "GitHub Actions run exists but job failed or artifact upload missing",
                "next_check": "workflow run logs and uploaded artifact list",
            },
            {
                "failure_class": "silent_failure",
                "detection": "no workflow run and no local launchd evidence",
                "next_check": "v70D diagnostic plus v71D assurance snapshot",
            },
        ),
        "approval_gate": {
            "workflow_patch_required": workflow_required,
            "workflow_patch_applied_by_this_pack": False,
            "human_approval_required": True,
            "approval_phrase": "I approve applying the weekly_candidate_brief GitHub Actions workflow patch.",
            "why_human_approval_required": approval["why_human_approval_required"],
        },
        "exact_proposed_workflow_patch": approval["exact_proposed_workflow_patch"],
        "readiness_verdict": (
            "workflow_patch_ready_for_human_approval_not_applied"
            if workflow_required
            else "tracked_workflow_schedule_sufficient_no_patch_needed"
        ),
        "next_task": "weekly_report_manual_backfill_command_pack_source_only",
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
            "trading_action_executed": False,
        },
    }


def format_weekly_report_workflow_patch_review_gate_markdown(payload: dict[str, Any]) -> str:
    schedule = payload["schedule"]
    gate = payload["approval_gate"]
    lines = [
        "# Weekly Report Workflow Patch Review / Human Approval Gate v72",
        "",
        "## Verdict",
        f"- readiness_verdict: {payload['readiness_verdict']}",
        f"- workflow_patch_required: {str(gate['workflow_patch_required']).lower()}",
        f"- workflow_patch_applied_by_this_pack: {str(gate['workflow_patch_applied_by_this_pack']).lower()}",
        "",
        "## Root Cause",
        f"- {payload['root_cause']}",
        "",
        "## Required Workflow Change",
        f"- {payload['required_workflow_change']}",
        f"- why_human_approval_required: {gate['why_human_approval_required']}",
        f"- approval_phrase: `{gate['approval_phrase']}`",
        "",
        "## Schedule",
        f"- UTC cron expression: `{schedule['utc_cron_expression']}`",
        f"- corresponding JST schedule: {schedule['corresponding_jst_schedule']}",
        f"- UTC schedule: {schedule['utc_schedule']}",
        "",
        "## Manual Workflow Dispatch Proposal",
    ]
    for key, value in payload["manual_workflow_dispatch_proposal"].items():
        lines.append(f"- {key}: {str(value).lower() if isinstance(value, bool) else value}")
    lines.extend(["", "## Failure Detection", "| failure_class | detection | next_check |", "|---|---|---|"])
    for row in payload["failure_detection"]:
        lines.append(f"| {row['failure_class']} | {row['detection']} | {row['next_check']} |")
    lines.extend(
        [
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


def format_weekly_report_workflow_patch_review_gate_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_weekly_report_workflow_patch_review_gate_outputs(
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
        md_path = root / "weekly_report_workflow_patch_review_gate.md"
        json_path = root / "weekly_report_workflow_patch_review_gate.json"
        md_path.write_text(markdown_text, encoding="utf-8")
        json_path.write_text(format_weekly_report_workflow_patch_review_gate_json(json_payload) + "\n", encoding="utf-8")
        paths[f"{label}_weekly_report_workflow_patch_review_gate_md"] = md_path
        paths[f"{label}_weekly_report_workflow_patch_review_gate_json"] = json_path
    return paths
