"""Phase 1a Task 6: ``debug jquants-watchlist-bars``."""

import json
from unittest.mock import patch

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.config.jp_watchlist import (
    extract_jp_watchlist_tickers,
    jquants_daily_bars_ticker_kind,
    load_jp_watchlist_tickers,
)
from invis_alpha_os.config.loader import load_yaml
from invis_alpha_os.config.paths import CONFIG_DIR

runner = CliRunner()


def test_load_jp_watchlist_tickers_contains_expected():
    tickers = load_jp_watchlist_tickers()
    assert "7011" in tickers
    assert "285A" in tickers
    assert "7203" in tickers
    assert tickers.index("7011") < tickers.index("6501")


def test_extract_from_loaded_yaml():
    data = load_yaml(CONFIG_DIR / "watchlist.yaml")
    t = extract_jp_watchlist_tickers(data)
    assert len(t) >= 11


def test_jquants_ticker_kind_four_digit_ok():
    assert jquants_daily_bars_ticker_kind("7011") == "ok"
    assert jquants_daily_bars_ticker_kind(" 7203 ") == "ok"


def test_jquants_ticker_kind_alnum_four_ok():
    """Kioxia-style alphanumeric Tokyo listings (Phase 1a refocus)."""
    assert jquants_daily_bars_ticker_kind("285A") == "ok"
    assert jquants_daily_bars_ticker_kind("285a") == "ok"
    assert jquants_daily_bars_ticker_kind("304A") == "ok"


def test_jquants_ticker_kind_bad_structures_skipped():
    assert jquants_daily_bars_ticker_kind("") == "skipped_unsupported_code"
    assert jquants_daily_bars_ticker_kind("123") == "skipped_unsupported_code"
    assert jquants_daily_bars_ticker_kind("12345") == "skipped_unsupported_code"
    assert jquants_daily_bars_ticker_kind("70-11") == "skipped_unsupported_code"
    assert jquants_daily_bars_ticker_kind("285 A") == "skipped_unsupported_code"


def test_watchlist_preview_285a_wire_query(monkeypatch):
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://jq.test.invalid/v2")
    monkeypatch.setenv("JQUANTS_ENABLED", "false")
    r = runner.invoke(
        app,
        [
            "debug",
            "jquants-watchlist-bars",
            "--preview-request",
            "--date",
            "2024-02-19",
            "--limit",
            "9",
        ],
    )
    assert r.exit_code == 0
    blob = json.loads(r.stdout.strip())
    row = next(x for x in blob["results"] if x["code"] == "285A")
    assert row["status"] != "skipped_unsupported_code"
    assert row["query_params"]["code"] == "285A"
    assert row["query_params"]["date"] == "20240219"


def test_watchlist_full_preview_includes_285a_no_skip(monkeypatch):
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://jq.test.invalid/v2")
    monkeypatch.setenv("JQUANTS_ENABLED", "false")
    r = runner.invoke(app, ["debug", "jquants-watchlist-bars", "--preview-request", "--date", "2024-02-19"])
    blob = json.loads(r.stdout.strip())
    row = next(x for x in blob["results"] if x["code"] == "285A")
    assert row["query_params"] == {"code": "285A", "date": "20240219"}


def test_watchlist_limit(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://jq.test.invalid/v2")
    r = runner.invoke(
        app,
        [
            "debug",
            "jquants-watchlist-bars",
            "--date",
            "2024-02-16",
            "--limit",
            "3",
        ],
    )
    assert r.exit_code == 0
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "dry_run"
    assert blob["target_count"] == 3
    assert len(blob["results"]) == 3
    assert blob["results"][0]["code"] == "7011"


def test_watchlist_preview_no_urlopen(monkeypatch):
    calls: list[str] = []

    def _u(*a, **k):
        calls.append("urlopen")
        raise AssertionError("no live http")

    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://jq.test.invalid/v2")
    monkeypatch.setenv("JQUANTS_ENABLED", "false")
    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_u):
        r = runner.invoke(
            app,
            [
                "debug",
                "jquants-watchlist-bars",
                "--preview-request",
                "--date",
                "2024-02-16",
                "--limit",
                "2",
            ],
        )
    assert r.exit_code == 0
    assert calls == []
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "preview"
    assert blob["results"][0]["query_params"]["date"] == "20240216"


