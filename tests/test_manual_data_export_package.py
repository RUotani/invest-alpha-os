from __future__ import annotations

from invis_alpha_os.reports.manual_data_export_package import build_manual_data_export_package


def test_export_package_per_target_rows() -> None:
    result = build_manual_data_export_package(
        targets_csv="5802,285A",
        report_date="2026-05-27",
    )
    assert len(result.json_payload["per_target"]) == 2
    assert "285A" in result.template_csv_text
    assert ".xlsx" in result.json_payload["supported_formats"]
