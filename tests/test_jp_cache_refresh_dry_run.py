from __future__ import annotations

from invis_alpha_os.reports.jp_cache_refresh_dry_run import build_jp_cache_refresh_dry_run


def test_jp_cache_refresh_dry_run_extracts_jquants_high_only() -> None:
    payload = {
        "targets": [
            {"ticker": "5802", "provider": "jquants", "priority": "high"},
            {"ticker": "6645", "provider": "jquants", "priority": "high"},
            {"ticker": "5801", "provider": "jquants", "priority": "high"},
            {"ticker": "QQQ", "provider": "us_daily_bars", "priority": "medium"},
        ]
    }
    result = build_jp_cache_refresh_dry_run(report_date="2026-05-27", plan_json_payload=payload)
    tickers = [row["ticker"] for row in result.json_payload["targets"]]
    assert tickers == ["5802", "6645", "5801"]
    assert "QQQ" not in result.markdown_text
    assert result.json_payload["live_http_executed"] is False
    assert result.json_payload["cache_write_executed"] is False
    assert result.json_payload["actual_refresh_executed"] is False
