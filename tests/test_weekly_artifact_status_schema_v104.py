from __future__ import annotations

import json

from invis_alpha_os.product.weekly_artifact_status_schema_v104 import (
    SCHEMA_VERSION_V104,
    build_weekly_artifact_status_v104,
    classify_trigger_event_v104,
    safe_trigger_metadata_from_env_v104,
    validate_weekly_artifact_status_v104,
    write_weekly_artifact_status_v104,
)


def _build_status(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "report_date": "2026-06-06",
        "full_report": "reports/2026-06-06/weekly_candidate_brief_v0_1.md",
        "copy_report": "reports/2026-06-06/weekly_candidate_brief_copy.md",
        "json_report": None,
        "email_text": "reports/2026-06-06/email/email_preview.txt",
        "email_html": "reports/2026-06-06/email/email_preview.html",
        "email_eml": "reports/2026-06-06/email/email_preview.eml",
        "status_file": "outputs/operator/weekly_candidate_brief/2026-06-06/status.json",
        "completed_at": "2026-06-05T22:01:00Z",
        "env": {},
        "existing_paths": (
            "reports/2026-06-06/weekly_candidate_brief_v0_1.md",
            "reports/2026-06-06/weekly_candidate_brief_copy.md",
            "reports/2026-06-06/email/email_preview.txt",
            "reports/2026-06-06/email/email_preview.html",
            "reports/2026-06-06/email/email_preview.eml",
        ),
    }
    values.update(overrides)
    return build_weekly_artifact_status_v104(**values)  # type: ignore[arg-type]


def test_v104_status_keeps_legacy_fields_and_adds_structured_observation_fields() -> None:
    status = _build_status()

    assert status["schema_version"] == SCHEMA_VERSION_V104
    assert status["date"] == "2026-06-06"
    assert status["status"] == "weekly_candidate_brief_generated"
    assert status["full_report"] == "reports/2026-06-06/weekly_candidate_brief_v0_1.md"
    assert status["copy_report"] == "reports/2026-06-06/weekly_candidate_brief_copy.md"
    assert status["completed_at"] == "2026-06-05T22:01:00Z"
    assert status["source_mode"] == "observation_only_no_live_http"
    assert status["dry_run"] is True
    assert status["trigger"]["event_name"] == "local"  # type: ignore[index]
    assert status["reports"]["full_report"] == "reports/2026-06-06/weekly_candidate_brief_v0_1.md"  # type: ignore[index]
    assert status["reports"]["copy_report"] == "reports/2026-06-06/weekly_candidate_brief_copy.md"  # type: ignore[index]
    assert status["reports"]["json_report"] is None  # type: ignore[index]
    assert status["email_preview"]["text"] == "reports/2026-06-06/email/email_preview.txt"  # type: ignore[index]
    assert status["email_preview"]["html"] == "reports/2026-06-06/email/email_preview.html"  # type: ignore[index]
    assert status["email_preview"]["eml"] == "reports/2026-06-06/email/email_preview.eml"  # type: ignore[index]
    assert status["email_preview"]["gmail_send_attempted"] is False  # type: ignore[index]
    assert status["observation"]["artifact_generation_complete"] is True  # type: ignore[index]
    assert validate_weekly_artifact_status_v104(status) == ()


def test_v104_trigger_metadata_distinguishes_schedule_dispatch_local_and_unknown() -> None:
    assert classify_trigger_event_v104("schedule") == "schedule"
    assert classify_trigger_event_v104("workflow_dispatch") == "workflow_dispatch"
    assert classify_trigger_event_v104(None) == "local"
    assert classify_trigger_event_v104("push") == "unknown"

    trigger = safe_trigger_metadata_from_env_v104(
        {
            "GITHUB_EVENT_NAME": "schedule",
            "GITHUB_WORKFLOW": "weekly-candidate-brief",
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": "2",
            "GITHUB_SHA": "abc",
            "GITHUB_REF": "refs/heads/main",
            "SECRET_SHOULD_NOT_BE_READ": "secret",
        }
    )
    assert trigger == {
        "event_name": "schedule",
        "workflow": "weekly-candidate-brief",
        "run_id": "123",
        "run_attempt": "2",
        "sha": "abc",
        "ref": "refs/heads/main",
    }
    assert "SECRET_SHOULD_NOT_BE_READ" not in trigger


def test_v104_marks_artifact_generation_incomplete_when_preview_is_missing() -> None:
    status = _build_status(
        existing_paths=(
            "reports/2026-06-06/weekly_candidate_brief_v0_1.md",
            "reports/2026-06-06/weekly_candidate_brief_copy.md",
        )
    )

    assert status["observation"]["artifact_generation_complete"] is False  # type: ignore[index]


def test_v104_validator_reports_invalid_schema_and_gmail_send_state() -> None:
    status = _build_status()
    status["schema_version"] = "old"
    status["email_preview"] = {"gmail_send_attempted": True}

    issues = validate_weekly_artifact_status_v104(status)

    assert "schema_version" in issues
    assert "email_preview.gmail_send_attempted" in issues


def test_v104_status_writer_round_trips_json(tmp_path) -> None:
    status = _build_status()
    output = tmp_path / "status.json"

    write_weekly_artifact_status_v104(str(output), status)

    assert json.loads(output.read_text(encoding="utf-8")) == status
