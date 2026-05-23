"""Tests for peer_sync observation_log append (cache-only; explicit opt-in)."""

from __future__ import annotations

from pathlib import Path

import pytest

from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.observation.us_peer_sync_batch import log_peer_sync_snapshot_observations
from invis_alpha_os.observation.us_peer_sync_note import (
    build_us_peer_sync_observation_note,
    parse_us_peer_sync_observation_note,
)


def test_build_and_parse_peer_sync_note() -> None:
    note = build_us_peer_sync_observation_note(
        {
            "anchor_symbol": "AAPL",
            "peer_symbol": "MSFT",
            "status": "diverged_peer_outperform",
            "return_spread": -0.057,
            "correlation": -0.12,
            "aligned_sessions": 69,
        }
    )
    assert "us_peer_sync observation_only" in note
    assert "not buy/sell advice" in note
    parsed = parse_us_peer_sync_observation_note(note)
    assert parsed["anchor"] == "AAPL"
    assert parsed["peer"] == "MSFT"
    assert parsed["status"] == "diverged_peer_outperform"


def test_log_peer_sync_snapshot_observations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.config.paths as config_paths
    import invis_alpha_os.data.us_daily_bars_cache as usc
    from invis_alpha_os.data.us_daily_bars_cache import save_us_daily_bars_cache
    from invis_alpha_os.signals.momentum import load_bars_json_file

    repo = Path(__file__).resolve().parents[1]
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)

    cfg = tmp_path / "config"
    cfg.mkdir()
    peer_map = cfg / "peer_map.yaml"
    peer_map.write_text(
        'peer_map:\n  MSFT:\n    - GOOGL\n',
        encoding="utf-8",
    )

    for sym, fixture in [("MSFT", "MSFT.json"), ("GOOGL", "GOOGL.json")]:
        bars = load_bars_json_file(repo / "tests" / "fixtures" / "us_daily_bars" / fixture)
        save_us_daily_bars_cache(
            sym,
            [dict(b) for b in bars],
            asset_class="us_equity",
            source="local_fixture",
            fetched_at="2026-05-24T12:00:00+00:00",
            generated_at="2026-05-24T12:00:05+00:00",
        )

    obs_path = tmp_path / "observation_log.jsonl"
    svc = ObservationService(observation_path=obs_path, outcome_path=tmp_path / "outcome.jsonl")
    result = log_peer_sync_snapshot_observations(
        path_base=tmp_path,
        service=svc,
        peer_map_path=peer_map,
    )
    assert result["logged"] >= 1
    text = obs_path.read_text(encoding="utf-8")
    assert "us_peer_sync observation_only" in text


def test_cli_log_peer_sync_snapshot_dry_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    import invis_alpha_os.cli.main as cli_main

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    (outputs / "observation_log" / "observation_log.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setattr(cli_main, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(cli_main, "OUTPUTS_DIR", outputs)
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "peer_map.yaml").write_text('peer_map: {}\n', encoding="utf-8")
    monkeypatch.setattr(cli_main, "CONFIG_DIR", cfg)

    runner = CliRunner()
    result = runner.invoke(cli_main.app, ["log", "peer-sync-snapshot"])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "logged" in result.stdout


def test_summarize_peer_sync_observation_log(tmp_path: Path) -> None:
    from invis_alpha_os.observation.us_peer_sync_summary import summarize_peer_sync_observation_log
    from invis_alpha_os.observation.service import ObservationService
    from invis_alpha_os.observation.us_peer_sync_note import build_us_peer_sync_observation_note

    obs_path = tmp_path / "observation_log.jsonl"
    svc = ObservationService(observation_path=obs_path, outcome_path=tmp_path / "outcome.jsonl")
    note = build_us_peer_sync_observation_note(
        {"anchor_symbol": "AAPL", "peer_symbol": "MSFT", "status": "in_sync"}
    )
    svc.log_observation("AAPL", note)
    summary = summarize_peer_sync_observation_log(obs_path)
    assert summary["peer_sync_rows"] == 1
    assert summary["by_status"].get("in_sync") == 1


def test_cli_log_peer_sync_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    import invis_alpha_os.cli.main as cli_main

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    (outputs / "observation_log" / "observation_log.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setattr(cli_main, "OUTPUTS_DIR", outputs)
    runner = CliRunner()
    result = runner.invoke(cli_main.app, ["log", "peer-sync-summary"])
    assert result.exit_code == 0
    assert "peer_sync_rows" in result.stdout
