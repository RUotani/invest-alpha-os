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
    credentials_configured,
    encode_message_raw,
    ensure_gmail_credentials,
    send_gmail_message,
    validate_gmail_send_gates,
)

runner = CliRunner()


def test_build_daily_email_from_bundle(tmp_path: Path) -> None:
    bundle = tmp_path / "2026-05-20"
    bundle.mkdir()
    (bundle / "operator_summary.md").write_text("stale 0 fresh_enough 16", encoding="utf-8")
    (bundle / "daily_us_cache_preview.md").write_text("### US Cache Preview (opt-in)\n", encoding="utf-8")
    (bundle / "signals_us_cache_preview.md").write_text(
        "## Momentum Signals — JP Watchlist\n\n"
        "| # | Code / Name | Sv2 | Labels | r5 | r20 | r60 | HiDist | VolR | Veto |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| 1 | 7203 トヨタ | 6 | positive_20d_60d_momentum | +0.1% | +0.4% | +0.5% | -0.4% | 1.02x | — |\n",
        encoding="utf-8",
    )
    draft = build_daily_email_from_bundle(bundle, main_commit="abc1234")
    assert "売買推奨" in draft.text_body
    assert "投資観測レポート" in draft.subject
    assert "2026-05-20" in draft.subject
    assert "## 日本株モメンタム観測" in draft.text_body
    assert "## 今日の注目ポイント" in draft.text_body
    assert "## 銘柄別コメント" in draft.text_body
    assert "7203" in draft.text_body
    assert "コード / 銘柄名" in draft.text_body or "コード" in draft.text_body


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


