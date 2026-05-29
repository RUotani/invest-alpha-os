from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.manual_data_discovery import discover_manual_data_candidates


def test_generic_csv_name_schema_candidate(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    export_csv = downloads / "random_export.csv"
    export_csv.write_text(
        "ticker,date,open,high,low,close,volume\n5802,2026-05-27,100,110,90,105,1000\n",
        encoding="utf-8",
    )
    rows = discover_manual_data_candidates(repo_root=repo, search_roots=[downloads])
    assert any(r.get("schema_ohlcv_candidate") for r in rows)
    assert any(r["filename"] == "random_export.csv" for r in rows)
