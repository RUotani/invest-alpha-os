from __future__ import annotations

import pytest

from invis_alpha_os.product.candidate_scoring_contract_v91 import (
    CandidateScoreBreakdown,
    CandidateScoreInput,
    CandidateScoreWeights,
    ScoreBand,
    classify_score_band,
    fixture_candidates_v91,
    format_candidate_scoring_contract_markdown,
    max_weighted_score,
    normalized_score,
    score_candidate,
    score_candidates,
    validate_score_breakdown,
    weighted_score,
)


def test_weighted_score_and_normalized_score_are_calculated() -> None:
    breakdown = CandidateScoreBreakdown(
        theme_fit=5,
        business_momentum=4,
        valuation_sanity=3,
        technical_demand=2,
        financial_quality=4,
        portfolio_fit=3,
        evidence_quality=4,
    )

    assert weighted_score(breakdown) == pytest.approx(29.2)
    assert max_weighted_score() == pytest.approx(40.0)
    assert normalized_score(breakdown) == pytest.approx(73.0)


def test_score_breakdown_rejects_out_of_range_axis() -> None:
    breakdown = CandidateScoreBreakdown(
        theme_fit=6,
        business_momentum=4,
        valuation_sanity=3,
        technical_demand=2,
        financial_quality=4,
        portfolio_fit=3,
        evidence_quality=4,
    )

    with pytest.raises(ValueError, match="theme_fit"):
        validate_score_breakdown(breakdown)


def test_hard_veto_axes_force_blocked_band() -> None:
    assert classify_score_band(
        CandidateScoreBreakdown(5, 5, 5, 5, 5, 5, 1)
    ) is ScoreBand.BLOCKED
    assert classify_score_band(
        CandidateScoreBreakdown(5, 5, 5, 5, 5, 1, 5)
    ) is ScoreBand.BLOCKED
    assert classify_score_band(
        CandidateScoreBreakdown(5, 5, 5, 5, 1, 5, 5)
    ) is ScoreBand.BLOCKED


def test_band_thresholds_watch_deep_dive_and_high_conviction_review() -> None:
    watch = CandidateScoreBreakdown(3, 3, 3, 2, 3, 2, 3)
    deep_dive = CandidateScoreBreakdown(4, 4, 3, 3, 4, 2, 3)
    high = CandidateScoreBreakdown(5, 5, 4, 4, 5, 4, 4)

    assert classify_score_band(watch) is ScoreBand.WATCH
    assert classify_score_band(deep_dive) is ScoreBand.DEEP_DIVE
    assert classify_score_band(high) is ScoreBand.HIGH_CONVICTION_REVIEW


def test_score_candidate_returns_veto_keys_and_context() -> None:
    candidate = CandidateScoreInput(
        symbol="HYPE_E",
        name="Hype Theme E",
        score_breakdown=CandidateScoreBreakdown(5, 2, 1, 5, 1, 1, 1),
        reasons_ja=("テーマと短期需給だけが強い",),
        missing_evidence_ja=("財務・根拠・portfolio整合が不足",),
        portfolio_constraints_ja=("高ボラと重複リスクを悪化させる可能性",),
    )

    result = score_candidate(candidate)

    assert result.band is ScoreBand.BLOCKED
    assert result.veto_keys == (
        "blocked_missing_evidence",
        "blocked_portfolio_constraint",
        "blocked_financial_quality",
    )
    assert result.reasons_ja == candidate.reasons_ja
    assert result.missing_evidence_ja == candidate.missing_evidence_ja
    assert result.portfolio_constraints_ja == candidate.portfolio_constraints_ja


def test_fixture_candidate_bands_are_stable() -> None:
    results = {result.symbol: result for result in score_candidates(fixture_candidates_v91())}

    assert results["GRID_A"].band is ScoreBand.BLOCKED
    assert results["ROBO_B"].band is ScoreBand.DEEP_DIVE
    assert results["MAT_C"].band is ScoreBand.WATCH
    assert results["CASH_D"].band is ScoreBand.HIGH_CONVICTION_REVIEW
    assert results["HYPE_E"].band is ScoreBand.BLOCKED
    assert results["CASH_D"].veto_keys == ()


def test_custom_weights_affect_normalized_score() -> None:
    breakdown = CandidateScoreBreakdown(3, 3, 3, 3, 3, 3, 3)
    weights = CandidateScoreWeights(portfolio_fit=2.0, evidence_quality=2.0)

    assert weighted_score(breakdown, weights=weights) == pytest.approx(27.9)
    assert normalized_score(breakdown, weights=weights) == pytest.approx(60.0)


def test_markdown_contract_lists_axes_bands_and_fixture_results() -> None:
    md = format_candidate_scoring_contract_markdown()

    assert "## Candidate Scoring Contract v91" in md
    assert "このscoreは売買指示ではなく、深掘り優先度を決めるための評価契約です。" in md
    for axis in (
        "theme_fit",
        "business_momentum",
        "valuation_sanity",
        "technical_demand",
        "financial_quality",
        "portfolio_fit",
        "evidence_quality",
    ):
        assert axis in md
    assert "| HIGH_CONVICTION_REVIEW | >=80 | 高優先でレビュー。ただし実行指示ではない |" in md
    assert "blocked_missing_evidence" in md
    assert "| CASH_D | HIGH_CONVICTION_REVIEW |" in md
    assert "| HYPE_E | BLOCKED |" in md
    assert "買い推奨" not in md
    assert "注文" not in md
