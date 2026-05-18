"""R6.16-A: read-only US daily bars cache inventory (no HTTP)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.us_daily_bars_cache_inventory import (
    build_us_daily_bars_cache_inventory,
    build_us_daily_bars_cache_inventory_row,
    format_us_daily_bars_cache_inventory_json,
)

REPO = Path(__file__).resolve().parents[1]
FIX_MINIMAL = REPO / "tests" / "fixtures" / "us_equities" / "minimal_msft_envelope.json"
FIX_25 = REPO / "tests" / "fixtures" / "us_equities" / "msft_25bars_metrics_envelope.json"
runner = CliRunner()


@pytest.fixture(autouse=True)
def _block_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("US cache inventory tests must not use live HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)


def test_inventory_row_missing(tmp_path: Path) -> None:
    row = build_us_daily_bars_cache_inventory_row("MSFT", tmp_path)
    assert row["status"] == "missing"
    assert row["file_exists"] is False
    assert row["live_http"] is False


def test_inventory_row_insufficient(tmp_path: Path) -> None:
    dest = tmp_path / "MSFT.json"
    dest.write_text(FIX_MINIMAL.read_text(encoding="utf-8"), encoding="utf-8")
    row = build_us_daily_bars_cache_inventory_row("MSFT", tmp_path)
    assert row["status"] == "insufficient"
    assert row["bar_count"] == 2


def test_inventory_row_stale_unknown(tmp_path: Path) -> None:
    dest = tmp_path / "MSFT.json"
    dest.write_text(FIX_25.read_text(encoding="utf-8"), encoding="utf-8")
    row = build_us_daily_bars_cache_inventory_row("MSFT", tmp_path)
    assert row["status"] == "stale_unknown"
    assert row["bar_count"] == 25


def test_inventory_row_ok_with_freshness(tmp_path: Path) -> None:
    payload = json.loads(FIX_25.read_text(encoding="utf-8"))
    payload["fetched_at"] = "2026-05-01T00:00:00Z"
    dest = tmp_path / "MSFT.json"
    dest.write_text(json.dumps(payload), encoding="utf-8")
    row = build_us_daily_bars_cache_inventory_row("MSFT", tmp_path)
    assert row["status"] == "ok"


def test_inventory_row_invalid(tmp_path: Path) -> None:
    bad = tmp_path / "MSFT.json"
    bad.write_text("{not json", encoding="utf-8")
    row = build_us_daily_bars_cache_inventory_row("MSFT", tmp_path)
    assert row["status"] == "invalid"


def test_build_inventory_json_symbols(tmp_path: Path) -> None:
    inv = build_us_daily_bars_cache_inventory(tmp_path, symbols=["MSFT", "AAPL"])
    assert inv["symbol_count"] == 2
    assert inv["live_http"] is False
    raw = format_us_daily_bars_cache_inventory_json(inv)
    parsed = json.loads(raw)
    assert parsed["status_counts"]["missing"] == 2


def test_cli_inventory_json_exit_one_when_missing(tmp_path: Path) -> None:
    r = runner.invoke(
        app,
        [
            "debug",
            "us-daily-bars-cache-inventory",
            "--cache-root",
            str(tmp_path),
            "--symbol",
            "MSFT",
            "--format",
            "json",
        ],
    )
    assert r.exit_code == 1
    assert '"status": "missing"' in r.stdout


def test_cli_inventory_markdown_ok(tmp_path: Path) -> None:
    dest = tmp_path / "MSFT.json"
    payload = json.loads(FIX_25.read_text(encoding="utf-8"))
    payload["generated_at"] = "2026-05-01T00:00:00Z"
    dest.write_text(json.dumps(payload), encoding="utf-8")
    r = runner.invoke(
        app,
        [
            "debug",
            "us-daily-bars-cache-inventory",
            "--cache-root",
            str(tmp_path),
            "--symbol",
            "MSFT",
            "--format",
            "markdown",
        ],
    )
    assert r.exit_code == 0
    assert "MSFT" in r.stdout
