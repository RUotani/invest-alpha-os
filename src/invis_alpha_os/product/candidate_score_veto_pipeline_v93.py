"""Candidate score + veto + pipeline integration v93 (source-only / fixture-only)."""

from __future__ import annotations

from dataclasses import dataclass

from invis_alpha_os.product.candidate_scoring_contract_v91 import (
    CandidateScoreResult,
    ScoreBand,
    fixture_candidates_v91,
    score_candidates,
)
from invis_alpha_os.product.candidate_veto_rules_v92 import (
    CandidateVetoResult,
    VetoSeverity,
    evaluate_candidate_vetoes,
    veto_input_from_score_result,
)


@dataclass(frozen=True)
class CandidateIntegratedAssessment:
    symbol: str
    name: str | None
    score_band: str
    normalized_score: float
    has_hard_veto: bool
    has_soft_veto: bool
    veto_keys: tuple[str, ...]
    pipeline_stage: str
    action_label_ja: str
    reason_summary_ja: str
    next_check_ja: str


PIPELINE_STAGE_ORDER: tuple[str, ...] = (
    "coverage_missing",
    "score_blocked",
    "veto_blocked",
    "watch",
    "deep_dive",
    "high_conviction_review",
)


def _severity_label(veto_result: CandidateVetoResult) -> str:
    if veto_result.has_hard_veto:
        return "HARD"
    if veto_result.has_soft_veto:
        return "SOFT"
    return "-"


def _veto_keys(veto_result: CandidateVetoResult) -> tuple[str, ...]:
    return tuple(reason.key for reason in veto_result.reasons)


def _reason_summary(score_result: CandidateScoreResult, veto_result: CandidateVetoResult) -> str:
    severity = _severity_label(veto_result)
    if severity == "-":
        return f"Score {score_result.band.name} / vetoなし。深掘り前の確認対象です。"
    keys = ", ".join(_veto_keys(veto_result))
    return f"Score {score_result.band.name} / veto {severity}: {keys}。"


def _next_check(veto_result: CandidateVetoResult, *, pipeline_stage: str) -> str:
    if veto_result.reasons:
        return veto_result.reasons[0].next_check_ja
    if pipeline_stage == "score_blocked":
        return "score内訳、coverage、根拠品質を確認"
    if pipeline_stage == "watch":
        return "次回runでscore・veto・portfolio制約の変化を確認"
    if pipeline_stage == "deep_dive":
        return "反証、根拠品質、重複exposureを確認"
    if pipeline_stage == "high_conviction_review":
        return "高優先レビューとして、反証とportfolio制約を人間が確認"
    return "coverage、score、vetoの各段階を確認"


def _stage_and_label(
    score_band: ScoreBand,
    veto_result: CandidateVetoResult,
) -> tuple[str, str]:
    if veto_result.has_hard_veto:
        return "veto_blocked", "veto確認"
    if score_band is ScoreBand.BLOCKED:
        return "score_blocked", "根拠補完"
    if score_band is ScoreBand.WATCH:
        return "watch", "監視"
    if score_band is ScoreBand.DEEP_DIVE:
        if veto_result.has_soft_veto:
            return "watch", "追加確認"
        return "deep_dive", "深掘り候補"
    if score_band is ScoreBand.HIGH_CONVICTION_REVIEW:
        if veto_result.has_soft_veto:
            return "deep_dive", "深掘り候補。ただしveto確認"
        return "high_conviction_review", "高優先レビュー"
    raise ValueError(f"unsupported score band: {score_band}")


