from __future__ import annotations

from invis_alpha_os.reports.manual_data_actual_import_approval_package import (
    APPROVAL_PHRASE,
    build_manual_data_actual_import_approval_package,
)


def test_approval_package_not_ready() -> None:
    result = build_manual_data_actual_import_approval_package(
        report_date="2026-05-29",
        discovery_payload={"selected_candidate": None},
        schema_payload=None,
        dry_run_payload=None,
    )
    assert result.json_payload["package_status"] == "not_ready"
    assert result.json_payload["required_approval_phrase"] == APPROVAL_PHRASE


def test_approval_package_ready() -> None:
    result = build_manual_data_actual_import_approval_package(
        report_date="2026-05-29",
        discovery_payload={"selected_candidate": {"filename": "manual_jp_bars.csv", "directory_label": "Downloads/x"}},
        schema_payload={"schema_valid": True, "prohibited_columns_detected": False, "target_ticker_coverage": []},
        dry_run_payload={
            "dry_run_status": "pass",
            "rows_newer_than_cache_total": 12,
            "expected_freshness_improvement": "rows_newer_than_cache",
        },
    )
    assert result.json_payload["package_status"] == "ready_for_user_approval"
