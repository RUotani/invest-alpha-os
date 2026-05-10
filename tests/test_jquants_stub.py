from invis_alpha_os.data.adapters.jquants_stub import JQuantsStubAdapter


def test_jquants_disabled_by_default(monkeypatch):
    monkeypatch.delenv("JQUANTS_ENABLED", raising=False)
    a = JQuantsStubAdapter()
    assert a.is_enabled() is False
    h = a.health()
    assert h.get("enabled") is False
    assert "client" in h
    assert a.get_daily_quotes_stub()["status"] == "disabled"
    assert a.get_listed_info_stub()["status"] == "disabled"


def test_jquants_stub_enabled_flag_still_no_http(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    a = JQuantsStubAdapter()
    assert a.is_enabled() is True
    assert a.get_daily_quotes_stub()["status"] == "stub"
    assert a.get_listed_info_stub()["status"] == "stub"
    q = a.get_quote("7011")
    assert q.symbol == "7011"
    assert q.currency == "JPY"


def test_jquants_disabled_explicit_false(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "false")
    assert JQuantsStubAdapter().is_enabled() is False


def test_jquants_health_client_has_safe_status_fields(monkeypatch):
    monkeypatch.delenv("JQUANTS_ENABLED", raising=False)
    h = JQuantsStubAdapter().health()
    c = h["client"]
    assert "api_version" in c
    assert "api_version_effective" in c
    assert "unsupported_api_version" in c
    assert "base_url_present" in c
    assert "allow_live_http" in c
    assert c.get("auth_method") == "api_key"
    assert "api_key_present" in c
    assert "configured" in c
