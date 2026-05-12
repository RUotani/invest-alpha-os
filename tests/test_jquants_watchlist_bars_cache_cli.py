"""Main J: bulk watchlist J-Quants bars cache CLI (no real HTTP)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.jquants_daily_bars_cache import load_jquants_daily_bars_cache

runner = CliRunner()


def _patch_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://jq.test.invalid/v2")


def test_watchlist_bars_cache_dry_run_no_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    _patch_base(monkeypatch)
    monkeypatch.delenv("JQUANTS_API_KEY", raising=False)
    monkeypatch.delenv("CONFIRM_LIVE_HTTP", raising=False)

    def _boom(*_a, **_k):
        raise AssertionError("dry-run must not open HTTP")

    with patch("urllib.request.urlopen", side_effect=_boom):
        r = runner.invoke(
            app,
            [
                "debug",
                "jquants-watchlist-bars-cache",
                "--from-date",
                "2024-01-01",
                "--to-date",
                "2024-01-10",
            ],
        )
    assert r.exit_code == 0
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "dry_run"
    assert blob["cache_written_count"] == 0


def test_watchlist_bars_cache_live_without_confirm_exit_2(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bulk --live (read-only) must still require CONFIRM_LIVE_HTTP=YES."""
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    _patch_base(monkeypatch)
    monkeypatch.delenv("CONFIRM_LIVE_HTTP", raising=False)

    r = runner.invoke(
        app,
        [
            "debug",
            "jquants-watchlist-bars-cache",
            "--from-date",
            "2024-01-01",
            "--to-date",
            "2024-01-10",
            "--live",
        ],
    )
    assert r.exit_code == 2
    err = r.stderr.strip() or r.stdout.strip()
    blob = json.loads(err)
    assert blob.get("status") == "live_blocked"
    assert blob.get("reason") == "confirm_live_http_required"


def test_watchlist_bars_cache_write_cache_without_confirm_exit_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    _patch_base(monkeypatch)
    monkeypatch.delenv("CONFIRM_LIVE_HTTP", raising=False)

    r = runner.invoke(
        app,
        [
            "debug",
            "jquants-watchlist-bars-cache",
            "--from-date",
            "2024-01-01",
            "--to-date",
            "2024-01-10",
            "--live",
            "--write-cache",
        ],
    )
    assert r.exit_code == 2
    err = r.stderr.strip() or r.stdout.strip()
    blob = json.loads(err)
    assert blob.get("status") == "live_blocked"
    assert blob.get("reason") == "confirm_live_http_required"


def test_watchlist_bars_cache_live_read_only_with_confirm_no_cache_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "NEVER_LEAK_THIS_KEY")
    monkeypatch.setenv("CONFIRM_LIVE_HTTP", "YES")
    _patch_base(monkeypatch)
    body = {"bars": [{"Date": "20240104", "Code": "70110", "AdjO": 1, "AdjH": 1, "AdjL": 1, "AdjC": 1, "AdjVo": 1}]}
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(body).encode("utf-8")
    cm.__exit__.return_value = None
    monkeypatch.setattr("invis_alpha_os.cli.main.load_jp_watchlist_tickers", lambda: ["7011"])
    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", return_value=cm):
        r = runner.invoke(
            app,
            [
                "debug",
                "jquants-watchlist-bars-cache",
                "--from-date",
                "2024-01-01",
                "--to-date",
                "2024-01-31",
                "--live",
            ],
        )
    assert r.exit_code == 0
    assert "NEVER_LEAK_THIS_KEY" not in r.stdout
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "completed"
    assert blob["cache_written_count"] == 0
    assert blob["results"][0]["status"] == "success"
    low = r.stdout.lower()
    assert "x-api-key:" not in low


def test_watchlist_bars_cache_live_write_saves_sanitized_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    out = tmp_path / "outputs"
    out.mkdir(parents=True)
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "true")
    monkeypatch.setenv("JQUANTS_API_KEY", "SECRET_NEVER_PRINT_XYZ")
    monkeypatch.setenv("CONFIRM_LIVE_HTTP", "YES")
    _patch_base(monkeypatch)
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", out)

    body = {
        "bars": [
            {
                "Date": "20240104",
                "Code": "70110",
                "AdjO": 10.0,
                "AdjH": 11.0,
                "AdjL": 9.0,
                "AdjC": 10.5,
                "AdjVo": 1000.0,
            },
        ]
    }
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(body).encode("utf-8")
    cm.__exit__.return_value = None

    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["7011"],
    )

    with patch("invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", return_value=cm):
        r = runner.invoke(
            app,
            [
                "debug",
                "jquants-watchlist-bars-cache",
                "--from-date",
                "2024-01-01",
                "--to-date",
                "2024-01-31",
                "--live",
                "--write-cache",
            ],
        )

    assert r.exit_code == 0
    assert "SECRET_NEVER_PRINT_XYZ" not in r.stdout
    low = r.stdout.lower()
    assert "x-api-key:" not in low
    blob = json.loads(r.stdout.strip())
    assert blob.get("raw_response_included") is False
    assert blob["status"] == "completed"
    assert blob["cache_written_count"] == 1
    row = blob["results"][0]
    assert row["status"] == "success"
    assert row.get("cache_written_to")
    cache_path = out / "market_data" / "jquants_daily_bars" / "7011.json"
    assert cache_path.is_file()
    loaded = load_jquants_daily_bars_cache("7011")
    assert loaded is not None
    bars, _meta = loaded
    assert len(bars) == 1
    text = cache_path.read_text(encoding="utf-8").lower()
    assert "api_key" not in text
    assert "raw_response" not in text


def test_watchlist_bars_cache_skips_invalid_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    _patch_base(monkeypatch)
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["7011", "%%%bad"],
    )

    r = runner.invoke(
        app,
        [
            "debug",
            "jquants-watchlist-bars-cache",
            "--from-date",
            "2024-01-01",
            "--to-date",
            "2024-01-10",
        ],
    )
    assert r.exit_code == 0
    blob = json.loads(r.stdout.strip())
    assert blob["skipped_count"] == 1
    sk = [x for x in blob["results"] if x["status"] == "skipped_unsupported_code"]
    assert len(sk) == 1
    assert sk[0]["code"] == "%%%bad"


def test_watchlist_bars_cache_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    _patch_base(monkeypatch)
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["7011", "7203", "6501"],
    )

    r = runner.invoke(
        app,
        [
            "debug",
            "jquants-watchlist-bars-cache",
            "--from-date",
            "2024-01-01",
            "--to-date",
            "2024-01-10",
            "--limit",
            "2",
        ],
    )
    assert r.exit_code == 0
    blob = json.loads(r.stdout.strip())
    assert blob["target_count"] == 2
    assert len(blob["results"]) == 2
