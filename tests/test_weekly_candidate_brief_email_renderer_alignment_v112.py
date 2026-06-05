from __future__ import annotations

from invis_alpha_os.product.weekly_candidate_brief_v0 import (
    WeeklyCandidateBriefV0,
    format_weekly_candidate_brief_v0_copy,
)
from invis_alpha_os.reports.weekly_candidate_brief_email import build_weekly_candidate_brief_email_draft


def test_email_draft_aligns_with_renderer_zero_candidate_copy() -> None:
    brief = WeeklyCandidateBriefV0(
        report_date="2026-06-06",
        generated_at_jp="fixture",
        generated_at_us="fixture",
        jp_scope="fixture",
        us_scope="fixture",
        macro_summary="fixture macro",
        coverage_note=(
            "coverage_note: JP candidates were unavailable due to insufficient JP cache quality / "
            "US equity candidates were unavailable due to insufficient data quality"
        ),
    )
    copy_body = format_weekly_candidate_brief_v0_copy(brief)
    draft = build_weekly_candidate_brief_email_draft(report_date="2026-06-06", copy_body=copy_body)

    assert "今週は新規買いを急がない" in draft.text_body
    assert "## 今週の結論（短縮）" in draft.text_body
    assert "今週やること:" in draft.text_body
    assert "今週やらないこと:" in draft.text_body
    assert "強い新規リスク候補: 0件" not in draft.text_body
    assert "## 今週の行動チェックリスト" not in draft.text_body
    assert "候補0件の主因:" in draft.text_body
    assert draft.html_body is not None
    assert "今週の結論（短縮）" in draft.html_body
    assert "強い新規リスク候補: 0件" not in draft.html_body


def test_email_draft_aligns_with_candidate_positive_renderer_copy() -> None:
    from invis_alpha_os.product.weekly_candidate_brief_v0 import (
        CandidateCard,
        UnifiedCandidate,
        WeeklyCandidateBriefV0,
    )

    brief = WeeklyCandidateBriefV0(
        report_date="2026-06-06",
        generated_at_jp="fixture",
        generated_at_us="fixture",
        jp_scope="fixture",
        us_scope="fixture",
        macro_summary="fixture macro",
        top_picks=[
            CandidateCard(
                brief_type="top_pick",
                candidate=UnifiedCandidate(
                    market="jp",
                    instrument_id="285A",
                    display_name="キオクシア",
                    discovery_score=10,
                    latest_date="2026-06-01",
                    close=100.0,
                    return_5d=0.02,
                    return_20d=0.15,
                    return_60d=0.20,
                    labels=("near_high",),
                    categories=("rapid_mover",),
                    data_quality="ok",
                    reason="surfaced: near_high",
                    themes=("memory",),
                    volume_status="normal",
                ),
                reason="注目理由: NAND市況改善。",
                counter_evidence=("割高感",),
                next_checks=("決算確認",),
            )
        ],
    )
    copy_body = format_weekly_candidate_brief_v0_copy(brief)
    draft = build_weekly_candidate_brief_email_draft(report_date="2026-06-06", copy_body=copy_body)

    assert "今週は候補あり" in copy_body
    assert "285A" in draft.text_body
    assert "これは売買指示ではありません" in copy_body
