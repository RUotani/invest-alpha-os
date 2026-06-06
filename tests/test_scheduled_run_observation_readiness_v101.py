from __future__ import annotations

from invis_alpha_os.product.scheduled_run_observation_readiness_v101 import (
    build_fixture_artifact_texts_for_scheduled_observation_v101,
    build_weekly_candidate_brief_scheduled_observation_checklist_v101,
    render_scheduled_observation_checklist_markdown_v101,
    validate_fixture_artifact_texts_for_scheduled_observation_v101,
)


def test_v101_checklist_builds_without_manual_dispatch_requirement() -> None:
    checklist = build_weekly_candidate_brief_scheduled_observation_checklist_v101()

    assert checklist.workflow_name == "weekly_candidate_brief"
    assert "0 22 * * 5 UTC" in checklist.expected_trigger
    assert checklist.expected_observation_after_jst == "2026-06-06 07:30 JST"
    assert checklist.manual_dispatch_required is False
    assert any(item.path == "weekly_candidate_brief_copy.md" for item in checklist.expected_artifacts)


def test_v101_expected_artifacts_are_listed_with_required_markers() -> None:
    checklist = build_weekly_candidate_brief_scheduled_observation_checklist_v101()
    by_path = {item.path: item for item in checklist.expected_artifacts}

    assert set(by_path) == {
        "weekly_candidate_brief_v0_1.md",
        "weekly_candidate_brief_copy.md",
        "weekly_candidate_brief.json",
        "email/email_preview.txt",
        "email/email_preview.html",
        "status.json",
    }
    assert "Score / Veto" in by_path["weekly_candidate_brief_copy.md"].must_contain
    assert "Sanitized Input" in by_path["weekly_candidate_brief_copy.md"].must_contain
    assert "現金11.7%" not in by_path["email/email_preview.txt"].must_contain
    assert "個別株19.6%" not in by_path["email/email_preview.html"].must_contain
    assert by_path["weekly_candidate_brief.json"].required is False
    assert by_path["status.json"].required is True
    assert "schema_version" in by_path["status.json"].must_contain
    assert "gmail_send_attempted" in by_path["status.json"].must_contain


def test_v101_fixture_texts_validate_weekly_copy_email_and_status() -> None:
    texts = build_fixture_artifact_texts_for_scheduled_observation_v101(report_date="2026-06-06")
    result = validate_fixture_artifact_texts_for_scheduled_observation_v101(texts)

    assert result.is_ready is True
    assert result.issues == ()
    assert "weekly_candidate_brief_copy.md" in result.checked_paths
    assert "Score / Veto" in texts["weekly_candidate_brief_copy.md"]
    assert "候補パイプライン" in texts["weekly_candidate_brief_copy.md"]
    assert "Sanitized Input" in texts["weekly_candidate_brief_copy.md"]
    assert "現金11.7%" in texts["email/email_preview.txt"]
    assert "個別株19.6%" in texts["email/email_preview.html"]
    assert '"schema_version": "v104"' in texts["status.json"]
    assert '"gmail_send_attempted": false' in texts["status.json"]


def test_v101_validation_reports_missing_required_text() -> None:
    texts = build_fixture_artifact_texts_for_scheduled_observation_v101()
    texts["weekly_candidate_brief_copy.md"] = texts["weekly_candidate_brief_copy.md"].replace(
        "Sanitized Input",
        "Sanitized Manual Input",
    )

    result = validate_fixture_artifact_texts_for_scheduled_observation_v101(texts)

    assert result.is_ready is False
    assert any(
        issue.path == "weekly_candidate_brief_copy.md" and issue.missing_text == "Sanitized Input"
        for issue in result.issues
    )


def test_v101_markdown_records_safety_boundaries_and_fixture_result() -> None:
    checklist = build_weekly_candidate_brief_scheduled_observation_checklist_v101()
    texts = build_fixture_artifact_texts_for_scheduled_observation_v101()
    result = validate_fixture_artifact_texts_for_scheduled_observation_v101(texts, checklist)
    markdown = render_scheduled_observation_checklist_markdown_v101(checklist, result)

    assert markdown.startswith("# Scheduled Run Observation Readiness v101")
    assert "manual_workflow_dispatch_required: false" in markdown
    assert "workflowファイル変更は行わない" in markdown
    assert "provider live HTTP / market-data live fetch は行わない" in markdown
    assert "cache write / actual import / broker API / raw Excel direct parsing は行わない" in markdown
    assert "trading action、実メール送信は行わない" in markdown
    assert "is_ready: true" in markdown
