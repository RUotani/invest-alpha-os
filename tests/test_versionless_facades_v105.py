from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re

import pytest

from invis_alpha_os.product import candidate_pipeline, portfolio_input, report_view_model


FACADE_PATHS = (
    Path(report_view_model.__file__),
    Path(portfolio_input.__file__),
    Path(candidate_pipeline.__file__),
)


def test_v105_facades_import_and_expose_only_versionless_public_names() -> None:
    for module in (report_view_model, portfolio_input, candidate_pipeline):
        assert module.__all__
        assert all(re.search(r"_v\d+", name.lower()) is None for name in module.__all__)


def test_v105_report_facade_reaches_shared_view_sanitized_review_and_status_schema() -> None:
    model = report_view_model.build_weekly_shared_view_model(
        score_veto_summary_lines=("score",),
        pipeline_summary_lines=("pipeline",),
        monthly_input_summary_lines=("monthly",),
        sanitized_manual_input_summary_lines=report_view_model.build_sanitized_manual_input_summary_lines(),
    )
    markdown = report_view_model.render_weekly_shared_view_model_markdown(model)
    review = report_view_model.build_sanitized_manual_input_user_review()
    review_markdown = report_view_model.render_sanitized_manual_input_user_review_markdown(review)
    status = report_view_model.build_weekly_artifact_status(
        report_date="2026-06-06",
        full_report="full.md",
        copy_report="copy.md",
        email_text="email.txt",
        email_html="email.html",
        email_eml="email.eml",
        status_file="status.json",
        completed_at="2026-06-05T22:01:00Z",
        env={},
        existing_paths=("full.md", "copy.md", "email.txt", "email.html", "email.eml"),
    )

    assert isinstance(model, report_view_model.WeeklySharedViewModel)
    assert "Sanitized / Manual Input" in "\n".join(markdown)
    assert "これは売買指示ではなく" in review_markdown
    assert report_view_model.validate_weekly_artifact_status(status) == ()


def test_v105_portfolio_facade_reaches_v98_canonical_v97_projection_and_v95_validation() -> None:
    fixture = portfolio_input.build_redacted_sanitized_manual_input_fixture()
    validation = portfolio_input.validate_sanitized_manual_input(fixture, current_month=fixture.as_of_month)
    context = portfolio_input.portfolio_context_from_sanitized_manual_input(fixture)
    context_validation = portfolio_input.validate_portfolio_context_input(context)
    gap = portfolio_input.compute_portfolio_context_allocation_gap(context)
    monthly = portfolio_input.monthly_input_from_sanitized_manual_input(fixture)
    monthly_validation = portfolio_input.validate_monthly_input_consistency(
        monthly,
        current_month=fixture.as_of_month,
    )

    assert isinstance(fixture, portfolio_input.SanitizedManualPortfolioInput)
    assert validation.overall_severity.value == "warn"
    assert isinstance(context, portfolio_input.PortfolioContextInput)
    assert context_validation.overall_severity.value == "warn"
    assert gap.gap_cash_pct < 0
    assert isinstance(monthly, portfolio_input.MonthlyPortfolioInput)
    assert monthly_validation.overall_severity.value == "warn"


def test_v105_portfolio_facade_preserves_validation_failure_path() -> None:
    fixture = portfolio_input.build_redacted_sanitized_manual_input_fixture()
    invalid = replace(fixture, currency="USD")

    result = portfolio_input.validate_sanitized_manual_input(invalid, current_month=fixture.as_of_month)

    assert any(issue.code == "invalid_currency" for issue in result.issues)


def test_v105_candidate_facade_reaches_trace_score_veto_and_integrated_assessment() -> None:
    trace = candidate_pipeline.build_candidate_pipeline_trace_summary(
        (
            candidate_pipeline.CandidateTraceInput(
                symbol="285A",
                name="Kioxia",
                has_required_coverage=True,
                score=80,
                score_threshold=65,
            ),
        )
    )
    score_result = candidate_pipeline.score_candidate(
        candidate_pipeline.CandidateScoreInput(
            symbol="285A",
            name="Kioxia",
            score_breakdown=candidate_pipeline.CandidateScoreBreakdown(4, 4, 3, 3, 4, 3, 4),
        )
    )
    veto = candidate_pipeline.evaluate_candidate_vetoes(
        candidate_pipeline.veto_input_from_score_result(score_result)
    )
    assessment = candidate_pipeline.build_integrated_candidate_assessment(score_result)

    assert trace.final_candidate_count == 1
    assert score_result.symbol == "285A"
    assert veto.symbol == "285A"
    assert isinstance(assessment, candidate_pipeline.CandidateIntegratedAssessment)


def test_v105_candidate_facade_preserves_invalid_score_failure() -> None:
    invalid = candidate_pipeline.CandidateScoreBreakdown(6, 4, 3, 3, 4, 3, 4)

    with pytest.raises(ValueError, match="theme_fit must be between 0 and 5"):
        candidate_pipeline.validate_score_breakdown(invalid)


def test_v105_facades_are_thin_and_do_not_contain_forbidden_execution_paths() -> None:
    forbidden = (
        "requests.",
        "urllib",
        "workflow_dispatch",
        "cache_write",
        "actual_import",
        "broker_api",
        "raw_excel",
        "send_gmail",
        "order_placement",
    )
    for path in FACADE_PATHS:
        text = path.read_text(encoding="utf-8").lower()
        assert all(term not in text for term in forbidden)
