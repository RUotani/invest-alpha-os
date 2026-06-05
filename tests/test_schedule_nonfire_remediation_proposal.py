from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PROPOSAL = REPO / "docs" / "proposals" / "schedule_nonfire_remediation_20260606.md"


def test_schedule_nonfire_proposal_documents_observed_gap() -> None:
    text = PROPOSAL.read_text(encoding="utf-8")

    assert "`weekly_candidate_brief.yml` had no visible `event=schedule` run" in text
    assert "recent visible workflow runs were `workflow_dispatch`" in text
    assert "Gmail was not sent" in text
    assert "v1.0 first-use remains usable" in text


def test_schedule_nonfire_proposal_keeps_delivery_expectations_unambiguous() -> None:
    text = PROPOSAL.read_text(encoding="utf-8")

    assert "`schedule_status` | `pending`" in text
    assert "`delivery_mode` | `local_markdown_or_artifact_preview`" in text
    assert "`gmail_sent` | `false`" in text
    assert "Missing Gmail is not automatically a report-generation failure" in text


def test_schedule_nonfire_proposal_lists_hard_gate_non_options() -> None:
    text = PROPOSAL.read_text(encoding="utf-8")

    required_markers = (
        "Do not use `workflow_dispatch` as proof of schedule success",
        "Do not add real Gmail sending now",
        "Do not change `.github/workflows/*` without explicit human approval",
        "live HTTP",
        "cache write",
        "actual import",
        "broker API",
        "env/secret display",
        "trading action",
        "real email send",
    )
    for marker in required_markers:
        assert marker in text
