from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.manual_data_dry_run_readiness import build_manual_data_dry_run_readiness


def test_manual_data_dry_run_readiness_no_import(tmp_path: Path) -> None:
    result = build_manual_data_dry_run_readiness(report_date="2026-05-27", repo_root=tmp_path)
    assert result.json_payload["actual_import_executed"] is False
    assert result.json_payload["contents_printed"] is False
    assert "dry_run_command" in result.json_payload
    assert "285A" in ",".join(result.json_payload["required_targets"])
