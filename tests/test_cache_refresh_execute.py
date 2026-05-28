from __future__ import annotations

from invis_alpha_os.reports.cache_refresh_execute import build_cache_refresh_execute_dry_run


def _plan_payload() -> dict:
    return {
        "targets": [
            {
                "ticker": "5802",
                "market": "JP",
                "provider": "jquants",
                "priority": "high",
                "plan_status": "planned_dry_run_only",
            },
            {
                "ticker": "QQQ",
                "market": "US",
                "provider": "us_daily_bars",
                "priority": "medium",
                "plan_status": "planned_dry_run_only",
            },
        ]
    }


def test_execute_dry_run_success_without_live_or_cache_write() -> None:
    result = build_cache_refresh_execute_dry_run(
        report_date="2026-05-27",
        plan_json_payload=_plan_payload(),
        execute_refresh=False,
        env={},
    )
    assert result.json_payload["dry_run_only"] is True
    assert result.json_payload["live_http_executed"] is False
    assert result.json_payload["cache_write_executed"] is False
    assert result.json_payload["actual_refresh_executed"] is False
    assert result.json_payload["status"] == "planned_dry_run_only"
    assert "5802" in result.markdown_text
    assert "QQQ" in result.markdown_text


def test_execute_refresh_rejected_without_implementation() -> None:
    result = build_cache_refresh_execute_dry_run(
        report_date="2026-05-27",
        plan_json_payload=_plan_payload(),
        execute_refresh=True,
        env={
            "ALLOW_LIVE_HTTP": "1",
            "CONFIRM_LIVE_HTTP": "YES",
            "ALLOW_CACHE_WRITE": "1",
            "CONFIRM_CACHE_WRITE": "YES",
            "CONFIRM_CACHE_REFRESH": "YES",
        },
    )
    assert result.json_payload["status"] == "actual_refresh_not_enabled"
    assert result.json_payload["error"] == "actual_refresh_not_enabled"
    assert result.json_payload["actual_refresh_executed"] is False
