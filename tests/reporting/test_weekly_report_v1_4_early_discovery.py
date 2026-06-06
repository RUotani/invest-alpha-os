from __future__ import annotations

from invis_alpha_os.discovery.candidate_classifier import PortfolioGateContext
from invis_alpha_os.product.weekly_candidate_brief_v0 import (
    CandidateCard,
    UnifiedCandidate,
    WeeklyCandidateBriefV0,
    build_weekly_candidate_brief_v0,
    format_weekly_candidate_brief_v0_copy,
    _partition_ranked_by_v14_classification,
)


def _candidate(
    symbol: str,
    name: str,
    *,
    market: str = "us",
    return_20d: float = 0.12,
    categories: tuple[str, ...] = ("rapid_mover",),
    labels: tuple[str, ...] = (),
) -> UnifiedCandidate:
    return UnifiedCandidate(
        market=market,
        instrument_id=symbol,
        display_name=name,
        discovery_score=8,
        latest_date="2026-06-05",
        close=100.0,
        return_5d=0.03,
        return_20d=return_20d,
        return_60d=0.21,
        labels=labels,
        categories=categories,
        data_quality="ok",
        reason="fixture",
        themes=("us_equity",),
    )


def test_285a_partitioned_to_overheated_not_early_discovery() -> None:
    ranked = [
        _candidate("285A", "キオクシア", market="jp", return_20d=0.73, categories=("rapid_mover", "overheated_caution"), labels=("overheat_caution",)),
        _candidate("AAPL", "Apple", return_20d=0.28),
    ]
    relaxed = PortfolioGateContext(cash_ratio=0.20, single_stock_ratio=0.12)
    early, overheated = _partition_ranked_by_v14_classification(ranked, portfolio=relaxed)
    assert [c.instrument_id for c in early] == ["AAPL"]
    assert [c.instrument_id for c in overheated] == ["285A"]


def test_v14_report_sections_separate_early_and_overheat() -> None:
    overheat_card = CandidateCard(
        brief_type="avoid",
        candidate=_candidate("285A", "キオクシア", market="jp", return_20d=0.73, categories=("overheated_caution",), labels=("overheat_caution",)),
        reason="過熱",
        counter_evidence=("急騰後",),
        next_checks=("周辺候補",),
    )
    early_card = CandidateCard(
        brief_type="top_pick",
        candidate=_candidate("AAPL", "Apple", return_20d=0.08),
        reason="初動",
        counter_evidence=(),
        next_checks=("決算",),
    )
    brief = WeeklyCandidateBriefV0(
        report_date="2026-06-06",
        generated_at_jp="f",
        generated_at_us="f",
        jp_scope="f",
        us_scope="f",
        macro_summary="fixture",
        top_picks=[early_card],
        early_discovery_picks=[early_card],
        overheated_leaders=[overheat_card],
    )
    body = format_weekly_candidate_brief_v0_copy(brief)
    assert "## 初動・深掘り候補" in body
    assert "## 過熱代表 / Do Not Chase" in body
    assert "285A" in body
    early_idx = body.index("## 初動・深掘り候補")
    overheat_idx = body.index("## 過熱代表 / Do Not Chase")
    assert early_idx < overheat_idx
    early_section = body[early_idx:overheat_idx]
    assert "AAPL" in early_section
    assert "285A" not in early_section
    assert "━━━━━━━━━━━━━━━━" in early_section


def test_v14_top_section_avoids_internal_score_terms() -> None:
    brief = build_weekly_candidate_brief_v0(report_date="2026-06-06", scan_limit=5)
    body = format_weekly_candidate_brief_v0_copy(brief)
    top = body.split("## 開発者向け集計")[0]
    for forbidden in ("discovery_score", "score_veto_pipeline_source", "Sanitized Input", "Manual Input"):
        assert forbidden not in top