def build_integrated_candidate_assessment(
    score_result: CandidateScoreResult,
    *,
    liquidity_score: int | None = None,
    duplicate_exposure: bool = False,
) -> CandidateIntegratedAssessment:
    veto_input = veto_input_from_score_result(
        score_result,
        liquidity_score=liquidity_score,
        duplicate_exposure=duplicate_exposure,
    )
    veto_result = evaluate_candidate_vetoes(veto_input)
    pipeline_stage, action_label = _stage_and_label(score_result.band, veto_result)
    return CandidateIntegratedAssessment(
        symbol=score_result.symbol,
        name=score_result.name,
        score_band=score_result.band.name,
        normalized_score=score_result.normalized_score,
        has_hard_veto=veto_result.has_hard_veto,
        has_soft_veto=veto_result.has_soft_veto,
        veto_keys=_veto_keys(veto_result),
        pipeline_stage=pipeline_stage,
        action_label_ja=action_label,
        reason_summary_ja=_reason_summary(score_result, veto_result),
        next_check_ja=_next_check(veto_result, pipeline_stage=pipeline_stage),
    )


def build_fixture_integrated_candidate_assessments_v93() -> tuple[CandidateIntegratedAssessment, ...]:
    results = score_candidates(fixture_candidates_v91())
    overrides: dict[str, dict[str, object]] = {
        "ROBO_B": {"duplicate_exposure": True},
        "HYPE_E": {"liquidity_score": 1, "duplicate_exposure": True},
    }
    assessments: list[CandidateIntegratedAssessment] = []
    for result in results:
        raw = overrides.get(result.symbol, {})
        assessments.append(
            build_integrated_candidate_assessment(
                result,
                liquidity_score=raw.get("liquidity_score"),  # type: ignore[arg-type]
                duplicate_exposure=bool(raw.get("duplicate_exposure", False)),
            )
        )
    return tuple(assessments)


def render_integrated_candidate_assessment_markdown(
    assessments: tuple[CandidateIntegratedAssessment, ...],
) -> str:
    lines = [
        "## Score / Veto 統合サマリー",
        "",
        "この表は売買指示ではなく、候補の深掘り優先度と安全確認ポイントを整理するものです。",
        "",
        "| 候補 | Score band | Score | Veto | Pipeline | 今週の扱い | 次確認 |",
        "|---|---|---:|---|---|---|---|",
    ]
    if not assessments:
        lines.append("| — | — | — | — | — | — | — |")
    for row in assessments:
        veto = _format_veto_cell(row)
        lines.append(
            f"| {row.symbol} | {row.score_band} | {row.normalized_score:.2f} | "
            f"{veto} | {row.pipeline_stage} | {row.action_label_ja} | {row.next_check_ja} |"
        )
    lines.extend(
        [
            "",
            *[f"- {line}" for line in render_integrated_candidate_assessment_summary_lines(assessments)],
            "",
        ]
    )
    return "\n".join(lines)


def render_integrated_candidate_assessment_summary_lines(
    assessments: tuple[CandidateIntegratedAssessment, ...],
) -> tuple[str, ...]:
    deep_dive_like = sum(
        1
        for row in assessments
        if row.pipeline_stage == "deep_dive"
        and not row.has_hard_veto
        and not row.has_soft_veto
    )
    watch_count = sum(1 for row in assessments if row.pipeline_stage == "watch")
    veto_count = sum(1 for row in assessments if row.pipeline_stage == "veto_blocked")
    score_blocked_count = sum(1 for row in assessments if row.pipeline_stage == "score_blocked")
    high_review_count = sum(1 for row in assessments if row.pipeline_stage == "high_conviction_review")
    return (
        (
            "Score/Veto: "
            f"深掘り候補{deep_dive_like} / 監視{watch_count} / "
            f"veto確認{veto_count} / score補完{score_blocked_count} / 高優先レビュー{high_review_count}。"
        ),
        "これは実行指示ではなく、根拠補完と安全確認の分類です。",
    )


def _format_veto_cell(row: CandidateIntegratedAssessment) -> str:
    if row.has_hard_veto:
        prefix = VetoSeverity.HARD.name
    elif row.has_soft_veto:
        prefix = VetoSeverity.SOFT.name
    else:
        return "-"
    return f"{prefix}: {', '.join(row.veto_keys)}"
