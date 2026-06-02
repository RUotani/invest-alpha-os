from __future__ import annotations

from invis_alpha_os.product.weekly_candidate_pipeline_trace_v90 import (
    CandidatePipelineTraceSummary,
    CandidateTraceInput,
    build_candidate_pipeline_trace_summary,
)


def test_build_pipeline_trace_summary_counts_stages() -> None:
    rows = (
        CandidateTraceInput(
            symbol="AAA",
            has_required_coverage=False,
            score=2.0,
            score_threshold=1.0,
            data_insufficient_reasons=("missing_price",),
        ),
        CandidateTraceInput(
            symbol="BBB",
            has_required_coverage=True,
            score=0.5,
            score_threshold=1.0,
        ),
        CandidateTraceInput(
            symbol="CCC",
            has_required_coverage=True,
            score=1.2,
            score_threshold=1.0,
            veto_reasons=("overheated_caution",),
        ),
        CandidateTraceInput(
            symbol="DDD",
            has_required_coverage=True,
            score=1.5,
            score_threshold=1.0,
        ),
    )
    s = build_candidate_pipeline_trace_summary(rows)

    assert isinstance(s, CandidatePipelineTraceSummary)
    assert s.input_count == 4
    assert s.coverage_missing_count == 1
    assert s.coverage_ok_count == 3
    assert s.data_insufficient_count == 1
    assert s.score_miss_count == 1
    assert s.score_pass_count == 2
    assert s.veto_count == 1
    assert s.final_candidate_count == 1
    assert s.coverage_missing_symbols == ("AAA",)
    assert s.score_miss_symbols == ("BBB",)
    assert len(s.veto_reason_log) == 1
    assert s.veto_reason_log[0].symbol == "CCC"
    assert s.veto_reason_log[0].veto_key == "overheated_caution"


def test_build_pipeline_trace_summary_without_veto_reason_log() -> None:
    rows = (
        CandidateTraceInput(
            symbol="AAA",
            has_required_coverage=True,
            score=1.3,
            score_threshold=1.0,
        ),
    )
    s = build_candidate_pipeline_trace_summary(rows)
    assert s.veto_count == 0
    assert s.veto_reason_log == ()
    assert s.final_candidate_count == 1
