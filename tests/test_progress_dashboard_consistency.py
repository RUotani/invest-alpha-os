from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.product.progress_dashboard_consistency import (
    check_progress_dashboard_consistency,
    format_progress_dashboard_consistency_json,
    render_progress_dashboard_consistency_markdown,
)

REPO = Path(__file__).resolve().parents[1]


def test_progress_dashboard_current_file_is_consistent() -> None:
    result = check_progress_dashboard_consistency(REPO / "docs" / "progress_dashboard.md")

    assert result.ok is True
    assert result.weighted_reference_pct == result.computed_weighted_pct
    assert result.computed_weighted_pct == 82
    actual = {row.domain: row for row in result.domain_rows}["Actual Import Readiness"]
    assert actual.completed == 0
    assert actual.progress_pct == 0


def test_progress_dashboard_checker_reports_section_mismatch(tmp_path: Path) -> None:
    source = (REPO / "docs" / "progress_dashboard.md").read_text(encoding="utf-8")
    broken = source.replace("| Report MVP | 20 | 17 | 20 | 85% |", "| Report MVP | 20 | 13 | 20 | 65% |")
    path = tmp_path / "progress_dashboard.md"
    path.write_text(broken, encoding="utf-8")

    result = check_progress_dashboard_consistency(path)

    assert result.ok is False
    assert any(issue.code == "section_header_table_mismatch" for issue in result.issues)
    assert "Report MVP" in render_progress_dashboard_consistency_markdown(result)


def test_progress_dashboard_checker_reports_actual_import_checked_item(tmp_path: Path) -> None:
    source = (REPO / "docs" / "progress_dashboard.md").read_text(encoding="utf-8")
    broken = source.replace("- [ ] human approval package", "- [x] human approval package")
    path = tmp_path / "progress_dashboard.md"
    path.write_text(broken, encoding="utf-8")

    result = check_progress_dashboard_consistency(path)

    assert result.ok is False
    assert any(issue.code == "actual_import_checked_items_present" for issue in result.issues)


def test_progress_dashboard_checker_json_renderer_is_machine_readable() -> None:
    result = check_progress_dashboard_consistency(REPO / "docs" / "progress_dashboard.md")
    payload = json.loads(format_progress_dashboard_consistency_json(result))

    assert payload["ok"] is True
    assert payload["computed_weighted_pct"] == 82
    assert payload["issues"] == []


def test_progress_dashboard_check_cli_returns_nonzero_for_broken_file(tmp_path: Path) -> None:
    source = (REPO / "docs" / "progress_dashboard.md").read_text(encoding="utf-8")
    broken = source.replace("**82%**", "**70%**")
    path = tmp_path / "progress_dashboard.md"
    path.write_text(broken, encoding="utf-8")

    result = CliRunner().invoke(app, ["progress-dashboard-check", "--path", str(path), "--format", "markdown"])

    assert result.exit_code == 1
    assert "weighted_reference_mismatch" in result.stdout


def test_progress_dashboard_check_cli_passes_current_file_json() -> None:
    result = CliRunner().invoke(
        app,
        ["progress-dashboard-check", "--path", str(REPO / "docs" / "progress_dashboard.md"), "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
