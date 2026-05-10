import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.adapters.jquants_client import JQuantsClient

runner = CliRunner()


def test_client_disabled_no_live_http(monkeypatch):
    monkeypatch.delenv("JQUANTS_ENABLED", raising=False)
    c = JQuantsClient.from_env()
    assert c.get_refresh_token()["status"] == "disabled"
    assert c.get_refresh_token(attempt_live=True)["status"] == "disabled"
    assert c.get_id_token()["status"] == "disabled"
    assert c.get_daily_quotes("7011")["status"] == "disabled"


def test_daily_quotes_live_blocked_without_allow(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_EMAIL", "u@example.local")
    monkeypatch.setenv("JQUANTS_PASSWORD", "x")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "false")
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("JQUANTS_ID_TOKEN", raising=False)

    c = JQuantsClient.from_env()
    out = c.get_daily_quotes("7011", from_date="2024-01-01", to_date="2024-01-05", attempt_live=True)
    assert out["status"] == "live_blocked"

    called: list[str] = []

    def _boom(*_a, **_k):
        called.append("http")
        raise AssertionError("no http")

    with patch(
        "invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen",
        side_effect=_boom,
    ):
        out2 = c.get_daily_quotes("7011", from_date="2024-01-01", to_date="2024-01-05", attempt_live=True)
    assert out2["status"] == "live_blocked"
    assert called == []


def test_refresh_token_success_no_secret_in_dict(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_EMAIL", "user@example.local")
    monkeypatch.setenv("JQUANTS_PASSWORD", "secret-value")

    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps({"refreshToken": "SUPER_SECRET_REFRESH"}).encode(
        "utf-8"
    )
    cm.__exit__.return_value = None

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", return_value=cm):
        out = JQuantsClient.from_env().get_refresh_token(attempt_live=True)

    assert out["status"] == "success"
    assert "refresh_token" not in out
    assert out.get("refresh_token_obtained") is True
    assert out.get("raw_response_included") is False
    serialized = json.dumps(out)
    assert "SUPER_SECRET" not in serialized
    assert "secret-value" not in serialized


def test_get_daily_quotes_live_success_no_body_in_dict(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_ID_TOKEN", "SECRET_ID_TOKEN_VALUE")
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)

    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(
        {"quotes": [{"Close": 100, "Code": "7011"}]}
    ).encode("utf-8")
    cm.__exit__.return_value = None

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", return_value=cm):
        out = JQuantsClient.from_env().get_daily_quotes(
            "7011",
            from_date="2024-01-02",
            to_date="2024-01-04",
            attempt_live=True,
        )

    assert out["status"] == "success"
    assert "body" not in out
    assert out.get("raw_response_included") is False
    s = json.dumps(out)
    assert "SECRET_ID_TOKEN" not in s
    assert '"Close"' not in s


def test_debug_jquants_status_never_calls_urlopen(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_EMAIL", "u@example.local")
    monkeypatch.setenv("JQUANTS_PASSWORD", "ultra-secret-password-123")
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "rt")
    monkeypatch.setenv("JQUANTS_ID_TOKEN", "id")

    called: list[str] = []

    def _boom(*_a, **_k):
        called.append("x")
        raise AssertionError("jquants-status must not open HTTP")

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_boom):
        r = runner.invoke(app, ["debug", "jquants-status"])
    assert r.exit_code == 0
    assert called == []
    assert "never performs HTTP" in r.stdout
    assert "ultra-secret-password-123" not in r.stdout


def test_debug_jquants_status_output_masked(monkeypatch):
    monkeypatch.delenv("JQUANTS_ENABLED", raising=False)
    r = runner.invoke(app, ["debug", "jquants-status"])
    assert r.exit_code == 0
    assert "token_preview" in r.stdout
    assert "***" in r.stdout


def test_debug_daily_quotes_default_dry_run(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_EMAIL", "a@b.c")
    monkeypatch.setenv("JQUANTS_PASSWORD", "s")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")

    called: list[str] = []

    def _boom(*_a, **_k):
        called.append("http")
        raise AssertionError("default must be dry-run")

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_boom):
        r = runner.invoke(
            app,
            [
                "debug",
                "jquants-daily-quotes",
                "--code",
                "7011",
                "--from-date",
                "2024-01-01",
                "--to-date",
                "2024-01-05",
            ],
        )
    assert r.exit_code == 0
    assert called == []
    assert "dry_run" in r.stdout


def test_debug_daily_quotes_live_without_allow_no_http(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ID_TOKEN", "X")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "false")

    called: list[str] = []

    def _boom(*_a, **_k):
        called.append("http")
        raise AssertionError("no http")

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_boom):
        r = runner.invoke(
            app,
            [
                "debug",
                "jquants-daily-quotes",
                "--live",
                "--code",
                "7011",
                "--from-date",
                "2024-01-01",
                "--to-date",
                "2024-01-05",
            ],
        )
    assert r.exit_code == 0
    assert called == []
    assert "live_blocked" in r.stdout


def test_client_dry_run_when_no_attempt_live(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_EMAIL", "user@example.local")
    monkeypatch.setenv("JQUANTS_PASSWORD", "x")
    c = JQuantsClient.from_env()
    assert c.get_refresh_token(attempt_live=False)["status"] == "dry_run"


def test_daily_quotes_default_dry_run_explicit(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    c = JQuantsClient.from_env()
    assert c.get_daily_quotes("7011", from_date="2024-01-01", to_date="2024-01-05")["status"] == "dry_run"
