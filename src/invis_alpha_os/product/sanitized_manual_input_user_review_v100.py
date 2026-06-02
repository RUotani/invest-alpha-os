"""v100 user-facing sanitized/manual input review pack (source-only / fixture-only)."""

from __future__ import annotations

from dataclasses import dataclass

from invis_alpha_os.product.portfolio_context_input_v97 import (
    compute_portfolio_context_allocation_gap_v97,
    validate_portfolio_context_input_v97,
)
from invis_alpha_os.product.sanitized_manual_input_report_connection_v99 import (
    build_sanitized_manual_input_summary_lines_v99,
)
from invis_alpha_os.product.sanitized_manual_input_v98 import (
    SanitizedManualPortfolioInputV98,
    build_redacted_sanitized_manual_input_fixture_v98,
    portfolio_context_from_sanitized_manual_input_v98,
    validate_sanitized_manual_input_v98,
    validate_v95_parity_from_sanitized_manual_input_v98,
)


@dataclass(frozen=True)
class SanitizedManualInputReviewItemV100:
    key: str
    severity: str
    title_ja: str
    detail_ja: str
    next_check_ja: str


@dataclass(frozen=True)
class SanitizedManualInputUserReviewV100:
    as_of_month: str
    overall_severity: str
    headline_ja: str
    safety_note_ja: str
    summary_lines_ja: tuple[str, ...]
    review_items: tuple[SanitizedManualInputReviewItemV100, ...]
    next_actions_ja: tuple[str, ...]


def _asset_ratio(input_data: SanitizedManualPortfolioInputV98, key: str) -> float:
    for asset in input_data.assets:
        if asset.key == key:
            return asset.ratio_pct or 0.0
    return 0.0


def _severity_from_values(*values: str) -> str:
    order = {"ERROR": 3, "WARN": 2, "INFO": 1}
    output = "INFO"
    for value in values:
        upper = value.upper()
        if order.get(upper, 0) > order[output]:
            output = upper
    return output


