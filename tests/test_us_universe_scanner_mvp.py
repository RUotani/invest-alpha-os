"""R7.0-C: US universe discovery scanner MVP (cache-only)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.us_daily_bars_cache import save_us_daily_bars_cache
from invis_alpha_os.discovery.us_universe_scanner import (
    DISCOVERY_MIN_BARS,
    FORBIDDEN_OUTPUT_TERMS,
    assert_no_forbidden_terms,
    format_us_discovery_json,
    format_us_discovery_markdown,
    scan_us_universe,
)

runner = CliRunner()


def _rows(n: int = 100, *, base: float = 100.0) -> list[dict[str, float | str]]:
    out: list[dict[str, float | str]] = []
    for i in range(n):
        c = base + i * 0.5
        out.append(
            {
                "date": f"2025-{(i % 12) + 1:02d}-01",
                "open": c - 0.2,
                "high": c + 0.4,
                "low": c - 0.5,
                "close": c,
                "volume": 1_000_000.0,
            }
        )
    return out


def test_scan_us_universe_with_fixture_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.discovery.us_universe_scanner.OUTPUTS_DIR", tmp_path)
    save_us_daily_bars_cache("MSFT", _rows(), source="unit")
    save_us_daily_bars_cache("AAPL", _rows(base=120.0), source="unit")
    result = scan_us_universe(limit=10)
    assert result.symbol_count >= 2
    assert len(result.candidates) >= 2
    assert result.candidates[0].data_quality == "ok"


def test_format_contract_and_forbidden_terms(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.discovery.us_universe_scanner.OUTPUTS_DIR", tmp_path)
    save_us_daily_bars_cache("MSFT", _rows(), source="unit")
    result = scan_us_universe(limit=5)
    md = format_us_discovery_markdown(result)
    assert "Observation only" in md
    assert "US Universe Discovery Candidates" in md
    assert_no_forbidden_terms(md)
    payload = format_us_discovery_json(result)
    assert payload["safety"]["live_http"] is False
    blob = json.dumps(payload).lower()
    for term in FORBIDDEN_OUTPUT_TERMS:
        assert not re.search(rf"\b{re.escape(term)}\b", blob)


def test_insufficient_history_marked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.discovery.us_universe_scanner.OUTPUTS_DIR", tmp_path)
    save_us_daily_bars_cache("MSFT", _rows(n=DISCOVERY_MIN_BARS - 10), source="unit")
    result = scan_us_universe(limit=10)
    assert any(x.symbol == "MSFT" for x in result.insufficient)


def test_cli_discover_us_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.discovery.us_universe_scanner.OUTPUTS_DIR", tmp_path)
    save_us_daily_bars_cache("MSFT", _rows(), source="unit")
    r = runner.invoke(app, ["discover-us", "--format", "json", "--limit", "5"])
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    assert "candidates" in data
    assert data["safety"]["live_http"] is False


def test_cli_discover_us_markdown_with_universe_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.discovery.us_universe_scanner.OUTPUTS_DIR", tmp_path)
    save_us_daily_bars_cache("MSFT", _rows(), source="unit")
    ufile = tmp_path / "us_universe.yaml"
    ufile.write_text("universe_scope: curated\nsymbols:\n  - symbol: MSFT\n", encoding="utf-8")
    r = runner.invoke(
        app,
        ["discover-us", "--format", "markdown", "--universe-file", str(ufile), "--limit", "10"],
    )
    assert r.exit_code == 0
    assert "US Universe Discovery Candidates" in r.stdout
    assert_no_forbidden_terms(r.stdout)
