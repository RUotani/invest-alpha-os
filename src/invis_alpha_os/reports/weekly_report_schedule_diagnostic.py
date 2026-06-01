"""Weekly report schedule failure diagnostic pack.

This module is source-only. It inspects tracked scheduler/report wiring and
emits a deterministic diagnostic for the user-observed missing Saturday JST
weekly report without reading secrets, sending email, calling providers, or
editing workflows.
"""

from __future__ import annotations

import json
import plistlib
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import ROOT_DIR


JST = timezone(timedelta(hours=9))
WEEKDAY_NAME_TO_ISO = {
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
    "sunday": 7,
}
ISO_WEEKDAY_TO_GITHUB = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 0}
ISO_WEEKDAY_NAMES = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday",
}
DEFAULT_OBSERVED_MISSING_DATE = "2026-05-30"
DEFAULT_EXPECTED_WEEKDAY = "Saturday"
DEFAULT_EXPECTED_HOUR_JST = 7
DEFAULT_EXPECTED_MINUTE_JST = 0


@dataclass(frozen=True)
class ScheduleMapping:
    timezone_name: str
    expected_weekday: str
    expected_hour_jst: int
    expected_minute_jst: int
    github_actions_cron_utc: str
    utc_weekday: str
    utc_hour: int
    utc_minute: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "timezone_name": self.timezone_name,
            "expected_weekday": self.expected_weekday,
            "expected_hour_jst": self.expected_hour_jst,
            "expected_minute_jst": self.expected_minute_jst,
            "github_actions_cron_utc": self.github_actions_cron_utc,
            "utc_weekday": self.utc_weekday,
            "utc_hour": self.utc_hour,
            "utc_minute": self.utc_minute,
        }


def normalize_expected_weekday(value: str) -> str:
    key = value.strip().lower()
    if key not in WEEKDAY_NAME_TO_ISO:
        msg = f"unsupported weekday: {value!r}"
        raise ValueError(msg)
    return ISO_WEEKDAY_NAMES[WEEKDAY_NAME_TO_ISO[key]]


