"""Main R6.3–R6.5.1: US manual live batch smoke scaffold, preflight, live preview, cache-write refusal."""

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


# ── R6.5.1 evaluate-cache-write refusal tests ───────────────────────────────


def _eval_cw_args(extra: list[str] | None = None) -> list[str]:
    base = [
        "debug", "us-provider-manual-live-batch-smoke",
        "--symbols", "MSFT", "--provider", "stooq_preview",
        "--evaluate-cache-write", "--max-http", "1",
    ]
    return base + (extra or [])


def test_eval_cw_without_live_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    r = runner.invoke(app, _eval_cw_args())
    assert r.exit_code == 2, r.stdout
    p = json.loads(r.stdout.strip())
    assert p["reason"] == "manual_batch_cache_write_requires_live"
    assert p["live_http_performed"] is False
    assert p["cache_write_performed"] is False
    assert p["evaluate_cache_write_requested"] is True


def test_eval_cw_with_live_no_preflight_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    r = runner.invoke(app, _eval_cw_args(["--live"]))
    assert r.exit_code == 2, r.stdout
    p = json.loads(r.stdout.strip())
    assert p["reason"] == "manual_batch_cache_write_requires_preflight"
    assert p["live_http_performed"] is False


def test_eval_cw_no_execute_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    r = runner.invoke(app, _eval_cw_args(["--live", "--preflight"]))
    assert r.exit_code == 2, r.stdout
    p = json.loads(r.stdout.strip())
    assert p["reason"] == "manual_batch_cache_write_requires_execute_live_http"
    assert p["live_http_performed"] is False


def test_eval_cw_missing_live_manual_gates_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    # all 3 flags but no env gates
    r = runner.invoke(app, _eval_cw_args(["--live", "--preflight", "--execute-live-http"]))
    assert r.exit_code == 2, r.stdout
    p = json.loads(r.stdout.strip())
    assert p["reason"] == "manual_batch_smoke_live_http_not_confirmed"
    assert p["live_http_performed"] is False


def test_eval_cw_missing_cache_gate_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    r = runner.invoke(app, _eval_cw_args(["--live", "--preflight", "--execute-live-http"]))
    assert r.exit_code == 2, r.stdout
    p = json.loads(r.stdout.strip())
    assert p["reason"] == "manual_batch_cache_write_requires_cache_gate"
    assert p["live_http_performed"] is False
    assert p["cache_write_performed"] is False


def test_eval_cw_all_gates_still_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    monkeypatch.setenv(uplp.CONFIRM_US_CACHE_WRITE_ENV, "YES")
    r = runner.invoke(app, _eval_cw_args(["--live", "--preflight", "--execute-live-http"]))
    assert r.exit_code == 2, r.stdout
    p = json.loads(r.stdout.strip())
    assert p["reason"] == "manual_batch_cache_write_not_enabled_in_r6_5_1"
    assert p["live_http_performed"] is False
    assert p["cache_write_performed"] is False
    assert p["mode"] == "cache_write_evaluation_refusal_no_write"


def test_eval_cw_never_calls_live_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(*_a: object, **_k: object) -> dict:
        raise AssertionError("R6.5.1 evaluate-cache-write must not call stooq_live_preview_sanitized_bars")

    monkeypatch.setattr(mlbs, "stooq_live_preview_sanitized_bars", _fail)
    # test all 6 refusal levels — none should call preview
    for extra in [
        [],
        ["--live"],
        ["--live", "--preflight"],
        ["--live", "--preflight", "--execute-live-http"],
    ]:
        r = runner.invoke(app, _eval_cw_args(extra))
        assert r.exit_code == 2, f"expected exit 2 for {extra}: {r.stdout}"


