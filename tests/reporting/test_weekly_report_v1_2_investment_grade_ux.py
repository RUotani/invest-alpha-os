from __future__ import annotations

from invis_alpha_os.product.weekly_candidate_brief_v0 import (
    CandidateCard,
    UnifiedCandidate,
    format_weekly_candidate_brief_v0_copy,
    format_weekly_candidate_brief_v0_markdown,
    WeeklyCandidateBriefV0,
)
from invis_alpha_os.product.weekly_report_user_summary import build_weekly_report_user_summary
from invis_alpha_os.reports.weekly_candidate_brief_email import build_weekly_candidate_brief_email_draft


def _candidate(
    symbol: str,
    name: str,
    *,
    market: str = "us",
    themes: tuple[str, ...] = ("us_equity",),
    return_20d: float = 0.12,
    discovery_score: int = 8,
) -> UnifiedCandidate:
    return UnifiedCandidate(
        market=market,
        instrument_id=symbol,
        display_name=name,
        discovery_score=discovery_score,
        latest_date="2026-06-05",
        close=100.0,
        return_5d=0.03,
        return_20d=return_20d,
        return_60d=0.21,
        labels=("rapid_mover_20d", "near_high"),
        categories=("rapid_mover", "near_high_quality_trend"),
        data_quality="ok",
        reason="fixture human candidate",
        themes=themes,
        volume_status="normal",
    )


def _card(candidate: UnifiedCandidate) -> CandidateCard:
    return CandidateCard(
        brief_type="top_pick",
        candidate=candidate,
        reason="注目理由: 20日モメンタムが強く、テーマ性も確認対象。",
        counter_evidence=("20日で大きく上昇しており、追いかけると反落リスクがある。",),
        next_checks=("決算・需給・バリュエーションを確認", "既存保有との重複を確認"),
    )


def _brief() -> WeeklyCandidateBriefV0:
    cards = [
        _card(_candidate("285A", "キオクシア", market="jp", themes=("memory", "semiconductors"), return_20d=0.73)),
        _card(_candidate("AAPL", "AAPL", return_20d=0.08)),
        _card(_candidate("QQQ", "QQQ", themes=("us_etf",), return_20d=0.06)),
        _card(_candidate("MSFT", "MSFT", return_20d=0.05)),
        _card(_candidate("NVDA", "NVDA", return_20d=0.18)),
    ]
    return WeeklyCandidateBriefV0(
        report_date="2026-06-06",
        generated_at_jp="fixture",
        generated_at_us="fixture",
        jp_scope="fixture",
        us_scope="fixture",
        macro_summary="fixture macro",
        top_picks=cards,
    )


def test_weekly_report_v1_2_markdown_contains_investment_grade_sections() -> None:
    body = format_weekly_candidate_brief_v0_markdown(_brief())

    for required in (
        "## Executive Summary",
        "## 用語の簡単な意味",
        "## Portfolio Guardrails",
        "## Candidate Comparison",
        "## Top 5 Deep Dive Cards",
        "## Action Matrix",
        "## If / Then Decision Rules",
        "深掘り候補",
        "追いかけ買い禁止",
        "これは売買指示ではありません",
    ):
        assert required in body

    assert "| 現金比率 | 11.7% | 15%以上 / 目標30% | RED / 不足 |" in body
    assert "| 1 | 285A キオクシア | 半導体/メモリ |" in body
    assert body.count("| 一言でいうと |") >= 5

    top_area = "\n".join(body.splitlines()[:80]).lower()
    for unexplained in ("score_veto_source", "matched_normal", "rows_matched"):
        assert unexplained not in top_area


def test_weekly_report_v1_2_email_html_has_tables_and_status_badges() -> None:
    copy_body = format_weekly_candidate_brief_v0_copy(_brief())
    draft = build_weekly_candidate_brief_email_draft(report_date="2026-06-06", copy_body=copy_body)

    assert draft.html_body is not None
    html = draft.html_body
    assert "Executive Summary" in html
    assert "Portfolio Guardrails" in html
    assert "If / Then Decision Rules" in html
    assert "<table" in html
    assert "DEEP DIVE" in html
    assert "background:#dcfce7" in html
    assert "border:1px solid #d1d5db" in html


def test_weekly_report_v1_2_one_page_summary_is_chatgpt_ready() -> None:
    summary = build_weekly_report_user_summary(source="composed", report_date="2026-06-06").body_markdown

    for required in (
        "# Weekly Report One-Page Summary",
        "## 1. 今週の結論",
        "## 2. 候補上位",
        "## 3. ポートフォリオ制約",
        "## 4. 深掘りしたい論点",
        "## 5. 見送り条件",
        "## 6. ChatGPTに聞きたい質問",
        "285Aは過熱後でも深掘り価値がありますか？",
        "今週は買うべきか、調査だけにすべきですか？",
    ):
        assert required in summary
