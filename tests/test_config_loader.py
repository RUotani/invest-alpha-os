from invis_alpha_os.config.loader import load_yaml
from invis_alpha_os.config.paths import CONFIG_DIR


def _jquants_report_config() -> dict:
    data = load_yaml(CONFIG_DIR / "market_data.yaml")
    md = data.get("market_data")
    assert isinstance(md, dict)
    adapters = md.get("adapters")
    assert isinstance(adapters, dict)
    jq = adapters.get("jquants")
    assert isinstance(jq, dict)
    rep = jq.get("report")
    assert isinstance(rep, dict)
    return rep


def test_load_watchlist_has_required_keys():
    data = load_yaml(CONFIG_DIR / "watchlist.yaml")
    assert "jp_watchlist" in data
    assert "us_watchlist" in data
    us = data["us_watchlist"]
    assert "tier_1_core" in us
    assert "tier_2_theme_peers" in us
    assert "tier_3_optional" in us
    jp = data["jp_watchlist"]
    assert isinstance(jp, list)
    assert len(jp) >= 11
    assert isinstance(jp[0], dict)
    assert jp[0].get("ticker")


def test_jquants_report_has_readiness_keys():
    rep = _jquants_report_config()
    assert rep.get("readiness_enabled") is True
    assert rep.get("readiness_green_requires_data_guard") is True
    assert rep.get("readiness_green_requires_smoke_record") is True
    assert rep.get("include_unsupported_codes") is True


def test_jp_watchlist_helpers():
    from invis_alpha_os.config.jp_watchlist import extract_jp_watchlist_tickers, jquants_daily_bars_ticker_kind

    data = load_yaml(CONFIG_DIR / "watchlist.yaml")
    tickers = extract_jp_watchlist_tickers(data)
    assert len(tickers) >= 11
    assert jquants_daily_bars_ticker_kind("6501") == "ok"
    assert jquants_daily_bars_ticker_kind("285A") == "skipped_unsupported_code"
