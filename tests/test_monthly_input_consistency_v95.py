from __future__ import annotations

import pytest

from invis_alpha_os.product.monthly_input_consistency_v95 import (
    MonthlyInputConsistencySeverityV95,
    build_redacted_monthly_portfolio_fixture_v95,
    render_monthly_input_consistency_markdown_v95,
    validate_monthly_portfolio_input_v95,
)


def test_v95_redacted_fixture_is_warn() -> None:
    fixture = build_redacted_monthly_portfolio_fixture_v95()
    result = validate_monthly_portfolio_input_v95(fixture, current_month="2026-05")
    assert result.overall_severity is MonthlyInputConsistencySeverityV95.WARN
    codes = {x.code for x in result.issues}
    assert "cash_below_minimum_guardrail" in codes
    assert "single_stock_above_target_band" in codes


def test_v95_net_worth_identity_holds() -> None:
    fixture = build_redacted_monthly_portfolio_fixture_v95()
    assert fixture.total_assets_10k_yen - fixture.loan_balance_10k_yen == pytest.approx(
        fixture.net_worth_10k_yen, abs=0.001
    )


def test_v95_asset_total_matches_total_assets() -> None:
    fixture = build_redacted_monthly_portfolio_fixture_v95()
    amount_total = (
        fixture.cash.amount_10k_yen
        + fixture.index.amount_10k_yen
        + fixture.individual_stocks.amount_10k_yen
        + fixture.bonds.amount_10k_yen
        + fixture.gold.amount_10k_yen
        + fixture.crypto_high_beta.amount_10k_yen
        + fixture.leverage.amount_10k_yen
    )
    assert amount_total == fixture.total_assets_10k_yen


def test_v95_equity_total_matches_index_plus_single() -> None:
    fixture = build_redacted_monthly_portfolio_fixture_v95()
    assert fixture.equity_total.amount_10k_yen == fixture.index.amount_10k_yen + fixture.individual_stocks.amount_10k_yen


def test_v95_cash_ratio_warn_threshold() -> None:
    fixture = build_redacted_monthly_portfolio_fixture_v95()
    result = validate_monthly_portfolio_input_v95(fixture, current_month="2026-05")
    assert any(x.code == "cash_below_minimum_guardrail" and x.severity is MonthlyInputConsistencySeverityV95.WARN for x in result.issues)


def test_v95_single_stock_ratio_warn_threshold() -> None:
    fixture = build_redacted_monthly_portfolio_fixture_v95()
    result = validate_monthly_portfolio_input_v95(fixture, current_month="2026-05")
    assert any(x.code == "single_stock_above_target_band" and x.severity is MonthlyInputConsistencySeverityV95.WARN for x in result.issues)


def test_v95_net_worth_mismatch_is_error() -> None:
    fixture = build_redacted_monthly_portfolio_fixture_v95()
    bad = fixture.__class__(**{**fixture.__dict__, "net_worth_10k_yen": 800.0})
    result = validate_monthly_portfolio_input_v95(bad, current_month="2026-05")
    assert any(x.code == "net_worth_mismatch" and x.severity is MonthlyInputConsistencySeverityV95.ERROR for x in result.issues)
    assert result.overall_severity is MonthlyInputConsistencySeverityV95.ERROR


def test_v95_asset_total_mismatch_is_error() -> None:
    fixture = build_redacted_monthly_portfolio_fixture_v95()
    bad_cash = fixture.cash.__class__(name=fixture.cash.name, amount_10k_yen=500.0, ratio_pct=fixture.cash.ratio_pct)
    bad = fixture.__class__(**{**fixture.__dict__, "cash": bad_cash})
    result = validate_monthly_portfolio_input_v95(bad, current_month="2026-05")
    assert any(x.code == "asset_total_mismatch" and x.severity is MonthlyInputConsistencySeverityV95.ERROR for x in result.issues)
    assert result.overall_severity is MonthlyInputConsistencySeverityV95.ERROR


def test_v95_future_month_is_error() -> None:
    fixture = build_redacted_monthly_portfolio_fixture_v95()
    bad = fixture.__class__(**{**fixture.__dict__, "as_of_month": "2026-07"})
    result = validate_monthly_portfolio_input_v95(bad, current_month="2026-05")
    assert any(x.code == "future_as_of_month" for x in result.issues)


def test_v95_markdown_contains_safety_notice() -> None:
    fixture = build_redacted_monthly_portfolio_fixture_v95()
    result = validate_monthly_portfolio_input_v95(fixture, current_month="2026-05")
    md = render_monthly_input_consistency_markdown_v95(fixture, result)
    assert "これは売買指示ではなく" in md
