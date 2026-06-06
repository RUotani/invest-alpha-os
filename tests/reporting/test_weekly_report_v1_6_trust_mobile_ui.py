from __future__ import annotations

import re

from invis_alpha_os.discovery.candidate_classifier import PortfolioGateContext
from invis_alpha_os.discovery.early_discovery_score import is_report_ui_overheat
from invis_alpha_os.product.weekly_candidate_brief_v0 import (
    CandidateCard,
    UnifiedCandidate,
    WeeklyCandidateBriefV0,
    build_weekly_candidate_brief_v0,
    format_weekly_candidate_brief_v0_copy,
    _partition_ranked_by_v16_classification,
)
from invis_alpha_os.product.weekly_report_render_model import (
    DEVELOPER_APPENDIX_SECTION_TITLE,
    build_weekly_report_render_model,
)
from invis_alpha_os.reports.weekly_candidate_brief_email import build_weekly_candidate_brief_email_draft


def _candidate(
    symbol: str,
    name: str,
    *,
    market: str = "us",
    return_20d: float = 0.12,
    latest_date: str = "2026-06-05",
    categories: tuple[str, ...] = ("rapid_mover",),
    labels: tuple[str, ...] = (),
) -> UnifiedCandidate:
    return UnifiedCandidate(
        market=market,
        instrument_id=symbol,
        display_name=name,
        discovery_score=8,
        latest_date=latest_date,
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


def _card(symbol: str, name: str, **kwargs: object) -> CandidateCard:
    return CandidateCard(
        brief_type="top_pick",
        candidate=_candidate(symbol, name, **kwargs),
        reason=f"注目: {symbol}",
        counter_evidence=("反証",),
        next_checks=("次確認",),
    )


def test_expired_candidates_move_to_freshness_pending() -> None:
    ranked = [
        _candidate("6857", "アドバンテスト", market="jp", latest_date="2026-02-17"),
        _candidate("AAPL", "Apple", return_20d=0.28, latest_date="2026-06-05"),
    ]
    relaxed = PortfolioGateContext(cash_ratio=0.20, single_stock_ratio=0.12)
    early, overheated, pending = _partition_ranked_by_v16_classification(
        ranked,
        report_date="2026-06-06",
        portfolio=relaxed,
    )
    assert [c.instrument_id for c in early] == ["AAPL"]
    assert [c.instrument_id for c in pending] == ["6857"]
    assert overheated == []


def test_285a_routes_to_overheated_not_investable() -> None:
    ranked = [
        _candidate(
            "285A",
            "キオクシア",
            market="jp",
            return_20d=0.73,
            categories=("rapid_mover", "overheated_caution"),
            labels=("overheat_caution",),
        ),
        _candidate("AAPL", "Apple", return_20d=0.28),
    ]
    relaxed = PortfolioGateContext(cash_ratio=0.20, single_stock_ratio=0.12)
    early, overheated, _pending = _partition_ranked_by_v16_classification(
        ranked,
        report_date="2026-06-06",
        portfolio=relaxed,
    )
    assert [c.instrument_id for c in early] == ["AAPL"]
    assert [c.instrument_id for c in overheated] == ["285A"]
    assert is_report_ui_overheat(ret_20d=0.73, ret_60d=1.75, categories=("overheated_caution",), labels=()) is True


def test_summary_counts_match_render_buckets() -> None:
    brief = WeeklyCandidateBriefV0(
        report_date="2026-06-06",
        generated_at_jp="f",
        generated_at_us="f",
        jp_scope="f",
        us_scope="f",
        macro_summary="fixture",
        early_discovery_picks=[_card("AAPL", "Apple")],
        overheated_leaders=[
            CandidateCard(
                brief_type="avoid",
                candidate=_candidate("285A", "キオクシア", market="jp", return_20d=0.73, categories=("overheated_caution",), labels=("overheat_caution",)),
                reason="過熱",
                counter_evidence=("急騰後",),
                next_checks=("周辺候補",),
            )
        ],
        freshness_pending_picks=[_card("6857", "アドバンテスト", market="jp", latest_date="2026-02-17")],
    )
    model = build_weekly_report_render_model(brief)
    body = format_weekly_candidate_brief_v0_copy(brief)
    assert f"初動・深掘り {model.investable_count}件" in body
    assert f"過熱代表 {model.overheat_count}件" in body
    assert f"鮮度不足 {model.freshness_pending_count}件" in body
    assert str(model.investable_count) in body
    assert model.score_veto_deep_dive_count == model.investable_count


def test_top_section_terminology_and_layout() -> None:
    brief = WeeklyCandidateBriefV0(
        report_date="2026-06-06",
        generated_at_jp="f",
        generated_at_us="f",
        jp_scope="f",
        us_scope="f",
        macro_summary="fixture",
        early_discovery_picks=[_card("MSFT", "Microsoft")],
        overheated_leaders=[],
    )
    body = format_weekly_candidate_brief_v0_copy(brief)
    top = body.split(DEVELOPER_APPENDIX_SECTION_TITLE, maxsplit=1)[0]
    assert "RED RED" not in body
    assert "YELLOW YELLOW" not in body
    assert "RED /" not in top
    for forbidden in ("Score / Veto", "Sanitized", "Manual Input", "Parity", "DEEP DIVE"):
        assert forbidden not in top
    investable = top.split("## 初動・深掘り候補", maxsplit=1)[1].split("## ", maxsplit=1)[0]
    assert "|---" not in investable or investable.count("|") < 12
    assert "━━━━━━━━━━━━━━━━" in investable


def test_score_veto_block_once_in_developer_appendix() -> None:
    brief = build_weekly_candidate_brief_v0(report_date="2026-06-06", scan_limit=5)
    body = format_weekly_candidate_brief_v0_copy(brief)
    appendix = body.split(DEVELOPER_APPENDIX_SECTION_TITLE, maxsplit=1)[1]
    assert appendix.count("## Score / Veto 統合サマリー") <= 1
    assert appendix.count("### Score / Veto（共有要約）") == 0


def test_overheat_section_language() -> None:
    brief = WeeklyCandidateBriefV0(
        report_date="2026-06-06",
        generated_at_jp="f",
        generated_at_us="f",
        jp_scope="f",
        us_scope="f",
        macro_summary="fixture",
        overheated_leaders=[
            CandidateCard(
                brief_type="avoid",
                candidate=_candidate("285A", "キオクシア", market="jp", return_20d=0.73, categories=("overheated_caution",), labels=("overheat_caution",)),
                reason="過熱",
                counter_evidence=("急騰後",),
                next_checks=("周辺候補",),
            )
        ],
    )
    body = format_weekly_candidate_brief_v0_copy(brief)
    overheat = body.split("## 過熱代表 / Do Not Chase", maxsplit=1)[1].split("## ", maxsplit=1)[0]
    assert "追いかけ禁止" in overheat
    assert "テーマ代表として観測" in overheat
    assert "周辺・出遅れ" in overheat
    assert "285A" in overheat
    investable = body.split("## 初動・深掘り候補", maxsplit=1)[1].split("## ", maxsplit=1)[0]
    assert "285A" not in investable


def test_email_html_has_candidate_card_blocks() -> None:
    brief = WeeklyCandidateBriefV0(
        report_date="2026-06-06",
        generated_at_jp="f",
        generated_at_us="f",
        jp_scope="f",
        us_scope="f",
        macro_summary="fixture",
        early_discovery_picks=[_card("MSFT", "Microsoft")],
    )
    copy_body = format_weekly_candidate_brief_v0_copy(brief)
    draft = build_weekly_candidate_brief_email_draft(report_date="2026-06-06", copy_body=copy_body)
    assert draft.html_body is not None
    assert "candidate-card" in draft.html_body
    assert "なぜ注目" in draft.html_body


def test_freshness_pending_list_renders_expired_label() -> None:
    brief = WeeklyCandidateBriefV0(
        report_date="2026-06-06",
        generated_at_jp="f",
        generated_at_us="f",
        jp_scope="f",
        us_scope="f",
        macro_summary="fixture",
        freshness_pending_picks=[_card("6857", "アドバンテスト", market="jp", latest_date="2026-02-17")],
    )
    body = format_weekly_candidate_brief_v0_copy(brief)
    pending = body.split("## データ鮮度不足リスト", maxsplit=1)[1].split("## ", maxsplit=1)[0]
    assert "6857" in pending
    assert "期限切れ" in pending
    assert re.search(r"109日前", pending) is not None
