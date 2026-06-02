from __future__ import annotations

import pytest

from invis_alpha_os.product.monthly_input_consistency_v95 import (
    MonthlyInputConsistencySeverityV95,
)
from invis_alpha_os.product.portfolio_context_input_v97 import (
    PortfolioContextSeverityV97,
    build_redacted_portfolio_context_fixture_v97,
    compute_portfolio_context_allocation_gap_v97,
    monthly_input_from_portfolio_context_v97,
    render_portfolio_context_summary_markdown_v97,
    validate_portfolio_context_input_v97,
    validate_v95_consistency_from_portfolio_context_v97,
)


def test_v97_fixture_builds_and_amount_unit_contract() -> None:
    fixture = build_redacted_portfolio_context_fixture_v97()
    assert fixture.as_of_month == "2026-05"
    assert fixture.amount_unit == "man_yen"
    assert fixture.currency == "JPY"


def test_v97_net_worth_identity_holds() -> None:
    fixture = build_redacted_portfolio_context_fixture_v97()
    result = validate_portfolio_context_input_v97(fixture)
    assert not any(x.code == "net_worth_mismatch" for x in result.issues)


def test_v97_asset_total_and_equity_total_hold() -> None:
    fixture = build_redacted_portfolio_context_fixture_v97()
    result = validate_portfolio_context_input_v97(fixture)
    assert not any(x.code == "asset_total_mismatch" for x in result.issues)
    assert not any(x.code == "equity_total_mismatch" for x in result.issues)


def test_v97_guardrail_warnings_detected() -> None:
    fixture = build_redacted_portfolio_context_fixture_v97()
    result = validate_portfolio_context_input_v97(fixture)
    codes = {x.code for x in result.issues}
    assert "cash_below_minimum_guardrail" in codes
    assert "single_stock_above_target_band" in codes
    assert result.overall_severity is PortfolioContextSeverityV97.WARN


def test_v97_allocation_gap_values() -> None:
    fixture = build_redacted_portfolio_context_fixture_v97()
    gap = compute_portfolio_context_allocation_gap_v97(fixture)
    assert gap.gap_cash_pct == pytest.approx(-18.3, abs=0.001)
    assert gap.gap_equity_pct == pytest.approx(18.8, abs=0.001)
    assert gap.gap_alternative_pct == pytest.approx(-3.6, abs=0.001)
    assert gap.gap_bond_pct == pytest.approx(3.0, abs=0.001)


def test_v97_maps_to_v95_and_keeps_main_warnings() -> None:
    fixture = build_redacted_portfolio_context_fixture_v97()
    monthly_input = monthly_input_from_portfolio_context_v97(fixture)
    assert monthly_input.amount_unit == "万円"
    monthly_result = validate_v95_consistency_from_portfolio_context_v97(fixture)
    assert monthly_result.overall_severity is MonthlyInputConsistencySeverityV95.WARN
    codes = {x.code for x in monthly_result.issues}
    assert "cash_below_minimum_guardrail" in codes
    assert "single_stock_above_target_band" in codes


def test_v97_markdown_contains_safety_wording() -> None:
    fixture = build_redacted_portfolio_context_fixture_v97()
    result = validate_portfolio_context_input_v97(fixture)
    gap = compute_portfolio_context_allocation_gap_v97(fixture)
    monthly_result = validate_v95_consistency_from_portfolio_context_v97(fixture)
    md = render_portfolio_context_summary_markdown_v97(
        fixture,
        result,
        gap,
        monthly_result_v95=monthly_result,
    )
    assert "これは売買指示ではなく" in md
    assert "Portfolio Context（v97）" in md
    assert "v95整合: WARN" in md
