from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_operator_user_guide_contains_safe_command_index_and_boundaries() -> None:
    text = (REPO / "docs" / "operator_user_guide.md").read_text(encoding="utf-8")

    for marker in (
        "weekly-artifact-local-verify",
        "operator-dashboard-summary",
        "progress-dashboard-check",
        "state-consistency-check",
        "sample-output-regeneration-contract",
        "monthly-review-pack-integration",
        "report-ux-language-contract",
        "manual workflow_dispatch",
        "live HTTP / market-data live fetch",
        "cache write",
        "actual refresh/import",
        "broker API",
        "raw Excel direct parsing",
        "real email send",
    ):
        assert marker in text


def test_operator_user_guide_keeps_email_preview_and_gmail_delivery_separate() -> None:
    text = (REPO / "docs" / "operator_user_guide.md").read_text(encoding="utf-8")

    assert "Preview artifacts are inspection outputs, not proof of Gmail delivery." in text
    assert "Real Gmail send remains NO-GO" in text


def test_sample_output_regeneration_links_back_to_operator_user_guide() -> None:
    text = (REPO / "docs" / "sample_output_regeneration.md").read_text(encoding="utf-8")

    assert "docs/operator_user_guide.md" in text
