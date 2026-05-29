from __future__ import annotations

from invis_alpha_os.reports.manual_csv_export_request import build_manual_csv_export_request


def test_export_request_lists_targets_and_columns() -> None:
    result = build_manual_csv_export_request(
        targets_csv="5802,285A",
        report_date="2026-05-27",
    )
    assert "5802" in result.json_payload["required_targets"]
    assert "285A" in result.json_payload["required_targets"]
    assert result.json_payload["preferred_filename"] == "manual_jp_bars.csv"
    assert "ticker" in result.json_payload["required_columns"]
