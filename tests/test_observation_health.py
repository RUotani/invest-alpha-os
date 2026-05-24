"""Tests for read-only observation health report (Wave B)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.observation.us_signal_note import build_us_signal_observation_note
from invis_alpha_os.product.observation_health import build_observation_health_report
from invis_alpha_os.signals.peer_sync import peer_sync_status_explanation


def test_peer_sync_status_explanation_known() -> None:
    assert "observation" in peer_sync_status_explanation("in_sync").lower()
    assert "cache" in peer_sync_status_explanation("missing_cache").lower()


def test_observation_health_missing_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.config.paths as config_paths

    outputs = tmp_path / "outputs"
    outputs.mkdir()
    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)
    report = build_observation_health_report(path_base=tmp_path)
    d = report.to_dict()
    assert d["us_signals"]["status"] == "missing"
    assert d["log_integrity"]["status"] == "missing"
    assert any("write-observation-log" in c for c in d["next_commands"])


def test_observation_health_malformed_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.config.paths as config_paths

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    obs = outputs / "observation_log" / "observation_log.jsonl"
    obs.write_text("{not json\n", encoding="utf-8")
    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)
    report = build_observation_health_report(path_base=tmp_path, observation_path=obs)
    assert report.log_integrity["json_parse_errors"] == 1


def test_observation_health_with_us_signal_row(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.config.paths as config_paths

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    obs = outputs / "observation_log" / "observation_log.jsonl"
    svc = ObservationService(observation_path=obs, outcome_path=tmp_path / "outcome.jsonl")
    note = build_us_signal_observation_note({"status": "ok", "momentum_label": "neutral"})
    svc.log_observation("MSFT", note)
    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)
    report = build_observation_health_report(path_base=tmp_path, observation_path=obs)
    assert report.us_signals["us_signal_rows"] == 1


def test_cli_snapshot_observation_health(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    import invis_alpha_os.cli.main as cli_main

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    (outputs / "observation_log" / "observation_log.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setattr(cli_main, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(cli_main, "OUTPUTS_DIR", outputs)
    runner = CliRunner()
    result = runner.invoke(cli_main.app, ["snapshot", "observation-health", "--format", "json"])
    assert result.exit_code == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert "us_signals" in payload
