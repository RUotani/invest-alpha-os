from __future__ import annotations

import pytest

from invis_alpha_os.product.monthly_input_consistency_v95 import MonthlyInputConsistencySeverityV95
from invis_alpha_os.product.sanitized_manual_input_v98 import (
    SanitizedManualAssetInputV98,
    SanitizedManualSeverityV98,
    build_redacted_sanitized_manual_input_fixture_v98,
    monthly_input_from_sanitized_manual_input_v98,
    portfolio_context_from_sanitized_manual_input_v98,
    render_sanitized_manual_input_markdown_v98,
    validate_sanitized_manual_input_v98,
    validate_v95_parity_from_sanitized_manual_input_v98,
)


def test_v98_fixture_builds_with_contract_basics() -> None:
    fixture = build_redacted_sanitized_manual_input_fixture_v98()
    assert fixture.as_of_month == "2026-05"
    assert fixture.amount_unit == "man_yen"
    assert fixture.currency == "JPY"


def test_v98_identity_and_totals_are_consistent() -> None:
    fixture = build_redacted_sanitized_manual_input_fixture_v98()
    result = validate_sanitized_manual_input_v98(fixture, current_month="2026-05")
    codes = {x.code for x in result.issues}
    assert "net_worth_mismatch" not in codes
    assert "asset_total_mismatch" not in codes
    assert "equity_total_mismatch" not in codes


def test_v98_warns_for_cash_and_single_stock_guardrails() -> None:
    fixture = build_redacted_sanitized_manual_input_fixture_v98()
    result = validate_sanitized_manual_input_v98(fixture, current_month="2026-05")
    codes = {x.code for x in result.issues}
    assert "cash_below_minimum_guardrail" in codes
    assert "single_stock_above_target_band" in codes
    assert result.overall_severity is SanitizedManualSeverityV98.WARN


def test_v98_converts_to_v97_and_v95() -> None:
    fixture = build_redacted_sanitized_manual_input_fixture_v98()
    portfolio = portfolio_context_from_sanitized_manual_input_v98(fixture)
    monthly = monthly_input_from_sanitized_manual_input_v98(fixture)
    assert portfolio.as_of_month == "2026-05"
    assert portfolio.amount_unit == "man_yen"
    assert monthly.amount_unit == "万円"
    assert monthly.cash.ratio_pct == pytest.approx(11.7, abs=0.001)


def test_v98_v95_warning_parity() -> None:
    fixture = build_redacted_sanitized_manual_input_fixture_v98()
    monthly_result = validate_v95_parity_from_sanitized_manual_input_v98(fixture)
    assert monthly_result.overall_severity is MonthlyInputConsistencySeverityV95.WARN
    codes = {x.code for x in monthly_result.issues}
    assert "cash_below_minimum_guardrail" in codes
    assert "single_stock_above_target_band" in codes


def test_v98_safety_wording_present_in_markdown() -> None:
    fixture = build_redacted_sanitized_manual_input_fixture_v98()
    result = validate_sanitized_manual_input_v98(fixture, current_month="2026-05")
    monthly_result = validate_v95_parity_from_sanitized_manual_input_v98(fixture)
    md = render_sanitized_manual_input_markdown_v98(
        fixture,
        result,
        monthly_result_v95=monthly_result,
    )
    assert "これは売買指示ではなく" in md
    assert "禁止: raw Excel / broker export / broker API / actual import / cache write / live HTTP" in md


def test_v98_validation_detects_schema_errors() -> None:
    fixture = build_redacted_sanitized_manual_input_fixture_v98()
    bad = fixture.__class__(
        **{
            **fixture.__dict__,
            "as_of_month": "2026-13",
            "currency": "USD",
            "amount_unit": "yen",
            "assets": fixture.assets
            + (
                SanitizedManualAssetInputV98("cash", "現金 duplicate", 1.0, 0.1),
                SanitizedManualAssetInputV98("unknown_asset", "未知", 1.0, 0.1),
            ),
        }
    )
    result = validate_sanitized_manual_input_v98(bad, current_month="2026-05")
    codes = {x.code for x in result.issues}
    assert "missing_as_of_month" in codes
    assert "invalid_currency" in codes
    assert "invalid_amount_unit" in codes
    assert "duplicate_asset_key" in codes
    assert "unknown_asset_key" in codes
    assert result.overall_severity is SanitizedManualSeverityV98.ERROR
