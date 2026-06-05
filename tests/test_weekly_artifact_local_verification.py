from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.product.scheduled_run_observation_readiness_v101 import (
    build_fixture_artifact_texts_for_scheduled_observation_v101,
)
from invis_alpha_os.product.weekly_artifact_local_verification import (
    format_weekly_artifact_local_verification_json,
    render_weekly_artifact_local_verification_markdown,
    verify_weekly_candidate_brief_local_artifacts,
)


def _write_fixture_artifacts(root: Path, report_date: str = "2026-06-06") -> tuple[Path, Path]:
    report_dir = root / "reports" / report_date
    status_file = root / "outputs" / "operator" / "weekly_candidate_brief" / report_date / "status.json"
    texts = build_fixture_artifact_texts_for_scheduled_observation_v101(report_date=report_date)
    for rel_path, text in texts.items():
        path = status_file if rel_path == "status.json" else report_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return report_dir, status_file


def test_weekly_artifact_local_verification_passes_complete_fixture(tmp_path: Path) -> None:
    report_dir, status_file = _write_fixture_artifacts(tmp_path)

    result = verify_weekly_candidate_brief_local_artifacts(
        report_date="2026-06-06",
        report_dir=report_dir,
        status_file=status_file,
    )

    assert result.ready is True
    assert result.issues == ()
    assert result.status_schema_version == "v104"
    assert result.status_trigger_event == "local"
    assert result.gmail_send_attempted is False
    assert any(path.endswith("weekly_candidate_brief.json") for path in result.checked_paths)


def test_weekly_artifact_local_verification_reports_missing_json(tmp_path: Path) -> None:
    report_dir, status_file = _write_fixture_artifacts(tmp_path)
    (report_dir / "weekly_candidate_brief.json").unlink()

    result = verify_weekly_candidate_brief_local_artifacts(
        report_date="2026-06-06",
        report_dir=report_dir,
        status_file=status_file,
    )

    assert result.ready is False
    assert any(issue.code == "missing_required_artifact" for issue in result.issues)
    assert "weekly_candidate_brief.json" in render_weekly_artifact_local_verification_markdown(result)


def test_weekly_artifact_local_verification_reports_status_date_mismatch(tmp_path: Path) -> None:
    report_dir, status_file = _write_fixture_artifacts(tmp_path)
    payload = json.loads(status_file.read_text(encoding="utf-8"))
    payload["date"] = "2026-06-05"
    status_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = verify_weekly_candidate_brief_local_artifacts(
        report_date="2026-06-06",
        report_dir=report_dir,
        status_file=status_file,
    )

    assert result.ready is False
    assert any(issue.code == "status_report_date_mismatch" for issue in result.issues)


def test_weekly_artifact_local_verification_json_renderer_is_machine_readable(tmp_path: Path) -> None:
    report_dir, status_file = _write_fixture_artifacts(tmp_path)
    result = verify_weekly_candidate_brief_local_artifacts(
        report_date="2026-06-06",
        report_dir=report_dir,
        status_file=status_file,
    )

    payload = json.loads(format_weekly_artifact_local_verification_json(result))

    assert payload["ready"] is True
    assert payload["gmail_send_attempted"] is False
    assert "workflow_dispatch is not executed" in payload["safety_notes"][0]


def test_weekly_artifact_local_verification_cli_returns_nonzero_when_not_ready(tmp_path: Path) -> None:
    report_dir, status_file = _write_fixture_artifacts(tmp_path)
    (report_dir / "weekly_candidate_brief_copy.md").unlink()

    result = CliRunner().invoke(
        app,
        [
            "weekly-artifact-local-verify",
            "--report-date",
            "2026-06-06",
            "--report-dir",
            str(report_dir),
            "--status-file",
            str(status_file),
            "--format",
            "markdown",
        ],
    )

    assert result.exit_code == 1
    assert "missing_required_artifact" in result.stdout
    assert "workflow_dispatch is not executed" in result.stdout
