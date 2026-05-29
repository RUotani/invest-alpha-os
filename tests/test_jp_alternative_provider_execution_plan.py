from __future__ import annotations

from invis_alpha_os.reports.jp_alternative_provider_execution_plan import build_jp_alternative_provider_execution_plan


def test_build_jp_alternative_provider_execution_plan_manual_csv_dry_run() -> None:
    readiness = {
        "recommended_provider": "manual_csv",
        "targets": ["5802", "6645", "5801"],
        "jquants_contract_limited": True,
    }
    result = build_jp_alternative_provider_execution_plan(
        report_date="2026-05-27",
        readiness_json_payload=readiness,
    )
    assert result.json_payload["provider_candidate"] == "manual_csv"
    assert result.json_payload["dry_run_only"] is True
    assert result.json_payload["cache_write_executed"] is False
    assert result.json_payload["actual_refresh_executed"] is False
    assert "date" in result.json_payload["input_file_schema"]["required_columns"]
    assert "JP Alternative Provider Execution Plan" in result.markdown_text
