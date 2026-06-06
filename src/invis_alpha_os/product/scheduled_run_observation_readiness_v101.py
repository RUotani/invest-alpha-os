"""v101 scheduled run observation readiness pack (source-only / fixture-only)."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Mapping

from invis_alpha_os.product.weekly_candidate_brief_v0 import (
    WeeklyCandidateBriefV0,
    format_weekly_candidate_brief_v0_copy,
    format_weekly_candidate_brief_v0_json,
    format_weekly_candidate_brief_v0_markdown,
)
from invis_alpha_os.product.weekly_artifact_status_schema_v104 import (
    build_weekly_artifact_status_v104,
)
from invis_alpha_os.reports.weekly_candidate_brief_email import build_weekly_candidate_brief_email_draft


@dataclass(frozen=True)
class ScheduledArtifactExpectationV101:
    path: str
    required: bool
    description_ja: str
    must_contain: tuple[str, ...]


@dataclass(frozen=True)
class ScheduledRunObservationChecklistV101:
    workflow_name: str
    expected_trigger: str
    expected_observation_after_jst: str
    manual_dispatch_required: bool
    expected_artifacts: tuple[ScheduledArtifactExpectationV101, ...]
    safety_notes_ja: tuple[str, ...]


@dataclass(frozen=True)
class ScheduledArtifactValidationIssueV101:
    path: str
    missing_text: str
    severity: str


@dataclass(frozen=True)
class ScheduledArtifactValidationResultV101:
    is_ready: bool
    issues: tuple[ScheduledArtifactValidationIssueV101, ...]
    checked_paths: tuple[str, ...]


def build_weekly_candidate_brief_scheduled_observation_checklist_v101() -> ScheduledRunObservationChecklistV101:
    return ScheduledRunObservationChecklistV101(
        workflow_name="weekly_candidate_brief",
        expected_trigger="schedule: 0 22 * * 5 UTC = Saturday 07:00 JST; observe after 2026-06-06 07:30 JST",
        expected_observation_after_jst="2026-06-06 07:30 JST",
        manual_dispatch_required=False,
        expected_artifacts=(
            ScheduledArtifactExpectationV101(
                path="weekly_candidate_brief_v0_1.md",
                required=True,
                description_ja="週次ブリーフ本文。copy-ready summaryと安全文言を含む。",
                must_contain=(
                    "Score / Veto",
                    "候補パイプライン",
                    "Sanitized Input",
                    "これは売買指示ではありません",
                ),
            ),
            ScheduledArtifactExpectationV101(
                path="weekly_candidate_brief_copy.md",
                required=True,
                description_ja="ChatGPT貼り付け用copy本文。週次判断の最短確認に使う。",
                must_contain=(
                    "Score / Veto",
                    "候補パイプライン",
                    "Sanitized Input",
                    "これは売買指示ではありません",
                ),
            ),
            ScheduledArtifactExpectationV101(
                path="weekly_candidate_brief.json",
                required=False,
                description_ja="任意の機械可読週次ブリーフpayload。現runnerではstatus.jsonを正本とする。",
                must_contain=("weekly_candidate_brief.v0.1", "score_veto_pipeline", "report_date"),
            ),
            ScheduledArtifactExpectationV101(
                path="email/email_preview.txt",
                required=True,
                description_ja="送信前確認用のテキスト版email preview。実メール送信ではない。",
                must_contain=(
                    "Score / Veto",
                    "Sanitized Input",
                    "これは実行指示ではなく",
                ),
            ),
            ScheduledArtifactExpectationV101(
                path="email/email_preview.html",
                required=True,
                description_ja="送信前確認用のHTML版email preview。実メール送信ではない。",
                must_contain=("Score / Veto", "Sanitized / Manual Input"),
            ),
            ScheduledArtifactExpectationV101(
                path="status.json",
                required=True,
                description_ja="scheduled run観測ステータス。dispatchではなく結果確認に使う。",
                must_contain=(
                    "schema_version",
                    "source_mode",
                    "trigger",
                    "reports",
                    "email_preview",
                    "gmail_send_attempted",
                    "artifact_generation_complete",
                ),
            ),
        ),
        safety_notes_ja=(
            "manual workflow_dispatch はこのreadiness packでは要求しない。",
            "workflowファイル変更は行わない。",
            "provider live HTTP / market-data live fetch は行わない。",
            "cache write / actual import / broker API / raw Excel direct parsing は行わない。",
            "env/secret display、trading action、実メール送信は行わない。",
        ),
    )


def build_fixture_artifact_texts_for_scheduled_observation_v101(
    *,
    report_date: str = "2026-06-06",
) -> dict[str, str]:
    """Build local fixture artifact texts without dispatching workflows or sending email."""

    brief = WeeklyCandidateBriefV0(
        report_date=report_date,
        generated_at_jp="fixture",
        generated_at_us="fixture",
        jp_scope="fixture",
        us_scope="fixture",
        macro_summary="fixture macro",
    )
    copy_body = format_weekly_candidate_brief_v0_copy(brief)
    email = build_weekly_candidate_brief_email_draft(report_date=report_date, copy_body=copy_body)
    status = build_weekly_artifact_status_v104(
        report_date=report_date,
        full_report="weekly_candidate_brief_v0_1.md",
        copy_report="weekly_candidate_brief_copy.md",
        json_report="weekly_candidate_brief.json",
        email_text="email/email_preview.txt",
        email_html="email/email_preview.html",
        email_eml="email/email_preview.eml",
        status_file="status.json",
        completed_at="2026-06-06T00:00:00Z",
        env={},
        existing_paths=(
            "weekly_candidate_brief_v0_1.md",
            "weekly_candidate_brief_copy.md",
            "email/email_preview.txt",
            "email/email_preview.html",
            "email/email_preview.eml",
        ),
    )
    return {
        "weekly_candidate_brief_v0_1.md": format_weekly_candidate_brief_v0_markdown(brief),
        "weekly_candidate_brief_copy.md": copy_body,
        "weekly_candidate_brief.json": format_weekly_candidate_brief_v0_json(brief),
        "email/email_preview.txt": email.text_body,
        "email/email_preview.html": email.html_body or "",
        "status.json": json.dumps(status, ensure_ascii=False),
    }


def validate_fixture_artifact_texts_for_scheduled_observation_v101(
    artifact_texts: Mapping[str, str],
    checklist: ScheduledRunObservationChecklistV101 | None = None,
) -> ScheduledArtifactValidationResultV101:
    source = checklist or build_weekly_candidate_brief_scheduled_observation_checklist_v101()
    issues: list[ScheduledArtifactValidationIssueV101] = []
    checked_paths: list[str] = []
    for expectation in source.expected_artifacts:
        checked_paths.append(expectation.path)
        text = artifact_texts.get(expectation.path)
        if text is None:
            if expectation.required:
                issues.append(
                    ScheduledArtifactValidationIssueV101(
                        path=expectation.path,
                        missing_text="<artifact missing>",
                        severity="ERROR",
                    )
                )
            continue
        for required_text in expectation.must_contain:
            if required_text not in text:
                issues.append(
                    ScheduledArtifactValidationIssueV101(
                        path=expectation.path,
                        missing_text=required_text,
                        severity="WARN",
                    )
                )
    return ScheduledArtifactValidationResultV101(
        is_ready=not issues,
        issues=tuple(issues),
        checked_paths=tuple(checked_paths),
    )


def render_scheduled_observation_checklist_markdown_v101(
    checklist: ScheduledRunObservationChecklistV101,
    validation_result: ScheduledArtifactValidationResultV101 | None = None,
) -> str:
    lines = [
        "# Scheduled Run Observation Readiness v101",
        "",
        f"- workflow: {checklist.workflow_name}",
        f"- expected_trigger: {checklist.expected_trigger}",
        f"- observe_after: {checklist.expected_observation_after_jst}",
        f"- manual_workflow_dispatch_required: {str(checklist.manual_dispatch_required).lower()}",
        "",
        "## Expected Artifacts",
        "",
        "| path | required | description | must contain |",
        "| --- | --- | --- | --- |",
    ]
    for item in checklist.expected_artifacts:
        lines.append(
            f"| {item.path} | {str(item.required).lower()} | {item.description_ja} | {', '.join(item.must_contain)} |"
        )
    lines.extend(["", "## Safety Notes"])
    lines.extend(f"- {note}" for note in checklist.safety_notes_ja)
    if validation_result is not None:
        lines.extend(["", "## Fixture Validation", f"- is_ready: {str(validation_result.is_ready).lower()}"])
        if validation_result.issues:
            for issue in validation_result.issues:
                lines.append(f"- [{issue.severity}] {issue.path}: missing {issue.missing_text}")
        else:
            lines.append("- all expected fixture artifacts contain required review markers")
    lines.append("")
    return "\n".join(lines)
