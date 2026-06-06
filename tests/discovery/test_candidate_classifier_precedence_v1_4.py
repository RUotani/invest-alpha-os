from __future__ import annotations

from invis_alpha_os.discovery.candidate_classifier import (
    CandidateInput,
    PortfolioGateContext,
    classify_candidate,
)
from invis_alpha_os.discovery.candidate_roles import CandidatePhase, CandidateRole


def test_285a_hard_overheat_classified_theme_proxy_do_not_chase() -> None:
    result = classify_candidate(
        CandidateInput(
            ticker="285A",
            ret_20d=0.73,
            ret_60d=1.75,
            momentum_high=True,
        )
    )
    assert result.phase == CandidatePhase.OVERHEAT
    assert result.role in {CandidateRole.THEME_PROXY, CandidateRole.DO_NOT_CHASE}
    assert result.early_discovery is False
    assert result.action == "do_not_chase"
    assert "surrounding" in result.next_step


def test_portfolio_hard_gate_reduces_buy_allowance() -> None:
    portfolio = PortfolioGateContext(cash_ratio=0.117, single_stock_ratio=0.196)
    assert portfolio.cash_hard_gate is True
    assert portfolio.single_stock_suppressed is True
    assert portfolio.buy_allowance == "zero"

    result = classify_candidate(
        CandidateInput(ticker="AAPL", ret_20d=0.08, ret_60d=0.16),
        portfolio=portfolio,
    )
    assert result.early_discovery is False
    assert result.portfolio_gate == "zero"


def test_moderate_momentum_can_be_early_discovery_when_gates_ok() -> None:
    portfolio = PortfolioGateContext(cash_ratio=0.20, single_stock_ratio=0.12)
    result = classify_candidate(
        CandidateInput(ticker="AAPL", ret_20d=0.28, ret_60d=0.22),
        portfolio=portfolio,
    )
    assert result.early_discovery is True
    assert result.role == CandidateRole.EARLY_DISCOVERY
