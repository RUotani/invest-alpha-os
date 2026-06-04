"""Source-only portfolio data-quality review built from sanitized fixtures."""

from __future__ import annotations

from dataclasses import dataclass

from invis_alpha_os.product import portfolio_input, report_view_model
from invis_alpha_os.product.validation_issue_taxonomy import (
    ValidationIssueCategory,
    get_validation_issue_category,
    normalize_validation_issue_key,
)


@dataclass(frozen=True)
class PortfolioDataQualityReviewItemV109:
    key: str
    severity: str
    category: str
    title_ja: str
    detail_ja: str
    why_it_matters_ja: str
    next_check_ja: str


@dataclass(frozen=True)
class PortfolioDataQualityReviewV109:
    as_of_month: str
    overall_severity: str
    source_mode: str
    summary_lines_ja: tuple[str, ...]
    review_items: tuple[PortfolioDataQualityReviewItemV109, ...]
    manual_confirmation_items_ja: tuple[str, ...]
    safety_note_ja: str


_SEVERITY_RANK = {"ERROR": 3, "WARN": 2, "INFO": 1}


def _asset_map(
    input_data: portfolio_input.SanitizedManualPortfolioInput,
) -> dict[str, portfolio_input.SanitizedManualAssetInput]:
    return {asset.key: asset for asset in input_data.assets}


def _category(key: str, fallback: ValidationIssueCategory) -> str:
    category = get_validation_issue_category(key)
    return (category or fallback).value


def _severity_for_meaning(
    key: str,
    issue_severities: dict[str, set[str]],
) -> str:
    severities = issue_severities.get(normalize_validation_issue_key(key), set())
    return max(severities, key=lambda value: _SEVERITY_RANK[value], default="INFO")


def _severity_for_meanings(
    keys: tuple[str, ...],
    issue_severities: dict[str, set[str]],
) -> str:
    severities = {
        severity
        for key in keys
        for severity in issue_severities.get(normalize_validation_issue_key(key), set())
    }
    return max(severities, key=lambda value: _SEVERITY_RANK[value], default="INFO")


def _structural_item(
    *,
    key: str,
    issue_severities: dict[str, set[str]],
    title_ja: str,
    detail_ja: str,
    why_it_matters_ja: str,
    next_check_ja: str,
    fallback_category: ValidationIssueCategory,
    related_keys: tuple[str, ...] = (),
) -> PortfolioDataQualityReviewItemV109:
    severity = _severity_for_meanings((key, *related_keys), issue_severities)
    status = "整合確認済み" if severity == "INFO" else "不整合を検出"
    return PortfolioDataQualityReviewItemV109(
        key=normalize_validation_issue_key(key),
        severity=severity,
        category=_category(key, fallback_category),
        title_ja=title_ja,
        detail_ja=f"{status}: {detail_ja}",
        why_it_matters_ja=why_it_matters_ja,
        next_check_ja=next_check_ja,
    )


