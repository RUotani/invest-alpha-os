"""v97 Portfolio Context Input Abstraction (source-only / fixture-only)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from invis_alpha_os.product.monthly_input_consistency_v95 import (
    MonthlyAssetClassInputV95,
    MonthlyInputConsistencyResultV95,
    MonthlyPortfolioInputV95,
    render_monthly_input_consistency_summary_lines_v95,
    validate_monthly_portfolio_input_v95,
)


class PortfolioContextSeverityV97(Enum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"


@dataclass(frozen=True)
class PortfolioAssetClassContextV97:
    key: str
    label_ja: str
    amount_man_yen: float
    ratio_pct: float


@dataclass(frozen=True)
class PortfolioGuardrailContextV97:
    cash_minimum_pct: float
    cash_preferred_recovery_pct: float
    single_stock_target_min_pct: float
    single_stock_target_max_pct: float
    target_cash_pct: float
    target_equity_pct: float
    target_alternative_pct: float
    target_bond_pct: float


@dataclass(frozen=True)
class PortfolioContextInputV97:
    as_of_month: str
    currency: str
    amount_unit: str
    total_assets_man_yen: float
    loan_balance_man_yen: float
    net_worth_man_yen: float
    asset_classes: tuple[PortfolioAssetClassContextV97, ...]
    guardrails: PortfolioGuardrailContextV97


@dataclass(frozen=True)
class PortfolioContextIssueV97:
    code: str
    severity: PortfolioContextSeverityV97
    message_ja: str


@dataclass(frozen=True)
class PortfolioContextValidationResultV97:
    as_of_month: str
    overall_severity: PortfolioContextSeverityV97
    issues: tuple[PortfolioContextIssueV97, ...]


@dataclass(frozen=True)
class PortfolioContextAllocationGapV97:
    current_cash_pct: float
    current_equity_pct: float
    current_alternative_pct: float
    current_bond_pct: float
    gap_cash_pct: float
    gap_equity_pct: float
    gap_alternative_pct: float
    gap_bond_pct: float


def build_redacted_portfolio_context_fixture_v97() -> PortfolioContextInputV97:
    return PortfolioContextInputV97(
        as_of_month="2026-05",
        currency="JPY",
        amount_unit="man_yen",
        total_assets_man_yen=4327.9,
        loan_balance_man_yen=3432.0,
        net_worth_man_yen=895.9,
        asset_classes=(
            PortfolioAssetClassContextV97("cash", "現金", 508.2, 11.7),
            PortfolioAssetClassContextV97("index", "INDEX", 2088.2, 48.2),
            PortfolioAssetClassContextV97("individual_stocks", "個別株", 846.3, 19.6),
            PortfolioAssetClassContextV97("equity_total", "株式系合計", 2934.5, 67.8),
            PortfolioAssetClassContextV97("bonds", "債券", 582.7, 13.5),
            PortfolioAssetClassContextV97("gold", "GOLD", 234.5, 5.4),
            PortfolioAssetClassContextV97("crypto_high_beta", "仮想通貨・高ベータ", 57.5, 1.3),
            PortfolioAssetClassContextV97("leverage", "レバ", 10.5, 0.2),
        ),
        guardrails=PortfolioGuardrailContextV97(
            cash_minimum_pct=15.0,
            cash_preferred_recovery_pct=20.0,
            single_stock_target_min_pct=10.0,
            single_stock_target_max_pct=15.0,
            target_cash_pct=30.0,
            target_equity_pct=49.0,
            target_alternative_pct=10.5,
            target_bond_pct=10.5,
        ),
    )


def _asset_map(input_data: PortfolioContextInputV97) -> dict[str, PortfolioAssetClassContextV97]:
    return {x.key: x for x in input_data.asset_classes}


def _overall_severity(issues: list[PortfolioContextIssueV97]) -> PortfolioContextSeverityV97:
    rank = {
        PortfolioContextSeverityV97.ERROR: 3,
        PortfolioContextSeverityV97.WARN: 2,
        PortfolioContextSeverityV97.INFO: 1,
    }
    out = PortfolioContextSeverityV97.INFO
    for item in issues:
        if rank[item.severity] > rank[out]:
            out = item.severity
    return out


def validate_portfolio_context_input_v97(
    input_data: PortfolioContextInputV97,
    *,
    amount_tolerance_man_yen: float = 0.2,
    ratio_tolerance_pct: float = 0.2,
) -> PortfolioContextValidationResultV97:
    issues: list[PortfolioContextIssueV97] = []
    assets = _asset_map(input_data)
    required_keys = (
        "cash",
        "index",
        "individual_stocks",
        "equity_total",
        "bonds",
        "gold",
        "crypto_high_beta",
        "leverage",
    )
    for key in required_keys:
        if key not in assets:
            issues.append(
                PortfolioContextIssueV97(
                    code="missing_required_asset_class",
                    severity=PortfolioContextSeverityV97.ERROR,
                    message_ja=f"必須資産クラス {key} が欠損しています。",
                )
            )
    if input_data.amount_unit != "man_yen":
        issues.append(
            PortfolioContextIssueV97(
                code="amount_unit_contract",
                severity=PortfolioContextSeverityV97.ERROR,
                message_ja=f"amount_unit={input_data.amount_unit!r}。man_yen 契約に一致しません。",
            )
        )
    expected_net = input_data.total_assets_man_yen - input_data.loan_balance_man_yen
    if abs(expected_net - input_data.net_worth_man_yen) > amount_tolerance_man_yen:
        issues.append(
            PortfolioContextIssueV97(
                code="net_worth_mismatch",
                severity=PortfolioContextSeverityV97.ERROR,
                message_ja="総資産-ローン残高と純資産が一致しません。",
            )
        )
    if all(key in assets for key in required_keys):
        leaf_total = (
            assets["cash"].amount_man_yen
            + assets["index"].amount_man_yen
            + assets["individual_stocks"].amount_man_yen
            + assets["bonds"].amount_man_yen
            + assets["gold"].amount_man_yen
            + assets["crypto_high_beta"].amount_man_yen
            + assets["leverage"].amount_man_yen
        )
        if abs(leaf_total - input_data.total_assets_man_yen) > amount_tolerance_man_yen:
            issues.append(
                PortfolioContextIssueV97(
                    code="asset_total_mismatch",
                    severity=PortfolioContextSeverityV97.ERROR,
                    message_ja="資産分類合計と総資産が一致しません。",
                )
            )
        leaf_ratio_total = (
            assets["cash"].ratio_pct
            + assets["index"].ratio_pct
            + assets["individual_stocks"].ratio_pct
            + assets["bonds"].ratio_pct
            + assets["gold"].ratio_pct
            + assets["crypto_high_beta"].ratio_pct
            + assets["leverage"].ratio_pct
        )
        if abs(leaf_ratio_total - 100.0) > ratio_tolerance_pct:
            issues.append(
                PortfolioContextIssueV97(
                    code="allocation_ratio_total_mismatch",
                    severity=PortfolioContextSeverityV97.ERROR,
                    message_ja="資産分類比率合計が100%から乖離しています。",
                )
            )
        if abs((assets["index"].amount_man_yen + assets["individual_stocks"].amount_man_yen) - assets["equity_total"].amount_man_yen) > amount_tolerance_man_yen:
            issues.append(
                PortfolioContextIssueV97(
                    code="equity_total_mismatch",
                    severity=PortfolioContextSeverityV97.ERROR,
                    message_ja="INDEX+個別株と株式系合計が一致しません。",
                )
            )
        if assets["cash"].ratio_pct < input_data.guardrails.cash_minimum_pct:
            issues.append(
                PortfolioContextIssueV97(
                    code="cash_below_minimum_guardrail",
                    severity=PortfolioContextSeverityV97.WARN,
                    message_ja=(
                        f"現金比率{assets['cash'].ratio_pct:.1f}% は minimum "
                        f"{input_data.guardrails.cash_minimum_pct:.1f}% 未満です。"
                    ),
                )
            )
        if assets["cash"].ratio_pct < input_data.guardrails.cash_preferred_recovery_pct:
            issues.append(
                PortfolioContextIssueV97(
                    code="cash_below_preferred_recovery_zone",
                    severity=PortfolioContextSeverityV97.INFO,
                    message_ja=(
                        f"現金比率{assets['cash'].ratio_pct:.1f}% は preferred "
                        f"{input_data.guardrails.cash_preferred_recovery_pct:.1f}% 未満です。"
                    ),
                )
            )
        if assets["individual_stocks"].ratio_pct > input_data.guardrails.single_stock_target_max_pct:
            issues.append(
                PortfolioContextIssueV97(
                    code="single_stock_above_target_band",
                    severity=PortfolioContextSeverityV97.WARN,
                    message_ja=(
                        f"個別株比率{assets['individual_stocks'].ratio_pct:.1f}% は target "
                        f"{input_data.guardrails.single_stock_target_min_pct:.1f}〜"
                        f"{input_data.guardrails.single_stock_target_max_pct:.1f}% を超えています。"
                    ),
                )
            )
    return PortfolioContextValidationResultV97(
        as_of_month=input_data.as_of_month,
        overall_severity=_overall_severity(issues),
        issues=tuple(issues),
    )


def compute_portfolio_context_allocation_gap_v97(
    input_data: PortfolioContextInputV97,
) -> PortfolioContextAllocationGapV97:
    assets = _asset_map(input_data)
    current_cash = assets["cash"].ratio_pct
    current_equity = assets["equity_total"].ratio_pct
    current_alternative = assets["gold"].ratio_pct + assets["crypto_high_beta"].ratio_pct + assets["leverage"].ratio_pct
    current_bond = assets["bonds"].ratio_pct
    return PortfolioContextAllocationGapV97(
        current_cash_pct=current_cash,
        current_equity_pct=current_equity,
        current_alternative_pct=current_alternative,
        current_bond_pct=current_bond,
        gap_cash_pct=current_cash - input_data.guardrails.target_cash_pct,
        gap_equity_pct=current_equity - input_data.guardrails.target_equity_pct,
        gap_alternative_pct=current_alternative - input_data.guardrails.target_alternative_pct,
        gap_bond_pct=current_bond - input_data.guardrails.target_bond_pct,
    )


def monthly_input_from_portfolio_context_v97(
    input_data: PortfolioContextInputV97,
) -> MonthlyPortfolioInputV95:
    assets = _asset_map(input_data)
    return MonthlyPortfolioInputV95(
        as_of_month=input_data.as_of_month,
        amount_unit="万円",
        total_assets_10k_yen=input_data.total_assets_man_yen,
        loan_balance_10k_yen=input_data.loan_balance_man_yen,
        net_worth_10k_yen=input_data.net_worth_man_yen,
        cash=MonthlyAssetClassInputV95("現金", assets["cash"].amount_man_yen, assets["cash"].ratio_pct),
        index=MonthlyAssetClassInputV95("INDEX", assets["index"].amount_man_yen, assets["index"].ratio_pct),
        individual_stocks=MonthlyAssetClassInputV95(
            "個別株",
            assets["individual_stocks"].amount_man_yen,
            assets["individual_stocks"].ratio_pct,
        ),
        equity_total=MonthlyAssetClassInputV95(
            "株式系合計",
            assets["equity_total"].amount_man_yen,
            assets["equity_total"].ratio_pct,
        ),
        bonds=MonthlyAssetClassInputV95("債券", assets["bonds"].amount_man_yen, assets["bonds"].ratio_pct),
        gold=MonthlyAssetClassInputV95("GOLD", assets["gold"].amount_man_yen, assets["gold"].ratio_pct),
        crypto_high_beta=MonthlyAssetClassInputV95(
            "仮想通貨・高ベータ",
            assets["crypto_high_beta"].amount_man_yen,
            assets["crypto_high_beta"].ratio_pct,
        ),
        leverage=MonthlyAssetClassInputV95("レバ", assets["leverage"].amount_man_yen, assets["leverage"].ratio_pct),
        cash_minimum_guardrail_pct=input_data.guardrails.cash_minimum_pct,
        cash_preferred_recovery_zone_pct=input_data.guardrails.cash_preferred_recovery_pct,
        single_stock_target_band_low_pct=input_data.guardrails.single_stock_target_min_pct,
        single_stock_target_band_high_pct=input_data.guardrails.single_stock_target_max_pct,
    )


def render_portfolio_context_summary_lines_v97(
    input_data: PortfolioContextInputV97,
    validation_result: PortfolioContextValidationResultV97,
    allocation_gap: PortfolioContextAllocationGapV97,
    *,
    monthly_result_v95: MonthlyInputConsistencyResultV95 | None = None,
) -> tuple[str, ...]:
    monthly_line = ""
    if monthly_result_v95 is not None:
        monthly_line = f"- v95整合: {monthly_result_v95.overall_severity.value.upper()}"
    return (
        (
            f"- Portfolio Context（v97）: {input_data.as_of_month} / "
            f"総資産{input_data.total_assets_man_yen:.1f}万円 / 純資産{input_data.net_worth_man_yen:.1f}万円"
        ),
        (
            f"- 現金{_asset_map(input_data)['cash'].ratio_pct:.1f}% "
            f"(minimum {input_data.guardrails.cash_minimum_pct:.1f}% / preferred {input_data.guardrails.cash_preferred_recovery_pct:.1f}%)"
        ),
        (
            f"- 個別株{_asset_map(input_data)['individual_stocks'].ratio_pct:.1f}% "
            f"(target {input_data.guardrails.single_stock_target_min_pct:.1f}〜{input_data.guardrails.single_stock_target_max_pct:.1f}%)"
        ),
        (
            f"- 目標配分ギャップ: cash {allocation_gap.gap_cash_pct:+.1f}pt / "
            f"equity {allocation_gap.gap_equity_pct:+.1f}pt / "
            f"alternative {allocation_gap.gap_alternative_pct:+.1f}pt / bond {allocation_gap.gap_bond_pct:+.1f}pt"
        ),
        f"- 判定: {validation_result.overall_severity.value.upper()}",
        monthly_line if monthly_line else "- v95整合: 参照なし",
    )


def render_portfolio_context_summary_markdown_v97(
    input_data: PortfolioContextInputV97,
    validation_result: PortfolioContextValidationResultV97,
    allocation_gap: PortfolioContextAllocationGapV97,
    *,
    monthly_result_v95: MonthlyInputConsistencyResultV95 | None = None,
) -> str:
    lines = [
        "## Portfolio Context Input Summary v97",
        "",
        *render_portfolio_context_summary_lines_v97(
            input_data,
            validation_result,
            allocation_gap,
            monthly_result_v95=monthly_result_v95,
        ),
        "",
        "### 検出事項",
    ]
    if validation_result.issues:
        for issue in validation_result.issues:
            lines.append(f"- [{issue.severity.value.upper()}] {issue.code}: {issue.message_ja}")
    else:
        lines.append("- 問題は検出されませんでした。")
    if monthly_result_v95 is not None:
        lines.extend(["", "### v95 Summary Mirror"])
        lines.extend(render_monthly_input_consistency_summary_lines_v95(monthly_input_from_portfolio_context_v97(input_data), monthly_result_v95))
    lines.extend(
        [
            "",
            "これは売買指示ではなく、portfolio context入力契約とguardrail整合性の確認です。",
            "",
        ]
    )
    return "\n".join(lines)


def validate_v95_consistency_from_portfolio_context_v97(
    input_data: PortfolioContextInputV97,
) -> MonthlyInputConsistencyResultV95:
    monthly_input = monthly_input_from_portfolio_context_v97(input_data)
    return validate_monthly_portfolio_input_v95(monthly_input, current_month=input_data.as_of_month)
