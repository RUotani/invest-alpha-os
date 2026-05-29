from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.manual_data_dropzone import build_manual_data_dropzone_status, ensure_dropzone_assets


def test_ensure_dropzone_assets(tmp_path: Path) -> None:
    paths = ensure_dropzone_assets(dropzone=tmp_path)
    assert paths["readme"].is_file()
    assert paths["template"].is_file()
    assert paths["paste_file"].is_file()


def test_dropzone_status_missing_manual(tmp_path: Path) -> None:
    ensure_dropzone_assets(dropzone=tmp_path)
    status = build_manual_data_dropzone_status(report_date="2026-05-29", dropzone=tmp_path)
    assert status.json_payload["manual_jp_bars_present"] is False
    assert "manual_jp_bars.csv" in status.json_payload["next_single_action"]
