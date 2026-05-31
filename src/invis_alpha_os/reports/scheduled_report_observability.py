"""Source-only scheduled report observability and missing-report sentinel."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import ROOT_DIR
from invis_alpha_os.reports.weekly_report_schedule_diagnostic import (
    DEFAULT_EXPECTED_HOUR_JST,
    DEFAULT_EXPECTED_WEEKDAY,
    JST,
    WEEKDAY_NAME_TO_ISO,
    github_actions_cron_for_jst,
    normalize_expected_weekday,
)


DEFAULT_GRACE_HOURS = 6
DEFAULT_LOOKBACK_DAYS = 10


@dataclass(frozen=True)
class ExpectedOccurrence:
    report_kind: str
    expected_date: str
    expected_at_jst: str
    grace_deadline_jst: str
    status_paths: tuple[str, ...]
    report_paths: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_kind": self.report_kind,
            "expected_date": self.expected_date,
            "expected_at_jst": self.expected_at_jst,
            "grace_deadline_jst": self.grace_deadline_jst,
            "status_paths": list(self.status_paths),
            "report_paths": list(self.report_paths),
        }


def _parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def previous_expected_occurrence_date(
    *,
    as_of_date: str,
    expected_weekday: str = DEFAULT_EXPECTED_WEEKDAY,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> str:
    if lookback_days <= 0:
        msg = "lookback_days must be positive"
        raise ValueError(msg)
    as_of = _parse_iso_date(as_of_date)
    weekday = normalize_expected_weekday(expected_weekday)
    target_iso = WEEKDAY_NAME_TO_ISO[weekday.lower()]
    for offset in range(lookback_days + 1):
        candidate = as_of - timedelta(days=offset)
        if candidate.isoweekday() == target_iso:
            return candidate.isoformat()
    msg = "expected occurrence not found within lookback_days"
    raise ValueError(msg)


def build_expected_occurrence(
    *,
    report_kind: str = "weekly",
    as_of_date: str = "2026-05-31",
    expected_weekday: str = DEFAULT_EXPECTED_WEEKDAY,
    expected_hour_jst: int = DEFAULT_EXPECTED_HOUR_JST,
    grace_hours: int = DEFAULT_GRACE_HOURS,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> ExpectedOccurrence:
    expected_date = previous_expected_occurrence_date(
        as_of_date=as_of_date,
        expected_weekday=expected_weekday,
        lookback_days=lookback_days,
    )
    expected_dt = datetime.combine(_parse_iso_date(expected_date), time(hour=expected_hour_jst), tzinfo=JST)
    grace_dt = expected_dt + timedelta(hours=grace_hours)
    return ExpectedOccurrence(
        report_kind=report_kind,
        expected_date=expected_date,
        expected_at_jst=expected_dt.isoformat(),
        grace_deadline_jst=grace_dt.isoformat(),
        status_paths=(
            f"outputs/operator/weekly_candidate_brief/{expected_date}/status.json",
        ),
        report_paths=(
            f"reports/{expected_date}/weekly_candidate_brief_v0_1.md",
            f"reports/{expected_date}/weekly_candidate_brief_copy.md",
            f"reports/{expected_date}/email/email_preview.txt",
        ),
    )


def _path_status(repo_root: Path, rel_paths: tuple[str, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rel in rel_paths:
        path = repo_root / rel
        rows.append(
            {
                "path": rel,
                "exists": path.is_file(),
                "raw_content_read": False,
            }
        )
    return rows


def build_scheduled_report_observability(
    *,
    report_kind: str = "weekly",
    as_of_date: str = "2026-05-31",
    timezone_name: str = "Asia/Tokyo",
    expected_weekday: str = DEFAULT_EXPECTED_WEEKDAY,
    expected_hour_jst: int = DEFAULT_EXPECTED_HOUR_JST,
    grace_hours: int = DEFAULT_GRACE_HOURS,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    repo_root: Path = ROOT_DIR,
) -> dict[str, Any]:
    occurrence = build_expected_occurrence(
        report_kind=report_kind,
        as_of_date=as_of_date,
        expected_weekday=expected_weekday,
        expected_hour_jst=expected_hour_jst,
        grace_hours=grace_hours,
        lookback_days=lookback_days,
    )
    mapping = github_actions_cron_for_jst(
        expected_weekday=expected_weekday,
        expected_hour_jst=expected_hour_jst,
        timezone_name=timezone_name,
    )
    report_status = _path_status(repo_root, occurrence.report_paths)
    status_status = _path_status(repo_root, occurrence.status_paths)
    report_exists = any(row["exists"] for row in report_status)
    status_exists = any(row["exists"] for row in status_status)
    if report_exists and status_exists:
        verdict = "expected_report_present"
    elif report_exists:
        verdict = "warn_report_present_status_missing"
    else:
        verdict = "missing_report_detected_source_artifact_absent"
    return {
        "pack_version": "v70E",
        "report_name": "scheduled_report_observability",
        "source_only": True,
        "expected_schedule": {
            "report_kind": report_kind,
            "timezone": timezone_name,
            "expected_weekday": normalize_expected_weekday(expected_weekday),
            "expected_hour_jst": expected_hour_jst,
            "github_actions_cron_utc": mapping.github_actions_cron_utc,
        },
        "last_expected_occurrence": occurrence.to_dict(),
        "grace_period": {
            "grace_hours": grace_hours,
            "within_grace_unknown_without_runtime_clock": True,
        },
        "evidence_inputs": {
            "report_artifact_paths": report_status,
            "status_artifact_paths": status_status,
            "raw_market_data_read": False,
            "raw_report_content_read": False,
        },
        "missing_report_verdict": verdict,
        "sentinel_schema": {
            "report_kind": "weekly",
            "expected_date": "YYYY-MM-DD",
            "expected_at_jst": "ISO-8601",
            "grace_deadline_jst": "ISO-8601",
            "report_artifact_exists": "boolean",
            "status_artifact_exists": "boolean",
            "verdict": "expected_report_present|warn_report_present_status_missing|missing_report_detected_source_artifact_absent|not_checked",
            "raw_values_allowed": False,
        },
        "notification_boundary": {
            "gmail_send_executed": False,
            "github_issue_created": False,
            "notification_required_manual_wiring": True,
        },
        "required_manual_wiring": (
            "wire this sentinel to a human-approved scheduler or run it manually after the expected weekly window"
        ),
        "next_cursor_handoff": {
            "handoff_status": "source_only_ready_for_v70f_recovery_runbook",
            "recommended_next_task": "v70F_weekly_report_recovery_runbook",
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
            "gmail_send_executed": False,
            "trading_action_executed": False,
        },
    }


def format_scheduled_report_observability_markdown(payload: dict[str, Any]) -> str:
    schedule = payload["expected_schedule"]
    occurrence = payload["last_expected_occurrence"]
    evidence = payload["evidence_inputs"]
    lines = [
        "# Scheduled Report Observability v70E",
        "",
        "## Expected Schedule",
        f"- report_kind: {schedule['report_kind']}",
        f"- timezone: {schedule['timezone']}",
        f"- expected_weekday: {schedule['expected_weekday']}",
        f"- expected_hour_jst: {schedule['expected_hour_jst']}",
        f"- github_actions_cron_utc: `{schedule['github_actions_cron_utc']}`",
        "",
        "## Last Expected Occurrence",
        f"- expected_date: {occurrence['expected_date']}",
        f"- expected_at_jst: {occurrence['expected_at_jst']}",
        f"- grace_deadline_jst: {occurrence['grace_deadline_jst']}",
        "",
        "## Grace Period",
        f"- grace_hours: {payload['grace_period']['grace_hours']}",
        "- runtime clock not inspected in source-only mode",
        "",
        "## Evidence Inputs",
        "| path | exists | raw_content_read |",
        "|---|---|---|",
    ]
    for row in evidence["report_artifact_paths"] + evidence["status_artifact_paths"]:
        lines.append(f"| {row['path']} | {str(row['exists']).lower()} | {str(row['raw_content_read']).lower()} |")
    lines.extend(
        [
            "",
            "## Missing Report Verdict",
            f"- {payload['missing_report_verdict']}",
            "",
            "## Sentinel Schema",
        ]
    )
    for key, value in payload["sentinel_schema"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Notification Boundary",
        ]
    )
    for key, value in payload["notification_boundary"].items():
        lines.append(f"- {key}: {str(value).lower() if isinstance(value, bool) else value}")
    lines.extend(
        [
            "",
            "## Required Manual Wiring",
            f"- {payload['required_manual_wiring']}",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def format_scheduled_report_observability_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_scheduled_report_observability_outputs(
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
        md_path = root / "scheduled_report_observability.md"
        json_path = root / "scheduled_report_observability.json"
        md_path.write_text(markdown_text, encoding="utf-8")
        json_path.write_text(format_scheduled_report_observability_json(json_payload) + "\n", encoding="utf-8")
        paths[f"{label}_scheduled_report_observability_md"] = md_path
        paths[f"{label}_scheduled_report_observability_json"] = json_path
    return paths
