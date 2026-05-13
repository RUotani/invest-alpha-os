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


# ── R6.4.0 preflight tests ──────────────────────────────────────────────────


def test_preflight_missing_gates_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
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
            "--preflight",
            "--max-http",
            "1",
        ],
    )
    assert r.exit_code == 2, r.stdout + r.stderr
    payload = json.loads(r.stdout.strip())
    assert payload["status"] == "validation_error"
    assert payload["reason"] == "manual_batch_smoke_live_http_not_confirmed"
    assert payload["preflight_requested"] is True


def test_preflight_max_http_zero_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
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
            "--preflight",
            "--max-http",
            "0",
        ],
    )
    assert r.exit_code == 2, r.stdout + r.stderr
    payload = json.loads(r.stdout.strip())
    assert payload["status"] == "validation_error"
    assert payload["reason"] == "manual_batch_smoke_max_http_zero"
    assert payload["preflight_requested"] is True


def test_preflight_ready_exit_0(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uplp, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-manual-live-batch-smoke",
            "--symbols",
            "MSFT,NVDA",
            "--provider",
            "stooq_preview",
            "--live",
            "--preflight",
            "--max-http",
            "1",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    payload = json.loads(r.stdout.strip())
    assert payload["status"] == "manual_live_batch_smoke_preflight_ready"
    assert payload["mode"] == "preflight_ready_no_http"
    assert payload["preflight_requested"] is True
    assert payload["live_requested"] is True


def test_preflight_ready_safety_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    out = mlbs.build_us_provider_manual_live_batch_smoke_payload(
        ["MSFT"],
        max_http=1,
        live_requested=True,
        preflight_requested=True,
    )
    assert out["status"] == "manual_live_batch_smoke_preflight_ready"
    assert out["live_http_performed"] is False
    assert out["cache_write_performed"] is False
    assert out["raw_response_included"] is False
    assert out["provider_api_key_value_included"] is False
    assert out["scheduled_ingest_enabled"] is False
    assert out["manual_batch_smoke_enabled"] is False
    assert out["observation_only"] is True


def test_preflight_ready_plan_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    out = mlbs.build_us_provider_manual_live_batch_smoke_payload(
        ["MSFT", "AAPL"],
        max_http=2,
        live_requested=True,
        preflight_requested=True,
    )
    assert out["status"] == "manual_live_batch_smoke_preflight_ready"
    for row in out["plan_rows"]:
        assert row["planned_action"] == "preflight_ready_no_http"
        assert row["reason"] == "r6_4_0_preflight_ready_no_http"
        assert row["live_http_allowed"] is False
        assert row["cache_write_allowed"] is False
    assert out["operator_summary"]["preflight_ready_count"] == 2


def test_preflight_ready_planned_http_respects_max(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    out = mlbs.build_us_provider_manual_live_batch_smoke_payload(
        ["MSFT", "NVDA", "AAPL"],
        max_http=2,
        live_requested=True,
        preflight_requested=True,
    )
    assert out["status"] == "manual_live_batch_smoke_preflight_ready"
    assert out["constraints"]["planned_http_attempts"] == 2
    assert out["operator_summary"]["planned_http_attempt_count"] == 2


def test_preflight_ready_api_key_not_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "preflight_secret_key_never_echo_r640_99999"
    monkeypatch.setenv("STOOQ_APIKEY", secret)
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
            "--preflight",
            "--max-http",
            "1",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    assert secret not in r.stdout
    assert secret not in (r.stderr or "")


def test_preflight_markdown_r640_wording(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    out = mlbs.build_us_provider_manual_live_batch_smoke_payload(
        ["MSFT"],
        max_http=1,
        live_requested=True,
        preflight_requested=True,
    )
    md = mlbs.render_manual_live_batch_smoke_markdown(out)
    assert "R6.4.0" in md
    assert "preflight" in md.lower()
    assert "no vendor HTTP" in md
    assert "no cache write" in md


def test_preflight_without_live_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    """--preflight without --live must return validation_error/manual_batch_smoke_preflight_requires_live."""
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
            "--preflight",
            "--max-http",
            "1",
        ],
    )
    assert r.exit_code == 2, r.stdout + r.stderr
    payload = json.loads(r.stdout.strip())
    assert payload["status"] == "validation_error"
    assert payload["reason"] == "manual_batch_smoke_preflight_requires_live"
    assert payload["live_requested"] is False
    assert payload["preflight_requested"] is True
    assert payload["live_http_performed"] is False
    assert payload["cache_write_performed"] is False
    assert payload["raw_response_included"] is False


# ── R6.4.1 execute-live-http tests ──────────────────────────────────────────


def _mock_preview_ok(symbol: str, *, live: bool = False, write_cache: bool = False) -> dict:
    return {
        "status": "preview_ok",
        "provider": "stooq_preview",
        "symbol": symbol,
        "row_count": 5,
        "first_date": "2024-01-01",
        "last_date": "2024-01-05",
        "live_http_performed": True,
        "cache_write_performed": False,
        "raw_response_included": False,
    }


def test_execute_without_live_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    r = runner.invoke(
        app,
        ["debug", "us-provider-manual-live-batch-smoke",
         "--symbols", "MSFT", "--provider", "stooq_preview",
         "--execute-live-http", "--max-http", "1"],
    )
    assert r.exit_code == 2, r.stdout
    p = json.loads(r.stdout.strip())
    assert p["reason"] == "manual_batch_smoke_execute_requires_live"
    assert p["live_http_performed"] is False


def test_execute_live_without_preflight_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    r = runner.invoke(
        app,
        ["debug", "us-provider-manual-live-batch-smoke",
         "--symbols", "MSFT", "--provider", "stooq_preview",
         "--live", "--execute-live-http", "--max-http", "1"],
    )
    assert r.exit_code == 2, r.stdout
    p = json.loads(r.stdout.strip())
    assert p["reason"] == "manual_batch_smoke_execute_requires_preflight"
    assert p["live_http_performed"] is False


def test_execute_missing_gates_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    r = runner.invoke(
        app,
        ["debug", "us-provider-manual-live-batch-smoke",
         "--symbols", "MSFT", "--provider", "stooq_preview",
         "--live", "--preflight", "--execute-live-http", "--max-http", "1"],
    )
    assert r.exit_code == 2, r.stdout
    p = json.loads(r.stdout.strip())
    assert p["reason"] == "manual_batch_smoke_live_http_not_confirmed"
    assert p["live_http_performed"] is False


def test_execute_max_http_zero_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    r = runner.invoke(
        app,
        ["debug", "us-provider-manual-live-batch-smoke",
         "--symbols", "MSFT", "--provider", "stooq_preview",
         "--live", "--preflight", "--execute-live-http", "--max-http", "0"],
    )
    assert r.exit_code == 2, r.stdout
    p = json.loads(r.stdout.strip())
    assert p["reason"] == "manual_batch_smoke_max_http_zero"
    assert p["live_http_performed"] is False


def test_execute_live_preview_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    monkeypatch.setattr(uplp, "stooq_live_preview_sanitized_bars", _mock_preview_ok)
    monkeypatch.setattr(mlbs, "stooq_live_preview_sanitized_bars", _mock_preview_ok)
    r = runner.invoke(
        app,
        ["debug", "us-provider-manual-live-batch-smoke",
         "--symbols", "MSFT", "--provider", "stooq_preview",
         "--live", "--preflight", "--execute-live-http", "--max-http", "1"],
    )
    assert r.exit_code == 0, r.stdout
    p = json.loads(r.stdout.strip())
    assert p["status"] == "manual_live_batch_smoke_live_preview_completed"
    assert p["live_http_performed"] is True
    assert p["cache_write_performed"] is False
    assert p["raw_response_included"] is False
    assert p["provider_api_key_value_included"] is False
    assert p["constraints"]["actual_http_attempts"] == 1
    assert p["operator_summary"]["actual_http_attempt_count"] == 1
    assert p["operator_summary"]["live_preview_success_count"] == 1
    assert p["operator_summary"]["cache_write_allowed_count"] == 0


def test_execute_max_http_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    monkeypatch.setattr(mlbs, "stooq_live_preview_sanitized_bars", _mock_preview_ok)
    out = mlbs.build_us_provider_manual_live_batch_smoke_payload(
        ["MSFT", "NVDA"],
        max_http=1,
        live_requested=True,
        preflight_requested=True,
        execute_live_http_requested=True,
    )
    assert out["status"] == "manual_live_batch_smoke_live_preview_completed"
    rows_by_sym = {r["symbol"]: r for r in out["plan_rows"]}
    assert rows_by_sym["MSFT"]["planned_action"] == "live_preview_http_get"
    assert rows_by_sym["NVDA"]["planned_action"] == "skipped_max_http_cap"
    assert rows_by_sym["NVDA"]["reason"] == "max_http_cap_reached"
    assert out["operator_summary"]["skipped_max_http_cap_count"] == 1


def test_execute_invalid_symbol_no_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    call_count = 0

    def _count_calls(symbol: str, *, live: bool = False, write_cache: bool = False) -> dict:
        nonlocal call_count
        call_count += 1
        return _mock_preview_ok(symbol, live=live, write_cache=write_cache)

    monkeypatch.setattr(mlbs, "stooq_live_preview_sanitized_bars", _count_calls)
    out = mlbs.build_us_provider_manual_live_batch_smoke_payload(
        ["bogus/sym", "MSFT"],
        max_http=2,
        live_requested=True,
        preflight_requested=True,
        execute_live_http_requested=True,
    )
    assert call_count == 1  # only MSFT, not bogus/sym
    assert out["operator_summary"]["invalid_symbol_count"] == 1


def test_execute_cache_writer_not_called(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    monkeypatch.setattr(mlbs, "stooq_live_preview_sanitized_bars", _mock_preview_ok)

    def _fail_if_called(*_a: object, **_k: object) -> None:
        raise AssertionError("R6.4.1 must not call save_us_daily_bars_cache")

    monkeypatch.setattr(udbc, "save_us_daily_bars_cache", _fail_if_called)
    out = mlbs.build_us_provider_manual_live_batch_smoke_payload(
        ["MSFT"],
        max_http=1,
        live_requested=True,
        preflight_requested=True,
        execute_live_http_requested=True,
    )
    assert out["cache_write_performed"] is False


def test_execute_api_key_not_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "r641_secret_key_never_echo_99999"
    monkeypatch.setenv("STOOQ_APIKEY", secret)
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    monkeypatch.setattr(mlbs, "stooq_live_preview_sanitized_bars", _mock_preview_ok)
    r = runner.invoke(
        app,
        ["debug", "us-provider-manual-live-batch-smoke",
         "--symbols", "MSFT", "--provider", "stooq_preview",
         "--live", "--preflight", "--execute-live-http", "--max-http", "1"],
    )
    assert r.exit_code == 0, r.stdout
    assert secret not in r.stdout
    assert secret not in (r.stderr or "")


def test_execute_raw_response_not_in_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    monkeypatch.setattr(mlbs, "stooq_live_preview_sanitized_bars", _mock_preview_ok)
    r = runner.invoke(
        app,
        ["debug", "us-provider-manual-live-batch-smoke",
         "--symbols", "MSFT", "--provider", "stooq_preview",
         "--live", "--preflight", "--execute-live-http", "--max-http", "1"],
    )
    p = json.loads(r.stdout.strip())
    assert p["raw_response_included"] is False
    for row in p.get("plan_rows", []):
        assert "raw_body" not in row
        assert "raw_csv" not in row


def test_execute_markdown_r641_wording(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    monkeypatch.setattr(mlbs, "stooq_live_preview_sanitized_bars", _mock_preview_ok)
    out = mlbs.build_us_provider_manual_live_batch_smoke_payload(
        ["MSFT"],
        max_http=1,
        live_requested=True,
        preflight_requested=True,
        execute_live_http_requested=True,
    )
    md = mlbs.render_manual_live_batch_smoke_markdown(out)
    assert "R6.4.1" in md
    assert "live preview completed" in md.lower()
    assert "no cache write" in md
    assert "raw response not included" in md.lower()
    assert "JSON" in md
