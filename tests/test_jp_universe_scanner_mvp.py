"""R7.0-B: JP universe discovery scanner MVP (fixtures only; no HTTP)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.jquants_daily_bars_cache import save_jquants_daily_bars_cache
from invis_alpha_os.discovery.jp_universe_scanner import (
    DISCOVERY_MIN_BARS,
    FORBIDDEN_OUTPUT_TERMS,
    analyze_code_for_discovery,
    assert_no_forbidden_terms,
    format_jp_discovery_json,
    format_jp_discovery_markdown,
)
from invis_alpha_os.signals.momentum import DailyBar, calculate_returns, volume_ratio_25d_prior_mean


def _flat_bars(
    closes: list[float],
    *,
    volumes: list[float] | None = None,
    highs: list[float] | None = None,
) -> list[DailyBar]:
    out: list[DailyBar] = []
    for i, c in enumerate(closes):
        h = highs[i] if highs is not None else c + 0.5
        v = volumes[i] if volumes is not None else 10_000.0
        out.append(
            {
                "date": f"2024-{(i % 12) + 1:02d}-15",
                "open": c,
                "high": h,
                "low": c - 0.1,
                "close": c,
                "volume": v,
            }
        )
    return out


def test_volume_ratio_excludes_latest_from_average() -> None:
    vols = [1000.0] * 25 + [3000.0]
    ratio = volume_ratio_25d_prior_mean(vols)
    assert ratio == pytest.approx(3.0)


def test_returns_include_r5_r20_r60() -> None:
    closes = [100.0 + i * 0.5 for i in range(90)]
    r = calculate_returns(closes, (5, 20, 60))
    assert r[5] is not None and r[5] > 0
    assert r[20] is not None and r[20] > 0
    assert r[60] is not None


def test_high_breakout_and_volume_spike_labels() -> None:
    n = 90
    closes = [100.0 + i * 0.02 for i in range(n)]
    highs = list(closes)
    volumes = [5000.0] * (n - 1) + [20_000.0]
    highs[-1] = closes[-1] + 5.0
    closes[-1] = highs[-1]
    bars = _flat_bars(closes, volumes=volumes, highs=highs)
    row = analyze_code_for_discovery("7011", bars)
    assert row.data_quality == "ok"
    assert "high_52w_breakout" in row.labels
    assert "volume_spike" in row.labels
    assert row.discovery_score >= 3


def test_insufficient_bars_marked() -> None:
    bars = _flat_bars([100.0] * 30)
    row = analyze_code_for_discovery("7011", bars)
    assert row.data_quality == "insufficient_history"
    assert "insufficient_data" in row.categories


def test_overheat_caution_label() -> None:
    closes = [100.0 * (1.01**i) for i in range(90)]
    bars = _flat_bars(closes)
    row = analyze_code_for_discovery("7011", bars)
    assert row.data_quality == "ok"
    if row.return_20d is not None and row.return_20d >= 0.40:
        assert "overheat_caution" in row.labels


def test_display_name_in_output() -> None:
    bars = _flat_bars([100.0 + i * 0.3 for i in range(90)])
    row = analyze_code_for_discovery("5802", bars)
    assert "5802" in row.code_name


def test_markdown_json_contract_and_forbidden_terms() -> None:
    bars = _flat_bars([100.0 + i * 0.2 for i in range(90)])
    from invis_alpha_os.discovery.jp_universe_scanner import JpDiscoveryScanResult

    row = analyze_code_for_discovery("7011", bars)
    result = JpDiscoveryScanResult(
        universe_scope="sample_jp_universe",
        generated_at="2026-05-20T00:00:00Z",
        candidates=[row],
        symbol_count=1,
    )
    md = format_jp_discovery_markdown(result)
    assert "Observation only" in md
    assert "Discovery score is only a sorting aid" in md
    assert "| rank | instrument |" in md
    assert_no_forbidden_terms(md)
    payload = format_jp_discovery_json(result)
    assert payload["universe_scope"] == "sample_jp_universe"
    assert payload["market"] == "jp"
    assert payload["schema_version"] == "discovery.cross_market.v1"
    assert "common_candidates" in payload
    assert payload["common_candidates"][0]["instrument_id"] == "7011"
    assert "candidates" in payload
    assert payload["safety"]["live_http"] is False
    assert payload["safety"]["cache_read_only"] is True
    blob = json.dumps(payload)
    for term in FORBIDDEN_OUTPUT_TERMS:
        assert not re.search(rf"\b{re.escape(term)}\b", blob.lower())


def test_cli_discover_jp_json_with_fixture_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("invis_alpha_os.discovery.jp_universe_scanner.OUTPUTS_DIR", tmp_path)
    rows = [
        {
            "date": f"2024-{(i % 12) + 1:02d}-01",
            "open": 100 + i * 0.2,
            "high": 101 + i * 0.2,
            "low": 99 + i * 0.2,
            "close": 100 + i * 0.2,
            "volume": 8000.0,
        }
        for i in range(DISCOVERY_MIN_BARS + 5)
    ]
    save_jquants_daily_bars_cache("7011", rows, source="unit")
    runner = CliRunner()
    r = runner.invoke(
        app,
        [
            "discover-jp",
            "--format",
            "json",
            "--limit",
            "5",
        ],
    )
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    assert data["universe_scope"] == "local_cache_available_symbols"
    assert "candidates" in data


def test_cli_discover_jp_markdown_universe_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.discovery.jp_universe_scanner.OUTPUTS_DIR", tmp_path)
    ufile = tmp_path / "universe.yaml"
    ufile.write_text(
        "universe_scope: sample_jp_universe\nsymbols:\n  - '7011'\n",
        encoding="utf-8",
    )
    rows = [
        {
            "date": f"2024-{(i % 12) + 1:02d}-01",
            "open": 100 + i * 0.2,
            "high": 101 + i * 0.2,
            "low": 99 + i * 0.2,
            "close": 100 + i * 0.2,
            "volume": 8000.0,
        }
        for i in range(DISCOVERY_MIN_BARS + 5)
    ]
    save_jquants_daily_bars_cache("7011", rows, source="unit")
    runner = CliRunner()
    r = runner.invoke(
        app,
        [
            "discover-jp",
            "--format",
            "markdown",
            "--universe-file",
            str(ufile),
            "--limit",
            "10",
        ],
    )
    assert r.exit_code == 0
    assert "JP Universe Discovery Candidates" in r.stdout
    assert_no_forbidden_terms(r.stdout)
