"""Product P2: US signals batch → observation_log (cache-only; no HTTP)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.observation.us_signals_batch import log_us_signals_batch_observations

REPO = Path(__file__).resolve().parents[1]
FIX_MANIFEST = REPO / "tests" / "fixtures" / "us_equities" / "us_cache_signals_batch_minimal.json"


@pytest.fixture(autouse=True)
def _block_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("observation batch tests must not use live HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)


def test_log_us_signals_batch_observations(tmp_path: Path) -> None:
    obs_path = tmp_path / "observation_log.jsonl"
    svc = ObservationService(observation_path=obs_path, outcome_path=tmp_path / "outcomes.jsonl")
    result = log_us_signals_batch_observations(FIX_MANIFEST, path_base=REPO, service=svc)
    assert result["manifest_status"] == "ok"
    assert result["logged"] == 2
    assert result["observation_only"] is True
    lines = obs_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    row = json.loads(lines[0])
    assert "us_cache_signal observation_only" in row["note"]
    assert "not buy/sell advice" in row["note"]


def test_cli_log_us_signals_batch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.cli.main as cli_main

    obs_root = tmp_path / "observation_log"
    obs_root.mkdir(parents=True)
    monkeypatch.setattr(cli_main, "OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(
        cli_main,
        "_obs_service",
        lambda: ObservationService(
            observation_path=obs_root / "observation_log.jsonl",
            outcome_path=obs_root / "outcome_log.jsonl",
        ),
    )
    runner = CliRunner()
    result = runner.invoke(app, ["log", "us-signals-batch", "--manifest", str(FIX_MANIFEST)])
    assert result.exit_code == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["logged"] == 2
