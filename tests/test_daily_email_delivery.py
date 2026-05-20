"""Daily email draft and gated Gmail delivery."""

from __future__ import annotations

import base64
from email import message_from_bytes
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.daily_email import build_daily_email_from_bundle
from invis_alpha_os.reports.gmail_delivery import (
    GmailSendBlockedError,
    build_mime_message,
    encode_message_raw,
    validate_gmail_send_gates,
    write_email_previews,
)

runner = CliRunner()


def test_build_daily_email_from_bundle(tmp_path: Path) -> None:
    bundle = tmp_path / "2026-05-20"
    bundle.mkdir()
    (bundle / "operator_summary.md").write_text("stale 0 fresh_enough 16", encoding="utf-8")
    (bundle / "daily_us_cache_preview.md").write_text("### US Cache Preview (opt-in)\n", encoding="utf-8")
    (bundle / "signals_us_cache_preview.md").write_text("preview ok", encoding="utf-8")
    draft = build_daily_email_from_bundle(bundle, main_commit="abc1234")
    assert "Observation only" in draft.text_body
    assert "not buy/sell" in draft.text_body.lower() or "not buy" in draft.text_body.lower()
    assert "2026-05-20" in draft.subject
    assert "daily_us_cache_preview" in draft.text_body or "US Cache Preview" in draft.text_body


def test_mime_raw_base64url() -> None:
    msg = build_mime_message(
        sender="me",
        to=["test@example.com"],
        subject="[invest-alpha-os] test",
        text_body="observation only",
    )
    raw = encode_message_raw(msg)
    decoded = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    parsed = message_from_bytes(decoded)
    assert parsed["Subject"] == "[invest-alpha-os] test"


def test_send_gate_requires_confirm() -> None:
    with pytest.raises(GmailSendBlockedError, match="CONFIRM_GMAIL_SEND"):
        validate_gmail_send_gates(recipient="a@b.com", confirm_env="")


def test_send_gate_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONFIRM_GMAIL_SEND", "YES")
    with pytest.raises(GmailSendBlockedError, match="GMAIL_REPORT_ALLOWLIST"):
        validate_gmail_send_gates(
            recipient="other@example.com",
            allowlist_env="self@example.com",
        )
    validate_gmail_send_gates(
        recipient="self@example.com",
        allowlist_env="self@example.com",
    )


def test_daily_email_dry_run_cli(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "operator_summary.md").write_text("summary", encoding="utf-8")
    r = runner.invoke(app, ["daily-email", "--bundle-dir", str(bundle), "--dry-run"])
    assert r.exit_code == 0, r.stdout + r.stderr
    assert (bundle / "email" / "email_preview.eml").is_file()
    assert "dry-run only" in r.stdout


def test_daily_email_send_without_confirm_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = tmp_path / "bundle2"
    bundle.mkdir()
    (bundle / "operator_summary.md").write_text("x", encoding="utf-8")
    monkeypatch.delenv("CONFIRM_GMAIL_SEND", raising=False)
    monkeypatch.setenv("GMAIL_REPORT_TO", "self@example.com")
    r = runner.invoke(app, ["daily-email", "--bundle-dir", str(bundle), "--send"])
    assert r.exit_code == 2
