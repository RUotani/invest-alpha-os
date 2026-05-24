"""Tests for read-only validate ops-smoke report."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from invis_alpha_os.product.ops_smoke_report import build_ops_smoke_report


@pytest.fixture
def mini_us_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    import invis_alpha_os.config.paths as config_paths
    import invis_alpha_os.data.us_daily_bars_cache as usc
    import invis_alpha_os.product.ops_smoke_report as ops_mod
    import invis_alpha_os.product.peer_sync_cache_only as psc
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
    monkeypatch.setattr(ops_mod, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(psc, "CONFIG_DIR", cfg)
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
    return tmp_path


def test_build_ops_smoke_report_ok(mini_us_cache: Path) -> None:
    report = build_ops_smoke_report(path_base=mini_us_cache)
    assert report.all_ok
    assert report.manifest_entries >= 1
    assert report.signals_ok >= 1


def test_cli_validate_ops_smoke_json(mini_us_cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    import invis_alpha_os.cli.main as cli_main

    monkeypatch.setattr(cli_main, "ROOT_DIR", mini_us_cache)
    outputs = mini_us_cache / "outputs"
    monkeypatch.setattr(cli_main, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(cli_main, "CONFIG_DIR", mini_us_cache / "config")
    runner = CliRunner()
    result = runner.invoke(cli_main.app, ["validate", "ops-smoke", "--format", "json"])
    assert result.exit_code == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["all_ok"] is True