def test_eval_cw_never_calls_cache_writer(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(*_a: object, **_k: object) -> None:
        raise AssertionError("R6.5.1 must not call save_us_daily_bars_cache")

    monkeypatch.setattr(udbc, "save_us_daily_bars_cache", _fail)
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    monkeypatch.setenv(uplp.CONFIRM_US_CACHE_WRITE_ENV, "YES")
    r = runner.invoke(app, _eval_cw_args(["--live", "--preflight", "--execute-live-http"]))
    assert r.exit_code == 2, r.stdout
    p = json.loads(r.stdout.strip())
    assert p["cache_write_performed"] is False


def test_eval_cw_api_key_not_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "r651_secret_key_never_echo_77777"
    monkeypatch.setenv("STOOQ_APIKEY", secret)
    r = runner.invoke(app, _eval_cw_args())
    assert secret not in r.stdout
    assert secret not in (r.stderr or "")


def test_eval_cw_safety_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(mlbs.CONFIRM_US_MANUAL_BATCH_SMOKE_ENV, "YES")
    monkeypatch.setenv(uplp.CONFIRM_US_CACHE_WRITE_ENV, "YES")
    out = mlbs.build_us_provider_manual_live_batch_smoke_payload(
        ["MSFT"],
        max_http=1,
        live_requested=True,
        preflight_requested=True,
        execute_live_http_requested=True,
        evaluate_cache_write_requested=True,
    )
    assert out["live_http_performed"] is False
    assert out["cache_write_performed"] is False
    assert out["raw_response_included"] is False
    assert out["provider_api_key_value_included"] is False
    assert out["scheduled_ingest_enabled"] is False
    assert out["evaluate_cache_write_requested"] is True


# ── R6.5.2 eligibility classifier tests ─────────────────────────────────────


def _ok_row(symbol: str = "MSFT", bar_count: int = 5) -> dict:
    return {
        "symbol": symbol,
        "status": "live_preview_ok",
        "planned_action": "live_preview_http_get",
        "live_http_performed": True,
        "cache_write_performed": False,
        "raw_response_included": False,
        "bars_source": "vendor_live_sanitized_preview",
        "sanitized_bar_count": bar_count,
    }


def test_eligible_row_classified_ok() -> None:
    r = mlbs.evaluate_manual_cache_write_eligibility_from_rows([_ok_row()])
    assert r["status"] == "manual_cache_write_eligibility_evaluated"
    assert r["eligible_count"] == 1
    assert r["rejected_count"] == 0
    row = r["rows"][0]
    assert row["cache_write_eligible"] is True
    assert row["reason"] == "manual_batch_cache_write_eligible_live_preview_ok"
    assert r["cache_write_performed"] is False
    assert r["live_http_performed"] is False
    assert r["raw_response_included"] is False
    assert r["provider_api_key_value_included"] is False


def test_invalid_symbol_row_rejected() -> None:
    row = {"symbol": "bad/sym", "reason": "invalid_symbol", "planned_action": "excluded_invalid_symbol"}
    r = mlbs.evaluate_manual_cache_write_eligibility_from_rows([row])
    assert r["rows"][0]["reason"] == "manual_batch_cache_write_rejects_invalid_symbol"
    assert r["eligible_count"] == 0
    assert r["summary"]["rejected_invalid_symbol_count"] == 1


def test_parse_error_row_rejected() -> None:
    row = {**_ok_row(), "status": "parse_error", "reason": "parse_error"}
    r = mlbs.evaluate_manual_cache_write_eligibility_from_rows([row])
    assert r["rows"][0]["reason"] == "manual_batch_cache_write_rejects_parse_error"
    assert r["summary"]["rejected_parse_error_count"] == 1


def test_transport_error_row_rejected() -> None:
    row = {**_ok_row(), "status": "transport_error"}
    r = mlbs.evaluate_manual_cache_write_eligibility_from_rows([row])
    assert r["rows"][0]["reason"] == "manual_batch_cache_write_rejects_transport_error"
    assert r["summary"]["rejected_transport_error_count"] == 1


def test_validation_error_row_rejected() -> None:
    row = {**_ok_row(), "status": "validation_error"}
    r = mlbs.evaluate_manual_cache_write_eligibility_from_rows([row])
    assert r["rows"][0]["reason"] == "manual_batch_cache_write_rejects_validation_error"
    assert r["summary"]["rejected_validation_error_count"] == 1


def test_max_http_cap_row_rejected() -> None:
    row = {"symbol": "MSFT", "planned_action": "skipped_max_http_cap", "reason": "max_http_cap_reached"}
    r = mlbs.evaluate_manual_cache_write_eligibility_from_rows([row])
    assert r["rows"][0]["reason"] == "manual_batch_cache_write_rejects_max_http_capped_row"
    assert r["summary"]["rejected_max_http_cap_count"] == 1


def test_raw_response_row_rejected() -> None:
    row = {**_ok_row(), "raw_response_included": True}
    r = mlbs.evaluate_manual_cache_write_eligibility_from_rows([row])
    assert r["rows"][0]["reason"] == "manual_batch_cache_write_rejects_raw_response"
    assert r["summary"]["rejected_raw_response_count"] == 1


def test_zero_bar_count_rejected() -> None:
    row = _ok_row(bar_count=0)
    r = mlbs.evaluate_manual_cache_write_eligibility_from_rows([row])
    assert r["rows"][0]["reason"] == "manual_batch_cache_write_rejects_unexpected_row_shape"
    assert r["summary"]["rejected_other_count"] == 1


def test_classifier_never_calls_cache_writer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(udbc, "save_us_daily_bars_cache", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not call cache writer")))
    r = mlbs.evaluate_manual_cache_write_eligibility_from_rows([_ok_row()])
    assert r["cache_write_performed"] is False


def test_classifier_never_calls_live_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mlbs, "stooq_live_preview_sanitized_bars", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not call live preview")))
    r = mlbs.evaluate_manual_cache_write_eligibility_from_rows([_ok_row()])
    assert r["live_http_performed"] is False


def test_classifier_no_secret_in_output(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "r652_secret_key_never_echo_55555"
    monkeypatch.setenv("STOOQ_APIKEY", secret)
    r = mlbs.evaluate_manual_cache_write_eligibility_from_rows([_ok_row()])
    assert secret not in str(r)


def test_eval_cw_markdown_r651_wording(monkeypatch: pytest.MonkeyPatch) -> None:
    out = mlbs.build_us_provider_manual_live_batch_smoke_payload(
        ["MSFT"],
        max_http=1,
        evaluate_cache_write_requested=True,
    )
    md = mlbs.render_manual_live_batch_smoke_markdown(out)
    assert "R6.5.1" in md
    assert "refusal scaffold" in md.lower()
    assert "no cache write" in md
    assert "no live HTTP consumed" in md
    assert "JSON" in md


# ── R6.5.3 execute_manual_cache_write_for_eligible_rows tests ────────────────


def _fake_writer_factory() -> tuple[list, Any]:
    calls: list[tuple] = []

    def _writer(symbol: str, payload: dict) -> None:
        calls.append((symbol, payload))

    return calls, _writer


def test_r653_cache_gate_missing_no_writer_call() -> None:
    calls, writer = _fake_writer_factory()
    r = mlbs.execute_manual_cache_write_for_eligible_rows([_ok_row()], writer=writer, cache_write_confirmed=False)
    assert r["status"] == "validation_error"
    assert r["reason"] == "manual_batch_cache_write_requires_cache_gate"
    assert r["cache_write_performed"] is False
    assert r["writer_call_count"] == 0
    assert calls == []


def test_r653_no_eligible_rows_no_writer_call() -> None:
    calls, writer = _fake_writer_factory()
    bad_row = {"symbol": "bad/sym", "reason": "invalid_symbol", "planned_action": "excluded_invalid_symbol"}
    r = mlbs.execute_manual_cache_write_for_eligible_rows([bad_row], writer=writer, cache_write_confirmed=True)
    assert r["status"] == "manual_cache_write_no_eligible_rows"
    assert r["cache_write_performed"] is False
    assert r["writer_call_count"] == 0
    assert calls == []


def test_r653_eligible_row_calls_writer_once() -> None:
    calls, writer = _fake_writer_factory()
    r = mlbs.execute_manual_cache_write_for_eligible_rows([_ok_row("MSFT")], writer=writer, cache_write_confirmed=True)
    assert r["status"] == "manual_cache_write_mock_execution_completed"
    assert r["cache_write_performed"] is True
    assert r["writer_call_count"] == 1
    assert r["written_count"] == 1
    assert len(calls) == 1
    assert calls[0][0] == "MSFT"
    assert r["live_http_performed"] is False
    assert r["raw_response_included"] is False
    assert r["provider_api_key_value_included"] is False


def test_r653_invalid_symbol_not_passed_to_writer() -> None:
    calls, writer = _fake_writer_factory()
    rows = [{"symbol": "bad/sym", "reason": "invalid_symbol", "planned_action": "excluded_invalid_symbol"}]
    r = mlbs.execute_manual_cache_write_for_eligible_rows(rows, writer=writer, cache_write_confirmed=True)
    assert calls == []
    assert r["written_count"] == 0


def test_r653_parse_error_not_passed_to_writer() -> None:
    calls, writer = _fake_writer_factory()
    r = mlbs.execute_manual_cache_write_for_eligible_rows([{**_ok_row(), "status": "parse_error"}], writer=writer, cache_write_confirmed=True)
    assert calls == []


def test_r653_transport_error_not_passed_to_writer() -> None:
    calls, writer = _fake_writer_factory()
    r = mlbs.execute_manual_cache_write_for_eligible_rows([{**_ok_row(), "status": "transport_error"}], writer=writer, cache_write_confirmed=True)
    assert calls == []


def test_r653_validation_error_not_passed_to_writer() -> None:
    calls, writer = _fake_writer_factory()
    r = mlbs.execute_manual_cache_write_for_eligible_rows([{**_ok_row(), "status": "validation_error"}], writer=writer, cache_write_confirmed=True)
    assert calls == []


def test_r653_max_http_cap_not_passed_to_writer() -> None:
    calls, writer = _fake_writer_factory()
    rows = [{"symbol": "MSFT", "planned_action": "skipped_max_http_cap", "reason": "max_http_cap_reached"}]
    r = mlbs.execute_manual_cache_write_for_eligible_rows(rows, writer=writer, cache_write_confirmed=True)
    assert calls == []


def test_r653_raw_response_row_not_passed_to_writer() -> None:
    calls, writer = _fake_writer_factory()
    r = mlbs.execute_manual_cache_write_for_eligible_rows([{**_ok_row(), "raw_response_included": True}], writer=writer, cache_write_confirmed=True)
    assert calls == []


def test_r653_mixed_rows_writer_only_eligible() -> None:
    calls, writer = _fake_writer_factory()
    rows = [
        _ok_row("MSFT"),
        {"symbol": "bad/sym", "reason": "invalid_symbol", "planned_action": "excluded_invalid_symbol"},
        {**_ok_row("AAPL"), "status": "parse_error"},
        _ok_row("NVDA"),
    ]
    r = mlbs.execute_manual_cache_write_for_eligible_rows(rows, writer=writer, cache_write_confirmed=True)
    assert r["written_count"] == 2
    written_syms = {c[0] for c in calls}
    assert written_syms == {"MSFT", "NVDA"}
    assert "bad/sym" not in written_syms
    assert "AAPL" not in written_syms


def test_r653_writer_payload_no_raw_response() -> None:
    calls, writer = _fake_writer_factory()
    mlbs.execute_manual_cache_write_for_eligible_rows([_ok_row()], writer=writer, cache_write_confirmed=True)
    assert len(calls) == 1
    _, payload = calls[0]
    assert "raw_response" not in payload
    assert "raw_body" not in payload
    assert "raw_csv" not in payload


def test_r653_no_secret_in_output(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "r653_secret_key_never_echo_33333"
    monkeypatch.setenv("STOOQ_APIKEY", secret)
    calls, writer = _fake_writer_factory()
    r = mlbs.execute_manual_cache_write_for_eligible_rows([_ok_row()], writer=writer, cache_write_confirmed=True)
    assert secret not in str(r)
    for c in calls:
        assert secret not in str(c)


def test_r653_no_live_preview_called(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mlbs, "stooq_live_preview_sanitized_bars", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not call")))
    calls, writer = _fake_writer_factory()
    r = mlbs.execute_manual_cache_write_for_eligible_rows([_ok_row()], writer=writer, cache_write_confirmed=True)
    assert r["live_http_performed"] is False


# ── R6.5.3.1 writer_invoked / real_cache_write_performed semantics tests ─────


def test_r6531_gate_missing_writer_invoked_false() -> None:
    _, writer = _fake_writer_factory()
    r = mlbs.execute_manual_cache_write_for_eligible_rows([_ok_row()], writer=writer, cache_write_confirmed=False)
    assert r["writer_invoked"] is False
    assert r["real_cache_write_performed"] is False
    assert r["writer_call_count"] == 0


def test_r6531_no_eligible_rows_writer_invoked_false() -> None:
    _, writer = _fake_writer_factory()
    bad = {"symbol": "bad/sym", "reason": "invalid_symbol", "planned_action": "excluded_invalid_symbol"}
    r = mlbs.execute_manual_cache_write_for_eligible_rows([bad], writer=writer, cache_write_confirmed=True)
    assert r["writer_invoked"] is False
    assert r["real_cache_write_performed"] is False
    assert r["writer_call_count"] == 0


def test_r6531_eligible_writer_invoked_true_real_false() -> None:
    calls, writer = _fake_writer_factory()
    r = mlbs.execute_manual_cache_write_for_eligible_rows([_ok_row("MSFT")], writer=writer, cache_write_confirmed=True)
    assert r["writer_invoked"] is True
    assert r["real_cache_write_performed"] is False
    assert r["writer_call_count"] == 1
    assert len(calls) == 1


def test_r6531_mixed_writer_invoked_real_false() -> None:
    calls, writer = _fake_writer_factory()
    rows = [
        _ok_row("MSFT"),
        {"symbol": "bad/sym", "reason": "invalid_symbol", "planned_action": "excluded_invalid_symbol"},
    ]
    r = mlbs.execute_manual_cache_write_for_eligible_rows(rows, writer=writer, cache_write_confirmed=True)
    assert r["writer_invoked"] is True
    assert r["real_cache_write_performed"] is False


def test_r6531_no_secret_in_output(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "r6531_secret_key_never_echo_22222"
    monkeypatch.setenv("STOOQ_APIKEY", secret)
    _, writer = _fake_writer_factory()
    r = mlbs.execute_manual_cache_write_for_eligible_rows([_ok_row()], writer=writer, cache_write_confirmed=True)
    assert secret not in str(r)


# ── R6.5.4 build_manual_cache_write_dry_run_plan tests ───────────────────────

_DEFAULT_ROOT = "outputs/market_data/us_daily_bars"


def test_r654_eligible_row_deterministic_path() -> None:
    r = mlbs.build_manual_cache_write_dry_run_plan([_ok_row("MSFT")])
    assert r["status"] == "manual_cache_write_dry_run_plan_built"
    assert r["planned_write_count"] == 1
    plan_rows = [x for x in r["rows"] if x.get("cache_write_eligible")]
    assert len(plan_rows) == 1
    assert plan_rows[0]["target_path"] == f"{_DEFAULT_ROOT}/MSFT.json"


def test_r654_dry_run_safety_flags() -> None:
    r = mlbs.build_manual_cache_write_dry_run_plan([_ok_row()])
    assert r["dry_run_only"] is True
    assert r["writer_invoked"] is False
    assert r["real_cache_write_performed"] is False
    assert r["cache_write_performed"] is False
    assert r["live_http_performed"] is False
    assert r["raw_response_included"] is False
    assert r["provider_api_key_value_included"] is False


def test_r654_invalid_symbol_no_target_path() -> None:
    row = {"symbol": "bad/sym", "reason": "invalid_symbol", "planned_action": "excluded_invalid_symbol"}
    r = mlbs.build_manual_cache_write_dry_run_plan([row])
    assert r["planned_write_count"] == 0
    for plan_row in r["rows"]:
        assert "target_path" not in plan_row or plan_row.get("cache_write_eligible") is True


def test_r654_unsafe_symbol_rejected() -> None:
    unsafe_row = {**_ok_row("../escape"), "symbol": "../escape"}
    r = mlbs.build_manual_cache_write_dry_run_plan([unsafe_row])
    assert r["planned_write_count"] == 0
    reasons = [x.get("reason") for x in r["rows"]]
    assert any("unsafe" in str(rs) for rs in reasons)


def test_r654_mixed_rows_planned_count() -> None:
    rows = [
        _ok_row("MSFT"),
        {"symbol": "bad/sym", "reason": "invalid_symbol", "planned_action": "excluded_invalid_symbol"},
        _ok_row("NVDA"),
    ]
    r = mlbs.build_manual_cache_write_dry_run_plan(rows)
    assert r["planned_write_count"] == 2
    targets = [x["target_path"] for x in r["rows"] if x.get("cache_write_eligible") and "target_path" in x]
    assert f"{_DEFAULT_ROOT}/MSFT.json" in targets
    assert f"{_DEFAULT_ROOT}/NVDA.json" in targets


def test_r654_target_path_under_output_root() -> None:
    r = mlbs.build_manual_cache_write_dry_run_plan([_ok_row("AAPL")])
    for row in r["rows"]:
        if tp := row.get("target_path"):
            assert tp.startswith(_DEFAULT_ROOT)
            assert ".." not in tp


def test_r654_no_raw_response_in_payload() -> None:
    r = mlbs.build_manual_cache_write_dry_run_plan([_ok_row()])
    payload_str = str(r)
    assert "raw_body" not in payload_str
    assert "raw_csv" not in payload_str
    assert "raw_response\"" not in payload_str


def test_r654_no_secret_in_output(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "r654_secret_key_never_echo_11111"
    monkeypatch.setenv("STOOQ_APIKEY", secret)
    r = mlbs.build_manual_cache_write_dry_run_plan([_ok_row()])
    assert secret not in str(r)


def test_r654_never_calls_cache_writer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(udbc, "save_us_daily_bars_cache", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not call")))
    r = mlbs.build_manual_cache_write_dry_run_plan([_ok_row()])
    assert r["cache_write_performed"] is False


def test_r654_never_calls_live_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mlbs, "stooq_live_preview_sanitized_bars", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not call")))
    r = mlbs.build_manual_cache_write_dry_run_plan([_ok_row()])
    assert r["live_http_performed"] is False


def test_r654_no_dir_or_file_created(tmp_path: "pytest.TempPathFactory") -> None:
    r = mlbs.build_manual_cache_write_dry_run_plan([_ok_row()], output_root=str(tmp_path / "test_out"))
    assert not (tmp_path / "test_out").exists()
    assert r["planned_write_count"] == 1


# ── R6.5.5 execute_manual_cache_write_dry_run_plan_with_injected_writer tests ─


def _make_dry_run_plan(rows=None) -> dict:
    if rows is None:
        rows = [_ok_row("MSFT")]
    return mlbs.build_manual_cache_write_dry_run_plan(rows)


def _collect_writer() -> tuple[list, Any]:
    calls: list[dict] = []
    return calls, lambda p: calls.append(p)


def test_r655_gate_false_refuses_no_writer() -> None:
    calls, w = _collect_writer()
    r = mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(_make_dry_run_plan(), writer=w, cache_write_confirmed=False)
    assert r["status"] == "validation_error"
    assert r["reason"] == "manual_batch_cache_write_requires_confirmed_gate"
    assert r["writer_invoked"] is False
    assert calls == []


def test_r655_none_writer_refuses() -> None:
    r = mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(_make_dry_run_plan(), writer=None, cache_write_confirmed=True)
    assert r["status"] == "validation_error"
    assert r["reason"] == "manual_batch_cache_write_requires_injected_writer"


def test_r655_valid_plan_invokes_writer_once() -> None:
    calls, w = _collect_writer()
    r = mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(_make_dry_run_plan(), writer=w, cache_write_confirmed=True)
    assert r["status"] == "manual_cache_write_injected_writer_completed"
    assert r["writer_invoked"] is True
    assert r["writer_invocation_count"] == 1
    assert len(calls) == 1


def test_r655_mixed_plan_writer_only_for_safe() -> None:
    calls, w = _collect_writer()
    rows = [_ok_row("MSFT"), {"symbol": "bad/sym", "reason": "invalid_symbol", "planned_action": "excluded_invalid_symbol"}, _ok_row("NVDA")]
    r = mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(_make_dry_run_plan(rows), writer=w, cache_write_confirmed=True)
    assert r["writer_invocation_count"] == 2
    syms = {c["symbol"] for c in calls}
    assert syms == {"MSFT", "NVDA"}


def test_r655_real_cache_write_performed_false() -> None:
    _, w = _collect_writer()
    r = mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(_make_dry_run_plan(), writer=w, cache_write_confirmed=True)
    assert r["real_cache_write_performed"] is False
    assert r["live_http_performed"] is False


def test_r655_writer_invoked_true_real_false_distinguished() -> None:
    _, w = _collect_writer()
    r = mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(_make_dry_run_plan(), writer=w, cache_write_confirmed=True)
    assert r["writer_invoked"] is True
    assert r["real_cache_write_performed"] is False


def test_r655_raw_response_in_plan_refuses() -> None:
    plan = {**_make_dry_run_plan(), "raw_response_included": True}
    _, w = _collect_writer()
    r = mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(plan, writer=w, cache_write_confirmed=True)
    assert r["status"] == "validation_error"
    assert r["reason"] == "manual_batch_cache_write_rejects_raw_response"


def test_r655_api_key_in_plan_refuses() -> None:
    plan = {**_make_dry_run_plan(), "provider_api_key_value_included": True}
    _, w = _collect_writer()
    r = mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(plan, writer=w, cache_write_confirmed=True)
    assert r["status"] == "validation_error"
    assert r["reason"] == "manual_batch_cache_write_rejects_provider_api_key_value"


def test_r655_non_dry_run_plan_refuses() -> None:
    bad_plan = {"dry_run_only": False, "observation_only": True, "real_cache_write_performed": False, "raw_response_included": False, "provider_api_key_value_included": False}
    _, w = _collect_writer()
    r = mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(bad_plan, writer=w, cache_write_confirmed=True)
    assert r["status"] == "validation_error"


def test_r655_writer_payload_no_raw_response() -> None:
    calls, w = _collect_writer()
    mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(_make_dry_run_plan(), writer=w, cache_write_confirmed=True)
    for p in calls:
        assert "raw_response" not in p
        assert "raw_body" not in p
        assert "raw_csv" not in p


def test_r655_no_secret_in_output(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "r655_secret_key_never_echo_44444"
    monkeypatch.setenv("STOOQ_APIKEY", secret)
    calls, w = _collect_writer()
    r = mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(_make_dry_run_plan(), writer=w, cache_write_confirmed=True)
    assert secret not in str(r)
    for c in calls:
        assert secret not in str(c)


def test_r655_no_cache_writer_called(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(udbc, "save_us_daily_bars_cache", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not call")))
    _, w = _collect_writer()
    r = mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(_make_dry_run_plan(), writer=w, cache_write_confirmed=True)
    assert r["real_cache_write_performed"] is False


def test_r655_no_live_preview_called(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mlbs, "stooq_live_preview_sanitized_bars", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not call")))
    _, w = _collect_writer()
    r = mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(_make_dry_run_plan(), writer=w, cache_write_confirmed=True)
    assert r["live_http_performed"] is False


def test_r655_no_file_created(tmp_path: "pytest.TempPathFactory") -> None:
    plan = mlbs.build_manual_cache_write_dry_run_plan([_ok_row()], output_root=str(tmp_path / "out"))
    _, w = _collect_writer()
    mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(plan, writer=w, cache_write_confirmed=True)
    assert not (tmp_path / "out").exists()


# ── R6.5.5.1 callable writer guard tests ─────────────────────────────────────


def test_r6551_non_callable_writer_refuses() -> None:
    r = mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(
        _make_dry_run_plan(), writer="not_a_callable", cache_write_confirmed=True
    )
    assert r["status"] == "validation_error"
    assert r["reason"] == "manual_batch_cache_write_requires_callable_injected_writer"
    assert r["writer_invoked"] is False
    assert r["cache_write_performed"] is False
    assert r["real_cache_write_performed"] is False
    assert r["writer_invocation_count"] == 0


def test_r6551_non_callable_does_not_raise_type_error() -> None:
    # must return validation_error, not raise
    for bad_writer in [42, "str", [], {}]:
        r = mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(
            _make_dry_run_plan(), writer=bad_writer, cache_write_confirmed=True
        )
        assert r["status"] == "validation_error", f"expected validation_error for writer={bad_writer!r}"


def test_r6551_callable_writer_still_works() -> None:
    calls, w = _collect_writer()
    r = mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(
        _make_dry_run_plan(), writer=w, cache_write_confirmed=True
    )
    assert r["status"] == "manual_cache_write_injected_writer_completed"
    assert r["writer_invoked"] is True
    assert len(calls) == 1


# ── R6.5.6 build_manual_cache_write_save_cache_writer_adapter tests ───────────


def _fake_save_cache_factory() -> tuple[list, Any]:
    calls: list = []
    return calls, lambda sym, bars: calls.append((sym, bars))


def _valid_writer_payload(symbol: str = "MSFT") -> dict:
    return {
        "symbol": symbol,
        "provider": "stooq_preview",
        "target_path": f"outputs/market_data/us_daily_bars/{symbol}.json",
        "sanitized_bar_count": 3,
        "sanitized_bars": [{"symbol": symbol, "date": "2024-01-01", "close": 100.0}],
        "planned_action": "manual_cache_write_injected_writer_payload",
        "dry_run_source": True,
        "cache_write_confirmed": True,
        "raw_response_included": False,
        "provider_api_key_value_included": False,
    }


def test_r656_gate_false_refuses() -> None:
    calls, sf = _fake_save_cache_factory()
    r = mlbs.build_manual_cache_write_save_cache_writer_adapter(sf, cache_write_confirmed=False)
    assert r["status"] == "validation_error"
    assert r["reason"] == "manual_batch_cache_write_requires_confirmed_gate"
    assert calls == []


def test_r656_none_save_func_refuses() -> None:
    r = mlbs.build_manual_cache_write_save_cache_writer_adapter(None, cache_write_confirmed=True)
    assert r["status"] == "validation_error"
    assert r["reason"] == "manual_batch_cache_write_requires_save_cache_func"


def test_r656_non_callable_save_func_refuses() -> None:
    r = mlbs.build_manual_cache_write_save_cache_writer_adapter("not_callable", cache_write_confirmed=True)
    assert r["status"] == "validation_error"
    assert r["reason"] == "manual_batch_cache_write_requires_callable_save_cache_func"


def test_r656_missing_sanitized_bars_refuses() -> None:
    calls, sf = _fake_save_cache_factory()
    adapter = mlbs.build_manual_cache_write_save_cache_writer_adapter(sf, cache_write_confirmed=True)
    w = adapter["writer"]
    payload = {**_valid_writer_payload()}
    del payload["sanitized_bars"]
    w(payload)
    log = adapter["invocation_log"]
    assert any(e["reason"] == "manual_batch_cache_write_requires_sanitized_bars" for e in log)
    assert calls == []


def test_r656_empty_sanitized_bars_refuses() -> None:
    calls, sf = _fake_save_cache_factory()
    adapter = mlbs.build_manual_cache_write_save_cache_writer_adapter(sf, cache_write_confirmed=True)
    adapter["writer"]({**_valid_writer_payload(), "sanitized_bars": []})
    assert any(e["reason"] == "manual_batch_cache_write_rejects_empty_sanitized_bars" for e in adapter["invocation_log"])
    assert calls == []


def test_r656_raw_response_refuses() -> None:
    calls, sf = _fake_save_cache_factory()
    adapter = mlbs.build_manual_cache_write_save_cache_writer_adapter(sf, cache_write_confirmed=True)
    adapter["writer"]({**_valid_writer_payload(), "raw_response_included": True})
    assert any(e["reason"] == "manual_batch_cache_write_rejects_raw_response" for e in adapter["invocation_log"])
    assert calls == []


def test_r656_api_key_refuses() -> None:
    calls, sf = _fake_save_cache_factory()
    adapter = mlbs.build_manual_cache_write_save_cache_writer_adapter(sf, cache_write_confirmed=True)
    adapter["writer"]({**_valid_writer_payload(), "provider_api_key_value_included": True})
    assert any(e["reason"] == "manual_batch_cache_write_rejects_provider_api_key_value" for e in adapter["invocation_log"])
    assert calls == []


def test_r656_missing_symbol_refuses() -> None:
    calls, sf = _fake_save_cache_factory()
    adapter = mlbs.build_manual_cache_write_save_cache_writer_adapter(sf, cache_write_confirmed=True)
    payload = {**_valid_writer_payload()}
    payload["symbol"] = ""
    adapter["writer"](payload)
    assert any(e["reason"] == "manual_batch_cache_write_rejects_unexpected_writer_payload" for e in adapter["invocation_log"])
    assert calls == []


def test_r656_symbol_mismatch_refuses() -> None:
    calls, sf = _fake_save_cache_factory()
    adapter = mlbs.build_manual_cache_write_save_cache_writer_adapter(sf, cache_write_confirmed=True)
    payload = {**_valid_writer_payload("MSFT"), "sanitized_bars": [{"symbol": "AAPL", "date": "2024-01-01"}]}
    adapter["writer"](payload)
    assert any(e["reason"] == "manual_batch_cache_write_rejects_symbol_mismatch" for e in adapter["invocation_log"])
    assert calls == []


def test_r656_valid_payload_calls_save_func_once() -> None:
    calls, sf = _fake_save_cache_factory()
    adapter = mlbs.build_manual_cache_write_save_cache_writer_adapter(sf, cache_write_confirmed=True)
    adapter["writer"](_valid_writer_payload("MSFT"))
    assert len(calls) == 1
    assert calls[0][0] == "MSFT"
    log = adapter["invocation_log"]
    assert log[0]["status"] == "written"


def test_r656_real_cache_write_performed_false() -> None:
    _, sf = _fake_save_cache_factory()
    adapter = mlbs.build_manual_cache_write_save_cache_writer_adapter(sf, cache_write_confirmed=True)
    assert adapter["real_cache_write_performed"] is False
    assert adapter["live_http_performed"] is False


def test_r656_no_secret_in_output(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "r656_secret_key_never_echo_99999"
    monkeypatch.setenv("STOOQ_APIKEY", secret)
    calls, sf = _fake_save_cache_factory()
    adapter = mlbs.build_manual_cache_write_save_cache_writer_adapter(sf, cache_write_confirmed=True)
    adapter["writer"](_valid_writer_payload())
    assert secret not in str(adapter)
    assert secret not in str(calls)


def test_r656_never_calls_real_save_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(udbc, "save_us_daily_bars_cache", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not call real")))
    calls, sf = _fake_save_cache_factory()
    adapter = mlbs.build_manual_cache_write_save_cache_writer_adapter(sf, cache_write_confirmed=True)
    adapter["writer"](_valid_writer_payload())
    assert calls[0][0] == "MSFT"


def test_r656_never_calls_live_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mlbs, "stooq_live_preview_sanitized_bars", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not call")))
    _, sf = _fake_save_cache_factory()
    adapter = mlbs.build_manual_cache_write_save_cache_writer_adapter(sf, cache_write_confirmed=True)
    assert adapter.get("live_http_performed") is False


def test_r656_no_file_created(tmp_path: "pytest.TempPathFactory") -> None:
    _, sf = _fake_save_cache_factory()
    adapter = mlbs.build_manual_cache_write_save_cache_writer_adapter(sf, cache_write_confirmed=True)
    adapter["writer"](_valid_writer_payload())
    assert not (tmp_path / "outputs").exists()


# ── R6.5.6 integration: adapter + executor + sanitized_bars ──────────────────


def _ok_row_with_bars(symbol: str = "MSFT") -> dict:
    return {
        **_ok_row(symbol),
        "sanitized_bars": [{"symbol": symbol, "date": "2024-01-01", "close": 100.0}],
    }


def test_r656_dry_run_plan_preserves_sanitized_bars() -> None:
    plan = mlbs.build_manual_cache_write_dry_run_plan([_ok_row_with_bars("MSFT")])
    target_rows = [r for r in plan["rows"] if r.get("cache_write_eligible")]
    assert len(target_rows) == 1
    assert "sanitized_bars" in target_rows[0]
    assert len(target_rows[0]["sanitized_bars"]) == 1


def test_r656_dry_run_plan_without_bars_no_key() -> None:
    plan = mlbs.build_manual_cache_write_dry_run_plan([_ok_row("MSFT")])
    target_rows = [r for r in plan["rows"] if r.get("cache_write_eligible")]
    assert "sanitized_bars" not in target_rows[0]


def test_r656_executor_passes_bars_to_writer() -> None:
    plan = mlbs.build_manual_cache_write_dry_run_plan([_ok_row_with_bars("MSFT")])
    received: list[dict] = []
    w = lambda p: received.append(p)  # noqa: E731
    mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(plan, writer=w, cache_write_confirmed=True)
    assert len(received) == 1
    assert "sanitized_bars" in received[0]


def test_r656_integration_adapter_executor_save_func_called_once() -> None:
    """Full pipeline: eligible row with bars -> dry-run plan -> adapter -> executor -> fake save_cache_func."""
    save_calls: list = []
    _, sf = _fake_save_cache_factory()
    # Override to capture
    sf_cap = lambda sym, bars: save_calls.append((sym, bars))

    plan = mlbs.build_manual_cache_write_dry_run_plan([_ok_row_with_bars("MSFT")])
    adapter = mlbs.build_manual_cache_write_save_cache_writer_adapter(sf_cap, cache_write_confirmed=True)
    result = mlbs.execute_manual_cache_write_dry_run_plan_with_injected_writer(
        plan, writer=adapter["writer"], cache_write_confirmed=True
    )
    assert len(save_calls) == 1
    assert save_calls[0][0] == "MSFT"
    assert result["real_cache_write_performed"] is False
    assert result["live_http_performed"] is False
    # no raw response in returned payload
    result_str = str(result)
    assert "raw_body" not in result_str
    assert "raw_csv" not in result_str


# ── R6.5.6 deep bar validation tests ─────────────────────────────────────────


def _adapter_with_calls() -> tuple[list, dict]:
    calls: list = []
    sf = lambda sym, bars: calls.append((sym, bars))
    adapter = mlbs.build_manual_cache_write_save_cache_writer_adapter(sf, cache_write_confirmed=True)
    return calls, adapter


def test_r656_second_bar_symbol_mismatch_refuses() -> None:
    calls, adapter = _adapter_with_calls()
    payload = {
        **_valid_writer_payload("MSFT"),
        "sanitized_bars": [
            {"symbol": "MSFT", "date": "2024-01-01"},
            {"symbol": "AAPL", "date": "2024-01-02"},  # mismatch
        ],
    }
    adapter["writer"](payload)
    assert calls == []
    assert any(e["reason"] == "manual_batch_cache_write_rejects_symbol_mismatch" for e in adapter["invocation_log"])


def test_r656_bar_with_api_key_refuses() -> None:
    calls, adapter = _adapter_with_calls()
    payload = {
        **_valid_writer_payload("MSFT"),
        "sanitized_bars": [{"symbol": "MSFT", "date": "2024-01-01", "api_key": "secret_val"}],
    }
    adapter["writer"](payload)
    assert calls == []
    assert any(e["reason"] == "manual_batch_cache_write_rejects_forbidden_sanitized_bar_field" for e in adapter["invocation_log"])


def test_r656_bar_with_raw_response_key_refuses() -> None:
    calls, adapter = _adapter_with_calls()
    payload = {
        **_valid_writer_payload("MSFT"),
        "sanitized_bars": [{"symbol": "MSFT", "date": "2024-01-01", "raw_response": "..."}],
    }
    adapter["writer"](payload)
    assert calls == []
    assert any(e["reason"] == "manual_batch_cache_write_rejects_forbidden_sanitized_bar_field" for e in adapter["invocation_log"])


def test_r656_non_dict_bar_refuses() -> None:
    calls, adapter = _adapter_with_calls()
    payload = {**_valid_writer_payload("MSFT"), "sanitized_bars": ["not_a_dict"]}
    adapter["writer"](payload)
    assert calls == []
    assert any(e["reason"] == "manual_batch_cache_write_rejects_non_dict_sanitized_bar" for e in adapter["invocation_log"])


def test_r656_valid_bars_calls_save_func_once_deep() -> None:
    calls, adapter = _adapter_with_calls()
    payload = {
        **_valid_writer_payload("MSFT"),
        "sanitized_bars": [
            {"symbol": "MSFT", "date": "2024-01-01", "close": 100.0},
            {"symbol": "MSFT", "date": "2024-01-02", "close": 101.0},
        ],
    }
    adapter["writer"](payload)
    assert len(calls) == 1


def test_r656_log_no_secret_values(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "r656deep_secret_never_echo_88888"
    monkeypatch.setenv("STOOQ_APIKEY", secret)
    calls, adapter = _adapter_with_calls()
    payload = {**_valid_writer_payload("MSFT"), "sanitized_bars": [{"symbol": "MSFT", "api_key": secret}]}
    adapter["writer"](payload)
    assert calls == []
    assert secret not in str(adapter["invocation_log"])
