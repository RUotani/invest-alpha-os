from __future__ import annotations

import pytest

from invis_alpha_os.portfolio.target_allocation_gap_calculator_v82 import (
    compute_target_allocation_gap_from_portfolio_context_v82,
    format_target_allocation_gap_markdown_short_v82,
    parse_amount_10k_yen,
)
from invis_alpha_os.product.weekly_candidate_brief_v0 import PORTFOLIO_CONTEXT_V81


def test_parse_amount_10k_yen_parses_amount_with_commas_and_approx() -> None:
    assert parse_amount_10k_yen("約4,327.9万円") == 4327.9
    assert parse_amount_10k_yen("508.2万円 / 11.7%") == 508.2


def test_parse_amount_10k_yen_raises_on_unexpected_format() -> None:
    with pytest.raises(ValueError):
        parse_amount_10k_yen("invalid-format")


def test_compute_target_allocation_gap_v82_expected_values() -> None:
    gap = compute_target_allocation_gap_from_portfolio_context_v82(PORTFOLIO_CONTEXT_V81)

    assert gap.cash_short_to_15_pct == pytest.approx(140.985, abs=0.3)
    assert gap.cash_short_to_20_pct == pytest.approx(357.38, abs=0.3)
    assert gap.cash_short_to_30_pct == pytest.approx(790.17, abs=0.3)

    assert gap.equity_over_amount == pytest.approx(813.829, abs=0.3)
    assert gap.individual_above_band_over_amount == pytest.approx(197.115, abs=0.3)
    assert gap.bonds_over_amount == pytest.approx(128.2705, abs=0.3)
    assert gap.alt_short_amount == pytest.approx(151.9295, abs=0.3)

    # Formatting smoke test (contains expected rounded values)
    md_lines = format_target_allocation_gap_markdown_short_v82(gap)
    md = "\n".join(md_lines)
    assert "## 目標配分ギャップ（v82）" in md
    assert "不足 790.2万円" in md
    assert "上回り +813.8万円" in md
    assert "超過" in md
    assert "上回り +128.3万円" in md
    assert "不足 151.9万円" in md

