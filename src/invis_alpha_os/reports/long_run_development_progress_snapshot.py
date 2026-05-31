"""Source-only long-run development progress snapshot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DOMAIN_PROGRESS: tuple[dict[str, Any], ...] = (
    {
        "domain": "cache_write",
        "progress_percent": 85,
        "status": "cache_write_pilot_ready_but_execution_not_approved",
        "completed_milestones": ("v67", "v68", "v69", "v69B", "v70", "v70B"),
        "remaining_blockers": ("explicit cache-write execution approval", "cache-write pilot result review after execution"),
    },
    {
        "domain": "weekly_report",
        "progress_percent": 90,
        "status": "source_side_ready_workflow_patch_needs_human_approval",
        "completed_milestones": ("v70D", "v70E", "v70F", "v71", "v71B", "v71C", "v71D", "v72", "v72B", "v72C"),
        "remaining_blockers": ("explicit .github/workflows approval", "observe next Saturday JST scheduled run"),
    },
    {
        "domain": "actual_import",
        "progress_percent": 55,
        "status": "separated_and_quarantined_not_approved",
        "completed_milestones": ("v70C",),
        "remaining_blockers": ("actual import approval phrase", "post-cache-write data quality acceptance"),
    },
    {
        "domain": "operator_runbook",
        "progress_percent": 80,
        "status": "sleep_guard_and_recovery_runbooks_standardized_source_only",
        "completed_milestones": ("v70F", "v71C", "v72B", "v72C"),
        "remaining_blockers": ("workflow patch human approval", "manual execution approvals for recovery actions"),
    },
)


def build_long_run_development_progress_snapshot(*, report_date: str) -> dict[str, Any]:
    return {
        "pack_version": "v72D",
        "report_name": "long_run_development_progress_snapshot",
        "source_only": True,
        "report_date": report_date,
        "progress_policy": {
            "single_overall_percent_allowed": False,
            "domain_percentages_only": True,
            "reason": "RULES.md section 16 forbids a single overall progress percentage.",
        },
        "milestone_range": "v63B_to_v72C",
        "domain_progress": DOMAIN_PROGRESS,
        "chatgpt_copy_table_columns": ("domain", "progress_percent", "status", "remaining_blockers"),
        "hard_gate_status": {
            "provider_live_access": "not_executed",
            "live_http": "not_executed",
            "cache_write": "not_executed",
            "actual_refresh_import": "not_executed",
            "raw_ohlcv_persistence": "not_executed",
            "reports_private_raw_data": "not_written",
            "env_secret_display": "none",
            "workflow_direct_change": "not_applied",
            "trading_action": "not_executed",
        },
        "next_recommended_sequence": (
            "human approval decision for weekly_candidate_brief workflow patch",
            "dedicated workflow-change PR if approved",
            "observe next Saturday JST scheduled report",
            "only then consider approved execution gates for cache-write/manual recovery",
        ),
        "readiness_verdict": "domain_progress_snapshot_ready_no_single_overall_percent",
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


def format_long_run_development_progress_snapshot_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Long-Run Development Progress Snapshot v72D",
        "",
        "## Verdict",
        f"- readiness_verdict: {payload['readiness_verdict']}",
        f"- milestone_range: {payload['milestone_range']}",
        f"- single_overall_percent_allowed: {str(payload['progress_policy']['single_overall_percent_allowed']).lower()}",
        "",
        "## Domain Progress",
        "| domain | progress_percent | status | remaining_blockers |",
        "|---|---:|---|---|",
    ]
    for row in payload["domain_progress"]:
        lines.append(
            f"| {row['domain']} | {row['progress_percent']} | {row['status']} | "
            f"{'; '.join(row['remaining_blockers'])} |"
        )
    lines.extend(["", "## Hard Gate Status"])
    for key, value in payload["hard_gate_status"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Next Recommended Sequence"])
    lines.extend(f"- {item}" for item in payload["next_recommended_sequence"])
    lines.extend(["", "## Safety Summary"])
    for key, value in payload["safety_summary"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def format_long_run_development_progress_snapshot_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_long_run_development_progress_snapshot_outputs(
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
        md_path = root / "long_run_development_progress_snapshot.md"
        json_path = root / "long_run_development_progress_snapshot.json"
        md_path.write_text(markdown_text, encoding="utf-8")
        json_path.write_text(format_long_run_development_progress_snapshot_json(json_payload) + "\n", encoding="utf-8")
        paths[f"{label}_long_run_development_progress_snapshot_md"] = md_path
        paths[f"{label}_long_run_development_progress_snapshot_json"] = json_path
    return paths
