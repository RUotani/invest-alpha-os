from __future__ import annotations

from invis_alpha_os.product.weekly_candidate_brief_v0 import (
    CandidateCard,
    UnifiedCandidate,
    WeeklyCandidateBriefV0,
    format_weekly_candidate_brief_v0_copy,
)
from invis_alpha_os.product.weekly_report_user_summary import build_weekly_report_user_summary
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
        return_60d=1.75,
        labels=labels,
        categories=categories,
        data_quality="ok",
        reason="fixture",
        themes=("jp_equity",),
    )


def _overheat_285a_card() -> CandidateCard:
    return CandidateCard(
        brief_type="avoid",
        candidate=_candidate(
            "285A",
            "キオクシア",
            market="jp",
            return_20d=0.73,
            categories=("rapid_mover", "overheated_caution"),
            labels=("overheat_caution",),
        ),
        reason="過熱（20日 73.2% / 60日 175.2%）",
        counter_evidence=("急伸後の調整局面を警戒する。",),
        next_checks=("NAND/DRAMなどメモリ/半導体市況（需給・価格）",),
    )


def _v161_brief() -> WeeklyCandidateBriefV0:
    return WeeklyCandidateBriefV0(
        report_date="2026-06-06",
        generated_at_jp="fixture",
        generated_at_us="fixture",
        jp_scope="fixture",
        us_scope="fixture",
        macro_summary="fixture",
        early_discovery_picks=[],
        overheated_leaders=[_overheat_285a_card()],
        freshness_pending_picks=[],
    )


def test_markdown_copy_top_summary_has_no_misleading_top_pick() -> None:
    body = format_weekly_candidate_brief_v0_copy(_v161_brief())
    top = body.split("## 過熱代表 / Do Not Chase", maxsplit=1)[0]

    assert "最重要候補 285A" not in body
    assert "第1候補 285A" not in body
    assert "Top Pick 285A" not in body
    assert "初動候補は0件" in top
    assert "285A" not in top.split("## 初動・深掘り候補", maxsplit=1)[1]


def test_email_preview_has_v161_top_summary() -> None:
    copy_body = format_weekly_candidate_brief_v0_copy(_v161_brief())
    draft = build_weekly_candidate_brief_email_draft(report_date="2026-06-06", copy_body=copy_body)

    assert "最重要候補 285A" not in draft.text_body
    assert "最重要候補 285A" not in (draft.html_body or "")
    assert "初動候補は0件" in draft.text_body
    assert "過熱代表" in draft.text_body
    assert "追いかけ禁止" in draft.text_body
    assert "285A" in draft.text_body
    assert draft.html_body is not None
    assert "過熱代表" in draft.html_body
    assert "最重要候補" not in draft.html_body


def test_user_summary_has_no_misleading_top_pick() -> None:
    summary = build_weekly_report_user_summary(source="composed", report_date="2026-06-06")
    body = summary.body_markdown

    assert "最重要候補 285A" not in body
    assert "第1候補 285A" not in body
    assert "Top Pick 285A" not in body
    assert "初動候補は0件" in body
    assert "過熱代表" in body
    assert "追いかけ禁止" in body
    assert "285A" in body
    assert "| 1 | 285A キオクシア | 深掘り" not in body


def test_285a_only_under_overheat_section_in_copy() -> None:
    body = format_weekly_candidate_brief_v0_copy(_v161_brief())
    investable = body.split("## 初動・深掘り候補", maxsplit=1)[1].split("## 過熱代表", maxsplit=1)[0]
    overheat = body.split("## 過熱代表 / Do Not Chase", maxsplit=1)[1].split("## ", maxsplit=1)[0]

    assert "285A" not in investable
    assert "285A" in overheat
    assert "追いかけ禁止" in overheat
