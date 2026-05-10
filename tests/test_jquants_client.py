import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.adapters.jquants_client import JQuantsClient

runner = CliRunner()


def _patch_base(monkeypatch) -> None:
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://jq.test.invalid/v0")


def test_client_disabled_no_live_http(monkeypatch):
    monkeypatch.delenv("JQUANTS_ENABLED", raising=False)
    _patch_base(monkeypatch)
    c = JQuantsClient.from_env()
    assert c.get_refresh_token()["status"] == "disabled"
    assert c.get_refresh_token(attempt_live=True)["status"] == "disabled"
    assert c.get_id_token()["status"] == "disabled"
    assert c.get_daily_quotes("7011")["status"] == "disabled"


def test_not_configured_when_base_url_missing(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.delenv("JQUANTS_API_BASE_URL", raising=False)

    c = JQuantsClient.from_env()
    status = c.safe_auth_status()
    assert status["base_url_present"] is False
    assert status["api_version"] == "v2"
    assert status["api_version_effective"] == "v2"
    assert status["unsupported_api_version"] is False

    nc = c.get_daily_quotes("7011")
    assert nc["status"] == "not_configured"
    assert nc.get("reason") == "base_url_missing"
    assert "JQUANTS_API_BASE_URL" in nc["missing"]


def test_daily_quotes_live_blocked_without_allow(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_EMAIL", "u@example.local")
    monkeypatch.setenv("JQUANTS_PASSWORD", "x")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "false")
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("JQUANTS_ID_TOKEN", raising=False)
    _patch_base(monkeypatch)

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
    _patch_base(monkeypatch)

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
    assert out.get("api_version") is not None
    serialized = json.dumps(out)
    assert "SUPER_SECRET" not in serialized
    assert "secret-value" not in serialized


def test_get_daily_quotes_live_success_no_body_in_dict(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_ID_TOKEN", "SECRET_ID_TOKEN_VALUE")
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    _patch_base(monkeypatch)

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
    data = json.loads(r.stdout.strip().split("(never")[0].strip())
    assert "allow_live_http" in data and "configured" in data
    assert data.get("unsupported_api_version") is False
    assert data.get("raw_response_included") is False
    assert "password" not in data


def test_debug_jquants_status_output_masked(monkeypatch):
    monkeypatch.delenv("JQUANTS_ENABLED", raising=False)
    r = runner.invoke(app, ["debug", "jquants-status"])
    assert r.exit_code == 0
    blob = json.loads(r.stdout.strip().split("(never")[0].strip())
    assert blob.get("token_preview") == "***"
    assert blob.get("base_url_present") is False
    assert blob.get("unsupported_api_version") is False


def test_debug_daily_quotes_default_dry_run(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_EMAIL", "a@b.c")
    monkeypatch.setenv("JQUANTS_PASSWORD", "s")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    _patch_base(monkeypatch)

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
    _patch_base(monkeypatch)

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
    _patch_base(monkeypatch)
    c = JQuantsClient.from_env()
    assert c.get_refresh_token(attempt_live=False)["status"] == "dry_run"


def test_daily_quotes_default_dry_run_explicit(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    _patch_base(monkeypatch)
    c = JQuantsClient.from_env()
    assert c.get_daily_quotes("7011", from_date="2024-01-01", to_date="2024-01-05")["status"] == "dry_run"


def test_safe_auth_status_respects_jquants_api_version_env(monkeypatch):
    monkeypatch.setenv("JQUANTS_API_VERSION", "v1")
    monkeypatch.delenv("JQUANTS_ENABLED", raising=False)
    s = JQuantsClient.from_env().safe_auth_status()
    assert s["api_version"] == "v1"
    assert s["api_version_effective"] == "v1"
    assert s["unsupported_api_version"] is False


def test_unsupported_api_version_blocks_all_http(monkeypatch):
    monkeypatch.setenv("JQUANTS_API_VERSION", "v3")
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_EMAIL", "u@example.local")
    monkeypatch.setenv("JQUANTS_PASSWORD", "pw")
    monkeypatch.setenv("JQUANTS_ID_TOKEN", "must-not-appear")
    _patch_base(monkeypatch)

    called: list[str] = []

    def _boom(*_a, **_k):
        called.append("http")
        raise AssertionError("no http for unsupported API version")

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_boom):
        c = JQuantsClient.from_env()
        assert c.safe_auth_status()["unsupported_api_version"] is True
        assert c.safe_auth_status()["api_version"] == "v3"
        assert c.safe_auth_status()["api_version_effective"] is None
        assert c.get_refresh_token(attempt_live=True)["status"] == "unsupported_version"
        assert c.get_id_token(attempt_live=True, refresh_override="rt")["status"] == "unsupported_version"
        out = c.get_daily_quotes(
            "7011",
            from_date="2024-01-01",
            to_date="2024-01-05",
            attempt_live=True,
        )
        assert out["status"] == "unsupported_version"

    assert called == []

    dumped = json.dumps(
        [
            c.get_refresh_token(attempt_live=True),
            c.safe_auth_status(),
        ]
    )
    assert "must-not-appear" not in dumped


def test_base_url_missing_full_live_gate_no_http(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_ID_TOKEN", "SECRET_SHOULD_NOT_LEAK")
    monkeypatch.delenv("JQUANTS_API_BASE_URL", raising=False)

    called: list[str] = []

    def _boom(*_a, **_k):
        called.append("x")
        raise AssertionError("urlopen")

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_boom):
        c = JQuantsClient.from_env()
        result = c.get_daily_quotes(
            "7011",
            from_date="2024-01-02",
            to_date="2024-01-04",
            attempt_live=True,
        )
    assert result["status"] == "not_configured"
    assert result.get("reason") == "base_url_missing"
    assert called == []
    assert "SECRET_SHOULD_NOT_LEAK" not in json.dumps(result)


def test_debug_jquants_daily_quotes_live_no_base_url_no_http(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_ID_TOKEN", "X")
    monkeypatch.delenv("JQUANTS_API_BASE_URL", raising=False)

    called: list[str] = []

    def _boom(*_a, **_k):
        called.append("x")
        raise AssertionError("urlopen")

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
    assert r.exit_code == 1
    assert called == []
    assert "not_configured" in r.stdout
    assert "base_url_missing" in r.stdout
    assert "X" not in r.stdout


def test_debug_jquants_status_shows_unsupported_version(monkeypatch):
    monkeypatch.setenv("JQUANTS_API_VERSION", "nightly")
    monkeypatch.delenv("JQUANTS_ENABLED", raising=False)
    r = runner.invoke(app, ["debug", "jquants-status"])
    assert r.exit_code == 0
    blob = json.loads(r.stdout.strip().split("(never")[0].strip())
    assert blob["api_version"] == "nightly"
    assert blob["unsupported_api_version"] is True
    assert blob["api_version_effective"] is None
