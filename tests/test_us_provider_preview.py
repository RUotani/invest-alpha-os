"""Main R2: US provider preview (no HTTP, no secrets)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.config.paths import CONFIG_DIR
from invis_alpha_os.config.us_watchlist import normalize_us_symbol
from invis_alpha_os.data.us_provider_preview import (
    build_alpha_vantage_daily_preview,
    build_stooq_daily_preview,
    build_us_provider_preview_plan,
    load_us_market_data_config,
    us_cache_target_relpath,
)

REPO = Path(__file__).resolve().parents[1]
DOC = REPO / "docs" / "11_us_market_data_provider_plan.md"
US_MD = CONFIG_DIR / "us_market_data.yaml"
runner = CliRunner()


@pytest.fixture(autouse=True)
def _block_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("US provider preview tests must not perform HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)


def test_us_market_data_yaml_has_no_literal_secrets() -> None:
    assert US_MD.is_file()
    txt = US_MD.read_text(encoding="utf-8")
    assert "=" not in txt  # discourage env-style secret assignments in committed yaml
    for ln in txt.splitlines():
        s = ln.strip().lower()
        if not s or s.startswith("#"):
            continue
        assert not s.startswith("api_key:")
        assert not s.startswith("apikey:")
        assert "password:" not in s
        assert "bearer " not in s


def test_alpha_vantage_preview_normalizes_symbol() -> None:
    preview = build_alpha_vantage_daily_preview(" msft ")
    assert preview["status"] == "preview_ok"
    assert preview["symbol"] == "MSFT"
    assert normalize_us_symbol("msft") == "MSFT"
    qp = preview["query_params_without_secrets"]
    assert qp["symbol"] == "MSFT"
    assert qp["apikey"] == "<redacted_required_later>"
    real_keyish = re.compile(r"\b[A-Z0-9]{15,}\b")
    dumped = json.dumps(preview)
    assert not real_keyish.search(dumped)


def test_stooq_preview_flags_and_wire_param() -> None:
    preview = build_stooq_daily_preview("MSFT")
    assert preview["live_http"] is False
    assert preview["raw_response_included"] is False
    assert preview["status"] == "preview_ok"
    assert preview["query_params_without_secrets"]["s"] == "msft.us"
    assert preview["query_params_without_secrets"]["i"] == "d"
    assert preview["query_params_without_secrets"]["apikey"] == "<redacted_required_later>"
    pu = preview.get("preview_url_without_secrets") or ""
    pl = pu.lower()
    assert "apikey=" in pl and "redacted_required_later" in pl


def test_stooq_class_b_mapping_uses_hyphen() -> None:
    p = build_stooq_daily_preview("BRK.B")
    assert p["status"] == "preview_ok"
    assert p["query_params_without_secrets"]["s"] == "brk-b.us"


def test_invalid_symbol_returns_validation_error() -> None:
    bad = build_us_provider_preview_plan("../x", "alpha_vantage_preview")
    assert bad["status"] == "validation_error"
    assert bad["reason"] == "invalid_symbol"


def test_unknown_provider_rejected() -> None:
    unk = build_us_provider_preview_plan("MSFT", "no_such_vendor")
    assert unk["status"] == "validation_error"
    assert unk["reason"] == "unknown_provider"
    assert unk["provider_input"] == "no_such_vendor"


def test_cli_preview_ok_json() -> None:
    r = runner.invoke(app, ["debug", "us-provider-preview", "--symbol", "GOOGL", "--provider", "alpha_vantage_preview"])
    assert r.exit_code == 0, r.stdout + r.stderr
    payload = json.loads(r.stdout.strip())
    assert payload["status"] == "preview_ok"
    assert payload["provider"] == "alpha_vantage_preview"
    assert payload["live_http"] is False
    assert payload["raw_response_included"] is False


def test_cli_invalid_symbol_exit_2() -> None:
    r = runner.invoke(app, ["debug", "us-provider-preview", "--symbol", "bad/name", "--provider", "stooq_preview"])
    assert r.exit_code == 2


def test_makefile_contains_us_provider_preview() -> None:
    makefile = REPO / "Makefile"
    m = makefile.read_text(encoding="utf-8")
    assert "\nus-provider-preview:" in m or m.startswith("us-provider-preview:")
    assert ".PHONY" in m and "us-provider-preview" in m


def test_plan_doc_contains_required_providers_and_safety() -> None:
    t = DOC.read_text(encoding="utf-8")
    for needle in (
        "Alpha Vantage",
        "Stooq",
        "yfinance",
        "Tiingo",
        "no live vendor HTTP",
        "`raw_response`",
        "provider_api_key_required",
    ):
        assert needle in t, needle


def test_load_us_market_data_config_has_providers() -> None:
    cfg = load_us_market_data_config(REPO / "config" / "us_market_data.yaml")
    assert cfg.get("provider_default") == "alpha_vantage_preview"
    pv = cfg.get("providers")
    assert isinstance(pv, dict)
    assert "alpha_vantage_preview" in pv
    assert "stooq_preview" in pv
    assert pv["manual_file"].get("enabled") is True
    st = pv["stooq_preview"]
    assert isinstance(st, dict)
    assert st.get("requires_api_key") is True
    assert st.get("api_key_env") == "STOOQ_APIKEY"


def test_us_cache_target_relpath_stable() -> None:
    assert us_cache_target_relpath("QQQ") == "outputs/market_data/us_daily_bars/QQQ.json"
