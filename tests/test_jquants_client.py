import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.adapters.jquants_client import JQuantsClient, normalize_v2_daily_bars_response

runner = CliRunner()


def _patch_base(monkeypatch) -> None:
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://jq.test.invalid/v0")


def test_paths_for_version_v2_daily_quotes():
    from invis_alpha_os.data.adapters.jquants_client import _paths_for_version

    p = _paths_for_version("v2")
    assert p["daily_quotes"] == "/equities/bars/daily"
    assert p["listed_master"] == "/equities/master"


def test_join_v2_base_path_no_duplicate_v2():
    from invis_alpha_os.data.adapters.jquants_client import _join_v2_base_and_path

    assert (
        _join_v2_base_and_path("https://api.jquants.com/v2", "/equities/bars/daily")
        == "https://api.jquants.com/v2/equities/bars/daily"
    )
    assert (
        _join_v2_base_and_path("https://api.jquants.com/v2/", "/v2/equities/bars/daily")
        == "https://api.jquants.com/v2/equities/bars/daily"
    )


def test_build_v2_preview_jquants_style_base_and_no_secret_leak(monkeypatch):
    monkeypatch.delenv("JQUANTS_ENABLED", raising=False)
    monkeypatch.setenv("JQUANTS_API_VERSION", "v2")
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://api.jquants.com/v2")
    monkeypatch.setenv("JQUANTS_API_KEY", "NEVER_PRINT_THIS_KEY_STRING")
    prv = JQuantsClient.from_env().build_v2_daily_bars_request_preview(
        "70110",
        from_date="2026-05-08",
        to_date="2026-05-08",
    )
    assert prv["status"] == "ok"
    assert prv["endpoint_url_without_query"] == "https://api.jquants.com/v2/equities/bars/daily"
    assert "/v2/v2/" not in prv["full_url_without_secrets"]
    assert prv["query_params"] == {"code": "70110", "from": "20260508", "to": "20260508"}
    q = urlparse(prv["full_url_without_secrets"]).query
    assert "from_date" not in q and "to_date" not in q
    assert parse_qs(q)["from"] == ["20260508"] and parse_qs(q)["to"] == ["20260508"]
    assert prv["api_key_header_present"] is True
    assert prv["api_key_value_included"] is False
    assert "NEVER_PRINT_THIS_KEY_STRING" not in json.dumps(prv)


