"""R6.10-A: US equities cache-only JSON reader (fixtures; no HTTP)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from invis_alpha_os.data.us_daily_bars_cache import load_us_daily_bars_json_file

REPO_ROOT = Path(__file__).resolve().parents[1]
_FIX_ROWS = REPO_ROOT / "tests" / "fixtures" / "us_daily_bars" / "MSFT.json"


def _envelope(rows: list, *, symbol: str = "MSFT") -> dict:
    return {
        "schema_version": 1,
        "symbol": symbol,
        "source": "fixture_test",
        "fetched_at": None,
        "generated_at": None,
        "bar_count": len(rows),
        "bars": rows,
    }


def test_load_us_daily_bars_json_file_fixture_rows(tmp_path: Path) -> None:
    rows = json.loads(_FIX_ROWS.read_text(encoding="utf-8"))
    assert isinstance(rows, list) and rows
    p = tmp_path / "msft.json"
    p.write_text(json.dumps(_envelope(rows)), encoding="utf-8")
    got = load_us_daily_bars_json_file(p)
    assert got is not None
    bars, meta = got
    assert len(bars) >= 1
    assert meta.get("symbol") == "MSFT"


def test_load_us_daily_bars_json_file_wrong_expect_symbol(tmp_path: Path) -> None:
    rows = json.loads(_FIX_ROWS.read_text(encoding="utf-8"))
    p = tmp_path / "msft.json"
    p.write_text(json.dumps(_envelope(rows)), encoding="utf-8")
    assert load_us_daily_bars_json_file(p, expect_symbol="GOOGL") is None


def test_load_us_daily_bars_json_file_expect_symbol_match(tmp_path: Path) -> None:
    rows = json.loads(_FIX_ROWS.read_text(encoding="utf-8"))
    p = tmp_path / "msft.json"
    p.write_text(json.dumps(_envelope(rows)), encoding="utf-8")
    got = load_us_daily_bars_json_file(p, expect_symbol="MSFT")
    assert got is not None


def test_load_us_daily_bars_json_file_malformed_json(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{", encoding="utf-8")
    assert load_us_daily_bars_json_file(p) is None


def test_load_us_daily_bars_json_file_empty_bars(tmp_path: Path) -> None:
    p = tmp_path / "empty.json"
    p.write_text(json.dumps(_envelope([], symbol="MSFT")), encoding="utf-8")
    assert load_us_daily_bars_json_file(p) is None
