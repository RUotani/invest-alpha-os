from __future__ import annotations

from invis_alpha_os.product.sanitized_manual_input_report_connection_v99 import (
    build_sanitized_manual_input_summary_lines_v99,
)
from invis_alpha_os.product.weekly_candidate_brief_v0 import WeeklyCandidateBriefV0, format_weekly_candidate_brief_v0_copy
from invis_alpha_os.reports.weekly_candidate_brief_email import build_weekly_candidate_brief_email_draft


def test_v99_summary_lines_build_from_v98_fixture() -> None:
    lines = build_sanitized_manual_input_summary_lines_v99()
    joined = "\n".join(lines)
    assert "Sanitized Input: 判定 WARN / 2026-05 / JPY / man_yen" in joined
    assert "現金11.7%はminimum 15.0%未満" in joined
    assert "個別株19.6%はtarget 10.0〜15.0%超過" in joined
    assert "v97/v95整合 WARN" in joined


def test_v99_weekly_and_email_render_sanitized_summary_consistently() -> None:
    brief = WeeklyCandidateBriefV0(
        report_date="2026-06-02",
        generated_at_jp="t1",
        generated_at_us="t2",
        jp_scope="jp",
        us_scope="us",
        macro_summary="macro",
    )
    copy_body = format_weekly_candidate_brief_v0_copy(brief)
    assert "### Sanitized / Manual Input（共有要約）" in copy_body
    assert "Sanitized Input: 判定 WARN / 2026-05 / JPY / man_yen" in copy_body
    assert "これは実行指示ではなく、根拠補完と安全確認の分類です。" in copy_body

    draft = build_weekly_candidate_brief_email_draft(report_date="2026-06-02", copy_body=copy_body)
    assert "## Sanitized / Manual Input（短縮）" in draft.text_body
    assert "Sanitized Input: 判定 WARN / 2026-05 / JPY / man_yen" in draft.text_body
    assert "Sanitized Guardrail: 現金11.7%はminimum 15.0%未満" in draft.text_body
    assert draft.html_body is not None
    assert "Sanitized / Manual Input（短縮）" in draft.html_body
    assert "Sanitized Input: 判定 WARN / 2026-05 / JPY / man_yen" in draft.html_body
    assert "| 順位 |" not in draft.text_body
