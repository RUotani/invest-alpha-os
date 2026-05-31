"""Source-only scheduled report failure triage matrix."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


FAILURE_CLASSES: tuple[dict[str, str], ...] = (
    {
        "failure_class": "scheduler_failure",
        "symptom": "No scheduled workflow or local scheduler run appears after the expected window.",
        "primary_evidence": "GitHub Actions run history and v71/v72 workflow approval status",
        "first_response": "Check workflow patch approval/application status and scheduled-report sentinel output.",
    },
    {
        "failure_class": "cli_failure",
        "symptom": "Workflow or local run starts but weekly-candidate-brief command exits non-zero.",
        "primary_evidence": "CLI exit code and stderr summary without secrets",
        "first_response": "Run CLI help and focused tests locally; do not trigger live data refresh.",
    },
    {
        "failure_class": "report_generation_failure",
        "symptom": "CLI exits successfully but expected weekly report artifacts are absent or empty.",
        "primary_evidence": "Expected output schema and artifact existence/size checks",
        "first_response": "Use v72B command pack schema; inspect generated report only, not raw data.",
    },
    {
        "failure_class": "delivery_export_failure",
        "symptom": "Report exists but email preview/export/artifact upload is missing.",
        "primary_evidence": "Artifact list, email preview directory, operator status JSON",
        "first_response": "Regenerate preview/export locally after approval; Gmail send remains separately gated.",
    },
    {
        "failure_class": "timezone_mismatch",
        "symptom": "Run occurs outside Saturday morning JST target window.",
        "primary_evidence": "UTC cron expression and JST conversion",
        "first_response": "Compare against approved cron 0 22 * * 5 for Saturday 07:00 JST.",
    },
    {
        "failure_class": "missing_secret",
        "symptom": "Workflow fails due to unavailable auth/config but secret values are not needed for triage.",
        "primary_evidence": "Presence/absence class only; never print secret values",
        "first_response": "Report missing secret class to operator; do not display env or token contents.",
    },
    {
        "failure_class": "permission_failure",
        "symptom": "Workflow cannot read repository contents or upload artifacts.",
        "primary_evidence": "GitHub Actions permission error class",
        "first_response": "Propose permission fix in docs/report only if workflow change is required.",
    },
    {
        "failure_class": "silent_failure",
        "symptom": "No run, no artifact, and no explicit error is visible.",
        "primary_evidence": "Sentinel missing-report verdict plus absence of workflow run",
        "first_response": "Escalate to workflow approval/status review and keep source-only diagnostics.",
    },
)


def build_scheduled_report_failure_triage_matrix(*, report_date: str, expected_cron_utc: str = "0 22 * * 5") -> dict[str, Any]:
    return {
        "pack_version": "v72C",
        "report_name": "scheduled_report_failure_triage_matrix",
        "source_only": True,
        "report_date": report_date,
        "expected_schedule": {
            "utc_cron_expression": expected_cron_utc,
            "corresponding_jst_schedule": "Saturday 07:00 Asia/Tokyo",
        },
        "triage_matrix": FAILURE_CLASSES,
        "triage_order": (
            "scheduler_failure",
            "timezone_mismatch",
            "permission_failure",
            "missing_secret",
            "cli_failure",
            "report_generation_failure",
            "delivery_export_failure",
            "silent_failure",
        ),
        "evidence_boundaries": {
            "secret_values_may_be_displayed": False,
            "raw_market_data_may_be_read": False,
            "raw_market_data_may_be_written": False,
            "live_http_may_be_used": False,
            "workflow_files_may_be_modified": False,
        },
        "readiness_verdict": "scheduled_report_failure_triage_matrix_ready_source_only",
        "next_task": "long_run_development_progress_snapshot_source_only",
        "safety_summary": {
            "provider_live_access_executed": False,
            "live_http_executed": False,
            "cache_write_executed": False,
            "actual_refresh_import_executed": False,
            "raw_ohlcv_persistence_executed": False,
            "reports_private_raw_data_written": False,
            "env_secret_displayed": False,
            "workflow_files_modified": False,
            "trading_action_executed": False,
        },
    }


def format_scheduled_report_failure_triage_matrix_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Scheduled Report Failure Triage Matrix v72C",
        "",
        "## Verdict",
        f"- readiness_verdict: {payload['readiness_verdict']}",
        f"- utc_cron_expression: `{payload['expected_schedule']['utc_cron_expression']}`",
        f"- corresponding_jst_schedule: {payload['expected_schedule']['corresponding_jst_schedule']}",
        "",
        "## Triage Matrix",
        "| failure_class | symptom | primary_evidence | first_response |",
        "|---|---|---|---|",
    ]
    for row in payload["triage_matrix"]:
        lines.append(
            f"| {row['failure_class']} | {row['symptom']} | {row['primary_evidence']} | {row['first_response']} |"
        )
    lines.extend(["", "## Triage Order"])
    lines.extend(f"- {item}" for item in payload["triage_order"])
    lines.extend(["", "## Evidence Boundaries"])
    for key, value in payload["evidence_boundaries"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(["", "## Safety Summary"])
    for key, value in payload["safety_summary"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def format_scheduled_report_failure_triage_matrix_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_scheduled_report_failure_triage_matrix_outputs(
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
        md_path = root / "scheduled_report_failure_triage_matrix.md"
        json_path = root / "scheduled_report_failure_triage_matrix.json"
        md_path.write_text(markdown_text, encoding="utf-8")
        json_path.write_text(format_scheduled_report_failure_triage_matrix_json(json_payload) + "\n", encoding="utf-8")
        paths[f"{label}_scheduled_report_failure_triage_matrix_md"] = md_path
        paths[f"{label}_scheduled_report_failure_triage_matrix_json"] = json_path
    return paths
