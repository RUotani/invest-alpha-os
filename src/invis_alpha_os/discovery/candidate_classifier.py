"""Phase × Role classifier with precedence rules (v1.4 fixture/cache-only)."""

from __future__ import annotations

from dataclasses import dataclass

from invis_alpha_os.discovery.candidate_roles import CandidatePhase, CandidateRole
from invis_alpha_os.discovery.early_discovery_score import (
    EARLY_DISCOVERY_SCORE_THRESHOLD,
    HARD_OVERHEAT_R20,
    compute_early_discovery_score,
    is_hard_overheat,
)
from invis_alpha_os.discovery.theme_dictionary import (
    lookup_theme_labels,
    lookup_ticker_themes,
    role_hint_for_ticker,
)

CASH_RATIO_HARD_GATE = 0.15
SINGLE_STOCK_RATIO_SOFT_GATE = 0.15


@dataclass(frozen=True)
class PortfolioGateContext:
    cash_ratio: float
    single_stock_ratio: float

    @property
    def cash_hard_gate(self) -> bool:
        return self.cash_ratio < CASH_RATIO_HARD_GATE

    @property
    def single_stock_suppressed(self) -> bool:
        return self.single_stock_ratio > SINGLE_STOCK_RATIO_SOFT_GATE

    @property
    def buy_allowance(self) -> str:
        if self.cash_hard_gate and self.single_stock_suppressed:
            return "zero"
        if self.cash_hard_gate or self.single_stock_suppressed:
            return "reduced"
        return "normal"


@dataclass(frozen=True)
class CandidateInput:
    ticker: str
    ret_20d: float | None = None
    ret_60d: float | None = None
    momentum_high: bool = False
    soft_veto: bool = False
    market: str = "jp"

    @property
    def overheat(self) -> bool:
        return is_hard_overheat(ret_20d=self.ret_20d, ret_60d=self.ret_60d) or self.momentum_high


@dataclass(frozen=True)
class ClassificationResult:
    ticker: str
    phase: CandidatePhase
    role: CandidateRole
    early_discovery: bool
    action: str
    next_step: str
    portfolio_gate: str | None
    theme_labels: tuple[str, ...]
    early_discovery_score: float


def _infer_phase(candidate: CandidateInput) -> CandidatePhase:
    if candidate.overheat:
        return CandidatePhase.OVERHEAT
    r20 = candidate.ret_20d
    if r20 is None:
        return CandidatePhase.UNKNOWN
    if r20 < 0.05:
        return CandidatePhase.EARLY
    if r20 < HARD_OVERHEAT_R20:
        return CandidatePhase.ACCEL
    return CandidatePhase.OVERHEAT


def classify_candidate(
    candidate: CandidateInput,
    *,
    portfolio: PortfolioGateContext | None = None,
) -> ClassificationResult:
    """Apply precedence: portfolio gate → hard overheat → soft veto → early score → theme proxy."""

    portfolio = portfolio or PortfolioGateContext(cash_ratio=0.117, single_stock_ratio=0.196)
    themes = lookup_ticker_themes(candidate.ticker)
    theme_labels = lookup_theme_labels(themes)
    score = compute_early_discovery_score(
        ret_20d=candidate.ret_20d,
        ret_60d=candidate.ret_60d,
        overheat=candidate.overheat,
    )
    phase = _infer_phase(candidate)
    gate_label = portfolio.buy_allowance if portfolio.cash_hard_gate or portfolio.single_stock_suppressed else None

    # 2. Hard overheat → Theme Proxy / Do Not Chase
    if candidate.overheat or phase == CandidatePhase.OVERHEAT:
        role = CandidateRole.DO_NOT_CHASE
        hint = role_hint_for_ticker(candidate.ticker)
        if hint == CandidateRole.THEME_PROXY:
            role = CandidateRole.THEME_PROXY
        return ClassificationResult(
            ticker=candidate.ticker,
            phase=CandidatePhase.OVERHEAT,
            role=role,
            early_discovery=False,
            action="do_not_chase",
            next_step="find surrounding / laggard candidates in same theme",
            portfolio_gate=gate_label,
            theme_labels=theme_labels,
            early_discovery_score=score,
        )

    # 3. Soft veto
    if candidate.soft_veto:
        return ClassificationResult(
            ticker=candidate.ticker,
            phase=phase,
            role=CandidateRole.AVOID,
            early_discovery=False,
            action="avoid",
            next_step="wait until veto clears",
            portfolio_gate=gate_label,
            theme_labels=theme_labels,
            early_discovery_score=score,
        )

    # 4. Early Discovery Score (suppressed when portfolio hard gate)
    if score >= EARLY_DISCOVERY_SCORE_THRESHOLD and portfolio.buy_allowance != "zero":
        return ClassificationResult(
            ticker=candidate.ticker,
            phase=phase,
            role=CandidateRole.EARLY_DISCOVERY,
            early_discovery=True,
            action="research_early_candidate",
            next_step="confirm thesis, counter-evidence, portfolio fit",
            portfolio_gate=gate_label,
            theme_labels=theme_labels,
            early_discovery_score=score,
        )

    # 5. Momentum / theme proxy fallback
    hint = role_hint_for_ticker(candidate.ticker)
    role = hint or CandidateRole.WATCH
    return ClassificationResult(
        ticker=candidate.ticker,
        phase=phase,
        role=role,
        early_discovery=False,
        action="watch",
        next_step="monitor; not a chase candidate",
        portfolio_gate=gate_label,
        theme_labels=theme_labels,
        early_discovery_score=score,
    )


def classify_unified_candidate_fields(
    *,
    instrument_id: str,
    return_20d: float | None,
    return_60d: float | None,
    categories: tuple[str, ...],
    labels: tuple[str, ...],
    portfolio: PortfolioGateContext | None = None,
) -> ClassificationResult:
    momentum_high = "overheated_caution" in categories
    soft_veto = "overheat_caution" in labels or "low_liquidity_caution" in labels
    return classify_candidate(
        CandidateInput(
            ticker=instrument_id,
            ret_20d=return_20d,
            ret_60d=return_60d,
            momentum_high=momentum_high,
            soft_veto=soft_veto,
        ),
        portfolio=portfolio,
    )
