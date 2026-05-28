from __future__ import annotations

from invis_alpha_os.reports.cache_refresh_postcheck import build_cache_refresh_postcheck


def test_cache_refresh_postcheck_compares_readiness_and_plan_presence() -> None:
    before_context = {"candidates": [{"ticker": "5802", "freshness_classification": "data_update_required", "stale_days": 99}]}
    after_context = {"candidates": [{"ticker": "5802", "freshness_classification": "stale", "stale_days": 5}]}
    before_readiness = {"stale_candidates": [{"ticker": "5802"}]}
    after_readiness = {"stale_candidates": []}
    before_plan = {"targets": [{"ticker": "5802"}]}
    after_plan = {"targets": []}
    result = build_cache_refresh_postcheck(
        report_date="2026-05-27",
        before_context_json_payload=before_context,
        after_context_json_payload=after_context,
        before_readiness_json_payload=before_readiness,
        after_readiness_json_payload=after_readiness,
        before_plan_json_payload=before_plan,
        after_plan_json_payload=after_plan,
    )
    row = result.json_payload["comparison_rows"][0]
    assert row["ticker"] == "5802"
    assert row["readiness_before"] is True
    assert row["readiness_after"] is False
    assert row["execution_plan_before"] is True
    assert row["execution_plan_after"] is False
