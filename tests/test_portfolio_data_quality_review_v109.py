from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from invis_alpha_os.product import portfolio_input
from invis_alpha_os.product.portfolio_data_quality_review_v109 import (
    build_portfolio_data_quality_review_v109,
    render_portfolio_data_quality_review_markdown_v109,
    render_portfolio_data_quality_review_summary_lines_v109,
)


def test_v109_builds_fixture_only_warn_review() -> None:
    review = build_portfolio_data_quality_review_v109()
    assert review.as_of_month == "2026-05"
    assert review.source_mode == "fixture_or_sanitized_manual_only"
    assert review.overall_severity == "WARN"


def test_v109_reviews_cash_single_stock_and_target_gap() -> None:
    review = build_portfolio_data_quality_review_v109()
    items = {item.key: item for item in review.review_items}
    assert items["cash_below_minimum_guardrail"].severity == "WARN"
    assert "現金11.7% / minimum 15.0%" in items["cash_below_minimum_guardrail"].detail_ja
    assert items["single_stock_above_target_band"].severity == "WARN"
    assert "個別株19.6% / target max 15.0%" in items["single_stock_above_target_band"].detail_ja
    assert "cash -18.3pt / equity +18.8pt" in items["target_allocation_gap"].detail_ja


def test_v109_reviews_structural_consistency_across_existing_validators() -> None:
    review = build_portfolio_data_quality_review_v109()
    items = {item.key: item for item in review.review_items}
    for key in ("invalid_amount_unit", "net_worth_mismatch", "asset_total_mismatch", "ratio_total_mismatch", "equity_total_mismatch"):
        assert items[key].severity == "INFO"
        assert items[key].detail_ja.startswith("整合確認済み:")


def test_v109_surfaces_existing_validation_failure_without_changing_validator() -> None:
    fixture = portfolio_input.build_redacted_sanitized_manual_input_fixture()
    invalid = replace(fixture, net_worth_man_yen=fixture.net_worth_man_yen + 10.0)
    review = build_portfolio_data_quality_review_v109(invalid)
    item = {entry.key: entry for entry in review.review_items}["net_worth_mismatch"]
    assert review.overall_severity == "ERROR"
    assert item.severity == "ERROR"
    assert item.detail_ja.startswith("不整合を検出:")


def test_v109_surfaces_invalid_currency_in_unit_review() -> None:
    fixture = portfolio_input.build_redacted_sanitized_manual_input_fixture()
    invalid = replace(fixture, currency="USD")
    review = build_portfolio_data_quality_review_v109(invalid)
    item = {entry.key: entry for entry in review.review_items}["invalid_amount_unit"]
    assert review.overall_severity == "ERROR"
    assert item.severity == "ERROR"
    assert "currency=USD" in item.detail_ja


def test_v109_manual_confirmation_items_cover_freshness_unit_and_boundary() -> None:
    review = build_portfolio_data_quality_review_v109()
    joined = "\n".join(review.manual_confirmation_items_ja)
    assert "対象月2026-05が最新portfolio inputか確認" in joined
    assert "currency=JPY / amount_unit=man_yen" in joined
    assert "同一時点" in joined
    assert "raw Excel / broker exportを直接解析せず" in joined


def test_v109_markdown_is_quality_review_not_trade_instruction() -> None:
    markdown = render_portfolio_data_quality_review_markdown_v109(build_portfolio_data_quality_review_v109())
    assert markdown.startswith("# Portfolio Data Quality Review")
    assert "これは売買指示ではなく" in markdown
    assert "actual import: not executed / not approved" in markdown
    assert "raw Excel direct parsing: not executed / not approved" in markdown
    assert "今すぐ購入" not in markdown
    assert "注文実行" not in markdown


def test_v109_summary_lines_are_report_ready() -> None:
    lines = render_portfolio_data_quality_review_summary_lines_v109(build_portfolio_data_quality_review_v109())
    assert lines[0] == "Portfolio Data Quality: WARN / 2026-05"
    assert "現金11.7% / 個別株19.6% / 株式系合計67.8%" in lines[1]
    assert "売買指示ではなく" in lines[-1]


def test_v109_module_has_no_forbidden_execution_paths() -> None:
    text = Path("src/invis_alpha_os/product/portfolio_data_quality_review_v109.py").read_text(encoding="utf-8").lower()
    forbidden = ("requests.", "urllib", "workflow_dispatch", "cache_write(", "actual_import(", "broker_api", "raw_excel", "send_gmail", "order_placement")
    assert all(term not in text for term in forbidden)
