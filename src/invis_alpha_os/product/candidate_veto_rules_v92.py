"""Candidate veto rules v92 (source-only / fixture-only)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from invis_alpha_os.product.candidate_scoring_contract_v91 import CandidateScoreResult


class VetoSeverity(Enum):
    INFO = "info"
    SOFT = "soft"
    HARD = "hard"


@dataclass(frozen=True)
class CandidateVetoInput:
    symbol: str
    normalized_score: float
    evidence_quality: int
    portfolio_fit: int
    valuation_sanity: int
    technical_demand: int
    financial_quality: int
    theme_fit: int = 0
    business_momentum: int = 0
    liquidity_score: int | None = None
    duplicate_exposure: bool = False


@dataclass(frozen=True)
class CandidateVetoReason:
    key: str
    severity: VetoSeverity
    description_ja: str
    next_check_ja: str


@dataclass(frozen=True)
class CandidateVetoResult:
    symbol: str
    reasons: tuple[CandidateVetoReason, ...]

    @property
    def has_hard_veto(self) -> bool:
        return any(reason.severity is VetoSeverity.HARD for reason in self.reasons)

    @property
    def has_soft_veto(self) -> bool:
        return any(reason.severity is VetoSeverity.SOFT for reason in self.reasons)


VETO_RULE_ORDER: tuple[str, ...] = (
    "missing_evidence",
    "portfolio_constraint_breach",
    "valuation_extreme",
    "technical_overheat",
    "financial_quality_red_flag",
    "liquidity_insufficient",
    "theme_only_hype",
    "duplicate_exposure",
)

VETO_RULE_CONDITION_JA: dict[str, str] = {
    "missing_evidence": "evidence_quality <= 1",
    "portfolio_constraint_breach": "portfolio_fit <= 1",
    "valuation_extreme": "valuation_sanity <= 1（technical_demand >= 4ならHARDへ格上げ）",
    "technical_overheat": "technical_demand >= 5 and valuation_sanity <= 2",
    "financial_quality_red_flag": "financial_quality <= 1",
    "liquidity_insufficient": "liquidity_score is not None and liquidity_score <= 1",
    "theme_only_hype": "theme_fit >= 4 and evidence_quality <= 2 and business_momentum <= 2",
    "duplicate_exposure": "duplicate_exposure is True",
}

VETO_RULE_PURPOSE_JA: dict[str, str] = {
    "missing_evidence": "根拠不足の候補を深掘り前に止める",
    "portfolio_constraint_breach": "現金不足・個別株過多・株式比率過多を悪化させる候補を止める",
    "valuation_extreme": "割高/割安の根拠が弱いまま過熱評価へ進むことを抑制する",
    "technical_overheat": "短期需給だけで候補を持ち上げることを抑制する",
    "financial_quality_red_flag": "財務悪化候補を深掘り前に止める",
    "liquidity_insufficient": "流動性・出来高・売買可能性の根拠不足を止める",
    "theme_only_hype": "テーマだけが強く、事業/根拠が弱い候補を抑制する",
    "duplicate_exposure": "既存の指数・業種・テーマリスクとの重複を抑制する",
}

_SCORE_FIELDS: tuple[str, ...] = (
    "evidence_quality",
    "portfolio_fit",
    "valuation_sanity",
    "technical_demand",
    "financial_quality",
    "theme_fit",
    "business_momentum",
)


def _validate_candidate(candidate: CandidateVetoInput) -> None:
    if not candidate.symbol:
        raise ValueError("symbol must not be empty")
    if candidate.normalized_score < 0 or candidate.normalized_score > 100:
        raise ValueError("normalized_score must be between 0 and 100")
    for field in _SCORE_FIELDS:
        value = int(getattr(candidate, field))
        if value < 0 or value > 5:
            raise ValueError(f"{field} must be between 0 and 5")
    if candidate.liquidity_score is not None and (
        candidate.liquidity_score < 0 or candidate.liquidity_score > 5
    ):
        raise ValueError("liquidity_score must be between 0 and 5")


def _reason(
    key: str,
    severity: VetoSeverity,
    *,
    description_ja: str,
    next_check_ja: str,
) -> CandidateVetoReason:
    return CandidateVetoReason(
        key=key,
        severity=severity,
        description_ja=description_ja,
        next_check_ja=next_check_ja,
    )


def evaluate_candidate_vetoes(candidate: CandidateVetoInput) -> CandidateVetoResult:
    _validate_candidate(candidate)
    reasons: list[CandidateVetoReason] = []

    if candidate.evidence_quality <= 1:
        reasons.append(
            _reason(
                "missing_evidence",
                VetoSeverity.HARD,
                description_ja="根拠品質が低く、scoreの解釈に必要な材料が不足しています。",
                next_check_ja="coverage、score内訳、価格根拠、一次情報の有無を確認します。",
            )
        )
    if candidate.portfolio_fit <= 1:
        reasons.append(
            _reason(
                "portfolio_constraint_breach",
                VetoSeverity.HARD,
                description_ja="現金比率・個別株比率・株式系比率の制約と整合しません。",
                next_check_ja="現金回復、個別株19.6%、株式系67.8%との重複を確認します。",
            )
        )
    if candidate.valuation_sanity <= 1:
        severity = VetoSeverity.HARD if candidate.technical_demand >= 4 else VetoSeverity.SOFT
        reasons.append(
            _reason(
                "valuation_extreme",
                severity,
                description_ja="valuationの妥当性が弱く、需給が強い場合は過熱リスクがあります。",
                next_check_ja="valuation指標、過去レンジ、同業比較、根拠品質を確認します。",
            )
        )
    if candidate.technical_demand >= 5 and candidate.valuation_sanity <= 2:
        reasons.append(
            _reason(
                "technical_overheat",
                VetoSeverity.SOFT,
                description_ja="短期需給が強い一方でvaluation確認が不足し、過熱を誤認するリスクがあります。",
                next_check_ja="出来高、価格レンジ、急騰要因、反落時の支持線を確認します。",
            )
        )
    if candidate.financial_quality <= 1:
        reasons.append(
            _reason(
                "financial_quality_red_flag",
                VetoSeverity.HARD,
                description_ja="財務品質が低く、深掘り前に安全性確認が必要です。",
                next_check_ja="負債、FCF、利益率、会計上の一過性要因を確認します。",
            )
        )
    if candidate.liquidity_score is not None and candidate.liquidity_score <= 1:
        reasons.append(
            _reason(
                "liquidity_insufficient",
                VetoSeverity.SOFT,
                description_ja="流動性または出来高の確認が不足しています。",
                next_check_ja="平均出来高、スプレッド、売買可能性、板の薄さを確認します。",
            )
        )
    if candidate.theme_fit >= 4 and candidate.evidence_quality <= 2 and candidate.business_momentum <= 2:
        reasons.append(
            _reason(
                "theme_only_hype",
                VetoSeverity.SOFT,
                description_ja="テーマ適合だけが強く、事業モメンタムと根拠が追いついていません。",
                next_check_ja="売上/受注/利益率の進捗、具体案件、継続性を確認します。",
            )
        )
    if candidate.duplicate_exposure:
        reasons.append(
            _reason(
                "duplicate_exposure",
                VetoSeverity.SOFT,
                description_ja="既存の指数・業種・テーマリスクと重複する可能性があります。",
                next_check_ja="既存保有、ETF、投信、テーマ別exposureとの重なりを確認します。",
            )
        )

    return CandidateVetoResult(symbol=candidate.symbol, reasons=tuple(reasons))


def veto_input_from_score_result(
    result: CandidateScoreResult,
    *,
    liquidity_score: int | None = None,
    duplicate_exposure: bool = False,
) -> CandidateVetoInput:
    breakdown = result.score_breakdown
    return CandidateVetoInput(
        symbol=result.symbol,
        normalized_score=result.normalized_score,
        evidence_quality=breakdown.evidence_quality,
        portfolio_fit=breakdown.portfolio_fit,
        valuation_sanity=breakdown.valuation_sanity,
        technical_demand=breakdown.technical_demand,
        financial_quality=breakdown.financial_quality,
        theme_fit=breakdown.theme_fit,
        business_momentum=breakdown.business_momentum,
        liquidity_score=liquidity_score,
        duplicate_exposure=duplicate_exposure,
    )


def render_candidate_veto_reasons_markdown(result: CandidateVetoResult) -> str:
    lines = [
        f"## Candidate Veto Reasons: {result.symbol}",
        "",
        "このvetoは売買指示ではなく、深掘り前の安全確認です。",
        "",
    ]
    if not result.reasons:
        lines.extend(
            [
                "veto reasonはありません。",
                "",
                "ただし、これは実行承認ではありません。別途、根拠確認・portfolio制約確認・人間レビューが必要です。",
                "",
            ]
        )
        return "\n".join(lines)
    lines.extend(
        [
            "| Key | Severity | 説明 | 次確認 |",
            "|---|---|---|---|",
        ]
    )
    for reason in result.reasons:
        lines.append(
            f"| {reason.key} | {reason.severity.name} | {reason.description_ja} | {reason.next_check_ja} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_veto_rule_contract_markdown() -> str:
    lines = [
        "## Candidate Veto Rule Contract v92",
        "",
        "このcontractは、候補scoreを売買判断へ直結させないためのsource-only / fixture-only安全契約です。",
        "",
        "### Rules",
        "",
        "| Key | Condition | Purpose |",
        "|---|---|---|",
    ]
    for key in VETO_RULE_ORDER:
        lines.append(f"| {key} | {VETO_RULE_CONDITION_JA[key]} | {VETO_RULE_PURPOSE_JA[key]} |")
    lines.extend(
        [
            "",
            "### Severity",
            "",
            "- `HARD`: 深掘り前に停止し、人間レビューで根拠または制約を確認する",
            "- `SOFT`: 候補を抑制し、次確認が終わるまで優先度を上げない",
            "- `INFO`: 将来の説明用。v92の自動付与対象ではない",
            "",
            "### Explicit Non-Approval",
            "",
            "- trading actionではない",
            "- order placementではない",
            "- provider live accessではない",
            "- market-data live fetchではない",
            "- cache writeではない",
            "- actual refresh/importではない",
            "- broker API accessではない",
        ]
    )
    return "\n".join(lines)
