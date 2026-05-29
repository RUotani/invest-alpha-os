from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.manual_data_dry_run_preflight import build_manual_data_dry_run_preflight


def test_preflight_without_input_file(tmp_path: Path) -> None:
    result = build_manual_data_dry_run_preflight(report_date="2026-05-27", repo_root=tmp_path)
    assert result.json_payload["actual_import_executed"] is False
    assert result.json_payload["import_flow_dry_run"] is None
    assert "285A" in ",".join(result.json_payload["readiness"]["required_targets"])
