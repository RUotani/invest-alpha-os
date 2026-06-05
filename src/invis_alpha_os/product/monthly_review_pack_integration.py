"""Monthly review pack integration hardening (source-only / fixture-only)."""

from __future__ import annotations

from dataclasses import dataclass
import json

from invis_alpha_os.portfolio.monthly_decision_sheet_v84 import (
    build_monthly_decision_sheet_v84_markdown,
    default_monthly_decision_sheet_input_v84,
)
from invis_alpha_os.product.monthly_input_consistency_v95 import (
    MonthlyInputConsistencySeverityV95,
    build_redacted_monthly_portfolio_fixture_v95,
    render_monthly_input_consistency_markdown_v95,
    validate_monthly_portfolio_input_v95,
)
from invis_alpha_os.product.portfolio_data_quality_review_v109 import (
    build_portfolio_data_quality_review_v109,
    render_portfolio_data_quality_review_markdown_v109,
)


@dataclass(frozen=True)
class MonthlyReviewIntegrationIssue:
    code: str
    severity: str
    component: str
    message: str


@dataclass(frozen=True)
class MonthlyReviewIntegrationResult:
    schema_version: str
    source_mode: str
    report_month: str
    ready: bool
    monthly_input_severity: str
    portfolio_data_quality_severity: str
    checked_components: tuple[str, ...]
    issues: tuple[MonthlyReviewIntegrationIssue, ...]
    safety_notes: tuple[str, ...]


_MONTHLY_DECISION_REQUIRED_MARKERS: tuple[str, ...] = (
    "# Monthly Decision Sheet",
    "## 今月の結論",
    "## 判断サマリー",
    "## 今月の意思決定テーブル",
    "## 現金回復ステップ",
    "## 配分ギャップ（v82再利用）",
    "## Safety note",
    "売買指示ではなく",
    "actual import / broker連携 / cache write は引き続き NO-GO",
    "pack_version: v84",
)

_MONTHLY_INPUT_REQUIRED_MARKERS: tuple[str, ...] = (
    "## Monthly Input Consistency Check",
    "cash_below_minimum_guardrail",
    "single_stock_above_target_band",
    "WARN",
)

_PORTFOLIO_QUALITY_REQUIRED_MARKERS: tuple[str, ...] = (
    "# Portfolio Data Quality Review",
    "Import Readiness: NO-GO",
    "Cache Write Readiness: NO-GO",
    "現金比率ガードレール",
    "個別株比率ガードレール",
    "目標配分ギャップ",
    "これは売買指示ではありません",
)


def _missing_marker_issues(
    *,
    component: str,
    text: str,
    markers: tuple[str, ...],
) -> tuple[MonthlyReviewIntegrationIssue, ...]:
    return tuple(
        MonthlyReviewIntegrationIssue(
            code="missing_required_marker",
            severity="ERROR",
            component=component,
            message=f"missing marker: {marker}",
        )
        for marker in markers
        if marker not in text
    )


