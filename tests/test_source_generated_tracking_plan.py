from __future__ import annotations

from pathlib import Path

from invis_alpha_os.security.source_generated_tracking_plan import (
    build_source_generated_tracking_plan,
    classify_tracked_path,
)


def test_classify_reports_date_md_untrack() -> None:
    assert classify_tracked_path("reports/2026-05-24/final_report.md") == "untrack_generated"


def test_classify_sample_report_keep() -> None:
    assert (
        classify_tracked_path("reports/2026-05-27/sample_weekly_observation_report_v1.md")
        == "keep_source_tracked"
    )


def test_classify_gitkeep_keep() -> None:
    assert classify_tracked_path("outputs/signals/.gitkeep") == "keep_source_tracked"


def test_build_plan_from_mocked_tracked(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.security.source_generated_tracking_plan._git_tracked_files",
        lambda _root: [
            "reports/2026-05-24/final_report.md",
            "reports/2026-05-27/sample_weekly_observation_report_v1.md",
            "outputs/signals/.gitkeep",
        ],
    )
    result = build_source_generated_tracking_plan(source_repo_path=tmp_path)
    assert result.json_payload["tracked_reports_count"] == 2
    assert result.json_payload["contents_printed"] is False
    assert "reports/2026-05-24/final_report.md" in result.json_payload["de_index_recommended"]
