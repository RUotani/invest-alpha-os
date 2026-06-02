"""Candidate Scoring Contract v91 (source-only / fixture-only)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ScoreBand(Enum):
    BLOCKED = "blocked"
    WATCH = "watch"
    DEEP_DIVE = "deep_dive"
    HIGH_CONVICTION_REVIEW = "high_conviction_review"


@dataclass(frozen=True)
class CandidateScoreBreakdown:
    theme_fit: int
    business_momentum: int
    valuation_sanity: int
    technical_demand: int
    financial_quality: int
    portfolio_fit: int
    evidence_quality: int


@dataclass(frozen=True)
class CandidateScoreWeights:
    theme_fit: float = 1.2
    business_momentum: float = 1.3
    valuation_sanity: float = 1.0
    technical_demand: float = 0.8
    financial_quality: float = 1.0
    portfolio_fit: float = 1.4
    evidence_quality: float = 1.3


@dataclass(frozen=True)
class CandidateScoreInput:
    symbol: str
    name: str | None
    score_breakdown: CandidateScoreBreakdown
    reasons_ja: tuple[str, ...] = ()
    missing_evidence_ja: tuple[str, ...] = ()
    portfolio_constraints_ja: tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateScoreResult:
    symbol: str
    name: str | None
    weighted_score: float
    max_score: float
    normalized_score: float
    band: ScoreBand
    score_breakdown: CandidateScoreBreakdown
    reasons_ja: tuple[str, ...]
    missing_evidence_ja: tuple[str, ...]
    portfolio_constraints_ja: tuple[str, ...]
    veto_keys: tuple[str, ...] = ()


SCORE_AXIS_ORDER: tuple[str, ...] = (
    "theme_fit",
    "business_momentum",
    "valuation_sanity",
    "technical_demand",
    "financial_quality",
    "portfolio_fit",
    "evidence_quality",
)

SCORE_AXIS_DESCRIPTION_JA: dict[str, str] = {
    "theme_fit": "長期テーマとの適合",
    "business_momentum": "業績・受注・利益率の勢い",
    "valuation_sanity": "割高/割安の初期確認",
    "technical_demand": "需給・価格モメンタム",
    "financial_quality": "財務安全性・FCF・負債",
    "portfolio_fit": "現金/個別株/株式比率制約との整合",
    "evidence_quality": "根拠の量と質",
}

PORTFOLIO_CONTEXT_JA_V91: tuple[str, ...] = (
    "現金: 508.2万円 / 11.7%（最低15%、できれば20%方向へ回復）",
    "個別株: 846.3万円 / 19.6%（10〜15%方向へ圧縮）",
    "株式系合計: 2,934.5万円 / 67.8%（既に高め）",
)


def _axis_values(breakdown: CandidateScoreBreakdown) -> tuple[int, ...]:
    return tuple(int(getattr(breakdown, axis)) for axis in SCORE_AXIS_ORDER)


def validate_score_breakdown(breakdown: CandidateScoreBreakdown) -> None:
    for axis, value in zip(SCORE_AXIS_ORDER, _axis_values(breakdown), strict=True):
        if value < 0 or value > 5:
            raise ValueError(f"{axis} must be between 0 and 5")


def _weight_values(weights: CandidateScoreWeights) -> tuple[float, ...]:
    return tuple(float(getattr(weights, axis)) for axis in SCORE_AXIS_ORDER)


def weighted_score(
    breakdown: CandidateScoreBreakdown,
    *,
    weights: CandidateScoreWeights = CandidateScoreWeights(),
) -> float:
    validate_score_breakdown(breakdown)
    total = sum(value * weight for value, weight in zip(_axis_values(breakdown), _weight_values(weights), strict=True))
    return round(total, 4)


def max_weighted_score(*, weights: CandidateScoreWeights = CandidateScoreWeights()) -> float:
    return round(sum(5 * weight for weight in _weight_values(weights)), 4)


def normalized_score(
    breakdown: CandidateScoreBreakdown,
    *,
    weights: CandidateScoreWeights = CandidateScoreWeights(),
) -> float:
    max_score = max_weighted_score(weights=weights)
    if max_score <= 0:
        raise ValueError("max_score must be positive")
    return round(weighted_score(breakdown, weights=weights) / max_score * 100, 2)


def derive_veto_keys(breakdown: CandidateScoreBreakdown) -> tuple[str, ...]:
    keys: list[str] = []
    if breakdown.evidence_quality <= 1:
        keys.append("blocked_missing_evidence")
    if breakdown.portfolio_fit <= 1:
        keys.append("blocked_portfolio_constraint")
    if breakdown.financial_quality <= 1:
        keys.append("blocked_financial_quality")
    return tuple(keys)


def classify_score_band(
    breakdown: CandidateScoreBreakdown,
    *,
    weights: CandidateScoreWeights = CandidateScoreWeights(),
) -> ScoreBand:
    score = normalized_score(breakdown, weights=weights)
    veto_keys = derive_veto_keys(breakdown)
    if score < 45 or veto_keys:
        return ScoreBand.BLOCKED
    if score < 65:
        return ScoreBand.WATCH
    if score < 80:
        if breakdown.evidence_quality >= 3 and breakdown.portfolio_fit >= 2:
            return ScoreBand.DEEP_DIVE
        return ScoreBand.WATCH
    if breakdown.evidence_quality >= 4 and breakdown.portfolio_fit >= 3:
        return ScoreBand.HIGH_CONVICTION_REVIEW
    return ScoreBand.DEEP_DIVE


def score_candidate(
    candidate: CandidateScoreInput,
    *,
    weights: CandidateScoreWeights = CandidateScoreWeights(),
) -> CandidateScoreResult:
    breakdown = candidate.score_breakdown
    score = weighted_score(breakdown, weights=weights)
    max_score = max_weighted_score(weights=weights)
    return CandidateScoreResult(
        symbol=candidate.symbol,
        name=candidate.name,
        weighted_score=score,
        max_score=max_score,
        normalized_score=round(score / max_score * 100, 2),
        band=classify_score_band(breakdown, weights=weights),
        score_breakdown=breakdown,
        reasons_ja=candidate.reasons_ja,
        missing_evidence_ja=candidate.missing_evidence_ja,
        portfolio_constraints_ja=candidate.portfolio_constraints_ja,
        veto_keys=derive_veto_keys(breakdown),
    )


def score_candidates(
    candidates: Iterable[CandidateScoreInput],
    *,
    weights: CandidateScoreWeights = CandidateScoreWeights(),
) -> tuple[CandidateScoreResult, ...]:
    return tuple(score_candidate(candidate, weights=weights) for candidate in candidates)


def fixture_candidates_v91() -> tuple[CandidateScoreInput, ...]:
    return (
        CandidateScoreInput(
            symbol="GRID_A",
            name="Grid Infrastructure A",
            score_breakdown=CandidateScoreBreakdown(5, 4, 2, 4, 3, 2, 1),
            reasons_ja=("テーマ適合と需給は強い",),
            missing_evidence_ja=("バリュエーションと定量根拠が不足",),
            portfolio_constraints_ja=("現金11.7%のため新規リスクには不向き",),
        ),
        CandidateScoreInput(
            symbol="ROBO_B",
            name="Robotics Compounder B",
            score_breakdown=CandidateScoreBreakdown(4, 4, 3, 3, 4, 2, 3),
            reasons_ja=("業績・財務は強いが、個別株19.6%の制約がある",),
            missing_evidence_ja=("position sizing前提は未確認",),
            portfolio_constraints_ja=("監視候補として扱い、現金回復を優先",),
        ),
        CandidateScoreInput(
            symbol="MAT_C",
            name="Materials Value C",
            score_breakdown=CandidateScoreBreakdown(2, 3, 5, 2, 4, 3, 3),
            reasons_ja=("割高感は小さいがテーマ適合は弱い",),
            missing_evidence_ja=("事業モメンタムの追加確認が必要",),
            portfolio_constraints_ja=("株式系67.8%の中で重複を確認",),
        ),
        CandidateScoreInput(
            symbol="CASH_D",
            name="Cash Recovery Candidate D",
            score_breakdown=CandidateScoreBreakdown(4, 4, 4, 3, 5, 5, 5),
            reasons_ja=("既存リスクを増やさず確認価値が高い",),
            missing_evidence_ja=(),
            portfolio_constraints_ja=("現金回復と整理監視に沿う",),
        ),
        CandidateScoreInput(
            symbol="HYPE_E",
            name="Hype Theme E",
            score_breakdown=CandidateScoreBreakdown(5, 2, 1, 5, 1, 1, 1),
            reasons_ja=("テーマと短期需給だけが強い",),
            missing_evidence_ja=("財務・根拠・portfolio整合が不足",),
            portfolio_constraints_ja=("高ボラと重複リスクを悪化させる可能性",),
        ),
    )


def format_candidate_scoring_contract_markdown(
    *,
    weights: CandidateScoreWeights = CandidateScoreWeights(),
    include_fixtures: bool = True,
) -> str:
    lines = [
        "## Candidate Scoring Contract v91",
        "",
        "このscoreは売買指示ではなく、深掘り優先度を決めるための評価契約です。",
        "",
        "### Portfolio Context",
        "",
    ]
    lines.extend(f"- {item}" for item in PORTFOLIO_CONTEXT_JA_V91)
    lines.extend(
        [
            "",
            "### Score Axes",
            "",
            "| 評価軸 | Weight | 説明 |",
            "|---|---:|---|",
        ]
    )
    for axis in SCORE_AXIS_ORDER:
        lines.append(f"| {axis} | {getattr(weights, axis):.1f} | {SCORE_AXIS_DESCRIPTION_JA[axis]} |")
    lines.extend(
        [
            "",
            "### Band",
            "",
            "| Band | Score | 意味 |",
            "|---|---:|---|",
            "| BLOCKED | <45 or hard constraint | 深掘り前に根拠補完/制約確認 |",
            "| WATCH | 45-65 | 監視候補 |",
            "| DEEP_DIVE | 65-80 | 深掘り候補 |",
            "| HIGH_CONVICTION_REVIEW | >=80 | 高優先でレビュー。ただし実行指示ではない |",
            "",
            "### Lightweight Veto Keys",
            "",
            "- `blocked_missing_evidence`: evidence_quality <= 1",
            "- `blocked_portfolio_constraint`: portfolio_fit <= 1",
            "- `blocked_financial_quality`: financial_quality <= 1",
        ]
    )
    if include_fixtures:
        results = score_candidates(fixture_candidates_v91(), weights=weights)
        lines.extend(
            [
                "",
                "### Fixture Candidates",
                "",
                "| Symbol | Band | Normalized | Veto Keys |",
                "|---|---|---:|---|",
            ]
        )
        for result in results:
            veto = ", ".join(result.veto_keys) if result.veto_keys else "-"
            lines.append(f"| {result.symbol} | {result.band.name} | {result.normalized_score:.2f} | {veto} |")
    lines.append("")
    return "\n".join(lines)
