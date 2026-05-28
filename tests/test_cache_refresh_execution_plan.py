from __future__ import annotations

from invis_alpha_os.reports.cache_refresh_execution_plan import build_cache_refresh_execution_plan


def test_build_cache_refresh_execution_plan_groups_by_provider() -> None:
    readiness = {
        "stale_candidates": [
            {"ticker": "5802", "market": "JP", "provider_candidate": "jquants", "refresh_priority": "high", "stale_days": 99, "reason": "stale"},
            {"ticker": "QQQ", "market": "US", "provider_candidate": "us_daily_bars", "refresh_priority": "medium", "stale_days": 9, "reason": "stale"},
        ]
    }
    result = build_cache_refresh_execution_plan(report_date="2026-05-27", readiness_json_payload=readiness)
    assert result.json_payload["dry_run_only"] is True
    assert result.json_payload["actual_refresh_executed"] is False
    assert "jquants" in result.json_payload["provider_groups"]
    assert "us_daily_bars" in result.json_payload["provider_groups"]
    assert "Cache Refresh Execution Plan" in result.markdown_text