def test_watchlist_dry_run_no_urlopen(monkeypatch):
    calls: list[str] = []

    def _u(*a, **k):
        calls.append("x")
        raise AssertionError("no http")

    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://jq.test.invalid/v2")
    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_u):
        r = runner.invoke(
            app,
            ["debug", "jquants-watchlist-bars", "--date", "2024-02-16", "--limit", "2"],
        )
    assert r.exit_code == 0
    assert calls == []
    assert "dry_run" in r.stdout


def test_watchlist_live_without_allow_no_urlopen(monkeypatch):
    calls: list[str] = []

    def _u(*a, **k):
        calls.append("x")

    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "false")
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://jq.test.invalid/v2")
    monkeypatch.setenv("JQUANTS_API_KEY", "PLACEHOLDER_NOT_REAL")
    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_u):
        r = runner.invoke(
            app,
            ["debug", "jquants-watchlist-bars", "--live", "--date", "2024-02-16", "--limit", "1"],
        )
    assert calls == []
    assert "live_blocked" in r.stdout or "PLACEHOLDER_NOT_REAL" not in r.stdout
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "completed"
    assert blob["results"][0].get("status") == "live_blocked"
    assert "PLACEHOLDER_NOT_REAL" not in r.stdout


def test_watchlist_dry_run_285a_wire(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://jq.test.invalid/v2")
    r = runner.invoke(
        app,
        ["debug", "jquants-watchlist-bars", "--date", "2024-02-16", "--limit", "11"],
    )
    blob = json.loads(r.stdout.strip())
    codes = {x["code"]: x["status"] for x in blob["results"]}
    assert codes.get("285A") == "dry_run"


def test_watchlist_no_secrets_in_stdout(monkeypatch):
    secret = "ULTRA_SECRET_API_KEY_XYZ"
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://jq.test.invalid/v2")
    monkeypatch.setenv("JQUANTS_API_KEY", secret)
    r = runner.invoke(
        app,
        ["debug", "jquants-watchlist-bars", "--date", "2024-02-16", "--limit", "1"],
    )
    assert secret not in r.stdout
    low = r.stdout.lower()
    assert "password" not in low


def test_watchlist_date_range_guard(monkeypatch):
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_FROM", "2024-02-17")
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_TO", "2026-02-17")
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://jq.test.invalid/v2")
    r = runner.invoke(
        app,
        ["debug", "jquants-watchlist-bars", "--date", "2020-01-01", "--limit", "1"],
    )
    assert r.exit_code == 1
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "validation_error"
    assert blob["reason"] == "date_out_of_available_range"


def test_watchlist_missing_date_errors(monkeypatch):
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    r = runner.invoke(app, ["debug", "jquants-watchlist-bars", "--limit", "1"])
    assert r.exit_code == 1
    blob = json.loads(r.stdout.strip())
    assert blob["reason"] == "missing_all_of_code_date_from_to"


def test_watchlist_from_without_to_rejected(monkeypatch):
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://jq.test.invalid/v2")
    r = runner.invoke(
        app,
        ["debug", "jquants-watchlist-bars", "--from-date", "2024-02-16", "--limit", "1"],
    )
    assert r.exit_code == 1
    blob = json.loads(r.stdout.strip())
    assert blob["reason"] == "watchlist_range_requires_both_from_and_to"


def test_watchlist_to_without_from_rejected(monkeypatch):
    r = runner.invoke(
        app,
        ["debug", "jquants-watchlist-bars", "--to-date", "2024-02-16", "--preview-request", "--limit", "1"],
    )
    assert r.exit_code == 1
    assert "watchlist_range_requires_both_from_and_to" in r.stdout
