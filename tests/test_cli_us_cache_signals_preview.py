"""R6.11-D: US cache signals preview CLI (no HTTP)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.us_cache_signals import (
    US_CACHE_SIGNAL_ROW_OK_KEYS,
    build_us_cache_signals_preview,
    format_us_cache_signals_preview_json,
)

REPO = Path(__file__).resolve().parents[1]
FIX_MINIMAL = REPO / "tests" / "fixtures" / "us_equities" / "minimal_msft_envelope.json"
FIX_25 = REPO / "tests" / "fixtures" / "us_equities" / "msft_25bars_metrics_envelope.json"

runner = CliRunner()


@pytest.fixture(autouse=True)
def _block_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("US cache signals CLI tests must not use live HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)


def test_cli_signals_preview_json_ok() -> None:
    r = runner.invoke(
        app,
        ["debug", "us-cache-signals-preview", "--path", str(FIX_25), "--format", "json"],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    body = json.loads(r.stdout.strip())
    assert body["status"] == "ok"
    assert body["momentum_label"] == "uptrend_aligned"


def test_cli_signals_preview_markdown_ok() -> None:
    r = runner.invoke(
        app,
        ["debug", "us-cache-signals-preview", "--path", str(FIX_25), "--format", "markdown"],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    assert "**symbol**: MSFT" in r.stdout
    assert "**momentum_label**: uptrend_aligned" in r.stdout


def test_cli_signals_preview_skipped_exit_one() -> None:
    r = runner.invoke(
        app,
        ["debug", "us-cache-signals-preview", "--path", str(FIX_MINIMAL), "--format", "json"],
    )
    assert r.exit_code == 1
    body = json.loads(r.stdout.strip())
    assert body["status"] == "skipped_insufficient_bars"


def test_cli_signals_preview_invalid_path() -> None:
    r = runner.invoke(
        app,
        ["debug", "us-cache-signals-preview", "--path", "/no/file.json", "--format", "json"],
    )
    assert r.exit_code == 1
    body = json.loads(r.stdout.strip())
    assert body["reason"] == "path_not_found"


def test_cli_symbol_mismatch_exit_one() -> None:
    r = runner.invoke(
        app,
        [
            "debug",
            "us-cache-signals-preview",
            "--path",
            str(FIX_25),
            "--symbol",
            "AAPL",
            "--format",
            "json",
        ],
    )
    assert r.exit_code == 1
    body = json.loads(r.stdout.strip())
    assert body["status"] == "invalid"
    assert body["reason"] == "parse_failed"


def test_cli_bad_format_exit_two() -> None:
    r = runner.invoke(
        app,
        ["debug", "us-cache-signals-preview", "--path", str(FIX_25), "--format", "yaml"],
    )
    assert r.exit_code == 2


def test_metrics_cli_unchanged() -> None:
    r = runner.invoke(
        app,
        ["debug", "us-daily-bars-cache-metrics", "--path", str(FIX_25), "--format", "json"],
    )
    assert r.exit_code == 0
    body = json.loads(r.stdout.strip())
    assert "momentum_label" not in body


def test_preview_helper_json_roundtrip() -> None:
    p = build_us_cache_signals_preview(FIX_25)
    parsed = json.loads(format_us_cache_signals_preview_json(p))
    assert set(parsed.keys()) == US_CACHE_SIGNAL_ROW_OK_KEYS | {"path"}
    assert parsed["status"] == "ok"