def build_portfolio_data_quality_review_v109(
    input_data: portfolio_input.SanitizedManualPortfolioInput | None = None,
) -> PortfolioDataQualityReviewV109:
    """Build a fixture/manual-input quality review without raw-data or live access."""

    source = input_data or portfolio_input.build_redacted_sanitized_manual_input_fixture()
    assets = _asset_map(source)
    v98_result = portfolio_input.validate_sanitized_manual_input(source, current_month=source.as_of_month)
    context = portfolio_input.portfolio_context_from_sanitized_manual_input(source)
    v97_result = portfolio_input.validate_portfolio_context_input(context)
    monthly = portfolio_input.monthly_input_from_sanitized_manual_input(source)
    v95_result = portfolio_input.validate_monthly_input_consistency(monthly, current_month=source.as_of_month)
    allocation_gap = portfolio_input.compute_portfolio_context_allocation_gap(context)
    v100_review = report_view_model.build_sanitized_manual_input_user_review(source)

    issue_severities: dict[str, set[str]] = {}
    for result in (v98_result, v97_result, v95_result):
        for issue in result.issues:
            key = normalize_validation_issue_key(issue.code)
            issue_severities.setdefault(key, set()).add(issue.severity.value.upper())

    cash_ratio = assets["cash"].ratio_pct or 0.0
    individual_ratio = assets["individual_stocks"].ratio_pct or 0.0
    equity_ratio = assets["equity_total"].ratio_pct or 0.0
    ratio_total = sum(
        (asset.ratio_pct or 0.0)
        for asset in source.assets
        if asset.key != "equity_total"
    )
    leaf_total = sum(
        asset.amount_man_yen
        for asset in source.assets
        if asset.key != "equity_total"
    )

    review_items = (
        _structural_item(
            key="invalid_amount_unit",
            issue_severities=issue_severities,
            title_ja="金額単位",
            detail_ja=f"currency={source.currency} / amount_unit={source.amount_unit}",
            why_it_matters_ja="単位誤認は全ての資産額・純資産評価を壊します。",
            next_check_ja="人間入力時にJPY / man_yen契約を再確認する。",
            fallback_category=ValidationIssueCategory.UNIT,
            related_keys=("invalid_currency",),
        ),
        _structural_item(
            key="net_worth_mismatch",
            issue_severities=issue_severities,
            title_ja="純資産整合",
            detail_ja=(
                f"総資産{source.total_assets_man_yen:.1f} - ローン{source.loan_balance_man_yen:.1f} "
                f"= 純資産{source.net_worth_man_yen:.1f}万円"
            ),
            why_it_matters_ja="純資産不整合は配分比率とリスク余力の前提を歪めます。",
            next_check_ja="総資産・ローン残高・純資産の同一時点性を確認する。",
            fallback_category=ValidationIssueCategory.AMOUNT,
        ),
        _structural_item(
            key="asset_total_mismatch",
            issue_severities=issue_severities,
            title_ja="資産分類合計",
            detail_ja=f"資産分類合計{leaf_total:.1f} / 総資産{source.total_assets_man_yen:.1f}万円",
            why_it_matters_ja="分類漏れや二重計上はportfolio制約判定を誤らせます。",
            next_check_ja="資産分類の漏れ・重複がないことを確認する。",
            fallback_category=ValidationIssueCategory.AMOUNT,
        ),
        _structural_item(
            key="ratio_total_mismatch",
            issue_severities=issue_severities,
            title_ja="比率合計",
            detail_ja=f"資産分類比率合計{ratio_total:.1f}%",
            why_it_matters_ja="比率合計の不整合は配分ギャップ評価を無効にします。",
            next_check_ja="丸め差を除き100%へ整合することを確認する。",
            fallback_category=ValidationIssueCategory.RATIO,
        ),
        _structural_item(
            key="equity_total_mismatch",
            issue_severities=issue_severities,
            title_ja="株式系合計",
            detail_ja=(
                f"INDEX{assets['index'].amount_man_yen:.1f} + 個別株{assets['individual_stocks'].amount_man_yen:.1f} "
                f"= 株式系合計{assets['equity_total'].amount_man_yen:.1f}万円"
            ),
            why_it_matters_ja="株式系合計はportfolio risk制約の主要入力です。",
            next_check_ja="INDEXと個別株の分類境界を確認する。",
            fallback_category=ValidationIssueCategory.EQUITY,
        ),
        PortfolioDataQualityReviewItemV109(
            key="cash_below_minimum_guardrail",
            severity=_severity_for_meaning("cash_below_minimum_guardrail", issue_severities),
            category=ValidationIssueCategory.GUARDRAIL.value,
            title_ja="現金比率ガードレール",
            detail_ja=f"現金{cash_ratio:.1f}% / minimum {source.cash_minimum_guardrail_pct:.1f}%",
            why_it_matters_ja="現金不足は新規リスク追加余力を制限します。",
            next_check_ja="最新入力でもminimum未満かを人間が確認する。",
        ),
        PortfolioDataQualityReviewItemV109(
            key="single_stock_above_target_band",
            severity=_severity_for_meaning("single_stock_above_target_band", issue_severities),
            category=ValidationIssueCategory.GUARDRAIL.value,
            title_ja="個別株比率ガードレール",
            detail_ja=f"個別株{individual_ratio:.1f}% / target max {source.single_stock_target_max_pct:.1f}%",
            why_it_matters_ja="個別株比率超過は集中・高ボラリスクを増やします。",
            next_check_ja="最新入力と分類定義で超過が継続しているか確認する。",
        ),
        PortfolioDataQualityReviewItemV109(
            key="target_allocation_gap",
            severity="WARN",
            category=ValidationIssueCategory.RATIO.value,
            title_ja="目標配分ギャップ",
            detail_ja=(
                f"cash {allocation_gap.gap_cash_pct:+.1f}pt / equity {allocation_gap.gap_equity_pct:+.1f}pt / "
                f"alternative {allocation_gap.gap_alternative_pct:+.1f}pt / bond {allocation_gap.gap_bond_pct:+.1f}pt"
            ),
            why_it_matters_ja="目標配分との差は候補評価時のportfolio制約です。",
            next_check_ja="目標比率と現在比率が同じ分類ルールか確認する。",
        ),
    )
    overall = max((item.severity for item in review_items), key=lambda value: _SEVERITY_RANK[value])
    return PortfolioDataQualityReviewV109(
        as_of_month=source.as_of_month,
        overall_severity=overall,
        source_mode="fixture_or_sanitized_manual_only",
        summary_lines_ja=(
            f"判定: {overall} / 対象月: {source.as_of_month}",
            f"現金{cash_ratio:.1f}% / 個別株{individual_ratio:.1f}% / 株式系合計{equity_ratio:.1f}%",
            f"v98={v98_result.overall_severity.value.upper()} / v97={v97_result.overall_severity.value.upper()} / "
            f"v95={v95_result.overall_severity.value.upper()} / v100={v100_review.overall_severity}",
            "構造整合、guardrail、目標配分ギャップ、manual confirmationを横断レビュー",
        ),
        review_items=review_items,
        manual_confirmation_items_ja=(
            f"対象月{source.as_of_month}が最新portfolio inputか確認する。",
            f"currency={source.currency} / amount_unit={source.amount_unit}が共有契約と一致するか確認する。",
            "総資産・ローン残高・純資産・各資産分類が同一時点の値か確認する。",
            "raw Excel / broker exportを直接解析せず、redacted/sanitized入力であることを確認する。",
        ),
        safety_note_ja="これは売買指示ではなく、portfolio入力品質と配分上の注意を確認するレビューです。",
    )


