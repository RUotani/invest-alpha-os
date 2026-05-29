from __future__ import annotations

from invis_alpha_os.reports.manual_data_actual_import_approval_package import (
    build_manual_data_actual_import_approval_package,
)


def test_approval_defer_low_benefit_when_no_new_rows() -> None:
    result = build_manual_data_actual_import_approval_package(
        report_date="2026-05-29",
        discovery_payload={"selected_candidate": {"filename": "manual_jp_bars.csv"}},
        schema_payload={"schema_valid": True, "prohibited_columns_detected": False},
        dry_run_payload={
            "dry_run_status": "pass",
            "rows_newer_than_cache_total": 0,
            "expected_freshness_improvement": "none_identified",
        },
    )
    assert result.json_payload["package_status"] == "defer_import_low_benefit"
    assert result.json_payload["actual_import_recommended"] is False
    assert result.json_payload["import_benefit"] == "low"


def test_approval_recommends_import_when_new_rows() -> None:
    result = build_manual_data_actual_import_approval_package(
        report_date="2026-05-29",
        discovery_payload={"selected_candidate": {"filename": "manual_jp_bars.csv"}},
        schema_payload={"schema_valid": True, "prohibited_columns_detected": False},
        dry_run_payload={
            "dry_run_status": "pass",
            "rows_newer_than_cache_total": 5,
            "expected_freshness_improvement": "rows_newer_than_cache",
        },
    )
    assert result.json_payload["actual_import_recommended"] is True
    assert result.json_payload["package_status"] == "ready_for_user_approval"
