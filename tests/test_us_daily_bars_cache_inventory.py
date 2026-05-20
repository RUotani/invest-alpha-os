"""R6.16-A/B/E: read-only US daily bars cache inventory (no HTTP)."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.us_daily_bars_cache_inventory import (
    build_us_daily_bars_cache_inventory,
    build_us_daily_bars_cache_inventory_row,
    format_us_daily_bars_cache_inventory_json,
    format_us_daily_bars_cache_inventory_markdown,
)

REPO = Path(__file__).resolve().parents[1]
FIX_MINIMAL = REPO / "tests" / "fixtures" / "us_equities" / "minimal_msft_envelope.json"
FIX_25 = REPO / "tests" / "fixtures" / "us_equities" / "msft_25bars_metrics_envelope.json"
runner = CliRunner()


def _envelope_last_day(symbol: str, last: str, *, n: int = 25) -> dict:
    end = date.fromisoformat(last)
    start = end - timedelta(days=n - 1)
    bars = [
        {
            "date": (start + timedelta(days=i)).isoformat(),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000.0,
        }
        for i in range(n)
    ]
    return {
        "schema_version": 1,
        "symbol": symbol,
        "source": "fixture_test",
        "fetched_at": "2026-05-01T00:00:00Z",
        "generated_at": "2026-05-01T00:00:00Z",
        "bar_count": n,
        "bars": bars,
    }


@pytest.fixture(autouse=True)
def _block_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("US cache inventory tests must not use live HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)


def test_inventory_row_missing(tmp_path: Path) -> None:
    row = build_us_daily_bars_cache_inventory_row("MSFT", tmp_path)
    assert row["status"] == "missing"
    assert row["reason"] == "missing_file"
    assert row["freshness_status"] == "not_applicable"
    assert row["latest_date"] is None
    assert row["file_exists"] is False
    assert row["live_http"] is False


def test_inventory_row_insufficient(tmp_path: Path) -> None:
    dest = tmp_path / "MSFT.json"
    dest.write_text(FIX_MINIMAL.read_text(encoding="utf-8"), encoding="utf-8")
    row = build_us_daily_bars_cache_inventory_row("MSFT", tmp_path)
    assert row["status"] == "insufficient"
    assert row["reason"] == "insufficient_bars"
    assert row["bar_count"] == 2


def test_inventory_row_stale_unknown(tmp_path: Path) -> None:
    dest = tmp_path / "MSFT.json"
    dest.write_text(FIX_25.read_text(encoding="utf-8"), encoding="utf-8")
    row = build_us_daily_bars_cache_inventory_row("MSFT", tmp_path)
    assert row["status"] == "stale_unknown"
    assert row["reason"] == "stale_unknown"
    assert row["bar_count"] == 25


def test_inventory_row_ok_with_freshness(tmp_path: Path) -> None:
    payload = _envelope_last_day("MSFT", "2026-05-15")
    (tmp_path / "MSFT.json").write_text(json.dumps(payload), encoding="utf-8")
    ref = date(2026, 5, 19)
    row = build_us_daily_bars_cache_inventory_row("MSFT", tmp_path, reference_date=ref, fresh_days=7)
    assert row["status"] == "ok"
    assert row["reason"] == "ok"
    assert row["latest_date"] == "2026-05-15"
    assert row["freshness_status"] == "fresh_enough"


def test_inventory_row_ok_but_stale_by_latest_date(tmp_path: Path) -> None:
    payload = _envelope_last_day("MSFT", "2024-01-25")
    (tmp_path / "MSFT.json").write_text(json.dumps(payload), encoding="utf-8")
    ref = date(2026, 5, 19)
    row = build_us_daily_bars_cache_inventory_row("MSFT", tmp_path, reference_date=ref, fresh_days=7)
    assert row["status"] == "ok"
    assert row["freshness_status"] == "stale"
    assert row["latest_date"] == "2024-01-25"


def test_freshness_summary_counts(tmp_path: Path) -> None:
    ref = date(2026, 5, 19)
    (tmp_path / "MSFT.json").write_text(
        json.dumps(_envelope_last_day("MSFT", "2026-05-18")), encoding="utf-8"
    )
    (tmp_path / "AAPL.json").write_text(
        json.dumps(_envelope_last_day("AAPL", "2024-01-10")), encoding="utf-8"
    )
    inv = build_us_daily_bars_cache_inventory(
        tmp_path, symbols=["MSFT", "AAPL"], reference_date=ref, fresh_days=7
    )
    s = inv["summary"]
    assert s["fresh_enough_count"] == 1
    assert s["stale_count"] == 1
    assert s["freshness_cutoff_date"] == "2026-05-12"
    assert s["newest_latest_date"] == "2026-05-18"


def test_inventory_row_invalid(tmp_path: Path) -> None:
    bad = tmp_path / "MSFT.json"
    bad.write_text("{not json", encoding="utf-8")
    row = build_us_daily_bars_cache_inventory_row("MSFT", tmp_path)
    assert row["status"] == "invalid"
    assert row["reason"] == "invalid_cache_payload"


def test_build_inventory_summary_counts(tmp_path: Path) -> None:
    inv = build_us_daily_bars_cache_inventory(tmp_path, symbols=["MSFT", "AAPL"])
    summary = inv["summary"]
    assert summary["total_symbols"] == 2
    assert summary["missing_count"] == 2
    assert summary["ok_count"] == 0
    assert summary["live_http"] is False
    assert summary["cache_root"] == str(tmp_path.resolve())


def test_build_inventory_json_symbols(tmp_path: Path) -> None:
    inv = build_us_daily_bars_cache_inventory(tmp_path, symbols=["MSFT", "AAPL"])
    assert inv["symbol_count"] == 2
    assert inv["live_http"] is False
    parsed = json.loads(format_us_daily_bars_cache_inventory_json(inv))
    assert parsed["summary"]["missing_count"] == 2
    assert parsed["status_counts"]["missing"] == 2


def test_markdown_summary_section(tmp_path: Path) -> None:
    inv = build_us_daily_bars_cache_inventory(tmp_path, symbols=["MSFT"])
    md = format_us_daily_bars_cache_inventory_markdown(inv)
    assert "### Summary" in md
    assert "**missing**:" in md
    assert "**fresh_enough**:" in md or "**freshness_unknown**:" in md
    assert "freshness" in md
    assert "### rows" in md


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
    assert '"missing_count": 1' in r.stdout


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
    assert "### Summary" in r.stdout
