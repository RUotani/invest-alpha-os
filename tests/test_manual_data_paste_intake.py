from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.manual_data_dropzone import PASTE_FILENAME
from invis_alpha_os.reports.manual_data_paste_intake import materialize_paste_to_working_csv


def test_paste_awaiting_data(tmp_path: Path) -> None:
    dropzone = tmp_path / "dropzone"
    dropzone.mkdir()
    (dropzone / PASTE_FILENAME).write_text("ticker\tdate\topen\thigh\tlow\tclose\tvolume\n", encoding="utf-8")
    work = tmp_path / "work"
    result = materialize_paste_to_working_csv(
        dropzone=dropzone,
        working_dir=work,
        report_date="2026-05-29",
    )
    assert result.json_payload["readiness_status"] == "awaiting_paste"
    assert result.materialized_path is None
