"""
v82 Target Allocation Gap Calculator

投資判断支援（観測・検証用）のため、現在配分と目標配分の差分を数値化し、
レポート/メールに貼れる Markdown へ整形する。
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping


_AMOUNT_RE = re.compile(r"(?P<amount>[-+]?\d[\d,]*(?:\.\d+)?)\s*万円")


def parse_amount_10k_yen(value: str) -> float:
    """
    "約4,327.9万円" / "508.2万円 / 11.7%" のような形式から、万円単位の数値を抽出する。
    """
    m = _AMOUNT_RE.search(value)
    if not m:
        raise ValueError(f"Could not parse amount (10k yen) from: {value!r}")
    amount_raw = m.group("amount").replace(",", "")
    return float(amount_raw)


def _pct(amount: float, total: float) -> float:
    if total <= 0:
        raise ValueError(f"total must be > 0, got {total}")
    return (amount / total) * 100.0


def _fmt_pct_1(pct_value: float) -> str:
    return f"{pct_value:.1f}%"


def _fmt_amount_1(amount_10k_yen: float) -> str:
    return f"{amount_10k_yen:.1f}万円"


def _fmt_signed_amount_1(amount_10k_yen: float) -> str:
    if amount_10k_yen < 0:
        return f"{amount_10k_yen:.1f}万円"
    return f"+{amount_10k_yen:.1f}万円"


@dataclass(frozen=True)
class TargetAllocationConfigV82:
    cash_target_pct: float = 30.0
    equity_target_pct: float = 49.0
    alt_target_pct: float = 10.5
    bonds_target_pct: float = 10.5

    individual_band_low_pct: float = 10.0
    individual_band_high_pct: float = 15.0

    cash_recovery_min_pct: float = 15.0
    cash_recovery_prefer_pct: float = 20.0
    cash_recovery_strategy_pct: float = 30.0


@dataclass(frozen=True)
class CurrentAllocationsV82:
    total_assets_10k_yen: float
    cash_amount_10k_yen: float
    equity_total_amount_10k_yen: float
    individual_stocks_amount_10k_yen: float
    bonds_amount_10k_yen: float
    gold_amount_10k_yen: float
    crypto_high_beta_amount_10k_yen: float
    leverage_amount_10k_yen: float

    @property
    def alt_amount_10k_yen(self) -> float:
        # "暫定オルタナティブ" = GOLD + 仮想通貨・高ベータ + レバ
        return self.gold_amount_10k_yen + self.crypto_high_beta_amount_10k_yen + self.leverage_amount_10k_yen


@dataclass(frozen=True)
class TargetAllocationGapV82:
    # Cash
    current_cash_pct: float
    cash_short_to_15_pct: float
    cash_short_to_20_pct: float
    cash_short_to_30_pct: float

    # Equity total
    current_equity_total_pct: float
    equity_over_amount: float

    # Individual band
    current_individual_pct: float
    individual_above_band_pct: float
    individual_above_band_over_amount: float

    # Bonds
    current_bonds_pct: float
    bonds_over_amount: float

    # Alternative (暫定)
    current_alt_pct: float
    alt_short_amount: float

    config: TargetAllocationConfigV82


def compute_target_allocation_gap_v82(
    *,
    current: CurrentAllocationsV82,
    config: TargetAllocationConfigV82 = TargetAllocationConfigV82(),
) -> TargetAllocationGapV82:
    """
    現在配分と目標配分の差分を計算する。
    """
    total = current.total_assets_10k_yen

    cash_current_pct = _pct(current.cash_amount_10k_yen, total)
    equity_current_pct = _pct(current.equity_total_amount_10k_yen, total)
    individual_current_pct = _pct(current.individual_stocks_amount_10k_yen, total)
    bonds_current_pct = _pct(current.bonds_amount_10k_yen, total)
    alt_current_pct = _pct(current.alt_amount_10k_yen, total)

    cash_short_to_15 = max(0.0, total * config.cash_recovery_min_pct / 100.0 - current.cash_amount_10k_yen)
    cash_short_to_20 = max(0.0, total * config.cash_recovery_prefer_pct / 100.0 - current.cash_amount_10k_yen)
    cash_short_to_30 = max(0.0, total * config.cash_recovery_strategy_pct / 100.0 - current.cash_amount_10k_yen)

    equity_target_amount = total * config.equity_target_pct / 100.0
    equity_over_amount = max(0.0, current.equity_total_amount_10k_yen - equity_target_amount)

    individual_upper_amount = total * config.individual_band_high_pct / 100.0
    individual_above_band_over_amount = max(0.0, current.individual_stocks_amount_10k_yen - individual_upper_amount)
    individual_above_band_pct = max(0.0, individual_current_pct - config.individual_band_high_pct)

    bonds_target_amount = total * config.bonds_target_pct / 100.0
    bonds_over_amount = max(0.0, current.bonds_amount_10k_yen - bonds_target_amount)

    alt_target_amount = total * config.alt_target_pct / 100.0
    alt_short_amount = max(0.0, alt_target_amount - current.alt_amount_10k_yen)

    return TargetAllocationGapV82(
        current_cash_pct=cash_current_pct,
        cash_short_to_15_pct=cash_short_to_15,
        cash_short_to_20_pct=cash_short_to_20,
        cash_short_to_30_pct=cash_short_to_30,
        current_equity_total_pct=equity_current_pct,
        equity_over_amount=equity_over_amount,
        current_individual_pct=individual_current_pct,
        individual_above_band_pct=individual_above_band_pct,
        individual_above_band_over_amount=individual_above_band_over_amount,
        current_bonds_pct=bonds_current_pct,
        bonds_over_amount=bonds_over_amount,
        current_alt_pct=alt_current_pct,
        alt_short_amount=alt_short_amount,
        config=config,
    )


def compute_target_allocation_gap_from_portfolio_context_v82(
    portfolio_context: Mapping[str, str],
    *,
    config: TargetAllocationConfigV82 = TargetAllocationConfigV82(),
) -> TargetAllocationGapV82:
    """
    PORTFOLIO_CONTEXT の文字列値（万円/％）を parse して差分を計算する。
    """
    required_keys = (
        "total_assets",
        "cash",
        "equity_total",
        "individual_stocks",
        "bonds",
        "gold",
        "crypto_high_beta",
        "leverage",
    )
    missing = [k for k in required_keys if k not in portfolio_context]
    if missing:
        raise KeyError(f"missing keys in portfolio_context: {missing}")

    total_assets = parse_amount_10k_yen(portfolio_context["total_assets"])
    current = CurrentAllocationsV82(
        total_assets_10k_yen=total_assets,
        cash_amount_10k_yen=parse_amount_10k_yen(portfolio_context["cash"]),
        equity_total_amount_10k_yen=parse_amount_10k_yen(portfolio_context["equity_total"]),
        individual_stocks_amount_10k_yen=parse_amount_10k_yen(portfolio_context["individual_stocks"]),
        bonds_amount_10k_yen=parse_amount_10k_yen(portfolio_context["bonds"]),
        gold_amount_10k_yen=parse_amount_10k_yen(portfolio_context["gold"]),
        crypto_high_beta_amount_10k_yen=parse_amount_10k_yen(portfolio_context["crypto_high_beta"]),
        leverage_amount_10k_yen=parse_amount_10k_yen(portfolio_context["leverage"]),
    )
    return compute_target_allocation_gap_v82(current=current, config=config)


def format_target_allocation_gap_markdown_short_v82(gap: TargetAllocationGapV82) -> list[str]:
    """
    weekly report 向け: 短縮版 Markdown（copy-readyブロックに差し込み可能）。
    """
    cash = gap.cash_short_to_30_pct
    cash_15 = gap.cash_short_to_15_pct
    cash_20 = gap.cash_short_to_20_pct

    return [
        "## 目標配分ギャップ（v82）",
        "",
        (
            f"- 現金: {_fmt_pct_1(gap.current_cash_pct)} → {gap.config.cash_target_pct:.1f}%目標で不足 "
            f"{_fmt_amount_1(cash)}（最低{gap.config.cash_recovery_min_pct:.0f}%まで +{_fmt_amount_1(cash_15)} / "
            f"{gap.config.cash_recovery_prefer_pct:.0f}%まで +{_fmt_amount_1(cash_20)}）"
        ),
        (
            f"- 株式系合計: {_fmt_pct_1(gap.current_equity_total_pct)} → {gap.config.equity_target_pct:.1f}%目標で上回り "
            f"{_fmt_signed_amount_1(gap.equity_over_amount)}"
        ),
        (
            f"- 個別株: {_fmt_pct_1(gap.current_individual_pct)}（目安{gap.config.individual_band_low_pct:.0f}〜{gap.config.individual_band_high_pct:.0f}%）"
            f"上限{gap.config.individual_band_high_pct:.0f}%超過 {gap.individual_above_band_pct:.1f}%（+{gap.individual_above_band_over_amount:.1f}万円）"
        ),
        (
            f"- 債券: {_fmt_pct_1(gap.current_bonds_pct)} → {gap.config.bonds_target_pct:.1f}%目標で上回り "
            f"{_fmt_signed_amount_1(gap.bonds_over_amount)}"
        ),
        (
            f"- オルタナ（GOLD+高ベータ+レバ）: {_fmt_pct_1(gap.current_alt_pct)} → {gap.config.alt_target_pct:.1f}%目標で不足 "
            f"{_fmt_amount_1(gap.alt_short_amount)}"
        ),
        "- 解釈: この差分は売買指示ではなく、現金回復と相対バランスの整理・監視優先度づけに使う観点です。",
        "",
    ]


def format_target_allocation_gap_email_3_lines_v82(gap: TargetAllocationGapV82) -> tuple[str, str, str]:
    """
    email preview 向け: 3行要約（箇条書き3項目として扱う想定）。
    """
    line1 = (
        f"現金 {_fmt_pct_1(gap.current_cash_pct)} → {gap.config.cash_target_pct:.1f}%目標で不足 "
        f"{_fmt_amount_1(gap.cash_short_to_30_pct)}（最低{gap.config.cash_recovery_min_pct:.0f}% +{_fmt_amount_1(gap.cash_short_to_15_pct)}, "
        f"{gap.config.cash_recovery_prefer_pct:.0f}% +{_fmt_amount_1(gap.cash_short_to_20_pct)}）"
    )
    line2 = (
        f"株式系 {_fmt_pct_1(gap.current_equity_total_pct)} → {gap.config.equity_target_pct:.1f}%で上回り "
        f"{_fmt_signed_amount_1(gap.equity_over_amount)}"
        f"。個別株 {_fmt_pct_1(gap.current_individual_pct)} は上限{gap.config.individual_band_high_pct:.0f}%超過 "
        f"+{gap.individual_above_band_pct:.1f}%（+{gap.individual_above_band_over_amount:.1f}万円）"
    )
    line3 = (
        f"債券 {_fmt_pct_1(gap.current_bonds_pct)} → {gap.config.bonds_target_pct:.1f}%で上回り "
        f"{_fmt_signed_amount_1(gap.bonds_over_amount)}"
        f"。オルタナ（GOLD+高ベータ+レバ） {_fmt_pct_1(gap.current_alt_pct)} → {gap.config.alt_target_pct:.1f}%で不足 "
        f"{_fmt_amount_1(gap.alt_short_amount)}"
    )
    return (line1, line2, line3)

