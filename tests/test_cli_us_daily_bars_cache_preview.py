"""R6.10-C: US daily bars cache-only preview CLI (no HTTP)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.us_daily_bars_cache import (
    PREVIEW_INVALID_BASE_KEYS,
    PREVIEW_OK_KEYS,
    build_us_daily_bars_cache_preview,
    format_us_daily_bars_cache_preview_json,
    format_us_daily_bars_cache_preview_markdown,
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


def test_json_ok_output_contract_keys() -> None:
    p = build_us_daily_bars_cache_preview(FIX)
    assert set(p.keys()) == PREVIEW_OK_KEYS
    assert p["validation_status"] == "ok"
    assert p["live_http"] is False
    assert isinstance(p["bar_count"], int)
    assert isinstance(p["last_close"], float)


def test_json_invalid_path_contract_keys() -> None:
    p = build_us_daily_bars_cache_preview(Path("/no/such/cache.json"))
    assert PREVIEW_INVALID_BASE_KEYS <= set(p.keys())
    assert p["reason"] == "path_not_found"


def test_markdown_ok_required_lines() -> None:
    md = format_us_daily_bars_cache_preview_markdown(build_us_daily_bars_cache_preview(FIX))
    for needle in ("## US daily bars cache preview", "**symbol**", "**bar_count**", "**last_close**"):
        assert needle in md


def test_markdown_invalid_includes_live_http() -> None:
    md = format_us_daily_bars_cache_preview_markdown(
        build_us_daily_bars_cache_preview(Path("/missing.json"))
    )
    assert "**live_http**: false" in md
    assert "**reason**: path_not_found" in md


def test_cli_bad_format_exit_two() -> None:
    r = runner.invoke(
        app,
        ["debug", "us-daily-bars-cache-preview", "--path", str(FIX), "--format", "yaml"],
    )
    assert r.exit_code == 2, r.stdout + r.stderr


def test_cli_invalid_json_exit_one(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    r = runner.invoke(
        app,
        ["debug", "us-daily-bars-cache-preview", "--path", str(bad), "--format", "json"],
    )
    assert r.exit_code == 1
    body = json.loads(r.stdout.strip())
    assert body["validation_status"] == "invalid"
    assert body["reason"] == "parse_failed"


@pytest.mark.parametrize(
    "payload",
    [
        _envelope([], bar_count=0),
        _envelope(_BARS, bar_count=99),
        _envelope([_BARS[0], {**_BARS[0]}]),
        _envelope(list(reversed(_BARS))),
    ],
)
def test_cli_invalid_envelope_exit_one(tmp_path: Path, payload: dict) -> None:
    path = _write_envelope(tmp_path, "bad.json", payload)
    r = runner.invoke(
        app,
        ["debug", "us-daily-bars-cache-preview", "--path", str(path), "--format", "json"],
    )
    assert r.exit_code == 1, r.stdout + r.stderr
    body = json.loads(r.stdout.strip())
    assert body["validation_status"] == "invalid"
    assert body["reason"] == "parse_failed"
    assert body["live_http"] is False
