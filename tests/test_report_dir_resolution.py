from __future__ import annotations

from pathlib import Path

import pytest

from invis_alpha_os.reports.report_dir_resolution import resolve_weekly_report_dir


def test_cli_option_has_priority(tmp_path: Path) -> None:
    cli_path = tmp_path / "custom" / "reports"
    resolution = resolve_weekly_report_dir(
        report_date="2026-05-27",
        report_dir=str(cli_path),
        repo_root=tmp_path,
    )
    assert resolution.path == cli_path
    assert resolution.resolution_source == "cli_option"
    assert resolution.used_fallback is False


def test_env_report_dir_used_when_cli_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = tmp_path / "env_reports" / "2026-05-27"
    monkeypatch.setenv("REPORT_DIR", str(env_path))
    resolution = resolve_weekly_report_dir(report_date="2026-05-27", repo_root=tmp_path)
    assert resolution.path == env_path
    assert resolution.resolution_source == "env_report_dir"


def test_fallback_to_repo_reports_date(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REPORT_DIR", raising=False)
    resolution = resolve_weekly_report_dir(report_date="2026-05-27", repo_root=tmp_path)
    assert resolution.path == tmp_path / "reports" / "2026-05-27"
    assert resolution.used_fallback is True
    assert resolution.warning is not None
