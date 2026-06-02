"""v84 Monthly Decision Sheet Pack (observation-only, source-only)."""

from __future__ import annotations

from dataclasses import dataclass

from invis_alpha_os.portfolio.target_allocation_gap_calculator_v82 import (
    CurrentAllocationsV82,
    TargetAllocationConfigV82,
    compute_target_allocation_gap_v82,
)


PACK_VERSION_V84 = "v84"
DEFAULT_REPORT_MONTH_V84 = "2026-05"

FORBIDDEN_DECISION_SHEET_PHRASES_V84: tuple[str, ...] = (
    "買うべき",
    "売るべき",
    "必ず売却",
    "今すぐ購入",
    "発注",
    "注文",
    "確実",
    "保証",
)

SAFETY_NOTE_LINES_V84: tuple[str, ...] = (
    "このシートは売買指示ではなく、ポートフォリオ制約に基づく意思決定補助・記録用です。",
    "実際の売買は、価格、税金、NISA枠、取得単価、家計キャッシュフロー、リスク許容度を別途確認して判断します。",
)


@dataclass(frozen=True)
class MonthlyDecisionSheetInputV84:
    report_month: str
    total_assets_10k_yen: float
    cash_10k_yen: float
    equity_total_10k_yen: float
    individual_stocks_10k_yen: float
    bonds_10k_yen: float
    temporary_alternatives_10k_yen: float


def default_monthly_decision_sheet_input_v84() -> MonthlyDecisionSheetInputV84:
    # v78 redacted portfolio context (2026-05 month-end corrected)
    return MonthlyDecisionSheetInputV84(
        report_month=DEFAULT_REPORT_MONTH_V84,
        total_assets_10k_yen=4327.9,
        cash_10k_yen=508.2,
        equity_total_10k_yen=2934.5,
        individual_stocks_10k_yen=846.3,
        bonds_10k_yen=582.7,
        temporary_alternatives_10k_yen=302.5,  # GOLD + crypto/high-beta + leveraged
    )


def _pct(amount_10k_yen: float, total_10k_yen: float) -> float:
    if total_10k_yen <= 0:
        raise ValueError("total assets must be positive")
    return (amount_10k_yen / total_10k_yen) * 100.0


def _fmt_amount_1(amount_10k_yen: float) -> str:
    return f"{amount_10k_yen:.1f}万円"


def _fmt_pct_1(pct_value: float) -> str:
    return f"{pct_value:.1f}%"


def _fmt_signed_amount_1(amount_10k_yen: float) -> str:
    sign = "+" if amount_10k_yen >= 0 else ""
    return f"{sign}{amount_10k_yen:.1f}万円"


def _build_current_allocations_for_v82(input_v84: MonthlyDecisionSheetInputV84) -> CurrentAllocationsV82:
    return CurrentAllocationsV82(
        total_assets_10k_yen=input_v84.total_assets_10k_yen,
        cash_amount_10k_yen=input_v84.cash_10k_yen,
        equity_total_amount_10k_yen=input_v84.equity_total_10k_yen,
        individual_stocks_amount_10k_yen=input_v84.individual_stocks_10k_yen,
        bonds_amount_10k_yen=input_v84.bonds_10k_yen,
        gold_amount_10k_yen=234.5,
        crypto_high_beta_amount_10k_yen=57.5,
        leverage_amount_10k_yen=10.5,
    )


