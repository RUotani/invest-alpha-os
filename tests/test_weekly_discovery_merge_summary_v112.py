from __future__ import annotations

from invis_alpha_os.product.weekly_candidate_brief_v0 import (
    WeeklyCandidateBriefV0,
    format_weekly_candidate_brief_v0_copy,
)


def test_zero_candidate_copy_includes_discovery_merge_summary_when_present() -> None:
    brief = WeeklyCandidateBriefV0(
        report_date="2026-06-06",
        generated_at_jp="fixture",
        generated_at_us="fixture",
        jp_scope="fixture",
        us_scope="fixture",
        macro_summary="fixture macro",
        discovery_merge={"schema_version": "discovery.cross_market.v1"},
    )
    body = format_weekly_candidate_brief_v0_copy(brief)
    assert "### Discovery merge（共有要約）" in body
    assert "discovery.cross_market.v1" in body
