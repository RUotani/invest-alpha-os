"""Normalized weekly report buckets — single source for counts and rendered sections (v1.6)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from invis_alpha_os.discovery.candidate_classifier import (
    PortfolioGateContext,
    classify_unified_candidate_fields,
)
from invis_alpha_os.discovery.candidate_roles import THEME_PROXY_ROLES, CandidatePhase
from invis_alpha_os.discovery.early_discovery_score import is_report_ui_overheat
from invis_alpha_os.discovery.freshness import (
    FreshnessInfo,
    freshness_info_for_latest_date,
)

DEFAULT_PORTFOLIO_GATE_V14 = PortfolioGateContext(cash_ratio=0.117, single_stock_ratio=0.196)

if TYPE_CHECKING:
    from invis_alpha_os.product.weekly_candidate_brief_v0 import (
        CandidateCard,
        UnifiedCandidate,
        WeeklyCandidateBriefV0,
    )

INVESTABLE_SECTION_TITLE = "## 初動・深掘り候補"
OVERHEAT_SECTION_TITLE = "## 過熱代表 / Do Not Chase"
FRESHNESS_PENDING_SECTION_TITLE = "## データ鮮度不足リスト"
DEVELOPER_APPENDIX_SECTION_TITLE = "## 開発者向け集計"
COMMON_DATA_WARNING = (
    "※ 候補カードの定量数値はキャッシュ由来です。鮮度ラベルと合わせて解釈してください。"
)


@dataclass(frozen=True)
class CandidateRenderItem:
    card: CandidateCard
    freshness: FreshnessInfo
    role_label: str


@dataclass(frozen=True)
class WeeklyReportRenderModel:
    report_date: str
    investable: tuple[CandidateRenderItem, ...]
    overheated: tuple[CandidateRenderItem, ...]
    freshness_pending: tuple[CandidateRenderItem, ...]

    @property
    def investable_count(self) -> int:
        return len(self.investable)

    @property
    def overheat_count(self) -> int:
        return len(self.overheated)

    @property
    def freshness_pending_count(self) -> int:
        return len(self.freshness_pending)

    @property
    def score_veto_deep_dive_count(self) -> int:
        return self.investable_count


def _role_label_for_investable(*, rank: int) -> str:
    if rank == 1:
        return "初動候補"
    return "深掘り候補"


def is_overheated_unified_candidate(
    c: UnifiedCandidate,
    *,
    portfolio: PortfolioGateContext,
) -> bool:
    if is_report_ui_overheat(
        ret_20d=c.return_20d,
        ret_60d=c.return_60d,
        categories=c.categories,
        labels=c.labels,
    ):
        return True
    cls = classify_unified_candidate_fields(
        instrument_id=c.instrument_id,
        return_20d=c.return_20d,
        return_60d=c.return_60d,
        categories=c.categories,
        labels=c.labels,
        portfolio=portfolio,
    )
    if cls.role in THEME_PROXY_ROLES:
        return True
    return cls.phase == CandidatePhase.OVERHEAT


def partition_ranked_candidates_v16(
    ranked: list[UnifiedCandidate],
    *,
    report_date: str,
    portfolio: PortfolioGateContext = DEFAULT_PORTFOLIO_GATE_V14,
) -> tuple[list[UnifiedCandidate], list[UnifiedCandidate], list[UnifiedCandidate]]:
    early: list[UnifiedCandidate] = []
    overheated: list[UnifiedCandidate] = []
    freshness_pending: list[UnifiedCandidate] = []

    for c in ranked:
        freshness = freshness_info_for_latest_date(c.latest_date, report_date)
        if not freshness.can_promote:
            freshness_pending.append(c)
            continue
        if is_overheated_unified_candidate(c, portfolio=portfolio):
            overheated.append(c)
            continue
        cls = classify_unified_candidate_fields(
            instrument_id=c.instrument_id,
            return_20d=c.return_20d,
            return_60d=c.return_60d,
            categories=c.categories,
            labels=c.labels,
            portfolio=portfolio,
        )
        if cls.early_discovery:
            early.append(c)

    return early, overheated, freshness_pending


def _render_item(
    card: CandidateCard,
    *,
    report_date: str,
    role_label: str,
) -> CandidateRenderItem:
    freshness = freshness_info_for_latest_date(card.candidate.latest_date, report_date)
    return CandidateRenderItem(card=card, freshness=freshness, role_label=role_label)


def build_weekly_report_render_model(
    brief: WeeklyCandidateBriefV0,
    *,
    portfolio: PortfolioGateContext = DEFAULT_PORTFOLIO_GATE_V14,
) -> WeeklyReportRenderModel:
    investable_items: list[CandidateRenderItem] = []
    for rank, card in enumerate(brief.early_discovery_picks, start=1):
        freshness = freshness_info_for_latest_date(card.candidate.latest_date, brief.report_date)
        if not freshness.can_promote:
            continue
        if is_overheated_unified_candidate(card.candidate, portfolio=portfolio):
            continue
        investable_items.append(
            _render_item(
                card,
                report_date=brief.report_date,
                role_label=_role_label_for_investable(rank=rank),
            )
        )

    overheated_items = [
        _render_item(card, report_date=brief.report_date, role_label="テーマ代表（追いかけ禁止）")
        for card in brief.overheated_leaders
    ]

    pending_cards = list(brief.freshness_pending_picks)
    pending_ids = {c.candidate.instrument_id for c in pending_cards}
    for card in brief.early_discovery_picks + brief.top_picks:
        if card.candidate.instrument_id in pending_ids:
            continue
        freshness = freshness_info_for_latest_date(card.candidate.latest_date, brief.report_date)
        if not freshness.can_promote:
            pending_cards.append(card)
            pending_ids.add(card.candidate.instrument_id)

    freshness_items = [
        _render_item(card, report_date=brief.report_date, role_label="データ更新待ち")
        for card in pending_cards
    ]

    return WeeklyReportRenderModel(
        report_date=brief.report_date,
        investable=tuple(investable_items),
        overheated=tuple(overheated_items),
        freshness_pending=tuple(freshness_items),
    )


def candidate_card_title(card: CandidateCard) -> str:
    c = card.candidate
    return f"{c.instrument_id}（{c.display_name}） {c.market.upper()}"