def build_monthly_decision_sheet_v84_markdown(
    *,
    input_v84: MonthlyDecisionSheetInputV84 | None = None,
    config_v82: TargetAllocationConfigV82 = TargetAllocationConfigV82(),
) -> str:
    """Generate monthly decision support sheet markdown."""
    data = input_v84 or default_monthly_decision_sheet_input_v84()
    gap = compute_target_allocation_gap_v82(
        current=_build_current_allocations_for_v82(data),
        config=config_v82,
    )

    cash_pct = _pct(data.cash_10k_yen, data.total_assets_10k_yen)
    equity_pct = _pct(data.equity_total_10k_yen, data.total_assets_10k_yen)
    individual_pct = _pct(data.individual_stocks_10k_yen, data.total_assets_10k_yen)
    bonds_pct = _pct(data.bonds_10k_yen, data.total_assets_10k_yen)
    alt_pct = _pct(data.temporary_alternatives_10k_yen, data.total_assets_10k_yen)

    lines = [
        "# Monthly Decision Sheet",
        "",
        "## 今月の結論",
        "",
        "- 新規株式リスク追加: 原則抑制",
        "- 現金回復: 最優先",
        "- 個別株: 新規追加より整理候補確認",
        "- オルタナティブ: 目標比では不足だが、現金不足下では慎重",
        "- 債券: 追加不要、保有確認",
        "",
        "## 判断サマリー",
        "",
        f"- 総資産: {_fmt_amount_1(data.total_assets_10k_yen)}",
        "",
        "| 判断領域 | 現状 | 判定 | 今月の扱い |",
        "|---|---:|---|---|",
        f"| 現金 | {_fmt_amount_1(data.cash_10k_yen)} / {_fmt_pct_1(cash_pct)} | under minimum | まず15〜20%回復を優先 |",
        f"| 株式系 | {_fmt_amount_1(data.equity_total_10k_yen)} / {_fmt_pct_1(equity_pct)} | overweight | 新規株式リスク追加を抑制 |",
        f"| 個別株 | {_fmt_amount_1(data.individual_stocks_10k_yen)} / {_fmt_pct_1(individual_pct)} | above band | 整理候補・重複リスクを確認 |",
        f"| 債券 | {_fmt_amount_1(data.bonds_10k_yen)} / {_fmt_pct_1(bonds_pct)} | above target | 追加不要、金利環境を確認 |",
        f"| 暫定オルタナ | {_fmt_amount_1(data.temporary_alternatives_10k_yen)} / {_fmt_pct_1(alt_pct)} | below target | 現金不足下では追加慎重 |",
        "",
        "## 今月の意思決定テーブル",
        "",
        "| アクション | 判定 | 理由 | 次に確認すること |",
        "|---|---|---|---|",
        "| 買う（新規個別株追加） | 原則しない | 現金11.7%、個別株19.6%、株式系67.8% | 既存個別株の重複・高ボラ偏り |",
        "| 保留（インデックス積立） | 継続/金額確認 | 長期コアだが株式系過多 | NISA年内進捗、現金回復余力 |",
        "| 保留（債券追加） | 今月は急がない | 目標10.5%に対して13.5% | 金利・満期・為替 |",
        "| 保留（GOLD/オルタナ追加） | 慎重 | 目標比では不足だが現金不足が優先 | 価格水準と現金回復状況 |",
        "| 現金回復 | 優先 | 15%まで約141万円不足 | 入金・固定費最適化・追加リスク抑制余地 |",
        "| 整理候補 | 実施 | 個別株・株式系が目標超過 | 重複テーマ、低conviction、高ボラ枠 |",
        "",
        "## 現金回復ステップ",
        "",
        "| 目安 | 必要額 | 差分 | 扱い |",
        "|---|---:|---:|---|",
        f"| 最低15% | {_fmt_amount_1(data.total_assets_10k_yen * 0.15)} | あと {_fmt_amount_1(gap.cash_short_to_15_pct)} | 最優先 |",
        f"| 回復20% | {_fmt_amount_1(data.total_assets_10k_yen * 0.20)} | あと {_fmt_amount_1(gap.cash_short_to_20_pct)} | 次の目安 |",
        f"| 戦略30% | {_fmt_amount_1(data.total_assets_10k_yen * 0.30)} | あと {_fmt_amount_1(gap.cash_short_to_30_pct)} | 中期目標 |",
        "",
        "## 次月への持ち越し",
        "",
        "- scheduled weekly runの安定確認",
        "- veto理由の表示粒度確認",
        "- 個別株整理候補のスコア化強化",
        "- NISA年内進捗との接続",
        "",
        "## 配分ギャップ（v82再利用）",
        "",
        f"- 現金: {_fmt_pct_1(cash_pct)}（最低15%まで {_fmt_amount_1(gap.cash_short_to_15_pct)}不足 / 20%まで {_fmt_amount_1(gap.cash_short_to_20_pct)}不足 / 30%まで {_fmt_amount_1(gap.cash_short_to_30_pct)}不足）",
        f"- 株式系: {_fmt_pct_1(equity_pct)} vs 49.0%（overweight {_fmt_signed_amount_1(gap.equity_over_amount)}）",
        f"- 個別株: {_fmt_pct_1(individual_pct)} vs 10〜15%（above band +{gap.individual_above_band_pct:.1f}% / {_fmt_signed_amount_1(gap.individual_above_band_over_amount)}）",
        f"- 債券: {_fmt_pct_1(bonds_pct)} vs 10.5%（above target {_fmt_signed_amount_1(gap.bonds_over_amount)}）",
        f"- 暫定オルタナ: {_fmt_pct_1(alt_pct)} vs 10.5%（below target {_fmt_amount_1(gap.alt_short_amount)}不足）",
        "",
        "## Safety note",
        "",
        *[f"- {x}" for x in SAFETY_NOTE_LINES_V84],
        "",
        f"- pack_version: {PACK_VERSION_V84}",
        f"- report_month: {data.report_month}",
        "",
    ]

    markdown = "\n".join(lines)
    for phrase in FORBIDDEN_DECISION_SHEET_PHRASES_V84:
        if phrase in markdown:
            raise ValueError(f"forbidden phrase detected in monthly decision sheet: {phrase}")
    return markdown

