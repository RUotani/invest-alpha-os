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
