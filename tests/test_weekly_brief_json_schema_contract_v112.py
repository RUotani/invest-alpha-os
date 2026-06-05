from __future__ import annotations

import json

from invis_alpha_os.product.candidate_score_veto_pipeline_v93 import (
    build_fixture_integrated_candidate_assessments_v93,
)
from invis_alpha_os.product.weekly_candidate_brief_v0 import (
    WeeklyCandidateBriefV0,
    format_weekly_candidate_brief_v0_json,
)


def test_json_marks_empty_pipeline_when_no_top_picks() -> None:
    brief = WeeklyCandidateBriefV0(
        report_date="2026-06-06",
        generated_at_jp="t1",
        generated_at_us="t2",
        jp_scope="jp",
        us_scope="us",
        macro_summary="macro",
    )
    payload = json.loads(format_weekly_candidate_brief_v0_json(brief))
    assert payload["score_veto_pipeline"] == []
    assert payload["score_veto_pipeline_source"] == "empty_no_top_picks"
    assert payload["coverage_reason_codes"] == []


def test_json_marks_explicit_assessments_source() -> None:
    brief = WeeklyCandidateBriefV0(
        report_date="2026-06-06",
        generated_at_jp="t1",
        generated_at_us="t2",
        jp_scope="jp",
        us_scope="us",
        macro_summary="macro",
        score_veto_assessments=build_fixture_integrated_candidate_assessments_v93(),
    )
    payload = json.loads(format_weekly_candidate_brief_v0_json(brief))
    assert len(payload["score_veto_pipeline"]) == 5
    assert payload["score_veto_pipeline_source"] == "explicit_assessments"


def test_json_includes_coverage_reason_codes_from_note() -> None:
    brief = WeeklyCandidateBriefV0(
        report_date="2026-06-06",
        generated_at_jp="t1",
        generated_at_us="t2",
        jp_scope="jp",
        us_scope="us",
        macro_summary="macro",
        coverage_note=(
            "coverage_note: JP candidates were unavailable due to insufficient JP cache quality / "
            "US equity candidates were unavailable due to insufficient data quality"
        ),
    )
    payload = json.loads(format_weekly_candidate_brief_v0_json(brief))
    assert payload["coverage_reason_codes"] == [
        "jp_cache_quality_insufficient",
        "us_data_quality_insufficient",
    ]
