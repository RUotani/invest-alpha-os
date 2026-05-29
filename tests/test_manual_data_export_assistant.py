from __future__ import annotations

from invis_alpha_os.reports.manual_data_export_assistant import build_manual_data_export_assistant


def test_export_assistant_has_three_steps() -> None:
    result = build_manual_data_export_assistant(report_date="2026-05-29")
    assert len(result.json_payload["human_steps"]) == 3
    assert result.json_payload["template_generated"] is True
    assert "285A" in result.template_csv_text
