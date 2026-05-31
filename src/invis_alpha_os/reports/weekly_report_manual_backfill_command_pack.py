"""Source-only weekly report manual backfill command pack."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_weekly_report_manual_backfill_command_pack(
    *,
    report_date: str,
    missed_report_date: str = "2026-05-30",
    timezone_name: str = "Asia/Tokyo",
    out_dir: str = "reports",
) -> dict[str, Any]:
    report_root = f"{out_dir}/{missed_report_date}"
    commands = (
        {
            "id": "generate_markdown",
            "command": (
                ".venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief "
                f"--report-date {missed_report_date} --format markdown "
                f"--out {report_root}/weekly_candidate_brief_v0_1.md"
            ),
            "execution_approved_by_this_pack": False,
        },
        {
            "id": "generate_json",
            "command": (
                ".venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief "
                f"--report-date {missed_report_date} --format json "
                f"--out {report_root}/weekly_candidate_brief_v0_1.json"
            ),
            "execution_approved_by_this_pack": False,
        },
        {
            "id": "generate_copy",
            "command": (
                ".venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief "
                f"--report-date {missed_report_date} --format copy "
                f"--out {report_root}/weekly_candidate_brief_copy.md"
            ),
            "execution_approved_by_this_pack": False,
        },
        {
            "id": "build_email_preview_no_send",
            "command": (
                ".venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief-email "
                f"--report-date {missed_report_date} --report-dir {report_root}"
            ),
            "execution_approved_by_this_pack": False,
        },
    )
    return {
        "pack_version": "v72B",
        "report_name": "weekly_report_manual_backfill_command_pack",
        "source_only": True,
        "report_date": report_date,
        "missed_report_date": missed_report_date,
        "timezone": timezone_name,
        "out_dir": out_dir,
        "dry_run_boundary": {
            "manual_backfill_execution_approved_by_this_pack": False,
            "provider_live_access_allowed": False,
            "live_http_allowed": False,
            "actual_refresh_import_allowed": False,
            "cache_write_allowed": False,
            "gmail_send_allowed": False,
        },
        "command_pack": commands,
        "expected_output_schema": {
            "markdown_report": f"{report_root}/weekly_candidate_brief_v0_1.md",
            "json_report": f"{report_root}/weekly_candidate_brief_v0_1.json",
            "copy_report": f"{report_root}/weekly_candidate_brief_copy.md",
            "email_preview_dir": f"{report_root}/email/",
            "operator_status": f"outputs/operator/weekly_candidate_brief/{missed_report_date}/status.json",
            "raw_data_outputs_allowed": False,
        },
        "operator_prechecks": (
            "confirm missed_report_date is the intended Saturday JST report date",
            "confirm workflow patch approval status separately",
            "run commands only after explicit manual backfill approval",
            "review generated markdown/copy artifacts before any notification step",
        ),
        "readiness_verdict": "manual_backfill_command_pack_ready_execution_not_approved",
        "next_task": "scheduled_report_failure_triage_matrix_source_only",
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


def format_weekly_report_manual_backfill_command_pack_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Weekly Report Manual Backfill Command Pack v72B",
        "",
        "## Verdict",
        f"- readiness_verdict: {payload['readiness_verdict']}",
        f"- missed_report_date: {payload['missed_report_date']}",
        f"- timezone: {payload['timezone']}",
        f"- out_dir: `{payload['out_dir']}`",
        "",
        "## Dry-Run Boundary",
    ]
    for key, value in payload["dry_run_boundary"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(["", "## Command Pack", "| id | execution_approved_by_this_pack | command |", "|---|---:|---|"])
    for row in payload["command_pack"]:
        lines.append(f"| {row['id']} | {str(row['execution_approved_by_this_pack']).lower()} | `{row['command']}` |")
    lines.extend(["", "## Expected Output Schema"])
    for key, value in payload["expected_output_schema"].items():
        lines.append(f"- {key}: {str(value).lower() if isinstance(value, bool) else f'`{value}`'}")
    lines.extend(["", "## Operator Prechecks"])
    lines.extend(f"- {item}" for item in payload["operator_prechecks"])
    lines.extend(["", "## Safety Summary"])
    for key, value in payload["safety_summary"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def format_weekly_report_manual_backfill_command_pack_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_weekly_report_manual_backfill_command_pack_outputs(
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
        md_path = root / "weekly_report_manual_backfill_command_pack.md"
        json_path = root / "weekly_report_manual_backfill_command_pack.json"
        md_path.write_text(markdown_text, encoding="utf-8")
        json_path.write_text(format_weekly_report_manual_backfill_command_pack_json(json_payload) + "\n", encoding="utf-8")
        paths[f"{label}_weekly_report_manual_backfill_command_pack_md"] = md_path
        paths[f"{label}_weekly_report_manual_backfill_command_pack_json"] = json_path
    return paths