def test_daily_email_has_no_markdown_attachments(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle_attach"
    bundle.mkdir()
    (bundle / "operator_summary.md").write_text("stale 0", encoding="utf-8")
    (bundle / "signals_us_cache_preview.md").write_text(
        "| # | Code / Name | Sv2 | Labels | r5 | r20 | r60 | HiDist | VolR | Veto |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| 1 | 7203 トヨタ | 6 | positive_20d_60d_momentum | +0.1% | +0.4% | +0.5% | -0.4% | 1.02x | — |\n",
        encoding="utf-8",
    )
    r = runner.invoke(app, ["daily-email", "--bundle-dir", str(bundle), "--dry-run"])
    assert r.exit_code == 0
    eml = (bundle / "email" / "email_preview.eml").read_bytes()
    assert b"Content-Disposition: attachment" not in eml
    assert b"operator_summary.md" not in eml


def test_daily_email_send_without_confirm_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = tmp_path / "bundle2"
    bundle.mkdir()
    (bundle / "operator_summary.md").write_text("x", encoding="utf-8")
    monkeypatch.delenv("CONFIRM_GMAIL_SEND", raising=False)
    monkeypatch.setenv("GMAIL_REPORT_TO", "self@example.com")
    r = runner.invoke(app, ["daily-email", "--bundle-dir", str(bundle), "--send"])
    assert r.exit_code == 2


def test_subject_japanese_observation_report(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle3"
    bundle.mkdir()
    (bundle / "operator_summary.md").write_text("stale 0 fresh_enough 16", encoding="utf-8")
    draft = build_daily_email_from_bundle(bundle)
    assert "投資観測レポート" in draft.subject
    assert "Daily Observation Report" not in draft.subject
    assert "期限切れ 0" in draft.subject


def test_credentials_configured_requires_credentials_file_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cred = tmp_path / "gmail_credentials.json"
    cred.write_text('{"installed": {}}', encoding="utf-8")
    token = tmp_path / "missing_token.json"
    monkeypatch.setenv("GMAIL_CREDENTIALS_FILE", str(cred))
    monkeypatch.setenv("GMAIL_TOKEN_FILE", str(token))
    assert credentials_configured() is True
    assert token.is_file() is False


def test_ensure_gmail_credentials_missing_token_runs_oauth_flow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cred = tmp_path / "gmail_credentials.json"
    cred.write_text('{"installed": {"client_id": "x", "client_secret": "y"}}', encoding="utf-8")
    token = tmp_path / "gmail_token.json"
    monkeypatch.setenv("GMAIL_CREDENTIALS_FILE", str(cred))
    monkeypatch.setenv("GMAIL_TOKEN_FILE", str(token))

    mock_creds = type("Creds", (), {"valid": True, "expired": False, "refresh_token": None})()
    mock_creds.to_json = lambda: '{"token": "saved"}'  # type: ignore[method-assign]

    class MockFlow:
        @staticmethod
        def from_client_secrets_file(path: str, scopes: list[str]) -> "MockFlow":
            assert path == str(cred)
            return MockFlow()

        def run_local_server(self, port: int = 0) -> object:
            assert port == 0
            return mock_creds

    from google.oauth2.credentials import Credentials

    monkeypatch.setattr(
        Credentials,
        "from_authorized_user_file",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("no token")),
    )
    monkeypatch.setattr("google_auth_oauthlib.flow.InstalledAppFlow", MockFlow)

    out = ensure_gmail_credentials()
    assert out is mock_creds
    assert token.is_file()
    assert "saved" in token.read_text(encoding="utf-8")


def test_ensure_gmail_credentials_valid_token_skips_oauth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cred = tmp_path / "gmail_credentials.json"
    cred.write_text("{}", encoding="utf-8")
    token = tmp_path / "gmail_token.json"
    token.write_text('{"token": "ok"}', encoding="utf-8")
    monkeypatch.setenv("GMAIL_CREDENTIALS_FILE", str(cred))
    monkeypatch.setenv("GMAIL_TOKEN_FILE", str(token))

    mock_creds = type("Creds", (), {"valid": True, "expired": False})()
    oauth_called = {"n": 0}

    class MockFlow:
        @staticmethod
        def from_client_secrets_file(*_a: object, **_k: object) -> object:
            oauth_called["n"] += 1
            raise AssertionError("OAuth should not run")

    from google.oauth2.credentials import Credentials

    monkeypatch.setattr(Credentials, "from_authorized_user_file", lambda *_a, **_k: mock_creds)
    monkeypatch.setattr("google_auth_oauthlib.flow.InstalledAppFlow", MockFlow)
    assert ensure_gmail_credentials() is mock_creds
    assert oauth_called["n"] == 0


def test_ensure_gmail_credentials_expired_refreshes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cred = tmp_path / "gmail_credentials.json"
    cred.write_text("{}", encoding="utf-8")
    token = tmp_path / "gmail_token.json"
    token.write_text('{"token": "old"}', encoding="utf-8")
    monkeypatch.setenv("GMAIL_CREDENTIALS_FILE", str(cred))
    monkeypatch.setenv("GMAIL_TOKEN_FILE", str(token))

    mock_creds = type(
        "Creds",
        (),
        {"valid": False, "expired": True, "refresh_token": "rt"},
    )()
    mock_creds.to_json = lambda: '{"token": "refreshed"}'  # type: ignore[method-assign]
    refreshed = {"called": False}

    def fake_refresh(_req: object) -> None:
        refreshed["called"] = True
        mock_creds.valid = True
        mock_creds.expired = False

    mock_creds.refresh = fake_refresh  # type: ignore[method-assign]

    class MockFlow:
        @staticmethod
        def from_client_secrets_file(*_a: object, **_k: object) -> object:
            raise AssertionError("OAuth should not run when refresh_token exists")

    from google.oauth2.credentials import Credentials

    monkeypatch.setattr(Credentials, "from_authorized_user_file", lambda *_a, **_k: mock_creds)
    monkeypatch.setattr("google_auth_oauthlib.flow.InstalledAppFlow", MockFlow)
    ensure_gmail_credentials()
    assert refreshed["called"] is True
    assert "refreshed" in token.read_text(encoding="utf-8")


def test_ensure_gmail_credentials_missing_credentials_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GMAIL_CREDENTIALS_FILE", str(tmp_path / "nope.json"))
    monkeypatch.setenv("GMAIL_TOKEN_FILE", str(tmp_path / "token.json"))
    with pytest.raises(GmailSendBlockedError, match="GMAIL_CREDENTIALS_FILE"):
        ensure_gmail_credentials(allow_interactive_oauth=False)


def test_send_gmail_message_uses_ensure_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cred = tmp_path / "gmail_credentials.json"
    cred.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GMAIL_CREDENTIALS_FILE", str(cred))
    monkeypatch.setenv("GMAIL_TOKEN_FILE", str(tmp_path / "token.json"))

    mock_creds = object()
    ensure_called = {"n": 0}

    def fake_ensure(**_k: object) -> object:
        ensure_called["n"] += 1
        return mock_creds

    monkeypatch.setattr("invis_alpha_os.reports.gmail_delivery.ensure_gmail_credentials", fake_ensure)

    class MockService:
        def users(self) -> "MockService":
            return self

        def messages(self) -> "MockService":
            return self

        def send(self, **kwargs: object) -> "MockService":
            return self

        def execute(self) -> dict[str, str]:
            return {"id": "msg123"}

    monkeypatch.setattr(
        "googleapiclient.discovery.build",
        lambda *_a, **_k: MockService(),
    )
    out = send_gmail_message("rawpayload")
    assert out["id"] == "msg123"
    assert ensure_called["n"] == 1
