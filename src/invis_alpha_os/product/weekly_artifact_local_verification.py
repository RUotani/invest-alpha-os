"""Local weekly candidate brief artifact verification (source-only/read-only)."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping

from invis_alpha_os.product.scheduled_run_observation_readiness_v101 import (
    build_weekly_candidate_brief_scheduled_observation_checklist_v101,
)
from invis_alpha_os.product.weekly_artifact_status_schema_v104 import (
    validate_weekly_artifact_status_v104,
)


@dataclass(frozen=True)
class WeeklyArtifactLocalVerificationIssue:
    path: str
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class WeeklyArtifactLocalVerificationResult:
    report_date: str
    report_dir: str
    status_file: str
    ready: bool
    checked_paths: tuple[str, ...]
    status_schema_version: str | None
    status_trigger_event: str | None
    gmail_send_attempted: bool | None
    issues: tuple[WeeklyArtifactLocalVerificationIssue, ...]
    safety_notes: tuple[str, ...]


def _path_for_expectation(report_dir: Path, status_file: Path, artifact_path: str) -> Path:
    if artifact_path == "status.json":
        return status_file
    return report_dir / artifact_path


def _read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _load_status(path: Path) -> tuple[Mapping[str, object] | None, str | None]:
    text = _read_text(path)
    if text is None:
        return None, None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"invalid_json:{exc.msg}"
    if not isinstance(payload, Mapping):
        return None, "not_object"
    return payload, None


def verify_weekly_candidate_brief_local_artifacts(
    *,
    report_date: str,
    report_dir: Path,
    status_file: Path,
    require_json_report: bool = True,
) -> WeeklyArtifactLocalVerificationResult:
    """Verify generated weekly artifacts without running the weekly workflow."""

    checklist = build_weekly_candidate_brief_scheduled_observation_checklist_v101()
    issues: list[WeeklyArtifactLocalVerificationIssue] = []
    checked_paths: list[str] = []

    for expectation in checklist.expected_artifacts:
        if expectation.path == "weekly_candidate_brief.json" and not require_json_report:
            required = False
        else:
            required = expectation.required or expectation.path == "weekly_candidate_brief.json"
        path = _path_for_expectation(report_dir, status_file, expectation.path)
        checked_paths.append(str(path))
        text = _read_text(path)
        if text is None:
            if required:
                issues.append(
                    WeeklyArtifactLocalVerificationIssue(
                        path=str(path),
                        code="missing_required_artifact",
                        severity="ERROR",
                        message=f"required artifact is missing: {expectation.path}",
                    )
                )
            continue
        for marker in expectation.must_contain:
            if marker not in text:
                issues.append(
                    WeeklyArtifactLocalVerificationIssue(
                        path=str(path),
                        code="missing_required_marker",
                        severity="WARN",
                        message=f"missing marker: {marker}",
                    )
                )

    status, status_load_error = _load_status(status_file)
    status_schema_version: str | None = None
    status_trigger_event: str | None = None
    gmail_send_attempted: bool | None = None
    if status_load_error is not None:
        issues.append(
            WeeklyArtifactLocalVerificationIssue(
                path=str(status_file),
                code="invalid_status_json",
                severity="ERROR",
                message=status_load_error,
            )
        )
    elif status is not None:
        status_schema_version = str(status.get("schema_version") or "") or None
        trigger = status.get("trigger")
        if isinstance(trigger, Mapping):
            status_trigger_event = str(trigger.get("event_name") or "") or None
        email_preview = status.get("email_preview")
        if isinstance(email_preview, Mapping):
            raw_send_flag = email_preview.get("gmail_send_attempted")
            if isinstance(raw_send_flag, bool):
                gmail_send_attempted = raw_send_flag
        for key in validate_weekly_artifact_status_v104(status):
            issues.append(
                WeeklyArtifactLocalVerificationIssue(
                    path=str(status_file),
                    code="status_schema_issue",
                    severity="ERROR",
                    message=f"v104 status schema issue: {key}",
                )
            )
        if str(status.get("date") or "") != report_date:
            issues.append(
                WeeklyArtifactLocalVerificationIssue(
                    path=str(status_file),
                    code="status_report_date_mismatch",
                    severity="ERROR",
                    message=f"status date does not match report_date={report_date}",
                )
            )
        reports = status.get("reports")
        if require_json_report and isinstance(reports, Mapping) and not reports.get("json_report"):
            issues.append(
                WeeklyArtifactLocalVerificationIssue(
                    path=str(status_file),
                    code="status_json_report_missing",
                    severity="ERROR",
                    message="status reports.json_report is required for the local runner contract",
                )
            )
        observation = status.get("observation")
        if isinstance(observation, Mapping) and observation.get("artifact_generation_complete") is not True:
            issues.append(
                WeeklyArtifactLocalVerificationIssue(
                    path=str(status_file),
                    code="artifact_generation_incomplete",
                    severity="ERROR",
                    message="status observation.artifact_generation_complete is not true",
                )
            )

    blocking = any(issue.severity == "ERROR" for issue in issues)
    return WeeklyArtifactLocalVerificationResult(
        report_date=report_date,
        report_dir=str(report_dir),
        status_file=str(status_file),
        ready=not blocking,
        checked_paths=tuple(checked_paths),
        status_schema_version=status_schema_version,
        status_trigger_event=status_trigger_event,
        gmail_send_attempted=gmail_send_attempted,
        issues=tuple(issues),
        safety_notes=(
            "read-only local artifact verification; workflow_dispatch is not executed",
            "provider live HTTP / market-data live fetch is not executed",
            "cache write / actual import / broker API / raw Excel parsing is not executed",
            "env/secret display, trading action, and real email send are not executed",
        ),
    )


def format_weekly_artifact_local_verification_json(result: WeeklyArtifactLocalVerificationResult) -> str:
    payload = {
        "report_date": result.report_date,
        "report_dir": result.report_dir,
        "status_file": result.status_file,
        "ready": result.ready,
        "checked_paths": list(result.checked_paths),
        "status_schema_version": result.status_schema_version,
        "status_trigger_event": result.status_trigger_event,
        "gmail_send_attempted": result.gmail_send_attempted,
        "issues": [issue.__dict__ for issue in result.issues],
        "safety_notes": list(result.safety_notes),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_weekly_artifact_local_verification_markdown(result: WeeklyArtifactLocalVerificationResult) -> str:
    lines = [
        "# Weekly Artifact Local Verification",
        "",
        f"- report_date: {result.report_date}",
        f"- ready: {str(result.ready).lower()}",
        f"- report_dir: `{result.report_dir}`",
        f"- status_file: `{result.status_file}`",
        f"- status_schema_version: {result.status_schema_version or 'unknown'}",
        f"- status_trigger_event: {result.status_trigger_event or 'unknown'}",
        f"- gmail_send_attempted: {str(result.gmail_send_attempted).lower()}",
        "",
        "## Checked Paths",
    ]
    lines.extend(f"- `{path}`" for path in result.checked_paths)
    lines.extend(["", "## Issues"])
    if result.issues:
        lines.extend(f"- [{issue.severity}] {issue.code}: `{issue.path}` — {issue.message}" for issue in result.issues)
    else:
        lines.append("- none")
    lines.extend(["", "## Safety Notes"])
    lines.extend(f"- {note}" for note in result.safety_notes)
    lines.append("")
    return "\n".join(lines)
