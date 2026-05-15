"""R6.10-C: US daily bars cache-only preview CLI (no HTTP)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.us_daily_bars_cache import (
    build_us_daily_bars_cache_preview,
    format_us_daily_bars_cache_preview_json,
    format_us_daily_bars_cache_preview_markdown,
)

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "tests" / "fixtures" / "us_equities" / "minimal_msft_envelope.json"
runner = CliRunner()


@pytest.fixture(autouse=True)
def _block_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("US cache preview tests must not use live HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)


def test_build_preview_ok_from_minimal_fixture() -> None:
    p = build_us_daily_bars_cache_preview(FIX)
    assert p["validation_status"] == "ok"
    assert p["symbol"] == "MSFT"
    assert p["bar_count"] == 2
    assert p["first_date"] == "2024-01-02"
    assert p["last_date"] == "2024-01-03"
    assert p["live_http"] is False


def test_build_preview_path_not_found() -> None:
    p = build_us_daily_bars_cache_preview(Path("/nonexistent/us_cache.json"))
    assert p["validation_status"] == "invalid"
    assert p["reason"] == "path_not_found"


def test_build_preview_symbol_mismatch() -> None:
    p = build_us_daily_bars_cache_preview(FIX, expect_symbol="AAPL")
    assert p["validation_status"] == "invalid"
    assert p["reason"] == "parse_failed"


def test_markdown_formatter_ok() -> None:
    md = format_us_daily_bars_cache_preview_markdown(build_us_daily_bars_cache_preview(FIX))
    assert "MSFT" in md
    assert "validation_status" in md


def test_json_formatter_ok() -> None:
    raw = format_us_daily_bars_cache_preview_json(build_us_daily_bars_cache_preview(FIX))
    p = json.loads(raw)
    assert p["validation_status"] == "ok"


def test_cli_preview_markdown_exit_zero() -> None:
    r = runner.invoke(
        app,
        [
            "debug",
            "us-daily-bars-cache-preview",
            "--path",
            str(FIX),
            "--format",
            "markdown",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    assert "MSFT" in r.stdout
    assert "validation_status" in r.stdout


def test_cli_preview_json_exit_zero() -> None:
    r = runner.invoke(
        app,
        [
            "debug",
            "us-daily-bars-cache-preview",
            "--path",
            str(FIX),
            "--format",
            "json",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    p = json.loads(r.stdout.strip())
    assert p["validation_status"] == "ok"
    assert p["symbol"] == "MSFT"


def test_cli_preview_invalid_path_exit_one() -> None:
    r = runner.invoke(
        app,
        [
            "debug",
            "us-daily-bars-cache-preview",
            "--path",
            "/no/such/file.json",
            "--format",
            "json",
        ],
    )
    assert r.exit_code == 1, r.stdout + r.stderr
    p = json.loads(r.stdout.strip())
    assert p["validation_status"] == "invalid"


def test_cli_preview_symbol_mismatch_exit_one() -> None:
    r = runner.invoke(
        app,
        [
            "debug",
            "us-daily-bars-cache-preview",
            "--path",
            str(FIX),
            "--symbol",
            "AAPL",
            "--format",
            "json",
        ],
    )
    assert r.exit_code == 1, r.stdout + r.stderr
