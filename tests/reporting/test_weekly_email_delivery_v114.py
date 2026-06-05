from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from pathlib import Path

import pytest

from invis_alpha_os.reporting.email_delivery import (
    deliver_weekly_report_email,
    load_weekly_email_content,
    redact_email_address,
    render_weekly_email_delivery_markdown,
)


def test_redact_email_address_masks_local_part() -> None:
    assert redact_email_address("person@gmail.com") == "p***@gmail.com"
    assert redact_email_address("bad") == "***"


def test_load_weekly_email_content_prefers_html_then_txt_then_readme(tmp_path: Path) -> None:
    report_root = tmp_path / "pack"
    report_root.mkdir()
    (report_root / "email").mkdir()
    (report_root / "email" / "email_preview.html").write_text("<p>html</p>", encoding="utf-8")
    (report_root / "email" / "email_preview.txt").write_text("txt", encoding="utf-8")
    (report_root / "README_FOR_USER.md").write_text("readme", encoding="utf-8")

    content = load_weekly_email_content(report_root=report_root, report_date="2026-06-06")

    assert content.content_source == "email_preview_html"
    assert content.html_body == "<p>html</p>"
    assert content.text_body == "txt"


def test_load_weekly_email_content_falls_back_to_readme(tmp_path: Path) -> None:
    report_root = tmp_path / "pack"
    report_root.mkdir()
    (report_root / "README_FOR_USER.md").write_text("# weekly", encoding="utf-8")

    content = load_weekly_email_content(report_root=report_root, report_date="2026-06-06")

    assert content.content_source == "README_FOR_USER"
    assert "weekly" in (content.text_body or "")


def test_deliver_weekly_report_email_dry_run_without_smtp_call(tmp_path: Path) -> None:
    report_root = tmp_path / "pack"
    report_root.mkdir()
    (report_root / "email").mkdir()
    (report_root / "email" / "email_preview.txt").write_text("body", encoding="utf-8")

    called = False

    def _smtp(**_kwargs: object) -> None:
        nonlocal called
        called = True

    result = deliver_weekly_report_email(
        report_root=report_root,
        report_date="2026-06-06",
        send=False,
        smtp_sender=_smtp,
    )

    assert result.email_delivery_status == "dry_run"
    assert result.content_source == "email_preview_txt"
    assert called is False


def test_deliver_weekly_report_email_blocked_when_env_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report_root = tmp_path / "pack"
    report_root.mkdir()
    (report_root / "email").mkdir()
    (report_root / "email" / "email_preview.txt").write_text("body", encoding="utf-8")
    monkeypatch.delenv("WEEKLY_REPORT_EMAIL_ENABLED", raising=False)

    result = deliver_weekly_report_email(
        report_root=report_root,
        report_date="2026-06-06",
        send=True,
    )

    assert result.email_delivery_status == "blocked"
    assert result.reason == "MISSING_REQUIRED_EMAIL_ENV"
    assert "WEEKLY_REPORT_EMAIL_ENABLED" in result.missing


def test_deliver_weekly_report_email_mocked_send_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report_root = tmp_path / "pack"
    report_root.mkdir()
    (report_root / "email").mkdir()
    (report_root / "email" / "email_preview.txt").write_text("body", encoding="utf-8")

    monkeypatch.setenv("WEEKLY_REPORT_EMAIL_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "sender@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password-secret")
    monkeypatch.setenv("WEEKLY_REPORT_EMAIL_FROM", "sender@gmail.com")
    monkeypatch.setenv("WEEKLY_REPORT_EMAIL_TO", "recipient@gmail.com")

    captured: dict[str, object] = {}

    def _smtp(*, message: EmailMessage, host: str, port: int, username: str, password: str) -> None:
        captured["host"] = host
        captured["port"] = port
        captured["username"] = username
        captured["password"] = password
        captured["subject"] = message["Subject"]

    result = deliver_weekly_report_email(
        report_root=report_root,
        report_date="2026-06-06",
        send=True,
        smtp_sender=_smtp,
    )

    assert result.email_delivery_status == "sent"
    assert result.recipient_redacted == "r***@gmail.com"
    assert captured["password"] == "app-password-secret"
    assert captured["subject"] == "[invest-alpha-os] Weekly Report 2026-06-06"
    rendered = render_weekly_email_delivery_markdown(result)
    assert "app-password-secret" not in rendered
    assert "recipient@gmail.com" not in rendered


def test_deliver_weekly_report_email_mocked_send_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report_root = tmp_path / "pack"
    report_root.mkdir()
    (report_root / "email").mkdir()
    (report_root / "email" / "email_preview.txt").write_text("body", encoding="utf-8")

    monkeypatch.setenv("WEEKLY_REPORT_EMAIL_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "sender@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password-secret")
    monkeypatch.setenv("WEEKLY_REPORT_EMAIL_FROM", "sender@gmail.com")
    monkeypatch.setenv("WEEKLY_REPORT_EMAIL_TO", "recipient@gmail.com")

    def _smtp(**_kwargs: object) -> None:
        raise smtplib.SMTPException("smtp failed")

    result = deliver_weekly_report_email(
        report_root=report_root,
        report_date="2026-06-06",
        send=True,
        smtp_sender=_smtp,
    )

    assert result.email_delivery_status == "failed"
    assert result.reason == "EMAIL_SEND_FAILED"


def test_weekly_report_email_send_cli_dry_run(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from invis_alpha_os.cli.main import app

    report_root = tmp_path / "pack"
    report_root.mkdir()
    (report_root / "README_FOR_USER.md").write_text("weekly", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "weekly-report-email-send",
            "--report-date",
            "2026-06-06",
            "--report-root",
            str(report_root),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["email_delivery_status"] == "dry_run"


def test_render_markdown_never_contains_password_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEEKLY_REPORT_EMAIL_ENABLED", "false")
    report_root = tmp_path / "pack"
    report_root.mkdir()
    (report_root / "README_FOR_USER.md").write_text("x", encoding="utf-8")
    result = deliver_weekly_report_email(report_root=report_root, report_date="2026-06-06", send=False)
    payload = json.loads(json.dumps({"missing": list(result.missing)}))
    assert "SMTP_PASSWORD" not in str(payload)
