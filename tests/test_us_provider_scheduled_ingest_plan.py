"""Main R6.1: US scheduled ingest dry-run plan (no vendor HTTP)."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data import us_provider_live_preview as uplp
from invis_alpha_os.data import us_provider_scheduled_ingest_plan as sip

runner = CliRunner()


@pytest.fixture(autouse=True)
def _clear_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, raising=False)
    monkeypatch.delenv(uplp.CONFIRM_US_CACHE_WRITE_ENV, raising=False)
    monkeypatch.delenv(sip.CONFIRM_US_SCHEDULED_INGEST_ENV, raising=False)
    monkeypatch.delenv(sip.ENV_MAX_SYMBOLS, raising=False)
    monkeypatch.delenv(sip.ENV_MAX_HTTP_PER_RUN, raising=False)
    monkeypatch.delenv(sip.ENV_MIN_SLEEP_SECONDS, raising=False)


def test_build_plan_two_symbols_no_vendor_io(monkeypatch: pytest.MonkeyPatch) -> None:

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("R6.1 plan must not HTTP")

    monkeypatch.setattr(uplp, "urlopen", _boom)
    out = sip.build_us_provider_scheduled_ingest_plan(
        ["MSFT", "GOOGL"],
        from_watchlist_used=False,
        symbols_csv_provided=True,
        limit_param=None,
    )
    assert out["status"] == "scheduled_plan_dry_run"
    assert out["mode"] == "dry_run_plan"
    assert out["live_http_performed"] is False
    assert out["cache_write_performed"] is False
    assert out["raw_response_included"] is False
    assert out["scheduled_ingest_enabled"] is False
    assert out["schedule_config_present"] is False
    assert out["provider_api_key_value_included"] is False
    assert out["provider_api_key_env_name"] == "STOOQ_APIKEY"
    assert out["symbol_count"] == 2
    assert out["symbols"] == ["MSFT", "GOOGL"]
    assert len(out["plan_rows"]) == 2
    for row in out["plan_rows"]:
        assert row["planned_action"] == "dry_run_only"
        assert row["reason"] == "r6_1_plan_only_no_http_no_write"
    assert out["operator_summary"]["dry_run_plan_count"] == 2
    assert out["gate_status"][sip.CONFIRM_US_SCHEDULED_INGEST_ENV] == "not_set"


def test_plan_limit_trims_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    out = sip.build_us_provider_scheduled_ingest_plan(
        ["MSFT", "AAPL", "MSFT"],
        limit_param=1,
        from_watchlist_used=False,
        symbols_csv_provided=True,
    )
    assert out["symbols"] == ["MSFT"]
    assert out["operator_summary"]["dry_run_plan_count"] == 1
    assert out["constraints"]["max_symbols"] == 1


def test_plan_invalid_row(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    out = sip.build_us_provider_scheduled_ingest_plan(
        ["bogus/name", "QQQ"],
        from_watchlist_used=False,
        symbols_csv_provided=True,
    )
    assert out["status"] == "scheduled_plan_dry_run"
    assert out["operator_summary"]["invalid_symbol_count"] == 1
    assert out["operator_summary"]["dry_run_plan_count"] == 1
    inv = [r for r in out["plan_rows"] if r["reason"] == "invalid_symbol"]
    assert len(inv) == 1


def test_plan_invalid_only_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    out = sip.build_us_provider_scheduled_ingest_plan(["###"], from_watchlist_used=False, symbols_csv_provided=True)
    assert out["status"] == "scheduled_plan_dry_run"
    assert out["symbols"] == []
    assert out["operator_summary"]["dry_run_plan_count"] == 0


def test_plan_env_max_symbols(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(sip.ENV_MAX_SYMBOLS, "1")
    out = sip.build_us_provider_scheduled_ingest_plan(["MSFT", "NVDA"])
    assert out["symbols"] == ["MSFT"]


def test_plan_unsupported_provider() -> None:
    out = sip.build_us_provider_scheduled_ingest_plan(["MSFT"], provider="alpha_vantage_preview")
    assert out["status"] == "validation_error"


def test_plan_empty() -> None:
    assert sip.build_us_provider_scheduled_ingest_plan([], from_watchlist_used=False)["status"] == "validation_error"


def test_gate_status_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(sip.CONFIRM_US_SCHEDULED_INGEST_ENV, "YES")
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    out = sip.build_us_provider_scheduled_ingest_plan(["XOM"])
    assert out["gate_status"][sip.CONFIRM_US_SCHEDULED_INGEST_ENV] == "YES"
    assert out["gate_status"][uplp.CONFIRM_US_LIVE_HTTP_ENV] == "YES"


def test_render_markdown_success() -> None:
    md = sip.render_us_provider_scheduled_ingest_plan_markdown(
        sip.build_us_provider_scheduled_ingest_plan(["MSFT"], from_watchlist_used=False),
    )
    assert "# US Scheduled Ingest Plan (dry-run)" in md
    assert "CONFIRM_US_SCHEDULED_INGEST" in md


def test_cli_plan_json_exit_0(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-scheduled-ingest-plan",
            "--symbols",
            "MSFT",
            "--provider",
            "stooq_preview",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    payload = json.loads(r.stdout.strip())
    assert payload["status"] == "scheduled_plan_dry_run"


def test_cli_plan_empty_exit_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    r = runner.invoke(app, ["debug", "us-provider-scheduled-ingest-plan", "--provider", "stooq_preview"])
    assert r.exit_code == 2, r.stdout + r.stderr
