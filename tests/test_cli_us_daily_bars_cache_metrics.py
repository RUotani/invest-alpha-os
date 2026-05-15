"""R6.10-F: US daily bars cache metrics CLI (no HTTP)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.us_daily_bars_metrics import (
    METRICS_PREVIEW_OK_KEYS,
    build_us_daily_bars_cache_metrics_preview,
    format_us_daily_bars_cache_metrics_json,
)

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "tests" / "fixtures" / "us_equities" / "minimal_msft_envelope.json"
runner = CliRunner()


@pytest.fixture(autouse=True)
def _block_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("US cache metrics CLI tests must not use live HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)


def test_metrics_preview_ok_json_contract() -> None:
    m = build_us_daily_bars_cache_metrics_preview(FIX)
    assert m["status"] == "ok"
    assert set(m.keys()) == METRICS_PREVIEW_OK_KEYS
    assert m["symbol"] == "MSFT"
    assert m["has_5d"] is False
    assert m["live_http"] is False


def test_cli_metrics_json_ok() -> None:
    r = runner.invoke(
        app,
        ["debug", "us-daily-bars-cache-metrics", "--path", str(FIX), "--format", "json"],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    body = json.loads(r.stdout.strip())
    assert body["status"] == "ok"
    assert body["return_5d"] is None


def test_cli_metrics_markdown_ok() -> None:
    r = runner.invoke(
        app,
        ["debug", "us-daily-bars-cache-metrics", "--path", str(FIX), "--format", "markdown"],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    assert "**symbol**: MSFT" in r.stdout
    assert "return_5d" in r.stdout


def test_cli_metrics_invalid_path() -> None:
    r = runner.invoke(
        app,
        ["debug", "us-daily-bars-cache-metrics", "--path", "/no/file.json", "--format", "json"],
    )
    assert r.exit_code == 1
    body = json.loads(r.stdout.strip())
    assert body["status"] == "invalid"
    assert body["reason"] == "path_not_found"


def test_preview_cli_unchanged_without_metrics_command() -> None:
    r = runner.invoke(
        app,
        ["debug", "us-daily-bars-cache-preview", "--path", str(FIX), "--format", "json"],
    )
    assert r.exit_code == 0
    body = json.loads(r.stdout.strip())
    assert body["validation_status"] == "ok"
    assert "total_return" not in body


def test_metrics_json_formatter_roundtrip() -> None:
    m = build_us_daily_bars_cache_metrics_preview(FIX)
    parsed = json.loads(format_us_daily_bars_cache_metrics_json(m))
    assert parsed["status"] == "ok"
