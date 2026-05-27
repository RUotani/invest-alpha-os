"""Tests for Weekly Observation Report v1 (read-only; MERGE/STOP sample)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def mini_us_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    import invis_alpha_os.config.paths as config_paths
    import invis_alpha_os.data.us_daily_bars_cache as usc
    import invis_alpha_os.product.weekly_us_observation as weekly

    repo = Path(__file__).resolve().parents[1]
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "peer_map.yaml").write_text('peer_map:\n  MSFT:\n    - MSFT\n', encoding="utf-8")
    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(config_paths, "CONFIG_DIR", cfg)
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(weekly, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(
        "invis_alpha_os.config.us_watchlist.load_us_watchlist_tickers",
        lambda: ["MSFT"],
    )
    monkeypatch.setattr(
        "invis_alpha_os.product.weekly_us_observation.load_us_watchlist_tickers",
        lambda: ["MSFT"],
    )
    from invis_alpha_os.data.us_daily_bars_cache import save_us_daily_bars_cache
    from invis_alpha_os.signals.momentum import load_bars_json_file

    bars = load_bars_json_file(repo / "tests" / "fixtures" / "us_daily_bars" / "MSFT.json")
    save_us_daily_bars_cache(
        "MSFT",
        [dict(b) for b in bars],
        asset_class="us_equity",
        source="local_fixture",
        fetched_at="2026-05-24T12:00:00+00:00",
        generated_at="2026-05-24T12:00:05+00:00",
    )
    monkeypatch.setattr(
        "invis_alpha_os.product.observation_health.build_us_universe_expansion_report",
        lambda **_kw: {"tier_1_missing_refresh_order": []},
    )
    return tmp_path


def test_build_weekly_observation_report_v1(mini_us_cache: Path) -> None:
    from invis_alpha_os.product.weekly_observation_report_v1 import (
        build_weekly_observation_report_v1,
    )

    report = build_weekly_observation_report_v1(
        path_base=mini_us_cache,
        report_date="2026-05-27",
    )
    gate = report.p3_monitoring_gate()
    assert gate["status"] == "immature_monitoring"
    assert "not a short-term development KPI" in gate["headline"]
    assert report.cycle.quality.get("symbol_count", 0) >= 1


def test_format_weekly_observation_report_v1_required_sections(mini_us_cache: Path) -> None:
    from invis_alpha_os.observation.service import ObservationService
    from invis_alpha_os.observation.us_signal_note import build_us_signal_observation_note
    from invis_alpha_os.product.weekly_observation_report_v1 import (
        build_weekly_observation_report_v1,
        format_weekly_observation_report_v1_markdown,
    )

    obs_path = mini_us_cache / "outputs" / "observation_log" / "observation_log.jsonl"
    obs_path.parent.mkdir(parents=True, exist_ok=True)
    svc = ObservationService(observation_path=obs_path, outcome_path=mini_us_cache / "outcome.jsonl")
    note = build_us_signal_observation_note(
        {"status": "ok", "momentum_label": "uptrend", "last_date": "2024-04-10"}
    )
    svc.log_observation("MSFT", note)

    report = build_weekly_observation_report_v1(
        path_base=mini_us_cache,
        report_date="2026-05-27",
    )
    md = format_weekly_observation_report_v1_markdown(report, path_base=mini_us_cache)
    for heading in (
        "# Weekly Observation Report v1",
        "## US signals",
        "## Risk veto",
        "## Portfolio observation",
        "## P10 gap",
        "## P3 live forward usable",
        "## Next human actions",
        "## Peer sync",
        "## Forward validation summary",
    ):
        assert heading in md, f"missing section: {heading}"
    assert "immature but monitoring" in md
    assert "not buy/sell" in md.lower()


def test_format_weekly_observation_report_v1_json(mini_us_cache: Path) -> None:
    from invis_alpha_os.product.weekly_observation_report_v1 import (
        build_weekly_observation_report_v1,
        format_weekly_observation_report_v1_json,
    )

    report = build_weekly_observation_report_v1(path_base=mini_us_cache)
    payload = json.loads(format_weekly_observation_report_v1_json(report))
    assert payload["schema_version"] == 1
    assert payload["p3_monitoring_gate"]["status"] == "immature_monitoring"


def test_cli_weekly_observation_report_v1(mini_us_cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    import invis_alpha_os.cli.main as cli_main

    monkeypatch.setattr(cli_main, "ROOT_DIR", mini_us_cache)
    outputs = mini_us_cache / "outputs"
    monkeypatch.setattr(cli_main, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(cli_main, "CONFIG_DIR", mini_us_cache / "config")
    runner = CliRunner()
    result = runner.invoke(
        cli_main.app,
        ["weekly-observation-report-v1", "--format", "markdown", "--report-date", "2026-05-27"],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "Weekly Observation Report v1" in result.stdout


def test_cli_weekly_observation_report_v1_invalid_format(
    mini_us_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    import invis_alpha_os.cli.main as cli_main

    monkeypatch.setattr(cli_main, "ROOT_DIR", mini_us_cache)
    runner = CliRunner()
    result = runner.invoke(cli_main.app, ["weekly-observation-report-v1", "--format", "xml"])
    assert result.exit_code == 2
