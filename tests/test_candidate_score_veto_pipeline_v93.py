from __future__ import annotations

import pytest

from invis_alpha_os.product.candidate_score_veto_pipeline_v93 import (
    build_fixture_integrated_candidate_assessments_v93,
    build_integrated_candidate_assessment,
    render_integrated_candidate_assessment_markdown,
    render_integrated_candidate_assessment_summary_lines,
)
from invis_alpha_os.product.candidate_scoring_contract_v91 import (
    CandidateScoreBreakdown,
    CandidateScoreResult,
    ScoreBand,
)


def _score_result(
    *,
    symbol: str,
    band: ScoreBand,
    normalized_score: float,
    breakdown: CandidateScoreBreakdown,
) -> CandidateScoreResult:
    return CandidateScoreResult(
        symbol=symbol,
        name=None,
        weighted_score=normalized_score,
        max_score=100.0,
        normalized_score=normalized_score,
        band=band,
        score_breakdown=breakdown,
        reasons_ja=(),
        missing_evidence_ja=(),
        portfolio_constraints_ja=(),
    )


def test_hard_veto_forces_veto_blocked() -> None:
    assessment = build_integrated_candidate_assessment(
        _score_result(
            symbol="HARD_A",
            band=ScoreBand.DEEP_DIVE,
            normalized_score=72.0,
            breakdown=CandidateScoreBreakdown(4, 4, 3, 3, 4, 1, 4),
        )
    )

    assert assessment.pipeline_stage == "veto_blocked"
    assert assessment.action_label_ja == "veto確認"
    assert assessment.has_hard_veto is True
    assert assessment.veto_keys == ("portfolio_constraint_breach",)


def test_blocked_score_without_hard_veto_becomes_score_blocked() -> None:
    assessment = build_integrated_candidate_assessment(
        _score_result(
            symbol="SCORE_A",
            band=ScoreBand.BLOCKED,
            normalized_score=42.0,
            breakdown=CandidateScoreBreakdown(2, 2, 2, 2, 2, 2, 2),
        )
    )

    assert assessment.pipeline_stage == "score_blocked"
    assert assessment.action_label_ja == "根拠補完"
    assert assessment.has_hard_veto is False


def test_soft_veto_deep_dive_is_reduced_to_watch() -> None:
    assessment = build_integrated_candidate_assessment(
        _score_result(
            symbol="SOFT_DD",
            band=ScoreBand.DEEP_DIVE,
            normalized_score=73.0,
            breakdown=CandidateScoreBreakdown(4, 4, 3, 3, 4, 3, 4),
        ),
        duplicate_exposure=True,
    )

    assert assessment.pipeline_stage == "watch"
    assert assessment.action_label_ja == "追加確認"
    assert assessment.has_soft_veto is True
    assert assessment.veto_keys == ("duplicate_exposure",)


def test_watch_band_stays_watch() -> None:
    assessment = build_integrated_candidate_assessment(
        _score_result(
            symbol="WATCH_A",
            band=ScoreBand.WATCH,
            normalized_score=58.0,
            breakdown=CandidateScoreBreakdown(3, 3, 3, 3, 3, 3, 3),
        )
    )

    assert assessment.pipeline_stage == "watch"
    assert assessment.action_label_ja == "監視"


def test_high_conviction_without_veto_stays_high_review() -> None:
    assessment = build_integrated_candidate_assessment(
        _score_result(
            symbol="HIGH_A",
            band=ScoreBand.HIGH_CONVICTION_REVIEW,
            normalized_score=86.0,
            breakdown=CandidateScoreBreakdown(5, 5, 4, 4, 5, 4, 5),
        )
    )

    assert assessment.pipeline_stage == "high_conviction_review"
    assert assessment.action_label_ja == "高優先レビュー"
    assert assessment.has_hard_veto is False
    assert assessment.has_soft_veto is False


def test_high_conviction_with_hard_veto_is_veto_blocked() -> None:
    assessment = build_integrated_candidate_assessment(
        _score_result(
            symbol="HIGH_HARD",
            band=ScoreBand.HIGH_CONVICTION_REVIEW,
            normalized_score=86.0,
            breakdown=CandidateScoreBreakdown(5, 5, 4, 4, 1, 4, 5),
        )
    )

    assert assessment.pipeline_stage == "veto_blocked"
    assert assessment.action_label_ja == "veto確認"
    assert assessment.veto_keys == ("financial_quality_red_flag",)


def test_invalid_score_from_v92_validation_is_rejected() -> None:
    with pytest.raises(ValueError, match="normalized_score"):
        build_integrated_candidate_assessment(
            _score_result(
                symbol="BAD_A",
                band=ScoreBand.WATCH,
                normalized_score=101.0,
                breakdown=CandidateScoreBreakdown(3, 3, 3, 3, 3, 3, 3),
            )
        )


def test_fixture_assessments_cover_score_veto_pipeline_states() -> None:
    assessments = {row.symbol: row for row in build_fixture_integrated_candidate_assessments_v93()}

    assert assessments["GRID_A"].pipeline_stage == "veto_blocked"
    assert assessments["ROBO_B"].pipeline_stage == "watch"
    assert assessments["MAT_C"].pipeline_stage == "watch"
    assert assessments["CASH_D"].pipeline_stage == "high_conviction_review"
    assert assessments["HYPE_E"].pipeline_stage == "veto_blocked"
    assert assessments["ROBO_B"].veto_keys == ("duplicate_exposure",)


def test_markdown_and_summary_lines_are_safe_and_informative() -> None:
    assessments = build_fixture_integrated_candidate_assessments_v93()
    markdown = render_integrated_candidate_assessment_markdown(assessments)
    lines = render_integrated_candidate_assessment_summary_lines(assessments)

    assert "## Score / Veto 統合サマリー" in markdown
    assert "| 候補 | Score band | Score | Veto | Pipeline | 今週の扱い | 次確認 |" in markdown
    assert "HARD: missing_evidence" in markdown
    assert "SOFT: duplicate_exposure" in markdown
    assert "veto_blocked" in markdown
    assert "Score/Veto: 深掘り候補0 / 監視2 / veto確認2 / score補完0 / 高優先レビュー1。" in lines
    assert "実行指示ではなく" in lines[1]
    assert "買い推奨" not in markdown
    assert "注文" not in markdown


def test_empty_markdown_still_renders_contract_shape() -> None:
    markdown = render_integrated_candidate_assessment_markdown(())

    assert "| — | — | — | — | — | — | — |" in markdown
    assert "Score/Veto: 深掘り候補0 / 監視0 / veto確認0 / score補完0 / 高優先レビュー0。" in markdown
