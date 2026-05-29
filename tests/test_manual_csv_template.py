from __future__ import annotations

from invis_alpha_os.reports.manual_csv_template import build_manual_csv_template


def test_template_includes_targets_and_columns() -> None:
    result = build_manual_csv_template(
        targets_csv="5802,285A",
        report_date="2026-05-27",
    )
    assert "5802" in result.csv_text
    assert "285A" in result.csv_text
    assert "ticker,date,open,high,low,close,volume" in result.csv_text
    assert "285A" in result.markdown_text
    assert result.json_payload["targets"] == ["5802", "285A"]
    assert result.json_payload["actual_import_executed"] is False
