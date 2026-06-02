from __future__ import annotations

from invis_alpha_os.product.sanitized_manual_input_user_review_v100 import (
    build_sanitized_manual_input_user_review_v100,
    render_sanitized_manual_input_user_review_markdown_v100,
    render_sanitized_manual_input_user_review_summary_lines_v100,
)


def test_v100_builds_user_review_from_redacted_fixture() -> None:
    review = build_sanitized_manual_input_user_review_v100()

    assert review.as_of_month == "2026-05"
    assert review.overall_severity == "WARN"
    assert "現金不足" in review.headline_ja
    assert "これは売買指示ではなく" in review.safety_note_ja


def test_v100_review_items_explain_cash_and_individual_stock_guardrails() -> None:
    review = build_sanitized_manual_input_user_review_v100()
    item_by_key = {item.key: item for item in review.review_items}

    cash = item_by_key["cash_guardrail"]
    assert cash.severity == "WARN"
    assert "現金11.7%" in cash.detail_ja
    assert "minimum 15.0%" in cash.detail_ja
    assert "preferred 20.0%" in cash.detail_ja

    individual = item_by_key["individual_stock_band"]
    assert individual.severity == "WARN"
    assert "個別株19.6%" in individual.detail_ja
    assert "target 10.0〜15.0%" in individual.detail_ja


def test_v100_preserves_v97_v95_v99_parity_without_contradiction() -> None:
    review = build_sanitized_manual_input_user_review_v100()
    joined = "\n".join(review.summary_lines_ja)

    assert "v97 Portfolio Context / v95 Monthly Input Consistency と整合" in joined
    assert "Sanitized Input: 判定 WARN / 2026-05 / JPY / man_yen" in joined
    assert "Sanitized Guardrail: 現金11.7%はminimum 15.0%未満" in joined
    assert "v97=WARN / v95=WARN" in "\n".join(item.detail_ja for item in review.review_items)


def test_v100_markdown_is_user_facing_and_safety_bounded() -> None:
    review = build_sanitized_manual_input_user_review_v100()
    markdown = render_sanitized_manual_input_user_review_markdown_v100(review)

    assert markdown.startswith("# Sanitized / Manual Input User Review")
    assert "## Key Review Items" in markdown
    assert "## Next Checks" in markdown
    assert "これは売買指示ではなく、入力整合性・安全確認・根拠補完のためのレビューです。" in markdown
    assert "raw Excel direct parsing: not executed / not approved" in markdown
    assert "broker API / raw broker export parsing: not executed / not approved" in markdown
    assert "cache write: not executed / not approved" in markdown
    assert "trading action: not executed / not approved" in markdown
    assert "注文実行" not in markdown
    assert "今すぐ購入" not in markdown


def test_v100_summary_lines_are_short_for_report_connection() -> None:
    review = build_sanitized_manual_input_user_review_v100()
    lines = render_sanitized_manual_input_user_review_summary_lines_v100(review)

    assert lines[0] == "Sanitized User Review: 判定 WARN / 2026-05"
    assert len(lines) == 3
    assert "売買指示ではなく" in lines[2]
