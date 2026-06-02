from __future__ import annotations

import pytest

from invis_alpha_os.product.candidate_scoring_contract_v91 import (
    fixture_candidates_v91,
    score_candidates,
)
from invis_alpha_os.product.candidate_veto_rules_v92 import (
    CandidateVetoInput,
    VetoSeverity,
    evaluate_candidate_vetoes,
    render_candidate_veto_reasons_markdown,
    render_veto_rule_contract_markdown,
    veto_input_from_score_result,
)


def _reason_keys(candidate: CandidateVetoInput) -> tuple[str, ...]:
    return tuple(reason.key for reason in evaluate_candidate_vetoes(candidate).reasons)


def test_hard_veto_rules_are_emitted() -> None:
    candidate = CandidateVetoInput(
        symbol="HARD_A",
        normalized_score=62.0,
        evidence_quality=1,
        portfolio_fit=1,
        valuation_sanity=3,
        technical_demand=2,
        financial_quality=1,
    )

    result = evaluate_candidate_vetoes(candidate)

    assert result.has_hard_veto is True
    assert result.has_soft_veto is False
    assert _reason_keys(candidate) == (
        "missing_evidence",
        "portfolio_constraint_breach",
        "financial_quality_red_flag",
    )
    assert all(reason.severity is VetoSeverity.HARD for reason in result.reasons)


def test_valuation_extreme_escalates_when_technical_demand_is_strong() -> None:
    soft = evaluate_candidate_vetoes(
        CandidateVetoInput(
            symbol="VALUE_SOFT",
            normalized_score=70.0,
            evidence_quality=3,
            portfolio_fit=3,
            valuation_sanity=1,
            technical_demand=3,
            financial_quality=3,
        )
    )
    hard = evaluate_candidate_vetoes(
        CandidateVetoInput(
            symbol="VALUE_HARD",
            normalized_score=70.0,
            evidence_quality=3,
            portfolio_fit=3,
            valuation_sanity=1,
            technical_demand=4,
            financial_quality=3,
        )
    )

    assert soft.reasons[0].key == "valuation_extreme"
    assert soft.reasons[0].severity is VetoSeverity.SOFT
    assert hard.reasons[0].key == "valuation_extreme"
    assert hard.reasons[0].severity is VetoSeverity.HARD


def test_soft_veto_rules_are_emitted_in_contract_order() -> None:
    candidate = CandidateVetoInput(
        symbol="SOFT_A",
        normalized_score=81.0,
        evidence_quality=2,
        portfolio_fit=3,
        valuation_sanity=2,
        technical_demand=5,
        financial_quality=3,
        theme_fit=5,
        business_momentum=2,
        liquidity_score=1,
        duplicate_exposure=True,
    )

    result = evaluate_candidate_vetoes(candidate)

    assert result.has_hard_veto is False
    assert result.has_soft_veto is True
    assert tuple(reason.key for reason in result.reasons) == (
        "technical_overheat",
        "liquidity_insufficient",
        "theme_only_hype",
        "duplicate_exposure",
    )


def test_no_reasons_does_not_mean_execution_approval() -> None:
    result = evaluate_candidate_vetoes(
        CandidateVetoInput(
            symbol="CLEAR_A",
            normalized_score=84.0,
            evidence_quality=5,
            portfolio_fit=4,
            valuation_sanity=4,
            technical_demand=3,
            financial_quality=5,
            theme_fit=4,
            business_momentum=4,
            liquidity_score=4,
        )
    )

    md = render_candidate_veto_reasons_markdown(result)

    assert result.reasons == ()
    assert result.has_hard_veto is False
    assert result.has_soft_veto is False
    assert "実行承認ではありません" in md


def test_veto_input_from_score_result_uses_v91_breakdown() -> None:
    results = {result.symbol: result for result in score_candidates(fixture_candidates_v91())}
    veto_input = veto_input_from_score_result(
        results["HYPE_E"],
        liquidity_score=1,
        duplicate_exposure=True,
    )

    result = evaluate_candidate_vetoes(veto_input)

    assert veto_input.normalized_score == results["HYPE_E"].normalized_score
    assert tuple(reason.key for reason in result.reasons) == (
        "missing_evidence",
        "portfolio_constraint_breach",
        "valuation_extreme",
        "technical_overheat",
        "financial_quality_red_flag",
        "liquidity_insufficient",
        "theme_only_hype",
        "duplicate_exposure",
    )
    assert result.has_hard_veto is True


def test_invalid_candidate_rejects_out_of_range_values() -> None:
    with pytest.raises(ValueError, match="normalized_score"):
        evaluate_candidate_vetoes(
            CandidateVetoInput(
                symbol="BAD_A",
                normalized_score=101,
                evidence_quality=3,
                portfolio_fit=3,
                valuation_sanity=3,
                technical_demand=3,
                financial_quality=3,
            )
        )
    with pytest.raises(ValueError, match="liquidity_score"):
        evaluate_candidate_vetoes(
            CandidateVetoInput(
                symbol="BAD_B",
                normalized_score=50,
                evidence_quality=3,
                portfolio_fit=3,
                valuation_sanity=3,
                technical_demand=3,
                financial_quality=3,
                liquidity_score=6,
            )
        )


def test_empty_symbol_is_rejected() -> None:
    with pytest.raises(ValueError, match="symbol"):
        evaluate_candidate_vetoes(
            CandidateVetoInput(
                symbol="",
                normalized_score=50,
                evidence_quality=3,
                portfolio_fit=3,
                valuation_sanity=3,
                technical_demand=3,
                financial_quality=3,
            )
        )


def test_markdown_renderers_include_rules_and_avoid_trading_instruction_words() -> None:
    result = evaluate_candidate_vetoes(
        CandidateVetoInput(
            symbol="SOFT_A",
            normalized_score=81.0,
            evidence_quality=2,
            portfolio_fit=3,
            valuation_sanity=2,
            technical_demand=5,
            financial_quality=3,
            theme_fit=5,
            business_momentum=2,
            liquidity_score=1,
            duplicate_exposure=True,
        )
    )

    reasons_md = render_candidate_veto_reasons_markdown(result)
    contract_md = render_veto_rule_contract_markdown()

    for key in (
        "missing_evidence",
        "portfolio_constraint_breach",
        "valuation_extreme",
        "technical_overheat",
        "financial_quality_red_flag",
        "liquidity_insufficient",
        "theme_only_hype",
        "duplicate_exposure",
    ):
        assert key in contract_md
    assert "technical_overheat" in reasons_md
    assert "trading actionではない" in contract_md
    assert "買い推奨" not in reasons_md
    assert "買い推奨" not in contract_md
    assert "注文" not in reasons_md
    assert "注文" not in contract_md