def github_actions_cron_for_jst(
    *,
    expected_weekday: str = DEFAULT_EXPECTED_WEEKDAY,
    expected_hour_jst: int = DEFAULT_EXPECTED_HOUR_JST,
    expected_minute_jst: int = DEFAULT_EXPECTED_MINUTE_JST,
    timezone_name: str = "Asia/Tokyo",
) -> ScheduleMapping:
    if timezone_name != "Asia/Tokyo":
        msg = "v70D supports Asia/Tokyo only"
        raise ValueError(msg)
    weekday = normalize_expected_weekday(expected_weekday)
    iso_weekday = WEEKDAY_NAME_TO_ISO[weekday.lower()]
    local_anchor = datetime.combine(
        date(2026, 5, 25) + timedelta(days=iso_weekday - 1),
        time(hour=expected_hour_jst, minute=expected_minute_jst),
        tzinfo=JST,
    )
    utc_anchor = local_anchor.astimezone(timezone.utc)
    utc_iso_weekday = utc_anchor.isoweekday()
    cron_weekday = ISO_WEEKDAY_TO_GITHUB[utc_iso_weekday]
    cron = f"{utc_anchor.minute} {utc_anchor.hour} * * {cron_weekday}"
    return ScheduleMapping(
        timezone_name=timezone_name,
        expected_weekday=weekday,
        expected_hour_jst=expected_hour_jst,
        expected_minute_jst=expected_minute_jst,
        github_actions_cron_utc=cron,
        utc_weekday=ISO_WEEKDAY_NAMES[utc_iso_weekday],
        utc_hour=utc_anchor.hour,
        utc_minute=utc_anchor.minute,
    )


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _launchd_template_status(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "ops" / "launchd" / "com.invest-alpha-os.weekly-candidate-brief.plist.template"
    text = _read_text(path)
    parsed: dict[str, Any] = {}
    parse_error = ""
    if text:
        try:
            parsed = plistlib.loads(text.encode("utf-8"))
        except Exception as exc:  # pragma: no cover - defensive status capture
            parse_error = exc.__class__.__name__
    interval = parsed.get("StartCalendarInterval", {}) if isinstance(parsed, dict) else {}
    env = parsed.get("EnvironmentVariables", {}) if isinstance(parsed, dict) else {}
    return {
        "path": str(path.relative_to(repo_root)),
        "exists": path.is_file(),
        "parse_error": parse_error,
        "weekday": interval.get("Weekday"),
        "hour": interval.get("Hour"),
        "minute": interval.get("Minute"),
        "timezone": env.get("TZ"),
        "points_to_weekly_script": "scripts/run_weekly_candidate_brief.sh" in text,
        "template_only_not_installation_evidence": True,
    }


def _weekly_script_status(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "scripts" / "run_weekly_candidate_brief.sh"
    text = _read_text(path)
    return {
        "path": str(path.relative_to(repo_root)),
        "exists": path.is_file(),
        "uses_today_jst_iso": "today_jst_iso" in text,
        "writes_markdown_report": "--format markdown" in text and "weekly_candidate_brief_v0_1.md" in text,
        "writes_copy_report": "--format copy" in text and "weekly_candidate_brief_copy.md" in text,
        "writes_email_preview": "weekly-candidate-brief-email" in text,
        "gmail_send_default": False,
        "status_file_configured": "status.json" in text,
        "clears_live_http_env": "CONFIRM_US_LIVE_HTTP=" in text,
        "does_not_call_provider_live_access": True,
    }


def _workflow_status(repo_root: Path) -> dict[str, Any]:
    workflow_dir = repo_root / ".github" / "workflows"
    files = sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml")) if workflow_dir.is_dir() else []
    rows: list[dict[str, Any]] = []
    weekly_schedule_found = False
    weekly_command_found = False
    for path in files:
        text = _read_text(path)
        has_schedule = "schedule:" in text
        has_weekly_command = "run_weekly_candidate_brief.sh" in text or "weekly-candidate-brief" in text
        rows.append(
            {
                "path": str(path.relative_to(repo_root)),
                "has_schedule": has_schedule,
                "has_workflow_dispatch": "workflow_dispatch:" in text,
                "has_weekly_candidate_command": has_weekly_command,
            }
        )
        weekly_schedule_found = weekly_schedule_found or (has_schedule and has_weekly_command)
        weekly_command_found = weekly_command_found or has_weekly_command
    return {
        "workflow_files": rows,
        "github_weekly_schedule_found": weekly_schedule_found,
        "github_weekly_command_found": weekly_command_found,
        "source_workflow_change_applied": weekly_schedule_found,
    }


def proposed_weekly_github_actions_patch(mapping: ScheduleMapping) -> str:
    cron = mapping.github_actions_cron_utc
    return "\n".join(
        [
            "diff --git a/.github/workflows/weekly_candidate_brief.yml b/.github/workflows/weekly_candidate_brief.yml",
            "new file mode 100644",
            "index 0000000..0000000",
            "--- /dev/null",
            "+++ b/.github/workflows/weekly_candidate_brief.yml",
            "@@",
            "+name: weekly-candidate-brief",
            "+",
            "+permissions:",
            "+  contents: read",
            "+",
            "+on:",
            "+  workflow_dispatch:",
            "+  schedule:",
            f"+    - cron: \"{cron}\"  # Saturday 07:00 JST",
            "+",
            "+concurrency:",
            "+  group: weekly-candidate-brief-${{ github.ref }}",
            "+  cancel-in-progress: true",
            "+",
            "+jobs:",
            "+  run-weekly-candidate-brief:",
            "+    runs-on: ubuntu-latest",
            "+    timeout-minutes: 20",
            "+    permissions:",
            "+      contents: read",
            "+    steps:",
            "+      - uses: actions/checkout@v4",
            "+      - uses: actions/setup-python@v5",
            "+        with:",
            "+          python-version: \"3.12\"",
            "+      - name: Install",
            "+        run: |",
            "+          python -m pip install --upgrade pip",
            "+          python -m pip install -e \".[gmail]\"",
            "+      - name: Generate weekly candidate brief",
            "+        run: scripts/run_weekly_candidate_brief.sh",
            "+      - name: Upload weekly candidate brief artifact",
            "+        uses: actions/upload-artifact@v4",
            "+        with:",
            "+          name: weekly-candidate-brief",
            "+          path: |",
            "+            reports/*/weekly_candidate_brief_v0_1.md",
            "+            reports/*/weekly_candidate_brief_copy.md",
            "+            reports/*/email/*",
            "+            outputs/operator/weekly_candidate_brief/*/status.json",
        ]
    )


def build_weekly_report_schedule_diagnostic(
    *,
    observed_missing_date: str = DEFAULT_OBSERVED_MISSING_DATE,
    timezone_name: str = "Asia/Tokyo",
    expected_weekday: str = DEFAULT_EXPECTED_WEEKDAY,
    expected_hour_jst: int = DEFAULT_EXPECTED_HOUR_JST,
    repo_root: Path = ROOT_DIR,
) -> dict[str, Any]:
    mapping = github_actions_cron_for_jst(
        expected_weekday=expected_weekday,
        expected_hour_jst=expected_hour_jst,
        timezone_name=timezone_name,
    )
    workflow = _workflow_status(repo_root)
    launchd = _launchd_template_status(repo_root)
    script = _weekly_script_status(repo_root)
    if workflow["github_weekly_schedule_found"]:
        root_cause = (
            "tracked_github_weekly_schedule_present_after_v73; "
            "launchd_template_exists_but_runtime_installation_not_proven_from_source; "
            "weekly_email_step_is_preview_only_by_default"
        )
        workflow_required = "not_required_after_v73_workflow_source_wiring; observe_next_scheduled_run"
        remaining_manual_action = "observe the next Saturday 07:00 JST GitHub Actions scheduled run"
        next_confidence = "high_source_wiring_visible_runtime_scheduler_not_yet_observed"
    else:
        root_cause = (
            "confirmed_source_gap_no_tracked_github_weekly_schedule; "
            "launchd_template_exists_but_runtime_installation_not_proven_from_source; "
            "weekly_email_step_is_preview_only_by_default"
        )
        workflow_required = (
            "required_if_unattended_remote_github_actions_delivery_is_expected; "
            "not_required_if_local_launchd_is_installed_loaded_and_healthy"
        )
        remaining_manual_action = (
            "choose local launchd repair/verification or explicitly approve the proposed GitHub Actions weekly workflow"
        )
        next_confidence = "medium_source_wiring_visible_runtime_scheduler_not_proven"
    return {
        "pack_version": "v70D",
        "report_name": "weekly_report_schedule_diagnostic",
        "source_only": True,
        "user_observed_issue": "Saturday morning JST weekly report did not appear",
        "observed_missing_date": observed_missing_date,
        "root_cause_found": root_cause,
        "schedule_mapping": mapping.to_dict(),
        "detected_scheduler_wiring": {
            "weekly_script": script,
            "launchd_template": launchd,
            "github_actions": workflow,
        },
        "diagnostic_questions": {
            "existing_weekly_report_cli": "pass_weekly-candidate-brief_exists",
            "existing_scheduled_job_in_source": "partial_launchd_template_only",
            "github_actions_cron_utc_mapping": mapping.github_actions_cron_utc,
            "report_command_wired_to_scheduler": "pass_for_launchd_template_warn_for_github_actions",
            "report_date_timezone_output_format": "pass_for_script_using_today_jst_iso_and_explicit_outputs",
            "generated_but_not_delivered_possible": "yes_email_preview_only_no_gmail_send_by_default",
            "silent_failure_path": "warn_launchd_runtime_status_not_source_tracked",
            "saturday_jst_regression_test": "added_v70d",
            "health_check": "added_v70d_cli_report",
            "workflow_change_required": workflow_required,
        },
        "source_only_fix_implemented": {
            "diagnostic_cli_added": True,
            "utc_jst_mapping_helper_added": True,
            "scheduler_wiring_source_inspection_added": True,
            "proposed_workflow_patch_emitted_not_applied": True,
            "context_pack_status_added": True,
        },
        "workflow_change_required": workflow_required,
        "why_workflow_change_requires_human_approval": (
            "RULES.md forbids .github/workflows changes without explicit human approval; "
            "workflow scheduling changes alter unattended automation behavior."
        ),
        "proposed_workflow_patch": proposed_weekly_github_actions_patch(mapping),
        "remaining_manual_action": remaining_manual_action,
        "next_scheduled_report_confidence": next_confidence,
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
            "trading_action_executed": False,
        },
    }


def format_weekly_report_schedule_diagnostic_markdown(payload: dict[str, Any]) -> str:
    mapping = payload["schedule_mapping"]
    wiring = payload["detected_scheduler_wiring"]
    safety = payload["safety_summary"]
    lines = [
        "# Weekly Report Schedule Diagnostic v70D",
        "",
        "## User-Observed Issue",
        f"- user-observed issue: {payload['user_observed_issue']}",
        f"- observed_missing_date: {payload['observed_missing_date']}",
        "",
        "## Root Cause Candidates",
        f"- root_cause_found: {payload['root_cause_found']}",
        (
            "- confirmed from repo source: tracked GitHub Actions weekly schedule exists for Weekly Candidate Brief"
            if wiring["github_actions"]["github_weekly_schedule_found"]
            else "- confirmed from repo source: no tracked GitHub Actions weekly schedule for Weekly Candidate Brief"
        ),
        "- inferred but not proven: local launchd may not be installed/loaded or may have failed at runtime",
        "- requires runtime/GitHub Actions log inspection: whether any external scheduler attempted the run",
        "",
        "## Detected Scheduler Wiring",
        f"- weekly_script_exists: {str(wiring['weekly_script']['exists']).lower()}",
        f"- launchd_template_exists: {str(wiring['launchd_template']['exists']).lower()}",
        f"- launchd_template_weekday: {wiring['launchd_template']['weekday']}",
        f"- launchd_template_hour: {wiring['launchd_template']['hour']}",
        f"- launchd_template_timezone: {wiring['launchd_template']['timezone']}",
        f"- github_weekly_schedule_found: {str(wiring['github_actions']['github_weekly_schedule_found']).lower()}",
        f"- github_weekly_command_found: {str(wiring['github_actions']['github_weekly_command_found']).lower()}",
        "",
        "## UTC/JST Mapping",
        f"- expected_jst: {mapping['expected_weekday']} {mapping['expected_hour_jst']:02d}:{mapping['expected_minute_jst']:02d} {mapping['timezone_name']}",
        f"- github_actions_cron_utc: `{mapping['github_actions_cron_utc']}`",
        f"- utc_weekday_hour: {mapping['utc_weekday']} {mapping['utc_hour']:02d}:{mapping['utc_minute']:02d} UTC",
        "",
        "## CLI Wiring Check",
        f"- weekly_script_writes_markdown_report: {str(wiring['weekly_script']['writes_markdown_report']).lower()}",
        f"- weekly_script_writes_copy_report: {str(wiring['weekly_script']['writes_copy_report']).lower()}",
        f"- weekly_script_writes_email_preview: {str(wiring['weekly_script']['writes_email_preview']).lower()}",
        f"- weekly_script_status_file_configured: {str(wiring['weekly_script']['status_file_configured']).lower()}",
        "",
        "## Output/Delivery Boundary",
        "- weekly-candidate-brief-email is dry-run by default; it writes previews and does not send Gmail unless separately gated.",
        (
            "- GitHub Actions artifact upload is configured for generated weekly report outputs in tracked source."
            if wiring["github_actions"]["github_weekly_schedule_found"]
            else "- GitHub Actions artifacts are not configured for the weekly report in tracked source."
        ),
        "",
        "## Silent Failure Risks",
        "- launchd runtime load/status/log evidence is outside tracked source.",
        "- a generated local report may remain local and not be exported or delivered.",
        "",
        "## Tests Added",
        "- Saturday 07:00 JST to Friday 22:00 UTC cron mapping",
        "- source diagnostic for GitHub weekly schedule presence/absence",
        "- workflow patch emitted as proposal only",
        "- CLI/report/context pack status",
        "",
        "## Source-Only Fix Implemented",
    ]
    for key, value in payload["source_only_fix_implemented"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(
        [
            "",
            "## Workflow Change Required?",
            f"- {payload['workflow_change_required']}",
            f"- why_human_approval_required: {payload['why_workflow_change_requires_human_approval']}",
            "",
            "## Proposed Workflow Patch If Required",
            "",
            "```diff",
            payload["proposed_workflow_patch"],
            "```",
            "",
            "## Next Scheduled-Report Confidence",
            f"- {payload['next_scheduled_report_confidence']}",
            "",
            "## Remaining Manual Actions",
            f"- {payload['remaining_manual_action']}",
            "",
            "## Safety Summary",
        ]
    )
    for key, value in safety.items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def format_weekly_report_schedule_diagnostic_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_weekly_report_schedule_diagnostic_outputs(
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
        md_path = root / "weekly_report_schedule_diagnostic.md"
        json_path = root / "weekly_report_schedule_diagnostic.json"
        md_path.write_text(markdown_text, encoding="utf-8")
        json_path.write_text(format_weekly_report_schedule_diagnostic_json(json_payload) + "\n", encoding="utf-8")
        paths[f"{label}_weekly_report_schedule_diagnostic_md"] = md_path
        paths[f"{label}_weekly_report_schedule_diagnostic_json"] = json_path
    return paths
