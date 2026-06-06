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
    categories: tuple[str, ...] = ("rapid_mover", "near_high_quality_trend"),
    labels: tuple[str, ...] = ("rapid_mover_20d", "near_high"),
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
        labels=labels,
        categories=categories,
        data_quality="ok",
        reason="fixture human candidate",
        themes=themes,
        volume_status="normal",
    )


def _card(candidate: UnifiedCandidate, *, brief_type: str = "top_pick") -> CandidateCard:
    return CandidateCard(
        brief_type=brief_type,
        candidate=candidate,
        reason="注目理由: 20日モメンタムが強く、テーマ性も確認対象。",
        counter_evidence=("20日で大きく上昇しており、追いかけると反落リスクがある。",),
        next_checks=("決算・需給・バリュエーションを確認", "既存保有との重複を確認"),
    )


def _brief() -> WeeklyCandidateBriefV0:
    early = _card(_candidate("AAPL", "AAPL", return_20d=0.28))
    overheat = _card(
        _candidate(
            "285A",
            "キオクシア",
            market="jp",
            themes=("memory", "semiconductors"),
            return_20d=0.73,
            categories=("rapid_mover", "overheated_caution"),
            labels=("overheat_caution",),
        ),
        brief_type="avoid",
    )
    return WeeklyCandidateBriefV0(
        report_date="2026-06-06",
        generated_at_jp="fixture",
        generated_at_us="fixture",
        jp_scope="fixture",
        us_scope="fixture",
        macro_summary="fixture macro",
        top_picks=[early],
        early_discovery_picks=[early],
        overheated_leaders=[overheat],
    )


def test_weekly_report_v1_2_markdown_contains_investment_grade_sections() -> None:
    body = format_weekly_candidate_brief_v0_markdown(_brief())

    for required in (
        "## 今週の結論（3行）",
        "## 初動・深掘り候補",
        "## 過熱代表 / Do Not Chase",
        "## If/Then 行動ルール",
        "## 用語・安全注記",
        "深掘り候補",
        "追いかけ禁止",
        "これは売買指示ではありません",
    ):
        assert required in body

    top_area = body.split("## 開発者向け集計")[0]
    assert "285A" in top_area
    assert "285A" not in top_area.split("## 初動・深掘り候補")[1].split("## 過熱代表")[0]
    assert "━━━━━━━━━━━━━━━━" in top_area
    for unexplained in ("score_veto_source", "matched_normal", "rows_matched"):
        assert unexplained not in top_area.lower()


def test_weekly_report_v1_2_email_html_has_tables_and_status_badges() -> None:
    copy_body = format_weekly_candidate_brief_v0_copy(_brief())
    draft = build_weekly_candidate_brief_email_draft(report_date="2026-06-06", copy_body=copy_body)

    assert draft.html_body is not None
    html = draft.html_body
    assert "candidate-card" in html
    assert "なぜ注目" in html
    assert "AAPL" in html


def test_weekly_report_v1_2_one_page_summary_is_chatgpt_ready() -> None:
    summary = build_weekly_report_user_summary(source="composed", report_date="2026-06-06").body_markdown

    for required in (
        "# Weekly Report One-Page Summary",
        "## 1. 今週の結論",
        "## 2. 候補の扱い",
        "## 3. ポートフォリオ制約",
        "## 4. 深掘りしたい論点",
        "初動候補は0件",
        "過熱代表",
    ):
        assert required in summary
