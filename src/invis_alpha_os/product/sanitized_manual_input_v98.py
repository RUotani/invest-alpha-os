"""v98 Sanitized / Manual Input Preparation (source-only / fixture-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from invis_alpha_os.product.monthly_input_consistency_v95 import (
    MonthlyInputConsistencyResultV95,
    MonthlyPortfolioInputV95,
    validate_monthly_portfolio_input_v95,
)
from invis_alpha_os.product.portfolio_context_input_v97 import (
    PortfolioAssetClassContextV97,
    PortfolioContextInputV97,
    PortfolioGuardrailContextV97,
    monthly_input_from_portfolio_context_v97,
)


class SanitizedManualSeverityV98(Enum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"


@dataclass(frozen=True)
class SanitizedManualAssetInputV98:
    key: str
    label_ja: str
    amount_man_yen: float
    ratio_pct: float | None = None


@dataclass(frozen=True)
class SanitizedManualPortfolioInputV98:
    as_of_month: str
    currency: str
    amount_unit: str
    total_assets_man_yen: float
    loan_balance_man_yen: float
    net_worth_man_yen: float
    assets: tuple[SanitizedManualAssetInputV98, ...]
    source_kind: str
    redaction_level: str
    notes_ja: tuple[str, ...]
    cash_minimum_guardrail_pct: float = 15.0
    cash_preferred_recovery_zone_pct: float = 20.0
    single_stock_target_min_pct: float = 10.0
    single_stock_target_max_pct: float = 15.0
    target_cash_pct: float = 30.0
    target_equity_pct: float = 49.0
    target_alternative_pct: float = 10.5
    target_bond_pct: float = 10.5


@dataclass(frozen=True)
class SanitizedManualIssueV98:
    code: str
    severity: SanitizedManualSeverityV98
    message_ja: str


@dataclass(frozen=True)
class SanitizedManualValidationResultV98:
    as_of_month: str
    overall_severity: SanitizedManualSeverityV98
    issues: tuple[SanitizedManualIssueV98, ...]


_REQUIRED_KEYS: tuple[str, ...] = (
    "cash",
    "index",
    "individual_stocks",
    "equity_total",
    "bonds",
    "gold",
    "crypto_high_beta",
    "leverage",
)
_KNOWN_KEYS: tuple[str, ...] = _REQUIRED_KEYS


def build_redacted_sanitized_manual_input_fixture_v98() -> SanitizedManualPortfolioInputV98:
    return SanitizedManualPortfolioInputV98(
        as_of_month="2026-05",
        currency="JPY",
        amount_unit="man_yen",
        total_assets_man_yen=4327.9,
        loan_balance_man_yen=3432.0,
        net_worth_man_yen=895.9,
        assets=(
            SanitizedManualAssetInputV98("cash", "現金", 508.2, 11.7),
            SanitizedManualAssetInputV98("index", "INDEX", 2088.2, 48.2),
            SanitizedManualAssetInputV98("individual_stocks", "個別株", 846.3, 19.6),
            SanitizedManualAssetInputV98("equity_total", "株式系合計", 2934.5, 67.8),
            SanitizedManualAssetInputV98("bonds", "債券", 582.7, 13.5),
            SanitizedManualAssetInputV98("gold", "GOLD", 234.5, 5.4),
            SanitizedManualAssetInputV98("crypto_high_beta", "仮想通貨・高ベータ", 57.5, 1.3),
            SanitizedManualAssetInputV98("leverage", "レバ", 10.5, 0.2),
        ),
        source_kind="manual_sanitized",
        redaction_level="strict_redacted",
        notes_ja=(
            "raw Excel / broker export / actual import は使用しない。",
            "manual/sanitized contract のみで v97/v95 へ変換する。",
        ),
    )


def _asset_map(input_data: SanitizedManualPortfolioInputV98) -> dict[str, SanitizedManualAssetInputV98]:
    return {x.key: x for x in input_data.assets}


def _parse_month(month: str) -> tuple[int, int] | None:
    parts = month.split("-")
    if len(parts) != 2 or (not parts[0].isdigit()) or (not parts[1].isdigit()):
        return None
    year, mon = int(parts[0]), int(parts[1])
    if mon < 1 or mon > 12:
        return None
    return year, mon


def _month_index(year: int, mon: int) -> int:
    return year * 12 + mon


def _overall_severity(issues: list[SanitizedManualIssueV98]) -> SanitizedManualSeverityV98:
    rank = {
        SanitizedManualSeverityV98.ERROR: 3,
        SanitizedManualSeverityV98.WARN: 2,
        SanitizedManualSeverityV98.INFO: 1,
    }
    out = SanitizedManualSeverityV98.INFO
    for issue in issues:
        if rank[issue.severity] > rank[out]:
            out = issue.severity
    return out


def validate_sanitized_manual_input_v98(
    input_data: SanitizedManualPortfolioInputV98,
    *,
    current_month: str | None = None,
    amount_tolerance_man_yen: float = 0.2,
    ratio_tolerance_pct: float = 0.2,
) -> SanitizedManualValidationResultV98:
    issues: list[SanitizedManualIssueV98] = []
    parsed = _parse_month(input_data.as_of_month)
    if parsed is None:
        issues.append(
            SanitizedManualIssueV98(
                code="missing_as_of_month",
                severity=SanitizedManualSeverityV98.ERROR,
                message_ja="as_of_month が欠損または形式不正です（YYYY-MM）。",
            )
        )
    else:
        if current_month is None:
            today = date.today()
            current_index = _month_index(today.year, today.month)
        else:
            cur = _parse_month(current_month)
            if cur is None:
                raise ValueError(f"invalid current_month format: {current_month!r}")
            current_index = _month_index(cur[0], cur[1])
        input_index = _month_index(parsed[0], parsed[1])
        if input_index > current_index:
            issues.append(
                SanitizedManualIssueV98(
                    code="future_as_of_month",
                    severity=SanitizedManualSeverityV98.ERROR,
                    message_ja=f"as_of_month={input_data.as_of_month} は未来月です。",
                )
            )
    if input_data.currency != "JPY":
        issues.append(
            SanitizedManualIssueV98(
                code="invalid_currency",
                severity=SanitizedManualSeverityV98.ERROR,
                message_ja=f"currency={input_data.currency!r}。JPYのみ許可されます。",
            )
        )
    if input_data.amount_unit != "man_yen":
        issues.append(
            SanitizedManualIssueV98(
                code="invalid_amount_unit",
                severity=SanitizedManualSeverityV98.ERROR,
                message_ja=f"amount_unit={input_data.amount_unit!r}。man_yenのみ許可されます。",
            )
        )
    keys = [x.key for x in input_data.assets]
    if len(keys) != len(set(keys)):
        issues.append(
            SanitizedManualIssueV98(
                code="duplicate_asset_key",
                severity=SanitizedManualSeverityV98.ERROR,
                message_ja="asset key が重複しています。",
            )
        )
    for key in keys:
        if key not in _KNOWN_KEYS:
            issues.append(
                SanitizedManualIssueV98(
                    code="unknown_asset_key",
                    severity=SanitizedManualSeverityV98.ERROR,
                    message_ja=f"未知のasset keyです: {key}",
                )
            )
    for key in _REQUIRED_KEYS:
        if key not in keys:
            issues.append(
                SanitizedManualIssueV98(
                    code="missing_required_asset_class",
                    severity=SanitizedManualSeverityV98.ERROR,
                    message_ja=f"必須asset class が欠損しています: {key}",
                )
            )
    assets = _asset_map(input_data)
    expected_net = input_data.total_assets_man_yen - input_data.loan_balance_man_yen
    if abs(expected_net - input_data.net_worth_man_yen) > amount_tolerance_man_yen:
        issues.append(
            SanitizedManualIssueV98(
                code="net_worth_mismatch",
                severity=SanitizedManualSeverityV98.ERROR,
                message_ja="総資産-ローン残高と純資産が一致しません。",
            )
        )
    if all(k in assets for k in _REQUIRED_KEYS):
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
                SanitizedManualIssueV98(
                    code="asset_total_mismatch",
                    severity=SanitizedManualSeverityV98.ERROR,
                    message_ja="asset合計と総資産が一致しません。",
                )
            )
        ratio_keys = (
            "cash",
            "index",
            "individual_stocks",
            "bonds",
            "gold",
            "crypto_high_beta",
            "leverage",
        )
        ratios = [assets[key].ratio_pct for key in ratio_keys if assets[key].ratio_pct is not None]
        if ratios and abs(sum(ratios) - 100.0) > ratio_tolerance_pct:
            issues.append(
                SanitizedManualIssueV98(
                    code="ratio_total_mismatch",
                    severity=SanitizedManualSeverityV98.ERROR,
                    message_ja="ratio合計が100%から乖離しています。",
                )
            )
        eq_sum = assets["index"].amount_man_yen + assets["individual_stocks"].amount_man_yen
        if abs(eq_sum - assets["equity_total"].amount_man_yen) > amount_tolerance_man_yen:
            issues.append(
                SanitizedManualIssueV98(
                    code="equity_total_mismatch",
                    severity=SanitizedManualSeverityV98.ERROR,
                    message_ja="INDEX+個別株と株式系合計が一致しません。",
                )
            )
        for row in input_data.assets:
            if row.amount_man_yen < 0:
                issues.append(
                    SanitizedManualIssueV98(
                        code="negative_amount",
                        severity=SanitizedManualSeverityV98.ERROR,
                        message_ja=f"{row.label_ja} の金額が負値です。",
                    )
                )
                break
        cash_ratio = assets["cash"].ratio_pct or 0.0
        single_ratio = assets["individual_stocks"].ratio_pct or 0.0
        if cash_ratio < input_data.cash_minimum_guardrail_pct:
            issues.append(
                SanitizedManualIssueV98(
                    code="cash_below_minimum_guardrail",
                    severity=SanitizedManualSeverityV98.WARN,
                    message_ja=(
                        f"現金比率{cash_ratio:.1f}% は minimum "
                        f"{input_data.cash_minimum_guardrail_pct:.1f}% 未満です。"
                    ),
                )
            )
        if single_ratio > input_data.single_stock_target_max_pct:
            issues.append(
                SanitizedManualIssueV98(
                    code="single_stock_above_target_band",
                    severity=SanitizedManualSeverityV98.WARN,
                    message_ja=(
                        f"個別株比率{single_ratio:.1f}% は target "
                        f"{input_data.single_stock_target_min_pct:.1f}〜"
                        f"{input_data.single_stock_target_max_pct:.1f}% を超えています。"
                    ),
                )
            )
    return SanitizedManualValidationResultV98(
        as_of_month=input_data.as_of_month,
        overall_severity=_overall_severity(issues),
        issues=tuple(issues),
    )


def portfolio_context_from_sanitized_manual_input_v98(
    input_data: SanitizedManualPortfolioInputV98,
) -> PortfolioContextInputV97:
    return PortfolioContextInputV97(
        as_of_month=input_data.as_of_month,
        currency=input_data.currency,
        amount_unit=input_data.amount_unit,
        total_assets_man_yen=input_data.total_assets_man_yen,
        loan_balance_man_yen=input_data.loan_balance_man_yen,
        net_worth_man_yen=input_data.net_worth_man_yen,
        asset_classes=tuple(
            PortfolioAssetClassContextV97(
                key=x.key,
                label_ja=x.label_ja,
                amount_man_yen=x.amount_man_yen,
                ratio_pct=(x.ratio_pct or 0.0),
            )
            for x in input_data.assets
        ),
        guardrails=PortfolioGuardrailContextV97(
            cash_minimum_pct=input_data.cash_minimum_guardrail_pct,
            cash_preferred_recovery_pct=input_data.cash_preferred_recovery_zone_pct,
            single_stock_target_min_pct=input_data.single_stock_target_min_pct,
            single_stock_target_max_pct=input_data.single_stock_target_max_pct,
            target_cash_pct=input_data.target_cash_pct,
            target_equity_pct=input_data.target_equity_pct,
            target_alternative_pct=input_data.target_alternative_pct,
            target_bond_pct=input_data.target_bond_pct,
        ),
    )


def monthly_input_from_sanitized_manual_input_v98(
    input_data: SanitizedManualPortfolioInputV98,
) -> MonthlyPortfolioInputV95:
    portfolio = portfolio_context_from_sanitized_manual_input_v98(input_data)
    return monthly_input_from_portfolio_context_v97(portfolio)


def validate_v95_parity_from_sanitized_manual_input_v98(
    input_data: SanitizedManualPortfolioInputV98,
) -> MonthlyInputConsistencyResultV95:
    monthly_input = monthly_input_from_sanitized_manual_input_v98(input_data)
    return validate_monthly_portfolio_input_v95(monthly_input, current_month=input_data.as_of_month)


def render_sanitized_manual_input_summary_lines_v98(
    input_data: SanitizedManualPortfolioInputV98,
    validation_result: SanitizedManualValidationResultV98,
    *,
    monthly_result_v95: MonthlyInputConsistencyResultV95 | None = None,
) -> tuple[str, ...]:
    assets = _asset_map(input_data)
    v95_line = "- v95整合: 未参照"
    if monthly_result_v95 is not None:
        v95_line = f"- v95整合: {monthly_result_v95.overall_severity.value.upper()}"
    return (
        (
            f"- Sanitized/Manual Input（v98）: {input_data.as_of_month} / "
            f"総資産{input_data.total_assets_man_yen:.1f}万円 / 純資産{input_data.net_worth_man_yen:.1f}万円"
        ),
        (
            f"- 現金{(assets['cash'].ratio_pct or 0.0):.1f}% "
            f"(minimum {input_data.cash_minimum_guardrail_pct:.1f}% / preferred {input_data.cash_preferred_recovery_zone_pct:.1f}%)"
        ),
        (
            f"- 個別株{(assets['individual_stocks'].ratio_pct or 0.0):.1f}% "
            f"(target {input_data.single_stock_target_min_pct:.1f}〜{input_data.single_stock_target_max_pct:.1f}%)"
        ),
        f"- source_kind: {input_data.source_kind} / redaction_level: {input_data.redaction_level}",
        f"- 判定: {validation_result.overall_severity.value.upper()}",
        v95_line,
    )


def render_sanitized_manual_input_markdown_v98(
    input_data: SanitizedManualPortfolioInputV98,
    validation_result: SanitizedManualValidationResultV98,
    *,
    monthly_result_v95: MonthlyInputConsistencyResultV95 | None = None,
) -> str:
    lines = [
        "## Sanitized / Manual Input Summary v98",
        "",
        *render_sanitized_manual_input_summary_lines_v98(
            input_data,
            validation_result,
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
    lines.extend(
        [
            "",
            "### Raw Data Boundary",
            "- 許可: redacted fixture / sanitized manual input / source-only conversion / validation / tests / docs",
            "- 禁止: raw Excel / broker export / broker API / actual import / cache write / live HTTP",
            "",
            "これは売買指示ではなく、sanitized/manual input 契約の整合性確認です。",
            "",
        ]
    )
    return "\n".join(lines)
