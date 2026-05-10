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