def render_portfolio_data_quality_review_summary_lines_v109(
    review: PortfolioDataQualityReviewV109,
) -> tuple[str, ...]:
    return (
        f"Portfolio Data Quality: {review.overall_severity} / {review.as_of_month}",
        *review.summary_lines_ja[1:],
        review.safety_note_ja,
    )


def render_portfolio_data_quality_review_markdown_v109(
    review: PortfolioDataQualityReviewV109,
) -> str:
    lines = [
        "# Portfolio Data Quality Review",
        "",
        f"- 対象月: {review.as_of_month}",
        f"- 判定: {review.overall_severity}",
        f"- source_mode: {review.source_mode}",
        f"- Safety: {review.safety_note_ja}",
        "",
        "## Review Items",
        "",
        "| key | severity | category | review | next check |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        f"| {item.key} | {item.severity} | {item.category} | "
        f"{item.title_ja}: {item.detail_ja} {item.why_it_matters_ja} | {item.next_check_ja} |"
        for item in review.review_items
    )
    lines.extend(["", "## Manual Confirmation Items"])
    lines.extend(f"- {item}" for item in review.manual_confirmation_items_ja)
    lines.extend(
        [
            "",
            "## Explicit Non-Approval",
            "- live HTTP / provider access: not executed / not approved",
            "- cache write / actual import: not executed / not approved",
            "- broker API / raw Excel direct parsing: not executed / not approved",
            "- trading action / real email send: not executed / not approved",
            "",
        ]
    )
    return "\n".join(lines)
