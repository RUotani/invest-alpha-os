"""R6.10-F: US daily bars cache metrics CLI (no HTTP)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from datetime import date, timedelta

from invis_alpha_os.data.us_daily_bars_metrics import (
    METRICS_PREVIEW_INVALID_BASE_KEYS,
    METRICS_PREVIEW_OK_KEYS,
    build_us_daily_bars_cache_metrics_preview,
    format_us_daily_bars_cache_metrics_json,
    format_us_daily_bars_cache_metrics_markdown,
)

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "tests" / "fixtures" / "us_equities" / "minimal_msft_envelope.json"
_BARS = [
    {"date": "2024-01-02", "open": 380.0, "high": 381.0, "low": 378.0, "close": 380.5, "volume": 1000.0},
    {"date": "2024-01-03", "open": 380.5, "high": 382.0, "low": 379.0, "close": 381.0, "volume": 1100.0},
]
runner = CliRunner()


def _envelope(rows: list, *, symbol: str = "MSFT", bar_count: int | None = None) -> dict:
    return {
        "schema_version": 1,
        "symbol": symbol,
        "source": "fixture_test",
        "fetched_at": None,
        "generated_at": None,
        "bar_count": bar_count if bar_count is not None else len(rows),
        "bars": rows,
    }


def _write_envelope(tmp_path: Path, name: str, payload: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def _synthetic_envelope_path(tmp_path: Path, n: int) -> Path:
    bars = []
    d = date(2024, 1, 2)
    for i in range(n):
        c = 100.0 + float(i)
        bars.append(
            {
                "date": d.isoformat(),
                "open": c,
                "high": c + 1,
                "low": c - 1,
                "close": c,
                "volume": 1000.0 + i,
            }
        )
        d += timedelta(days=1)
    return _write_envelope(tmp_path, f"bars_{n}.json", _envelope(bars))


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


def test_invalid_path_json_contract() -> None:
    m = build_us_daily_bars_cache_metrics_preview(Path("/missing/cache.json"))
    assert METRICS_PREVIEW_INVALID_BASE_KEYS <= set(m.keys())
    assert m["reason"] == "path_not_found"


def test_markdown_invalid_includes_live_http() -> None:
    md = format_us_daily_bars_cache_metrics_markdown(
        build_us_daily_bars_cache_metrics_preview(Path("/missing.json"))
    )
    assert "**live_http**: false" in md
    assert "**reason**: path_not_found" in md


def test_cli_symbol_mismatch_exit_one() -> None:
    r = runner.invoke(
        app,
        [
            "debug",
            "us-daily-bars-cache-metrics",
            "--path",
            str(FIX),
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
        ["debug", "us-daily-bars-cache-metrics", "--path", str(FIX), "--format", "yaml"],
    )
    assert r.exit_code == 2


@pytest.mark.parametrize(
    "payload",
    [
        _envelope([], bar_count=0),
        _envelope(_BARS, bar_count=99),
        _envelope([_BARS[0], {**_BARS[0]}]),
    ],
)
def test_cli_invalid_envelope_exit_one(tmp_path: Path, payload: dict) -> None:
    path = _write_envelope(tmp_path, "bad.json", payload)
    r = runner.invoke(
        app,
        ["debug", "us-daily-bars-cache-metrics", "--path", str(path), "--format", "json"],
    )
    assert r.exit_code == 1
    body = json.loads(r.stdout.strip())
    assert body["status"] == "invalid"
    assert body["live_http"] is False


def test_cli_25_bars_has_return_5d(tmp_path: Path) -> None:
    path = _synthetic_envelope_path(tmp_path, 25)
    r = runner.invoke(
        app,
        ["debug", "us-daily-bars-cache-metrics", "--path", str(path), "--format", "json"],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    body = json.loads(r.stdout.strip())
    assert body["has_5d"] is True
    assert body["return_5d"] is not None


def test_markdown_ok_required_lines() -> None:
    md = format_us_daily_bars_cache_metrics_markdown(build_us_daily_bars_cache_metrics_preview(FIX))
    for needle in ("## US daily bars cache metrics", "**symbol**", "**bar_count**", "return_5d"):
        assert needle in md
