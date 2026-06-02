"""v95 Monthly Input Consistency Hardening (source-only / fixture-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class MonthlyInputConsistencySeverityV95(Enum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"


@dataclass(frozen=True)
class MonthlyAssetClassInputV95:
    name: str
    amount_10k_yen: float
    ratio_pct: float


@dataclass(frozen=True)
class MonthlyPortfolioInputV95:
    as_of_month: str
    amount_unit: str
    total_assets_10k_yen: float
    loan_balance_10k_yen: float
    net_worth_10k_yen: float
    cash: MonthlyAssetClassInputV95
    index: MonthlyAssetClassInputV95
    individual_stocks: MonthlyAssetClassInputV95
    equity_total: MonthlyAssetClassInputV95
    bonds: MonthlyAssetClassInputV95
    gold: MonthlyAssetClassInputV95
    crypto_high_beta: MonthlyAssetClassInputV95
    leverage: MonthlyAssetClassInputV95
    cash_minimum_guardrail_pct: float = 15.0
    cash_preferred_recovery_zone_pct: float = 20.0
    single_stock_target_band_low_pct: float = 10.0
    single_stock_target_band_high_pct: float = 15.0


@dataclass(frozen=True)
class MonthlyInputConsistencyIssueV95:
    code: str
    severity: MonthlyInputConsistencySeverityV95
    message_ja: str


@dataclass(frozen=True)
class MonthlyInputConsistencyResultV95:
    as_of_month: str
    overall_severity: MonthlyInputConsistencySeverityV95
    issues: tuple[MonthlyInputConsistencyIssueV95, ...]


def build_redacted_monthly_portfolio_fixture_v95() -> MonthlyPortfolioInputV95:
    return MonthlyPortfolioInputV95(
        as_of_month="2026-05",
        amount_unit="万円",
        total_assets_10k_yen=4327.9,
        loan_balance_10k_yen=3432.0,
        net_worth_10k_yen=895.9,
        cash=MonthlyAssetClassInputV95("現金", 508.2, 11.7),
        index=MonthlyAssetClassInputV95("INDEX", 2088.2, 48.2),
        individual_stocks=MonthlyAssetClassInputV95("個別株", 846.3, 19.6),
        equity_total=MonthlyAssetClassInputV95("株式系合計", 2934.5, 67.8),
        bonds=MonthlyAssetClassInputV95("債券", 582.7, 13.5),
        gold=MonthlyAssetClassInputV95("GOLD", 234.5, 5.4),
        crypto_high_beta=MonthlyAssetClassInputV95("仮想通貨・高ベータ", 57.5, 1.3),
        leverage=MonthlyAssetClassInputV95("レバ", 10.5, 0.2),
    )


def _parse_month(month: str) -> tuple[int, int] | None:
    parts = month.split("-")
    if len(parts) != 2:
        return None
    if (not parts[0].isdigit()) or (not parts[1].isdigit()):
        return None
    year = int(parts[0])
    mon = int(parts[1])
    if mon < 1 or mon > 12:
        return None
    return year, mon


def _month_index(year: int, mon: int) -> int:
    return year * 12 + mon


def validate_monthly_portfolio_input_v95(
    input_data: MonthlyPortfolioInputV95,
    *,
    current_month: str | None = None,
    amount_tolerance_10k_yen: float = 0.2,
    ratio_tolerance_pct: float = 0.2,
) -> MonthlyInputConsistencyResultV95:
    issues: list[MonthlyInputConsistencyIssueV95] = []

    parsed = _parse_month(input_data.as_of_month)
    if parsed is None:
        issues.append(
            MonthlyInputConsistencyIssueV95(
                code="missing_as_of_month",
                severity=MonthlyInputConsistencySeverityV95.ERROR,
                message_ja="as_of_month が欠損または形式不正です（YYYY-MM）。",
            )
        )
    else:
        y, m = parsed
        if current_month is None:
            today = date.today()
            current_index = _month_index(today.year, today.month)
        else:
            cur = _parse_month(current_month)
            if cur is None:
                raise ValueError(f"invalid current_month format: {current_month!r}")
            current_index = _month_index(cur[0], cur[1])
        input_index = _month_index(y, m)
        if input_index > current_index:
            issues.append(
                MonthlyInputConsistencyIssueV95(
                    code="future_as_of_month",
                    severity=MonthlyInputConsistencySeverityV95.ERROR,
                    message_ja=f"as_of_month={input_data.as_of_month} は未来月です。",
                )
            )
        elif current_index - input_index >= 2:
            issues.append(
                MonthlyInputConsistencyIssueV95(
                    code="stale_as_of_month",
                    severity=MonthlyInputConsistencySeverityV95.WARN,
                    message_ja=f"as_of_month={input_data.as_of_month} は古い月です。",
                )
            )

    if input_data.amount_unit != "万円":
        issues.append(
            MonthlyInputConsistencyIssueV95(
                code="amount_unit_contract",
                severity=MonthlyInputConsistencySeverityV95.ERROR,
                message_ja=f"amount_unit={input_data.amount_unit!r}。万円単位契約に一致しません。",
            )
        )

    expected_net = input_data.total_assets_10k_yen - input_data.loan_balance_10k_yen
    if abs(expected_net - input_data.net_worth_10k_yen) > amount_tolerance_10k_yen:
        issues.append(
            MonthlyInputConsistencyIssueV95(
                code="net_worth_mismatch",
                severity=MonthlyInputConsistencySeverityV95.ERROR,
                message_ja=(
                    f"総資産-ローン残高={expected_net:.1f}万円 と "
                    f"純資産={input_data.net_worth_10k_yen:.1f}万円 が一致しません。"
                ),
            )
        )

    leaf_amount_total = (
        input_data.cash.amount_10k_yen
        + input_data.index.amount_10k_yen
        + input_data.individual_stocks.amount_10k_yen
        + input_data.bonds.amount_10k_yen
        + input_data.gold.amount_10k_yen
        + input_data.crypto_high_beta.amount_10k_yen
        + input_data.leverage.amount_10k_yen
    )
    if abs(leaf_amount_total - input_data.total_assets_10k_yen) > amount_tolerance_10k_yen:
        issues.append(
            MonthlyInputConsistencyIssueV95(
                code="asset_total_mismatch",
                severity=MonthlyInputConsistencySeverityV95.ERROR,
                message_ja=(
                    f"資産分類合計={leaf_amount_total:.1f}万円 と "
                    f"総資産={input_data.total_assets_10k_yen:.1f}万円 が一致しません。"
                ),
            )
        )

    leaf_ratio_total = (
        input_data.cash.ratio_pct
        + input_data.index.ratio_pct
        + input_data.individual_stocks.ratio_pct
        + input_data.bonds.ratio_pct
        + input_data.gold.ratio_pct
        + input_data.crypto_high_beta.ratio_pct
        + input_data.leverage.ratio_pct
    )
    if abs(leaf_ratio_total - 100.0) > ratio_tolerance_pct:
        issues.append(
            MonthlyInputConsistencyIssueV95(
                code="allocation_ratio_total_mismatch",
                severity=MonthlyInputConsistencySeverityV95.ERROR,
                message_ja=f"資産分類の比率合計={leaf_ratio_total:.1f}% が 100% から乖離しています。",
            )
        )

    if abs((input_data.index.amount_10k_yen + input_data.individual_stocks.amount_10k_yen) - input_data.equity_total.amount_10k_yen) > amount_tolerance_10k_yen:
        issues.append(
            MonthlyInputConsistencyIssueV95(
                code="equity_total_mismatch",
                severity=MonthlyInputConsistencySeverityV95.ERROR,
                message_ja="株式系合計と INDEX+個別株 の金額が一致しません。",
            )
        )

    if input_data.cash.ratio_pct < input_data.cash_minimum_guardrail_pct:
        issues.append(
            MonthlyInputConsistencyIssueV95(
                code="cash_below_minimum_guardrail",
                severity=MonthlyInputConsistencySeverityV95.WARN,
                message_ja=(
                    f"現金比率{input_data.cash.ratio_pct:.1f}% は minimum "
                    f"{input_data.cash_minimum_guardrail_pct:.1f}% 未満です。"
                ),
            )
        )
    if input_data.cash.ratio_pct < input_data.cash_preferred_recovery_zone_pct:
        issues.append(
            MonthlyInputConsistencyIssueV95(
                code="cash_below_preferred_recovery_zone",
                severity=MonthlyInputConsistencySeverityV95.INFO,
                message_ja=(
                    f"現金比率{input_data.cash.ratio_pct:.1f}% は preferred "
                    f"{input_data.cash_preferred_recovery_zone_pct:.1f}% 未満です。"
                ),
            )
        )
    if input_data.individual_stocks.ratio_pct > input_data.single_stock_target_band_high_pct:
        issues.append(
            MonthlyInputConsistencyIssueV95(
                code="single_stock_above_target_band",
                severity=MonthlyInputConsistencySeverityV95.WARN,
                message_ja=(
                    f"個別株比率{input_data.individual_stocks.ratio_pct:.1f}% は target band "
                    f"{input_data.single_stock_target_band_low_pct:.1f}〜"
                    f"{input_data.single_stock_target_band_high_pct:.1f}% を超えています。"
                ),
            )
        )

    for asset in (
        input_data.cash,
        input_data.index,
        input_data.individual_stocks,
        input_data.equity_total,
        input_data.bonds,
        input_data.gold,
        input_data.crypto_high_beta,
        input_data.leverage,
    ):
        if asset.amount_10k_yen < 0:
            issues.append(
                MonthlyInputConsistencyIssueV95(
                    code="negative_amount",
                    severity=MonthlyInputConsistencySeverityV95.ERROR,
                    message_ja=f"{asset.name} の金額が負値です。",
                )
            )
            break

    severity_rank = {
        MonthlyInputConsistencySeverityV95.ERROR: 3,
        MonthlyInputConsistencySeverityV95.WARN: 2,
        MonthlyInputConsistencySeverityV95.INFO: 1,
    }
    overall = MonthlyInputConsistencySeverityV95.INFO
    for issue in issues:
        if severity_rank[issue.severity] > severity_rank[overall]:
            overall = issue.severity

    return MonthlyInputConsistencyResultV95(
        as_of_month=input_data.as_of_month,
        overall_severity=overall,
        issues=tuple(issues),
    )


def render_monthly_input_consistency_summary_lines_v95(
    input_data: MonthlyPortfolioInputV95,
    result: MonthlyInputConsistencyResultV95,
) -> tuple[str, ...]:
    net_ok = abs((input_data.total_assets_10k_yen - input_data.loan_balance_10k_yen) - input_data.net_worth_10k_yen) <= 0.2
    equity_ok = abs((input_data.index.amount_10k_yen + input_data.individual_stocks.amount_10k_yen) - input_data.equity_total.amount_10k_yen) <= 0.2
    return (
        f"- 判定: {result.overall_severity.value.upper()}",
        f"- 対象月: {input_data.as_of_month}",
        f"- 総資産/ローン/純資産: {'OK' if net_ok else 'NG'}",
        f"- 株式系合計=INDEX+個別株: {'OK' if equity_ok else 'NG'}",
        (
            f"- 現金比率: {input_data.cash.ratio_pct:.1f}% "
            f"(minimum {input_data.cash_minimum_guardrail_pct:.1f}% / preferred {input_data.cash_preferred_recovery_zone_pct:.1f}%)"
        ),
        (
            f"- 個別株比率: {input_data.individual_stocks.ratio_pct:.1f}% "
            f"(target {input_data.single_stock_target_band_low_pct:.1f}〜{input_data.single_stock_target_band_high_pct:.1f}%)"
        ),
    )


def render_monthly_input_consistency_markdown_v95(
    input_data: MonthlyPortfolioInputV95,
    result: MonthlyInputConsistencyResultV95,
) -> str:
    lines = [
        "## Monthly Input Consistency Check",
        "",
        *render_monthly_input_consistency_summary_lines_v95(input_data, result),
        "",
        "### 検出事項",
    ]
    if not result.issues:
        lines.append("- 問題は検出されませんでした。")
    else:
        for issue in result.issues:
            lines.append(f"- [{issue.severity.value.upper()}] {issue.code}: {issue.message_ja}")
    lines.extend(
        [
            "",
            "これは売買指示ではなく、月次入力の整合性とポートフォリオ制約の確認です。",
            "",
        ]
    )
    return "\n".join(lines)
