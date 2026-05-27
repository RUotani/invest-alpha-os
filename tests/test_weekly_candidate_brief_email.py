"""Weekly Candidate Brief Gmail preview (dry-run only)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.discovery.cross_market_contract import FORBIDDEN_OUTPUT_TERMS
from invis_alpha_os.reports.weekly_candidate_brief_email import (
    build_weekly_candidate_brief_email_draft,
    build_weekly_candidate_brief_email_subject,
)

runner = CliRunner()


def test_weekly_candidate_brief_email_subject() -> None:
    assert build_weekly_candidate_brief_email_subject("2026-05-27") == (
        "[invest-alpha-os] Weekly Candidate Brief 2026-05-27"
    )


def test_weekly_candidate_brief_email_draft_uses_copy_body() -> None:
    copy = "<<< COPY FROM HERE >>>\n# Weekly Candidate Brief — 2026-05-27\n<<< COPY TO HERE >>>\n"
    draft = build_weekly_candidate_brief_email_draft(report_date="2026-05-27", copy_body=copy)
    assert draft.subject.endswith("2026-05-27")
    assert "<<< COPY FROM HERE >>>" in draft.text_body
    assert "Weekly Observation Report" not in draft.text_body
    lower = draft.text_body.lower()
    for term in FORBIDDEN_OUTPUT_TERMS:
        assert term not in lower


def test_weekly_candidate_brief_email_dry_run_cli(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    report_dir.mkdir(parents=True)
    copy_path = report_dir / "weekly_candidate_brief_copy.md"
    copy_path.write_text(
        "<<< COPY FROM HERE >>>\n# Weekly Candidate Brief — 2026-05-27\n<<< COPY TO HERE >>>\n",
        encoding="utf-8",
    )
    full_md = report_dir / "weekly_candidate_brief_v0_1.md"
    full_md.write_text("# full report\n", encoding="utf-8")

    r = runner.invoke(
        app,
        [
            "weekly-candidate-brief-email",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(report_dir),
            "--copy-file",
            str(copy_path),
            "--full-md",
            str(full_md),
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    assert (report_dir / "email" / "email_preview.eml").is_file()
    assert "dry-run only" in r.stdout
    assert "[invest-alpha-os] Weekly Candidate Brief 2026-05-27" in r.stdout
    txt = (report_dir / "email" / "email_preview.txt").read_text(encoding="utf-8")
    assert "<<< COPY FROM HERE >>>" in txt


def test_weekly_candidate_brief_email_missing_copy_exit2(tmp_path: Path) -> None:
    r = runner.invoke(
        app,
        [
            "weekly-candidate-brief-email",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(tmp_path),
        ],
    )
    assert r.exit_code == 2
