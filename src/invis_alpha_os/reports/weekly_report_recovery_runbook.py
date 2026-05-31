"""Source-only Weekly Candidate Brief recovery runbook."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.scheduled_report_observability import build_scheduled_report_observability


DEFAULT_MISSED_REPORT_DATE = "2026-05-30"


def build_weekly_report_recovery_runbook(
    *,
    missed_report_date: str = DEFAULT_MISSED_REPORT_DATE,
    timezone_name: str = "Asia/Tokyo",
) -> dict[str, Any]:
    observability = build_scheduled_report_observability(
        as_of_date=missed_report_date,
        timezone_name=timezone_name,
    )
    return {
        "pack_version": "v70F",
        "report_name": "weekly_report_recovery_runbook",
        "source_only": True,
        "missed_report_context": {
            "missed_report_date": missed_report_date,
            "timezone": timezone_name,
            "user_observed_issue": "Saturday morning JST weekly report did not appear",
            "current_sentinel_verdict": observability["missing_report_verdict"],
        },
        "safe_recovery_paths": (
            {
                "path_id": "RECOVERY-01",
                "title": "local_report_regeneration_preview",
                "status": "allowed_as_manual_source_only_backfill_after_human_operator_choice",
                "writes_generated_reports": True,
                "sends_email": False,
                "uses_provider_live_access": False,
                "uses_cache_write": False,
                "uses_actual_import": False,
            },
            {
                "path_id": "RECOVERY-02",
                "title": "diagnose_scheduler_without_backfill",
                "status": "allowed_source_only",
                "writes_generated_reports": False,
                "sends_email": False,
                "uses_provider_live_access": False,
                "uses_cache_write": False,
                "uses_actual_import": False,
            },
            {
                "path_id": "RECOVERY-03",
                "title": "approve_or_repair_scheduler",
                "status": "requires_human_approval_for_workflow_or_launchd_runtime_change",
                "writes_generated_reports": False,
                "sends_email": False,
                "uses_provider_live_access": False,
                "uses_cache_write": False,
                "uses_actual_import": False,
            },
        ),
        "dry_run_commands": (
            {
                "command_id": "CMD-01",
                "description": "re-run v70D schedule diagnostic",
                "command": (
                    ".venv/bin/python -m invis_alpha_os.cli.main "
                    "weekly-candidate-brief-schedule-diagnostic "
                    f"--observed-missing-date {missed_report_date} --format markdown"
                ),
                "executes_recovery": False,
            },
            {
                "command_id": "CMD-02",
                "description": "run v70E missing-report sentinel",
                "command": (
                    ".venv/bin/python -m invis_alpha_os.cli.main "
                    "weekly-candidate-brief-scheduled-report-observability "
                    f"--as-of-date {missed_report_date} --format markdown"
                ),
                "executes_recovery": False,
            },
            {
                "command_id": "CMD-03",
                "description": "manual local report regeneration candidate; writes generated report artifacts only",
                "command": (
                    ".venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief "
                    f"--report-date {missed_report_date} --format markdown "
                    f"--out reports/{missed_report_date}/weekly_candidate_brief_v0_1.md"
                ),
                "executes_recovery": True,
            },
            {
                "command_id": "CMD-04",
                "description": "manual copy block regeneration candidate; writes generated report artifacts only",
                "command": (
                    ".venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief "
                    f"--report-date {missed_report_date} --format copy "
                    f"--out reports/{missed_report_date}/weekly_candidate_brief_copy.md"
                ),
                "executes_recovery": True,
            },
            {
                "command_id": "CMD-05",
                "description": "manual email preview regeneration candidate; dry-run only, no Gmail send",
                "command": (
                    ".venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief-email "
                    f"--report-date {missed_report_date} --report-dir reports/{missed_report_date}"
                ),
                "executes_recovery": True,
            },
        ),
        "backfill_approval_boundary": {
            "this_pack_approves_backfill_execution": False,
            "manual_backfill_requires_human_choice": True,
            "manual_backfill_may_write_generated_reports_under_reports_date": True,
            "gmail_send_approved": False,
            "workflow_change_approved": False,
            "provider_live_access_approved": False,
            "cache_write_approved": False,
            "actual_import_approved": False,
            "trading_action_approved": False,
        },
        "live_fetch_boundary": {
            "provider_live_access_allowed": False,
            "tiingo_api_call_allowed": False,
            "stooq_yahoo_polygon_fetch_allowed": False,
        },
        "cache_write_boundary": {
            "cache_write_allowed": False,
            "raw_ohlcv_persistence_allowed": False,
            "raw_api_response_persistence_allowed": False,
        },
        "actual_import_boundary": {
            "actual_refresh_import_allowed": False,
            "manual_actual_import_allowed": False,
        },
        "human_action_required": (
            "choose whether to run manual local backfill commands, repair local launchd, or approve the proposed workflow patch"
        ),
        "next_confidence_check": (
            "after any manual backfill or scheduler repair, run v70E sentinel and confirm expected_report_present"
        ),
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
            "gmail_send_executed": False,
            "trading_action_executed": False,
        },
    }


def format_weekly_report_recovery_runbook_markdown(payload: dict[str, Any]) -> str:
    context = payload["missed_report_context"]
    lines = [
        "# Weekly Report Recovery Runbook v70F",
        "",
        "## Missed Report Context",
        f"- missed_report_date: {context['missed_report_date']}",
        f"- timezone: {context['timezone']}",
        f"- user_observed_issue: {context['user_observed_issue']}",
        f"- current_sentinel_verdict: {context['current_sentinel_verdict']}",
        "",
        "## Safe Recovery Paths",
        "| path_id | title | status | writes_generated_reports | sends_email |",
        "|---|---|---|---|---|",
    ]
    for row in payload["safe_recovery_paths"]:
        lines.append(
            f"| {row['path_id']} | {row['title']} | {row['status']} | "
            f"{str(row['writes_generated_reports']).lower()} | {str(row['sends_email']).lower()} |"
        )
    lines.extend(["", "## Dry-Run Commands", ""])
    for row in payload["dry_run_commands"]:
        lines.extend(
            [
                f"### {row['command_id']} {row['description']}",
                f"- executes_recovery: {str(row['executes_recovery']).lower()}",
                "```bash",
                row["command"],
                "```",
                "",
            ]
        )
    for title, key in (
        ("Backfill Approval Boundary", "backfill_approval_boundary"),
        ("Live Fetch Boundary", "live_fetch_boundary"),
        ("Cache Write Boundary", "cache_write_boundary"),
        ("Actual Import Boundary", "actual_import_boundary"),
    ):
        lines.extend(["", f"## {title}"])
        for item_key, value in payload[key].items():
            lines.append(f"- {item_key}: {str(value).lower() if isinstance(value, bool) else value}")
    lines.extend(
        [
            "",
            "## Human Action Required",
            f"- {payload['human_action_required']}",
            "",
            "## Next Confidence Check",
            f"- {payload['next_confidence_check']}",
            "",
            "## Safety Summary",
        ]
    )
    for key, value in payload["safety_summary"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def format_weekly_report_recovery_runbook_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_weekly_report_recovery_runbook_outputs(
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
        md_path = root / "weekly_report_recovery_runbook.md"
        json_path = root / "weekly_report_recovery_runbook.json"
        md_path.write_text(markdown_text, encoding="utf-8")
        json_path.write_text(format_weekly_report_recovery_runbook_json(json_payload) + "\n", encoding="utf-8")
        paths[f"{label}_weekly_report_recovery_runbook_md"] = md_path
        paths[f"{label}_weekly_report_recovery_runbook_json"] = json_path
    return paths