def build_monthly_review_pack_integration_result() -> MonthlyReviewIntegrationResult:
    monthly_input = default_monthly_decision_sheet_input_v84()
    monthly_decision_md = build_monthly_decision_sheet_v84_markdown(input_v84=monthly_input)

    v95_fixture = build_redacted_monthly_portfolio_fixture_v95()
    v95_result = validate_monthly_portfolio_input_v95(v95_fixture, current_month=v95_fixture.as_of_month)
    v95_md = render_monthly_input_consistency_markdown_v95(v95_fixture, v95_result)

    portfolio_quality = build_portfolio_data_quality_review_v109()
    portfolio_quality_md = render_portfolio_data_quality_review_markdown_v109(portfolio_quality)

    issues: list[MonthlyReviewIntegrationIssue] = []
    issues.extend(
        _missing_marker_issues(
            component="monthly_decision_sheet_v84",
            text=monthly_decision_md,
            markers=_MONTHLY_DECISION_REQUIRED_MARKERS,
        )
    )
    issues.extend(
        _missing_marker_issues(
            component="monthly_input_consistency_v95",
            text=v95_md,
            markers=_MONTHLY_INPUT_REQUIRED_MARKERS,
        )
    )
    issues.extend(
        _missing_marker_issues(
            component="portfolio_data_quality_review_v109",
            text=portfolio_quality_md,
            markers=_PORTFOLIO_QUALITY_REQUIRED_MARKERS,
        )
    )

    if monthly_input.report_month != v95_fixture.as_of_month:
        issues.append(
            MonthlyReviewIntegrationIssue(
                code="report_month_mismatch",
                severity="ERROR",
                component="monthly_decision_sheet_v84/monthly_input_consistency_v95",
                message=f"v84 report_month={monthly_input.report_month} != v95 as_of_month={v95_fixture.as_of_month}",
            )
        )
    if portfolio_quality.as_of_month != v95_fixture.as_of_month:
        issues.append(
            MonthlyReviewIntegrationIssue(
                code="portfolio_quality_month_mismatch",
                severity="ERROR",
                component="portfolio_data_quality_review_v109/monthly_input_consistency_v95",
                message=(
                    f"v109 as_of_month={portfolio_quality.as_of_month} "
                    f"!= v95 as_of_month={v95_fixture.as_of_month}"
                ),
            )
        )
    if v95_result.overall_severity is MonthlyInputConsistencySeverityV95.ERROR:
        issues.append(
            MonthlyReviewIntegrationIssue(
                code="monthly_input_error",
                severity="ERROR",
                component="monthly_input_consistency_v95",
                message="monthly input consistency returned ERROR for the redacted fixture",
            )
        )
    if portfolio_quality.source_mode != "fixture_or_sanitized_manual_only":
        issues.append(
            MonthlyReviewIntegrationIssue(
                code="unexpected_portfolio_quality_source_mode",
                severity="ERROR",
                component="portfolio_data_quality_review_v109",
                message=f"unexpected source_mode={portfolio_quality.source_mode}",
            )
        )

    ready = not any(issue.severity == "ERROR" for issue in issues)
    return MonthlyReviewIntegrationResult(
        schema_version="monthly_review_pack_integration.v1",
        source_mode="source_only_fixture_only_no_live_access",
        report_month=monthly_input.report_month,
        ready=ready,
        monthly_input_severity=v95_result.overall_severity.value.upper(),
        portfolio_data_quality_severity=portfolio_quality.overall_severity,
        checked_components=(
            "monthly_decision_sheet_v84",
            "monthly_input_consistency_v95",
            "portfolio_data_quality_review_v109",
            "target_allocation_gap_v82",
        ),
        issues=tuple(issues),
        safety_notes=(
            "source-only / fixture-only monthly review integration check",
            "no workflow change / workflow_dispatch",
            "no live HTTP / market-data live fetch",
            "no cache write / actual import / manual import",
            "no broker API / raw Excel direct parsing / env secret display",
            "no trading action / real email send",
        ),
    )


def format_monthly_review_pack_integration_json(result: MonthlyReviewIntegrationResult) -> str:
    payload = {
        "schema_version": result.schema_version,
        "source_mode": result.source_mode,
        "report_month": result.report_month,
        "ready": result.ready,
        "monthly_input_severity": result.monthly_input_severity,
        "portfolio_data_quality_severity": result.portfolio_data_quality_severity,
        "checked_components": list(result.checked_components),
        "issues": [issue.__dict__ for issue in result.issues],
        "safety_notes": list(result.safety_notes),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_monthly_review_pack_integration_markdown(result: MonthlyReviewIntegrationResult) -> str:
    lines = [
        "# Monthly Review Pack Integration",
        "",
        f"- schema_version: {result.schema_version}",
        f"- source_mode: {result.source_mode}",
        f"- report_month: {result.report_month}",
        f"- ready: {str(result.ready).lower()}",
        f"- monthly_input_severity: {result.monthly_input_severity}",
        f"- portfolio_data_quality_severity: {result.portfolio_data_quality_severity}",
        "",
        "## Checked Components",
    ]
    lines.extend(f"- {component}" for component in result.checked_components)
    lines.extend(["", "## Issues"])
    if result.issues:
        lines.extend(
            f"- [{issue.severity}] {issue.component} / {issue.code}: {issue.message}"
            for issue in result.issues
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Safety Notes"])
    lines.extend(f"- {note}" for note in result.safety_notes)
    lines.append("")
    return "\n".join(lines)
