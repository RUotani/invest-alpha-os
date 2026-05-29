from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.cache_refresh_readiness import build_cache_refresh_readiness_report


def test_build_cache_refresh_readiness_report_extracts_stale_candidates(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_TO", "20260306")
    context_payload = {
        "candidates": [
            {
                "ticker": "5802",
                "market": "JP",
                "stale_days": 82,
                "latest_bar_date": "2026-03-06",
                "freshness_classification": "data_update_required",
                "timing": "overheated_watch",
                "timing_warnings": ["data_update_required"],
                "missing_data_reasons": [],
            },
            {
                "ticker": "QQQ",
                "market": "ETF",
                "stale_days": 9,
                "latest_bar_date": "2026-05-18",
                "freshness_classification": "stale",
                "timing": "watch_continue",
                "timing_warnings": ["stale"],
                "missing_data_reasons": [],
            },
        ]
    }
    result = build_cache_refresh_readiness_report(
        report_date="2026-05-27",
        repo_root=tmp_path,
        context_json_payload=context_payload,
    )
    assert "Cache Refresh Readiness Report" in result.markdown_text
    assert result.json_payload["dry_run_only"] is True
    rows = result.json_payload["stale_candidates"]
    assert rows[0]["ticker"] == "5802"
    assert rows[0]["refresh_priority"] == "high"
    assert rows[0]["data_contract_limited"] is True
    assert any(x["ticker"] == "QQQ" for x in rows)


def test_readiness_notes_contract_env_not_loaded_when_env_missing(monkeypatch) -> None:
    monkeypatch.delenv("JQUANTS_DATA_AVAILABLE_TO", raising=False)
    context_payload = {
        "candidates": [
            {
                "ticker": "5802",
                "market": "JP",
                "stale_days": 82,
                "latest_bar_date": "2026-02-17",
                "freshness_classification": "data_update_required",
                "timing_warnings": [],
                "missing_data_reasons": [],
            }
        ]
    }
    result = build_cache_refresh_readiness_report(
        report_date="2026-05-27",
        repo_root=Path("."),
        context_json_payload=context_payload,
    )
    assert result.json_payload["contract_env"]["contract_env_not_loaded"] is True
    assert "contract_env_not_loaded" in result.json_payload["stale_candidates"][0]["timing_warnings"]
    assert any("--env-file" in note for note in result.json_payload["notes"])
