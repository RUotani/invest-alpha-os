from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.manual_data_freshness_pipeline import (
    build_manual_data_freshness_pipeline,
)


def test_freshness_pipeline_without_manual_file(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "data").mkdir(parents=True)
    report_dir = tmp_path / "reports" / "2026-05-27"
    report_dir.mkdir(parents=True)
    (report_dir / "weekly_candidate_brief_v0_1.json").write_text("{}", encoding="utf-8")
    result = build_manual_data_freshness_pipeline(
        report_date="2026-05-29",
        repo_root=repo,
        report_dir=report_dir,
    )
    assert result.summary["manual_file_detected"] is False
    assert result.export_assistant is not None
    assert result.context_pack is not None