def build_sanitized_manual_input_user_review_v100(
    input_data: SanitizedManualPortfolioInputV98 | None = None,
) -> SanitizedManualInputUserReviewV100:
    """Build a user-facing review from sanitized/manual inputs without any live or raw-data access."""

    source = input_data or build_redacted_sanitized_manual_input_fixture_v98()
    v98_result = validate_sanitized_manual_input_v98(source, current_month=source.as_of_month)
    v95_result = validate_v95_parity_from_sanitized_manual_input_v98(source)
    portfolio_context = portfolio_context_from_sanitized_manual_input_v98(source)
    v97_result = validate_portfolio_context_input_v97(portfolio_context)
    allocation_gap = compute_portfolio_context_allocation_gap_v97(portfolio_context)
    cash_ratio = _asset_ratio(source, "cash")
    individual_ratio = _asset_ratio(source, "individual_stocks")
    equity_ratio = _asset_ratio(source, "equity_total")

    overall = _severity_from_values(
        v98_result.overall_severity.value,
        v95_result.overall_severity.value,
        v97_result.overall_severity.value,
    )
    review_items = (
        SanitizedManualInputReviewItemV100(
            key="cash_guardrail",
            severity="WARN" if cash_ratio < source.cash_minimum_guardrail_pct else "INFO",
            title_ja="現金比率ガードレール",
            detail_ja=(
                f"現金{cash_ratio:.1f}% は minimum {source.cash_minimum_guardrail_pct:.1f}% 未満、"
                f"preferred {source.cash_preferred_recovery_zone_pct:.1f}% 未満です。"
            ),
            next_check_ja="新規リスク追加より、現金回復余地と今週の見送り条件を確認する。",
        ),
        SanitizedManualInputReviewItemV100(
            key="individual_stock_band",
            severity="WARN" if individual_ratio > source.single_stock_target_max_pct else "INFO",
            title_ja="個別株比率ターゲット",
            detail_ja=(
                f"個別株{individual_ratio:.1f}% は target "
                f"{source.single_stock_target_min_pct:.1f}〜{source.single_stock_target_max_pct:.1f}% を超過しています。"
            ),
            next_check_ja="候補追加ではなく、重複リスク・高ボラ枠・根拠不足枠の整理優先度を確認する。",
        ),
        SanitizedManualInputReviewItemV100(
            key="target_allocation_gap",
            severity="WARN",
            title_ja="目標配分ギャップ",
            detail_ja=(
                f"目標比率との差は cash {allocation_gap.gap_cash_pct:+.1f}pt / "
                f"equity {allocation_gap.gap_equity_pct:+.1f}pt / "
                f"alternative {allocation_gap.gap_alternative_pct:+.1f}pt / "
                f"bond {allocation_gap.gap_bond_pct:+.1f}pt です。"
            ),
            next_check_ja="週次レポートでは、現金不足と株式系過多を候補評価の制約として扱う。",
        ),
        SanitizedManualInputReviewItemV100(
            key="contract_parity",
            severity=overall,
            title_ja="v98/v97/v95 契約整合",
            detail_ja=(
                f"v98={v98_result.overall_severity.value.upper()} / "
                f"v97={v97_result.overall_severity.value.upper()} / "
                f"v95={v95_result.overall_severity.value.upper()}。"
                "WARN は主にガードレール由来で、金額・比率の構造不整合ではありません。"
            ),
            next_check_ja="月次入力を更新したら、同じ redacted/sanitized 契約で再検証する。",
        ),
        SanitizedManualInputReviewItemV100(
            key="raw_data_boundary",
            severity="INFO",
            title_ja="Raw Data Boundary",
            detail_ja="raw Excel / broker export / broker API / actual import / cache write / live HTTP は使用していません。",
            next_check_ja="人間が共有する場合も、redacted summary と比率だけを入力する。",
        ),
    )
    summary_lines = (
        f"対象: {source.as_of_month} / {source.currency} / {source.amount_unit}",
        f"判定: {overall}",
        f"現金: {cash_ratio:.1f}%（minimum {source.cash_minimum_guardrail_pct:.1f}% / preferred {source.cash_preferred_recovery_zone_pct:.1f}%）",
        f"個別株: {individual_ratio:.1f}%（target {source.single_stock_target_min_pct:.1f}〜{source.single_stock_target_max_pct:.1f}%）",
        f"株式系合計: {equity_ratio:.1f}%",
        "v97 Portfolio Context / v95 Monthly Input Consistency と整合",
        *build_sanitized_manual_input_summary_lines_v99(),
    )
    return SanitizedManualInputUserReviewV100(
        as_of_month=source.as_of_month,
        overall_severity=overall,
        headline_ja="現金不足と個別株比率超過を、週次判断の制約として明示するレビューです。",
        safety_note_ja="これは売買指示ではなく、入力整合性・安全確認・根拠補完のためのレビューです。",
        summary_lines_ja=summary_lines,
        review_items=review_items,
        next_actions_ja=(
            "候補0件時も、現金不足・個別株過多・株式系過多を見送り理由として表示する。",
            "週次レポートでは、新規候補より監視・整理・現金回復を優先する制約を残す。",
            "次回の人間入力では、対象月・通貨・単位・比率合計・redaction boundary を確認する。",
        ),
    )


def render_sanitized_manual_input_user_review_summary_lines_v100(
    review: SanitizedManualInputUserReviewV100,
) -> tuple[str, ...]:
    return (
        f"Sanitized User Review: 判定 {review.overall_severity} / {review.as_of_month}",
        review.headline_ja,
        review.safety_note_ja,
    )


def render_sanitized_manual_input_user_review_markdown_v100(
    review: SanitizedManualInputUserReviewV100,
) -> str:
    lines = [
        "# Sanitized / Manual Input User Review",
        "",
        f"- 対象月: {review.as_of_month}",
        f"- 判定: {review.overall_severity}",
        f"- 要約: {review.headline_ja}",
        f"- Safety: {review.safety_note_ja}",
        "",
        "## Summary",
    ]
    lines.extend(f"- {line}" for line in review.summary_lines_ja)
    lines.extend(
        [
            "",
            "## Key Review Items",
            "",
            "| key | severity | review | next check |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in review.review_items:
        lines.append(
            f"| {item.key} | {item.severity} | {item.title_ja}: {item.detail_ja} | {item.next_check_ja} |"
        )
    lines.extend(["", "## Next Checks"])
    lines.extend(f"- {item}" for item in review.next_actions_ja)
    lines.extend(
        [
            "",
            "## Explicit Non-Approval",
            "- provider live access: not executed / not approved",
            "- live HTTP: not executed / not approved",
            "- cache write: not executed / not approved",
            "- actual import: not executed / not approved",
            "- broker API / raw broker export parsing: not executed / not approved",
            "- raw Excel direct parsing: not executed / not approved",
            "- env/secret display: not executed / not approved",
            "- trading action: not executed / not approved",
            "",
        ]
    )
    return "\n".join(lines)