def test_preview_request_cli_never_opens_http(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://api.jquants.com/v2")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")

    called: list[str] = []

    def _boom(*_a, **_k):
        called.append("http")
        raise AssertionError("preview must not call urlopen")

    with patch(
        "invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen",
        side_effect=_boom,
    ):
        r = runner.invoke(
            app,
            [
                "debug",
                "jquants-daily-quotes",
                "--preview-request",
                "--code",
                "70110",
                "--from-date",
                "2026-05-08",
                "--to-date",
                "2026-05-08",
            ],
        )
    assert r.exit_code == 0
    assert called == []
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "ok"


def test_v2_safe_auth_status_auth_method_and_api_key_present(monkeypatch):
    monkeypatch.delenv("JQUANTS_API_VERSION", raising=False)
    monkeypatch.setenv("JQUANTS_API_KEY", "fake-key-for-test-only")
    monkeypatch.delenv("JQUANTS_ENABLED", raising=False)
    s = JQuantsClient.from_env().safe_auth_status()
    assert s["api_version_effective"] == "v2"
    assert s["auth_method"] == "api_key"
    assert s["api_key_present"] is True
    assert s["configured"] is True


def test_v2_safe_auth_status_no_api_key(monkeypatch):
    monkeypatch.delenv("JQUANTS_API_VERSION", raising=False)
    monkeypatch.delenv("JQUANTS_API_KEY", raising=False)
    s = JQuantsClient.from_env().safe_auth_status()
    assert s["auth_method"] == "api_key"
    assert s["api_key_present"] is False
    assert s["configured"] is False


def test_v2_get_refresh_token_not_applicable(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    _patch_base(monkeypatch)
    c = JQuantsClient.from_env()
    assert c.get_refresh_token(attempt_live=False)["status"] == "not_applicable"


def test_v2_get_daily_quotes_live_missing_api_key(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.delenv("JQUANTS_API_KEY", raising=False)
    _patch_base(monkeypatch)
    out = JQuantsClient.from_env().get_daily_quotes("7011", attempt_live=True)
    assert out["status"] == "not_configured"
    assert out.get("reason") == "api_key_missing"


def test_normalize_v2_daily_bars_data_must_be_list():
    assert normalize_v2_daily_bars_response({"data": {"message": "error"}}) == {
        "status": "invalid_response",
        "reason": "data_not_list",
    }


def test_normalize_v2_daily_bars_success_list():
    r = normalize_v2_daily_bars_response({"data": [{"Code": "86970"}]})
    assert r == {"status": "success", "row_count": 1, "source_key": "data"}


def test_normalize_v2_daily_bars_empty_list_success():
    r = normalize_v2_daily_bars_response({"data": []})
    assert r == {"status": "success", "row_count": 0, "source_key": "data"}


def test_normalize_v2_message_only_invalid():
    assert normalize_v2_daily_bars_response({"message": "error"}) == {
        "status": "invalid_response",
        "reason": "missing_list_field",
    }


def test_normalize_v2_first_key_wins_data_before_daily_quotes():
    r = normalize_v2_daily_bars_response({"data": [], "daily_quotes": [{"x": 1}]})
    assert r["row_count"] == 0
    assert r["source_key"] == "data"


def test_v2_get_daily_quotes_live_success_x_api_key_header(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "PLACEHOLDER_KEY_FOR_CI_TEST")
    _patch_base(monkeypatch)
    captured: dict[str, str | None] = {}

    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps({"bars": [{"open": 1}]}).encode("utf-8")
    cm.__exit__.return_value = None

    def _urlopen(req, timeout=None):  # noqa: ANN001
        hdrs = {k.lower(): v for k, v in req.header_items()}
        captured["x-api-key"] = hdrs.get("x-api-key")
        return cm

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_urlopen):
        out = JQuantsClient.from_env().get_daily_quotes("7011", from_date="2024-01-02", attempt_live=True)
    assert out["status"] == "success"
    assert captured["x-api-key"] == "PLACEHOLDER_KEY_FOR_CI_TEST"
    assert out.get("row_count") == 1
    assert out.get("source_key") == "bars"
    assert json.dumps(out).count("PLACEHOLDER") == 0


def test_v2_live_query_hyphen_input_becomes_yyyymmdd(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    _patch_base(monkeypatch)
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps({"data": []}).encode("utf-8")
    cm.__exit__.return_value = None
    captured_url: list[str] = []

    def _urlopen(req, timeout=None):  # noqa: ANN001
        captured_url.append(req.full_url)
        return cm

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_urlopen):
        out = JQuantsClient.from_env().get_daily_quotes(
            "70110",
            from_date="2026-05-08",
            to_date="2026-05-08",
            attempt_live=True,
        )
    assert out["status"] == "success"
    assert len(captured_url) == 1
    q = urlparse(captured_url[0]).query
    lowered = q.lower()
    assert "from_date" not in lowered
    assert "to_date" not in lowered
    assert "date_from" not in lowered
    assert "date_to" not in lowered
    assert "from=20260508" in q and "to=20260508" in q
    assert parse_qs(q) == {"code": ["70110"], "from": ["20260508"], "to": ["20260508"]}


def test_v2_live_query_compact_input_wire_yyyymmdd(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    _patch_base(monkeypatch)
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps({"data": []}).encode("utf-8")
    cm.__exit__.return_value = None
    captured_url: list[str] = []

    def _urlopen(req, timeout=None):  # noqa: ANN001
        captured_url.append(req.full_url)
        return cm

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_urlopen):
        JQuantsClient.from_env().get_daily_quotes(
            "70110",
            from_date="20260508",
            to_date="20260508",
            attempt_live=True,
        )
    q = urlparse(captured_url[0]).query
    assert parse_qs(q)["from"] == ["20260508"]
    assert parse_qs(q)["to"] == ["20260508"]


def test_v2_get_daily_quotes_http_error_no_response_body_in_dict(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    _patch_base(monkeypatch)

    def _urlopen(req, timeout=None):  # noqa: ANN001
        raise urllib.error.HTTPError(
            req.full_url,
            400,
            "Bad Request",
            {},
            BytesIO(b'{"message":"upstream hint"}'),
        )

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_urlopen):
        out = JQuantsClient.from_env().get_daily_quotes(
            "70110",
            from_date="2026-05-08",
            to_date="2026-05-08",
            attempt_live=True,
        )
    assert out["status"] == "http_error"
    assert out["http_status"] == 400
    assert out.get("error_body_preview") == "message: upstream hint"
    assert "upstream hint" in json.dumps(out)
    assert out["endpoint_url_without_query"] == "https://jq.test.invalid/v0/equities/bars/daily"
    assert out["query_params"] == {"code": "70110", "from": "20260508", "to": "20260508"}
    assert "/v2/v2/" not in out.get("full_url_without_secrets", "")


def test_cli_jquants_daily_quotes_http_error_safe_stdout(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    _patch_base(monkeypatch)

    def _urlopen(req, timeout=None):  # noqa: ANN001
        raise urllib.error.HTTPError(
            req.full_url,
            400,
            "Bad Request",
            {},
            BytesIO(b'{"message":"see documentation"}'),
        )

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_urlopen):
        r = runner.invoke(
            app,
            [
                "debug",
                "jquants-daily-quotes",
                "--live",
                "--code",
                "70110",
                "--from-date",
                "2026-05-08",
                "--to-date",
                "2026-05-08",
            ],
        )
    assert r.exit_code == 1
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "http_error"
    assert blob["http_status"] == 400
    assert blob["code"] == "70110"
    assert blob["date_from"] == "2026-05-08"
    assert blob["query_params"] == {"code": "70110", "from": "20260508", "to": "20260508"}
    assert blob["api_key_header_name"] == "x-api-key"
    assert blob["api_key_value_included"] is False
    assert blob["raw_response_included"] is False
    assert blob.get("error_body_preview") == "message: see documentation"
    assert blob["endpoint_url_without_query"].endswith("/equities/bars/daily")
    assert "/v2/v2/" not in blob.get("full_url_without_secrets", "")
    assert "see documentation" in r.stdout


def test_v2_get_daily_quotes_live_non_json_not_success(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "PLACEHOLDER_KEY_FOR_CI_TEST")
    _patch_base(monkeypatch)
    leaked = "SECRET_RAW_BODY_MARKER_XYZ987"
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = f"<html>{leaked}</html>".encode("utf-8")
    cm.__exit__.return_value = None
    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", return_value=cm):
        out = JQuantsClient.from_env().get_daily_quotes(
            "7011",
            from_date="2024-01-02",
            attempt_live=True,
        )
    assert out["status"] == "non_json_response"
    assert leaked not in json.dumps(out)
    assert out.get("raw_response_included") is False


def test_v2_get_daily_quotes_live_json_array_invalid(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    _patch_base(monkeypatch)
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps([{"foo": 1}]).encode("utf-8")
    cm.__exit__.return_value = None
    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", return_value=cm):
        out = JQuantsClient.from_env().get_daily_quotes("7011", attempt_live=True)
    assert out["status"] == "invalid_response"
    assert out.get("reason") == "top_level_array"


def test_v2_get_daily_quotes_live_dict_missing_expected_keys(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    _patch_base(monkeypatch)
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps({"quotes": [], "items": []}).encode("utf-8")
    cm.__exit__.return_value = None
    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", return_value=cm):
        out = JQuantsClient.from_env().get_daily_quotes("7011", attempt_live=True)
    assert out["status"] == "invalid_response"
    assert out.get("reason") == "missing_list_field"


def test_v2_get_daily_quotes_live_dict_with_data_key_success(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    _patch_base(monkeypatch)
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps({"data": [{"Close": 1}]}).encode("utf-8")
    cm.__exit__.return_value = None
    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", return_value=cm):
        out = JQuantsClient.from_env().get_daily_quotes("7011", attempt_live=True)
    assert out["status"] == "success"
    assert out.get("row_count") == 1
    assert out.get("source_key") == "data"
    blob = json.dumps(out)
    assert '"Close"' not in blob


def test_v2_get_daily_quotes_live_data_object_invalid(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    _patch_base(monkeypatch)
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps({"data": {"message": "error"}}).encode("utf-8")
    cm.__exit__.return_value = None
    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", return_value=cm):
        out = JQuantsClient.from_env().get_daily_quotes("70110", attempt_live=True)
    assert out["status"] == "invalid_response"
    assert out.get("reason") == "data_not_list"


def test_v2_get_daily_quotes_live_json_null_invalid(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    _patch_base(monkeypatch)
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(None).encode("utf-8")
    cm.__exit__.return_value = None
    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", return_value=cm):
        out = JQuantsClient.from_env().get_daily_quotes("7011", attempt_live=True)
    assert out["status"] == "invalid_response"
    assert out.get("reason") == "not_json_object"


def test_debug_jquants_daily_quotes_live_invalid_response_exit_1(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    _patch_base(monkeypatch)
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps({"message": "error"}).encode("utf-8")
    cm.__exit__.return_value = None
    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", return_value=cm):
        r = runner.invoke(
            app,
            [
                "debug",
                "jquants-daily-quotes",
                "--live",
                "--code",
                "70110",
                "--from-date",
                "2024-01-01",
                "--to-date",
                "2024-01-05",
            ],
        )
    assert r.exit_code == 1
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "invalid_response"


def test_debug_jquants_daily_quotes_live_success_output_has_no_secret_fields(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "NEVER_LEAK_THIS_KEY_VALUE")
    _patch_base(monkeypatch)
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps({"data": [{"Code": "70110"}]}).encode("utf-8")
    cm.__exit__.return_value = None
    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", return_value=cm):
        r = runner.invoke(
            app,
            [
                "debug",
                "jquants-daily-quotes",
                "--live",
                "--code",
                "70110",
                "--from-date",
                "2024-01-01",
                "--to-date",
                "2024-01-02",
            ],
        )
    assert r.exit_code == 0
    assert "NEVER_LEAK_THIS_KEY_VALUE" not in r.stdout
    assert "70110" in r.stdout
    data = json.loads(r.stdout.strip())
    assert data["row_count"] == 1
    assert "token" not in "".join(r.stdout.lower())
    assert "password" not in r.stdout.lower()
    assert '"Code"' not in r.stdout


def test_debug_daily_quotes_live_non_json_exit_1(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    _patch_base(monkeypatch)
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = b"unexpected plain text body"
    cm.__exit__.return_value = None
    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", return_value=cm):
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
    assert "non_json_response" in r.stdout
    assert "unexpected plain text body" not in r.stdout


def test_v2_api_key_but_base_url_missing_live(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    monkeypatch.delenv("JQUANTS_API_BASE_URL", raising=False)
    out = JQuantsClient.from_env().get_daily_quotes("7011", attempt_live=True)
    assert out["status"] == "not_configured"
    assert out.get("reason") == "base_url_missing"


def test_debug_jquants_status_includes_auth_method_no_secret(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "NEVER_SHOW_THIS_KEY_ON_CLI")
    _patch_base(monkeypatch)
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    r = runner.invoke(app, ["debug", "jquants-status"])
    assert r.exit_code == 0
    assert "NEVER_SHOW_THIS_KEY_ON_CLI" not in r.stdout
    data = json.loads(r.stdout.strip().split("(never")[0].strip())
    assert data["auth_method"] == "api_key"
    assert data["api_key_present"] is True
    assert data.get("api_key_preview") == "***"


def test_debug_daily_quotes_live_missing_api_key_exit_1(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.delenv("JQUANTS_API_KEY", raising=False)
    _patch_base(monkeypatch)
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
    assert "api_key_missing" in r.stdout


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
    monkeypatch.setenv("JQUANTS_API_VERSION", "v1")
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


def test_get_daily_quotes_live_success_v1_bearer_no_body_in_dict(monkeypatch):
    monkeypatch.setenv("JQUANTS_API_VERSION", "v1")
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
    assert data.get("auth_method") == "api_key"
    assert data.get("api_key_present") is False
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
    assert blob.get("auth_method") == "api_key"


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
    assert "equities/bars/daily" in r.stdout


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
    assert r.exit_code == 1
    assert called == []
    assert "live_blocked" in r.stdout


def test_debug_daily_quotes_disabled_no_flag_exit_0(monkeypatch):
    monkeypatch.delenv("JQUANTS_ENABLED", raising=False)
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "false")
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
    assert r.stdout.count("disabled") >= 1


def test_debug_daily_quotes_disabled_with_live_exit_1(monkeypatch):
    monkeypatch.delenv("JQUANTS_ENABLED", raising=False)
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
    assert "disabled" in r.stdout


def test_debug_daily_quotes_live_unsupported_version_exit_1(monkeypatch):
    monkeypatch.setenv("JQUANTS_API_VERSION", "v3")
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    _patch_base(monkeypatch)
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
    assert "unsupported_version" in r.stdout


def test_v1_refresh_token_dry_run_when_no_attempt_live(monkeypatch):
    monkeypatch.setenv("JQUANTS_API_VERSION", "v1")
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


def test_cli_jquants_daily_quotes_code_only_no_missing_option(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    _patch_base(monkeypatch)
    monkeypatch.delenv("JQUANTS_API_VERSION", raising=False)
    r = runner.invoke(app, ["debug", "jquants-daily-quotes", "--code", "7011"])
    assert r.exit_code == 0
    assert "Missing option" not in r.stdout
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "dry_run"


def test_cli_jquants_daily_quotes_date_only(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    _patch_base(monkeypatch)
    monkeypatch.delenv("JQUANTS_API_VERSION", raising=False)
    r = runner.invoke(app, ["debug", "jquants-daily-quotes", "--date", "2026-05-08"])
    assert r.exit_code == 0
    qp = json.loads(r.stdout.strip()).get("query_params")
    assert qp == {"date": "20260508"}


def test_cli_jquants_daily_quotes_code_and_date(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    _patch_base(monkeypatch)
    monkeypatch.delenv("JQUANTS_API_VERSION", raising=False)
    r = runner.invoke(app, ["debug", "jquants-daily-quotes", "--code", "7011", "--date", "2026-05-08"])
    assert r.exit_code == 0
    qp = json.loads(r.stdout.strip()).get("query_params")
    assert qp == {"code": "7011", "date": "20260508"}


def test_cli_jquants_daily_quotes_date_plus_from_exclusive(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    _patch_base(monkeypatch)
    monkeypatch.delenv("JQUANTS_API_VERSION", raising=False)
    r = runner.invoke(
        app,
        [
            "debug",
            "jquants-daily-quotes",
            "--date",
            "2026-05-08",
            "--from-date",
            "2026-05-07",
        ],
    )
    assert r.exit_code == 1
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "validation_error"
    assert blob["reason"] == "date_mutually_exclusive_with_from_to"


def test_cli_jquants_daily_quotes_no_args_validation(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    _patch_base(monkeypatch)
    monkeypatch.delenv("JQUANTS_API_VERSION", raising=False)
    r = runner.invoke(app, ["debug", "jquants-daily-quotes"])
    assert r.exit_code == 1
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "validation_error"
    assert blob["reason"] == "missing_all_of_code_date_from_to"


def test_preview_request_code_only_query_params(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.delenv("JQUANTS_API_VERSION", raising=False)
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://api.jquants.com/v2")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    r = runner.invoke(app, ["debug", "jquants-daily-quotes", "--preview-request", "--code", "7011"])
    assert r.exit_code == 0
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "ok"
    assert blob["query_params"] == {"code": "7011"}
    q = urlparse(blob["full_url_without_secrets"]).query.lower()
    assert "from_date" not in q and "date_from" not in q


def test_preview_request_date_only_no_secret_in_output(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://api.jquants.com/v2")
    monkeypatch.setenv("JQUANTS_API_KEY", "NEVER_LEAK_PREVIEW_KEY_XYZ")
    r = runner.invoke(
        app,
        ["debug", "jquants-daily-quotes", "--preview-request", "--date", "2026-05-08"],
    )
    assert r.exit_code == 0
    blob = json.loads(r.stdout.strip())
    assert blob["query_params"] == {"date": "20260508"}
    assert blob["api_key_value_included"] is False
    assert "NEVER_LEAK_PREVIEW_KEY_XYZ" not in json.dumps(blob)


def test_preview_request_date_and_from_exclusive_exit_1(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://api.jquants.com/v2")
    r = runner.invoke(
        app,
        [
            "debug",
            "jquants-daily-quotes",
            "--preview-request",
            "--date",
            "2026-05-08",
            "--from-date",
            "2026-05-07",
            "--code",
            "7011",
        ],
    )
    assert r.exit_code == 1
    assert json.loads(r.stdout.strip())["reason"] == "date_mutually_exclusive_with_from_to"


def test_v2_get_daily_quotes_rejects_date_with_from(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    _patch_base(monkeypatch)
    out = JQuantsClient.from_env().get_daily_quotes(
        "7011",
        date="2026-05-08",
        from_date="2026-05-07",
        attempt_live=False,
    )
    assert out["status"] == "validation_error"


def test_v2_live_query_from_only(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    _patch_base(monkeypatch)
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps({"data": []}).encode("utf-8")
    cm.__exit__.return_value = None
    captured: list[str] = []

    def _urlopen(req, timeout=None):  # noqa: ANN001
        captured.append(req.full_url)
        return cm

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_urlopen):
        out = JQuantsClient.from_env().get_daily_quotes(from_date="2026-05-08", attempt_live=True)
    assert out["status"] == "success"
    q = urlparse(captured[0]).query.lower()
    assert "from_date" not in q and "date_from" not in q and "to_date" not in q and "date_to" not in q
    assert parse_qs(urlparse(captured[0]).query) == {"from": ["20260508"]}


def test_v1_validate_requires_code_even_with_date(monkeypatch):
    monkeypatch.setenv("JQUANTS_API_VERSION", "v1")
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    c = JQuantsClient.from_env()
    err = c.validate_daily_quotes_cli_args(None, date="2026-05-08", from_date=None, to_date=None)
    assert err is not None and err["reason"] == "v1_requires_code"


def test_parse_v2_daily_bars_date_hyphen_and_compact():
    from invis_alpha_os.data.adapters.jquants_client import _parse_v2_daily_bars_date

    assert _parse_v2_daily_bars_date("2026-05-08") == "20260508"
    assert _parse_v2_daily_bars_date("20260508") == "20260508"
    assert _parse_v2_daily_bars_date("2026-5-8") is None
    assert _parse_v2_daily_bars_date("20230229") is None


def test_cli_jquants_daily_quotes_invalid_calendar_date(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    _patch_base(monkeypatch)
    r = runner.invoke(
        app,
        ["debug", "jquants-daily-quotes", "--code", "7011", "--date", "2026-13-40"],
    )
    assert r.exit_code == 1
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "validation_error"
    assert blob["reason"] == "invalid_date_format"


def test_preview_request_code_date_full_url_uses_yyyymmdd(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://api.jquants.com/v2")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    r = runner.invoke(
        app,
        ["debug", "jquants-daily-quotes", "--preview-request", "--code", "7011", "--date", "2026-05-08"],
    )
    assert r.exit_code == 0
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "ok"
    assert blob["query_params"] == {"code": "7011", "date": "20260508"}
    assert blob["full_url_without_secrets"] == (
        "https://api.jquants.com/v2/equities/bars/daily?code=7011&date=20260508"
    )


def test_preview_request_285a_code_date_daily_quotes(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://api.jquants.com/v2")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    r = runner.invoke(
        app,
        ["debug", "jquants-daily-quotes", "--preview-request", "--code", "285A", "--date", "2024-02-19"],
    )
    assert r.exit_code == 0
    blob = json.loads(r.stdout.strip())
    assert blob["query_params"] == {"code": "285A", "date": "20240219"}


def test_v2_http_error_json_message_bad_request(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    _patch_base(monkeypatch)

    def _urlopen(req, timeout=None):  # noqa: ANN001
        raise urllib.error.HTTPError(
            req.full_url, 400, "Bad Request", {}, BytesIO(b'{"message":"bad request"}')
        )

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_urlopen):
        out = JQuantsClient.from_env().get_daily_quotes("7011", date="2026-05-08", attempt_live=True)
    assert out.get("error_body_preview") == "message: bad request"


def test_v2_http_error_plain_text_truncated_to_300(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    _patch_base(monkeypatch)
    chunk = "abcdefghijklmnopqrstuvwxyz0123456789\n" * 20

    def _urlopen(req, timeout=None):  # noqa: ANN001
        raise urllib.error.HTTPError(
            req.full_url, 400, "Bad Request", {}, BytesIO(chunk.encode("utf-8"))
        )

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_urlopen):
        out = JQuantsClient.from_env().get_daily_quotes("7011", attempt_live=True)
    prev = out.get("error_body_preview")
    assert prev is not None
    assert len(prev) == 300
    assert "raw_response" not in out


def test_v2_http_error_masks_jquants_api_key_in_body(monkeypatch):
    secret = "MASK_ME_KEY_VALUE_98765"
    monkeypatch.setenv("JQUANTS_API_KEY", secret)
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    _patch_base(monkeypatch)
    payload = json.dumps({"message": f"denied for {secret}"})

    def _urlopen(req, timeout=None):  # noqa: ANN001
        raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {}, BytesIO(payload.encode()))

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_urlopen):
        out = JQuantsClient.from_env().get_daily_quotes("7011", attempt_live=True)
    assert secret not in json.dumps(out)
    eb = out.get("error_body_preview") or ""
    assert "***" in eb


def test_v2_http_error_json_without_allowlisted_keys_omits_preview(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    _patch_base(monkeypatch)
    payload = json.dumps({"unexpected": "SHOULD_NOT_LEAK_XYZ998", "other": 1})

    def _urlopen(req, timeout=None):  # noqa: ANN001
        raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {}, BytesIO(payload.encode()))

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_urlopen):
        out = JQuantsClient.from_env().get_daily_quotes("7011", attempt_live=True)
    assert out["status"] == "http_error"
    assert out.get("error_body_preview") is None
    assert "SHOULD_NOT_LEAK_XYZ998" not in json.dumps(out)


def test_summarize_http_error_plain_json_array_returns_none():
    from invis_alpha_os.data.adapters.jquants_client import summarize_http_error_body_preview

    raw = b'[{"a":1}]'
    assert summarize_http_error_body_preview(raw, []) is None


def test_v2_http_error_masks_access_token_in_nested_json(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "k")
    _patch_base(monkeypatch)
    payload = json.dumps(
        {
            "message": "failed",
            "error": {"access_token": "NESTED_TOKEN_LEAK_XYZ", "code": 1},
        }
    )

    def _urlopen(req, timeout=None):  # noqa: ANN001
        raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {}, BytesIO(payload.encode()))

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_urlopen):
        out = JQuantsClient.from_env().get_daily_quotes("7011", attempt_live=True)
    blob = json.dumps(out)
    assert "NESTED_TOKEN_LEAK_XYZ" not in blob


def _set_jquants_data_window(monkeypatch) -> None:
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_FROM", "2024-02-17")
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_TO", "2026-02-17")


def test_v2_date_in_data_window_ok(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    _set_jquants_data_window(monkeypatch)
    _patch_base(monkeypatch)
    err = JQuantsClient.from_env().validate_daily_quotes_cli_args(
        "7974", date="2024-02-19", from_date=None, to_date=None
    )
    assert err is None


def test_v2_date_before_data_window_validation_error(monkeypatch):
    _set_jquants_data_window(monkeypatch)
    err = JQuantsClient.from_env().validate_daily_quotes_cli_args(
        "7974", date="2024-01-04", from_date=None, to_date=None
    )
    assert err is not None
    assert err["status"] == "validation_error"
    assert err["reason"] == "date_out_of_available_range"
    assert err["data_available_from"] == "2024-02-17"
    assert err["data_available_to"] == "2026-02-17"


def test_v2_date_after_data_window_validation_error(monkeypatch):
    _set_jquants_data_window(monkeypatch)
    err = JQuantsClient.from_env().validate_daily_quotes_cli_args(
        "7011", date="2026-05-08", from_date=None, to_date=None
    )
    assert err is not None
    assert err["reason"] == "date_out_of_available_range"


def test_v2_from_to_outside_window_validation_error(monkeypatch):
    _set_jquants_data_window(monkeypatch)
    err = JQuantsClient.from_env().validate_daily_quotes_cli_args(
        "7011", date=None, from_date="20240201", to_date="20240215"
    )
    assert err is not None
    assert err["reason"] == "date_out_of_available_range"


def test_v2_data_window_accepts_compact_iso_equivalent(monkeypatch):
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_FROM", "20240217")
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_TO", "20260217")
    err = JQuantsClient.from_env().validate_daily_quotes_cli_args(
        "7011", date="2024-02-19", from_date=None, to_date=None
    )
    assert err is None


def test_cli_preview_request_data_window_no_leaks(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    _set_jquants_data_window(monkeypatch)
    monkeypatch.setenv("JQUANTS_API_KEY", "NEVER_LEAK_SECRET_KEY_999")
    _patch_base(monkeypatch)
    r = runner.invoke(
        app,
        ["debug", "jquants-daily-quotes", "--preview-request", "--code", "7011", "--date", "2024-01-04"],
    )
    assert r.exit_code == 1
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "validation_error"
    assert blob["reason"] == "date_out_of_available_range"
    assert blob["data_available_from"] == "2024-02-17"
    assert "NEVER_LEAK_SECRET_KEY_999" not in r.stdout
    low = r.stdout.lower()
    assert "password" not in low
    assert "token" not in low


def test_get_daily_quotes_blocked_before_http_when_outside_window(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    _set_jquants_data_window(monkeypatch)
    monkeypatch.setenv("JQUANTS_API_KEY", "NEVER_LEAK_THIS_LIVE_KEY")
    _patch_base(monkeypatch)
    out = JQuantsClient.from_env().get_daily_quotes("7011", date="2024-01-04", attempt_live=True)
    assert out["status"] == "validation_error"
    assert out["reason"] == "date_out_of_available_range"
    blob = json.dumps(out)
    assert "NEVER_LEAK_THIS_LIVE_KEY" not in blob


def test_jquants_watchlist_smoke_error_statuses_excludes_benign():
    from invis_alpha_os.data.adapters.jquants_client import JQUANTS_WATCHLIST_SMOKE_ERROR_STATUSES

    for s in (
        "http_error",
        "validation_error",
        "invalid_response",
        "non_json_response",
        "live_blocked",
        "not_configured",
        "api_key_missing",
        "base_url_missing",
        "unsupported_version",
        "failed",
        "error",
    ):
        assert s in JQUANTS_WATCHLIST_SMOKE_ERROR_STATUSES

    assert "dry_run" not in JQUANTS_WATCHLIST_SMOKE_ERROR_STATUSES
    assert "success" not in JQUANTS_WATCHLIST_SMOKE_ERROR_STATUSES
