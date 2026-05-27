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
SAMPLE_COPY = """<<< COPY FROM HERE >>>
# Weekly Candidate Brief — 2026-05-27

## 今週の深掘り候補 Top 5

| Rank | Symbol | Name | Market | Type | Short reason |
|---|---|---|---|---|---|
| 1 | 7203 | トヨタ | JP | 注目 | 20日モメンタム継続 |

## 候補別メモ

### 1. 7203 トヨタ
- 反証: 過熱後の反落リスク
- 次確認: 需要と為替の再確認

<<< COPY TO HERE >>>
"""


def test_weekly_candidate_brief_email_subject() -> None:
    assert build_weekly_candidate_brief_email_subject("2026-05-27") == (
        "[TEST][invest-alpha-os] Weekly Candidate Brief 2026-05-27"
    )


def test_weekly_candidate_brief_email_draft_uses_copy_body() -> None:
    draft = build_weekly_candidate_brief_email_draft(report_date="2026-05-27", copy_body=SAMPLE_COPY)
    assert draft.subject.endswith("2026-05-27")
    assert "7203" in draft.text_body
    assert len(draft.text_body) > 800
    assert draft.text_body.startswith("TEST EMAIL")
    assert draft.html_body is not None
    assert len(draft.html_body) > 1200
    assert "TEST EMAIL" in draft.html_body
    assert "Moving Average Context" in draft.text_body
    assert "Momentum Rationale" in draft.text_body
    assert "Counter Evidence" in draft.text_body
    assert "Sources" in draft.text_body
    assert "Next Checks" in draft.text_body
    assert "Moving Average Context" in draft.html_body
    assert "Momentum Rationale" in draft.html_body
    assert "Counter Evidence" in draft.html_body
    assert "Sources" in draft.html_body
    assert "Next Checks" in draft.html_body
    assert "Weekly Observation Report" not in draft.text_body
    lower = draft.text_body.lower()
    for term in FORBIDDEN_OUTPUT_TERMS:
        assert term not in lower


def test_weekly_candidate_brief_email_dry_run_cli(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    report_dir.mkdir(parents=True)
    copy_path = report_dir / "weekly_candidate_brief_copy.md"
    copy_path.write_text(
        SAMPLE_COPY,
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
    assert "[TEST][invest-alpha-os] Weekly Candidate Brief 2026-05-27" in r.stdout
    txt = (report_dir / "email" / "email_preview.txt").read_text(encoding="utf-8")
    html = (report_dir / "email" / "email_preview.html").read_text(encoding="utf-8")
    assert "TEST EMAIL" in txt
    assert "TEST EMAIL" in html
    assert "7203" in txt
    assert "Moving Average Context" in txt
    assert "Counter Evidence" in txt


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


def test_weekly_candidate_brief_email_send_test_requires_gate_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    report_dir.mkdir(parents=True)
    copy_path = report_dir / "weekly_candidate_brief_copy.md"
    copy_path.write_text("# brief\n", encoding="utf-8")
    monkeypatch.setenv("GMAIL_TO", "tester@example.com")
    monkeypatch.delenv("INVEST_ALPHA_OS_ALLOW_GMAIL_TEST_SEND", raising=False)
    r = runner.invoke(
        app,
        [
            "weekly-candidate-brief-email",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(report_dir),
            "--send-test",
        ],
    )
    assert r.exit_code == 2
    assert "test send blocked" in r.stderr


def test_weekly_candidate_brief_email_send_test_requires_gmail_to(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    report_dir.mkdir(parents=True)
    copy_path = report_dir / "weekly_candidate_brief_copy.md"
    copy_path.write_text("# brief\n", encoding="utf-8")
    monkeypatch.setenv("INVEST_ALPHA_OS_ALLOW_GMAIL_TEST_SEND", "1")
    monkeypatch.delenv("GMAIL_TO", raising=False)
    r = runner.invoke(
        app,
        [
            "weekly-candidate-brief-email",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(report_dir),
            "--send-test",
        ],
    )
    assert r.exit_code == 2
    assert "GMAIL_TO is required" in r.stderr


def test_weekly_candidate_brief_email_send_test_blocks_recipient_not_in_allowlist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    report_dir.mkdir(parents=True)
    copy_path = report_dir / "weekly_candidate_brief_copy.md"
    copy_path.write_text("# brief\n", encoding="utf-8")
    monkeypatch.setenv("INVEST_ALPHA_OS_ALLOW_GMAIL_TEST_SEND", "1")
    monkeypatch.setenv("CONFIRM_GMAIL_SEND", "YES")
    monkeypatch.setenv("GMAIL_TO", "other@example.com")
    monkeypatch.setenv("GMAIL_SELF_EMAIL", "self@example.com")
    monkeypatch.setenv("GMAIL_REPORT_FROM", "sender@example.com")
    monkeypatch.setattr("invis_alpha_os.cli.main.credentials_configured", lambda: True)
    r = runner.invoke(
        app,
        [
            "weekly-candidate-brief-email",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(report_dir),
            "--send-test",
        ],
    )
    assert r.exit_code == 2
    assert "gmail_send_gate_recipient" in r.stderr


def test_weekly_candidate_brief_email_send_test_sends_when_gated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    report_dir.mkdir(parents=True)
    copy_path = report_dir / "weekly_candidate_brief_copy.md"
    copy_path.write_text("# brief\n", encoding="utf-8")
    monkeypatch.setenv("INVEST_ALPHA_OS_ALLOW_GMAIL_TEST_SEND", "1")
    monkeypatch.setenv("CONFIRM_GMAIL_SEND", "YES")
    monkeypatch.setenv("GMAIL_TO", "tester@example.com")
    monkeypatch.setenv("GMAIL_SELF_EMAIL", "tester@example.com")
    monkeypatch.setenv("GMAIL_REPORT_FROM", "sender@example.com")
    monkeypatch.setattr("invis_alpha_os.cli.main.credentials_configured", lambda: True)
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.send_gmail_message",
        lambda raw, allow_interactive_oauth=False: {"id": "test-id-1"},
    )
    r = runner.invoke(
        app,
        [
            "weekly-candidate-brief-email",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(report_dir),
            "--send-test",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    assert "sent test message id='test-id-1'" in r.stdout
