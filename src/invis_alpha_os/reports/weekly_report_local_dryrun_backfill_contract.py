"""Source-only local dry-run and backfill verification contract for weekly reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _safe_command_inventory(missed_report_date: str) -> tuple[dict[str, Any], ...]:
    report_dir = f"reports/{missed_report_date}"
    return (
        {
            "id": "generate_markdown_report",
            "purpose": "Generate the weekly candidate brief markdown artifact for the missed date.",
            "command": (
                ".venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief "
                f"--report-date {missed_report_date} --format markdown "
                f"--out {report_dir}/weekly_candidate_brief_v0_1.md"
            ),
            "allowed": True,
            "execution_approved_by_this_pack": False,
            "requires_human_choice_before_backfill": True,
        },
        {
            "id": "generate_copy_report",
            "purpose": "Generate the copy-ready weekly candidate brief artifact for the missed date.",
            "command": (
                ".venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief "
                f"--report-date {missed_report_date} --format copy "
                f"--out {report_dir}/weekly_candidate_brief_copy.md"
            ),
            "allowed": True,
            "execution_approved_by_this_pack": False,
            "requires_human_choice_before_backfill": True,
        },
        {
            "id": "build_email_draft_preview",
            "purpose": "Build a local email preview without Gmail send.",
            "command": (
                ".venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief-email "
                f"--report-date {missed_report_date} --report-dir {report_dir}"
            ),
            "allowed": True,
            "execution_approved_by_this_pack": False,
            "requires_human_choice_before_backfill": True,
        },
        {
            "id": "run_schedule_diagnostic",
            "purpose": "Re-render the source-only schedule diagnostic.",
            "command": (
                ".venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief-schedule-diagnostic "
                f"--observed-missing-date {missed_report_date} --format markdown"
            ),
            "allowed": True,
            "execution_approved_by_this_pack": True,
            "requires_human_choice_before_backfill": False,
        },
        {
            "id": "run_missing_report_sentinel",
            "purpose": "Re-render the source-only scheduled report observability sentinel.",
            "command": (
                ".venv/bin/python -m invis_alpha_os.cli.main "
                f"weekly-candidate-brief-scheduled-report-observability --as-of-date {missed_report_date} "
                "--format markdown"
            ),
            "allowed": True,
            "execution_approved_by_this_pack": True,
            "requires_human_choice_before_backfill": False,
        },
    )


def _failure_mode_matrix() -> tuple[dict[str, str], ...]:
    return (
        {
            "id": "CLI_MISSING",
            "detection": "required weekly-candidate-brief command is not registered or returns non-zero on --help",
            "classification": "blocked_until_source_fix",
            "required_response": "repair CLI registration before any local dry-run/backfill attempt",
        },
        {
            "id": "DATE_MISMATCH",
            "detection": "requested report_date does not match the missed Saturday JST report date",
            "classification": "blocked_until_operator_confirms_date",
            "required_response": "confirm missed_report_date and regenerate commands with the corrected date",
        },
        {
            "id": "TIMEZONE_MISMATCH",
            "detection": "operator target is not Saturday morning JST or does not map to the approved UTC cron",
            "classification": "blocked_until_schedule_contract_review",
            "required_response": "use the v71 workflow approval package schedule mapping before backfill",
        },
        {
            "id": "OUTPUT_MISSING",
            "detection": "expected generated report artifact is absent after an approved local dry-run",
            "classification": "blocked_until_artifact_review",
            "required_response": "inspect CLI stderr/stdout and regenerate only after cause is understood",
        },
        {
            "id": "EMPTY_REPORT",
            "detection": "generated markdown/copy artifact exists but has no usable candidate sections",
            "classification": "blocked_until_report_quality_review",
            "required_response": "treat as failed dry-run and do not send/export",
        },
        {
            "id": "NOTIFICATION_EXPORT_MISSING",
            "detection": "email preview/export artifact is absent or incomplete",
            "classification": "blocked_until_notification_preview_review",
            "required_response": "rebuild preview locally; Gmail send remains outside this pack",
        },
        {
            "id": "WORKFLOW_NOT_APPROVED",
            "detection": "tracked .github/workflows patch has not received explicit human approval",
            "classification": "scheduled_delivery_still_not_ready",
            "required_response": "use v71 approval package; do not edit workflow directly from this pack",
        },
    )


def build_weekly_report_local_dryrun_backfill_contract(
    *,
    report_date: str,
    missed_report_date: str = "2026-05-30",
) -> dict[str, Any]:
    """Build the source-only contract without executing report generation or backfill."""
    command_inventory = _safe_command_inventory(missed_report_date)
    return {
        "pack_version": "v71B",
        "report_name": "weekly_report_local_dryrun_backfill_contract",
        "source_only": True,
        "report_date": report_date,
        "missed_report_date": missed_report_date,
        "scope": {
            "purpose": "Define local dry-run/backfill verification without live data access or raw data writes.",
            "local_dryrun_execution_approved_by_this_pack": False,
            "manual_backfill_execution_approved_by_this_pack": False,
            "gmail_send_approved_by_this_pack": False,
            "workflow_change_approved_by_this_pack": False,
        },
        "offline_only_checks": {
            "fixture_or_mock_required": True,
            "provider_live_access_allowed": False,
            "live_http_allowed": False,
            "cache_write_allowed": False,
            "actual_refresh_import_allowed": False,
            "raw_market_data_read_required": False,
            "raw_market_data_write_allowed": False,
        },
        "command_inventory": command_inventory,
        "output_contract": {
            "allowed_redacted_or_generated_outputs": (
                f"reports/{missed_report_date}/weekly_candidate_brief_v0_1.md",
                f"reports/{missed_report_date}/weekly_candidate_brief_copy.md",
                f"reports/{missed_report_date}/email/*",
                f"outputs/operator/weekly_candidate_brief/{missed_report_date}/status.json",
                "outputs/chatgpt_context/latest/weekly_report_local_dryrun_backfill_contract.*",
            ),
            "forbidden_locations": (
                "raw OHLCV files in the Git-tracked repository",
                "raw API responses in the Git-tracked repository",
                "reports-private raw market data",
                "cache directories used for provider OHLCV persistence",
                "broker/manual raw data exports",
            ),
            "raw_data_policy": "generated reports and redacted summaries are allowed; raw market data persistence is not allowed",
        },
        "failure_mode_matrix": _failure_mode_matrix(),
        "readiness_verdict": "local_dryrun_backfill_contract_ready_execution_not_approved",
        "next_task": "long_run_operator_preflight_sleep_guard_pack_source_only",
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


def format_weekly_report_local_dryrun_backfill_contract_markdown(payload: dict[str, Any]) -> str:
    scope = payload["scope"]
    output_contract = payload["output_contract"]
    lines = [
        "# Weekly Report Local Dry-Run / Backfill Verification Contract v71B",
        "",
        "## Verdict",
        f"- readiness_verdict: {payload['readiness_verdict']}",
        f"- missed_report_date: {payload['missed_report_date']}",
        f"- local_dryrun_execution_approved_by_this_pack: {str(scope['local_dryrun_execution_approved_by_this_pack']).lower()}",
        f"- manual_backfill_execution_approved_by_this_pack: {str(scope['manual_backfill_execution_approved_by_this_pack']).lower()}",
        "",
        "## Offline-Only Boundary",
    ]
    for key, value in payload["offline_only_checks"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(["", "## Command Inventory", "| id | allowed | execution_approved_by_this_pack | command |", "|---|---:|---:|---|"])
    for row in payload["command_inventory"]:
        lines.append(
            f"| {row['id']} | {str(row['allowed']).lower()} | "
            f"{str(row['execution_approved_by_this_pack']).lower()} | `{row['command']}` |"
        )
    lines.extend(["", "## Output Contract", "### Allowed Redacted Or Generated Outputs"])
    lines.extend(f"- `{path}`" for path in output_contract["allowed_redacted_or_generated_outputs"])
    lines.extend(["", "### Forbidden Locations"])
    lines.extend(f"- {path}" for path in output_contract["forbidden_locations"])
    lines.extend(["", f"- raw_data_policy: {output_contract['raw_data_policy']}", "", "## Failure Mode Matrix"])
    lines.extend(["| id | classification | required_response |", "|---|---|---|"])
    for row in payload["failure_mode_matrix"]:
        lines.append(f"| {row['id']} | {row['classification']} | {row['required_response']} |")
    lines.extend(["", "## Safety Summary"])
    for key, value in payload["safety_summary"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def format_weekly_report_local_dryrun_backfill_contract_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_weekly_report_local_dryrun_backfill_contract_outputs(
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
        md_path = root / "weekly_report_local_dryrun_backfill_contract.md"
        json_path = root / "weekly_report_local_dryrun_backfill_contract.json"
        md_path.write_text(markdown_text, encoding="utf-8")
        json_path.write_text(format_weekly_report_local_dryrun_backfill_contract_json(json_payload) + "\n", encoding="utf-8")
        paths[f"{label}_weekly_report_local_dryrun_backfill_contract_md"] = md_path
        paths[f"{label}_weekly_report_local_dryrun_backfill_contract_json"] = json_path
    return paths
