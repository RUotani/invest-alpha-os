"""Main R6.3: US manual live batch smoke scaffold (no vendor HTTP / no cache write)."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data import us_provider_live_preview as uplp
from invis_alpha_os.data import us_provider_manual_live_batch_smoke as mlbs
from invis_alpha_os.data import us_daily_bars_cache as udbc
from invis_alpha_os.data import us_provider_scheduled_ingest_plan as sip

runner = CliRunner()


@pytest.fixture(autouse=True)
def _clear_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, raising=False)
    monkeypatch.delenv(uplp.CONFIRM_US_CACHE_WRITE_ENV, raising=False)
    monkeypatch.delenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, raising=False)
    monkeypatch.delenv(sip.ENV_MAX_SYMBOLS, raising=False)
    monkeypatch.delenv(sip.ENV_MIN_SLEEP_SECONDS, raising=False)
    monkeypatch.delenv("STOOQ_APIKEY", raising=False)


def test_scaffold_two_symbols_no_vendor_io(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("R6.3 must not HTTP")))

    calls: list[object] = []

    def _no_cache_write(*_a: object, **_k: object) -> None:
        calls.append(True)

    monkeypatch.setattr(udbc, "save_us_daily_bars_cache", _no_cache_write)

    out = mlbs.build_us_provider_manual_live_batch_smoke_payload(
        ["MSFT", "GOOGL"],
        from_watchlist_used=False,
        symbols_csv_provided=True,
        limit_param=None,
        max_http=2,
        live_requested=False,
    )
    assert out["status"] == "manual_live_batch_smoke_dry_run"
    assert out["mode"] == "scaffold_dry_run"
    assert out["live_requested"] is False
    assert out["live_http_performed"] is False
    assert out["cache_write_performed"] is False
    assert out["raw_response_included"] is False
    assert out["scheduled_ingest_enabled"] is False
    assert out["manual_batch_smoke_enabled"] is False
    assert out["provider_api_key_value_included"] is False
    assert out["provider"] == "stooq_preview"
    assert out["symbols"] == ["MSFT", "GOOGL"]
    assert out["operator_summary"]["planned_http_attempt_count"] == 2
    assert out["constraints"]["planned_http_attempts"] == 2
    assert calls == []


def test_cli_dry_run_json_exit_0(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-manual-live-batch-smoke",
            "--symbols",
            "MSFT,NVDA",
            "--provider",
            "stooq_preview",
            "--max-http",
            "1",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    payload = json.loads(r.stdout.strip())
    assert payload["status"] == "manual_live_batch_smoke_dry_run"
    assert payload["operator_summary"]["planned_http_attempt_count"] == 1


def test_live_without_gates_exit_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-manual-live-batch-smoke",
            "--symbols",
            "MSFT",
            "--provider",
            "stooq_preview",
            "--live",
            "--max-http",
            "1",
        ],
    )
    assert r.exit_code == 2, r.stdout + r.stderr
    payload = json.loads(r.stdout.strip())
    assert payload["reason"] == "manual_batch_smoke_live_http_not_confirmed"
    assert payload["live_requested"] is True
    assert payload["scheduled_ingest_enabled"] is False


def test_live_with_gates_still_exit_2_not_implemented(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-manual-live-batch-smoke",
            "--symbols",
            "MSFT",
            "--provider",
            "stooq_preview",
            "--live",
            "--max-http",
            "1",
        ],
    )
    assert r.exit_code == 2, r.stdout + r.stderr
    payload = json.loads(r.stdout.strip())
    assert payload["reason"] == "manual_batch_smoke_live_execution_not_implemented_in_r6_3"


def test_live_max_http_zero_exit_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-manual-live-batch-smoke",
            "--symbols",
            "MSFT",
            "--provider",
            "stooq_preview",
            "--live",
            "--max-http",
            "0",
        ],
    )
    assert r.exit_code == 2, r.stdout + r.stderr
    payload = json.loads(r.stdout.strip())
    assert payload["reason"] == "manual_batch_smoke_max_http_zero"


def test_unsupported_provider_exit_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-manual-live-batch-smoke",
            "--symbols",
            "MSFT",
            "--provider",
            "alpha_vantage_preview",
        ],
    )
    assert r.exit_code == 2, r.stdout + r.stderr
    assert json.loads(r.stdout.strip())["reason"] == "unsupported_provider"


def test_empty_symbol_batch_exit_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    r = runner.invoke(
        app,
        ["debug", "us-provider-manual-live-batch-smoke", "--provider", "stooq_preview"],
    )
    assert r.exit_code == 2, r.stdout + r.stderr
    assert json.loads(r.stdout.strip())["reason"] == "empty_symbol_batch"


def test_invalid_symbol_row_and_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    out = mlbs.build_us_provider_manual_live_batch_smoke_payload(
        ["bogus/name", "QQQ"],
        max_http=2,
    )
    assert out["status"] == "manual_live_batch_smoke_dry_run"
    assert out["operator_summary"]["invalid_symbol_count"] == 1
    inv = [r for r in out["plan_rows"] if r.get("reason") == "invalid_symbol"]
    assert len(inv) == 1
    assert inv[0]["planned_action"] == "excluded_invalid_symbol"


def test_limit_trims(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    out = mlbs.build_us_provider_manual_live_batch_smoke_payload(
        ["MSFT", "AAPL", "MSFT"],
        limit_param=1,
        max_http=5,
    )
    assert out["symbols"] == ["MSFT"]
    assert out["operator_summary"]["dry_run_plan_count"] == 1


def test_max_http_caps_planned_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    out = mlbs.build_us_provider_manual_live_batch_smoke_payload(
        ["MSFT", "NVDA"],
        max_http=1,
    )
    assert out["constraints"]["planned_http_attempts"] == 1
    assert out["operator_summary"]["planned_http_attempt_count"] == 1


def test_markdown_contains_scaffold_notes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    out = mlbs.build_us_provider_manual_live_batch_smoke_payload(["MSFT"], max_http=1)
    md = mlbs.render_manual_live_batch_smoke_markdown(out)
    assert "R6.3 scaffold only" in md
    assert "no vendor HTTP" in md
    assert "no cache write" in md
    assert "CONFIRM_US_MANUAL_BATCH_SMOKE" in md


def test_api_key_value_never_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "test_secret_key_value_never_echo_12345"
    monkeypatch.setenv("STOOQ_APIKEY", secret)
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-manual-live-batch-smoke",
            "--symbols",
            "MSFT",
            "--provider",
            "stooq_preview",
            "--max-http",
            "0",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    assert secret not in r.stdout
    assert secret not in (r.stderr or "")


def test_cli_help_includes_command() -> None:
    r = runner.invoke(app, ["debug", "us-provider-manual-live-batch-smoke", "--help"])
    assert r.exit_code == 0, r.stdout + r.stderr
    assert "us-provider-manual-live-batch-smoke" in r.stdout or "manual" in r.stdout.lower()
