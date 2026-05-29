from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.manual_data_actual_import_v35 import (
    build_manual_data_actual_import_rollback_plan,
)
from invis_alpha_os.reports.stooq_manual_csv_ticker_inference import infer_ticker_from_filename


def test_rollback_plan_metadata_only(tmp_path: Path) -> None:
    md, payload = build_manual_data_actual_import_rollback_plan(
        report_date="2026-05-29",
        targets_csv="5802",
        backup_root=tmp_path / "backups",
        import_command="test-cmd",
    )
    assert "5802" in md
    assert payload["raw_cache_contents_printed"] is False
    assert "secret" not in md.lower()


def test_infer_285a() -> None:
    assert infer_ticker_from_filename(Path("285a.csv")).ticker == "285A"
