"""Tests for validate p3-horizon-timeline export."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.product.p3_path_to_usable import build_p3_horizon_timeline_export


def test_build_p3_horizon_timeline_export_empty(tmp_path: Path) -> None:
    obs = tmp_path / "observation_log.jsonl"
    obs.write_text("", encoding="utf-8")
    cache = tmp_path / "cache"
    cache.mkdir()
    export = build_p3_horizon_timeline_export(
        path_base=tmp_path,
        observation_path=obs,
        cache_dir=cache,
        horizon_timeline_max_rows=24,
    )
    assert export["observation_only"] is True
    assert export["horizon_timeline_max_rows"] == 24
    assert "p3_horizon_timeline" in export


def test_cli_p3_horizon_timeline_invalid_rows_exit_2() -> None:
    result = CliRunner().invoke(
        app,
        ["validate", "p3-horizon-timeline", "--horizon-rows", "0"],
    )
    assert result.exit_code == 2


def test_cli_p3_horizon_timeline_json(tmp_path: Path, monkeypatch) -> None:
    from invis_alpha_os.config import paths as paths_mod

    (tmp_path / "observation_log").mkdir(exist_ok=True)
    obs = tmp_path / "observation_log" / "observation_log.jsonl"
    obs.write_text("", encoding="utf-8")
    monkeypatch.setattr(paths_mod, "OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(paths_mod, "ROOT_DIR", tmp_path)

    result = CliRunner().invoke(
        app,
        ["validate", "p3-horizon-timeline", "--format", "json", "--horizon-rows", "20"],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload.get("p3_horizon_timeline") is not None
