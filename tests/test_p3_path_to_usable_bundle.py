"""Tests for validate p3-path-to-usable bundle and CLI."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.product.p3_path_to_usable import (
    build_p3_path_to_usable_bundle,
    format_p3_path_to_usable_bundle_markdown,
)


def test_build_p3_path_to_usable_bundle_empty_log(tmp_path: Path) -> None:
    obs = tmp_path / "observation_log.jsonl"
    obs.write_text("", encoding="utf-8")
    cache = tmp_path / "cache"
    cache.mkdir()
    bundle = build_p3_path_to_usable_bundle(
        path_base=tmp_path,
        observation_path=obs,
        cache_dir=cache,
        horizon_timeline_max_rows=32,
    )
    assert bundle["observation_only"] is True
    assert bundle["schema_version"] == 1
    path = bundle.get("p3_path_to_usable") or {}
    assert "dominant_path" in path
    assert bundle["horizon_timeline_max_rows"] == 32
    md = format_p3_path_to_usable_bundle_markdown(bundle)
    assert "## P3 path to usable" in md


def test_cli_p3_path_to_usable_json(tmp_path: Path, monkeypatch) -> None:
    from invis_alpha_os.config import paths as paths_mod

    obs = tmp_path / "observation_log.jsonl"
    obs.write_text("", encoding="utf-8")
    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setattr(paths_mod, "OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(paths_mod, "ROOT_DIR", tmp_path)
    (tmp_path / "observation_log").mkdir(exist_ok=True)
    obs_default = tmp_path / "observation_log" / "observation_log.jsonl"
    obs_default.write_text("", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["validate", "p3-path-to-usable", "--format", "json", "--horizon-rows", "20"],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert "dominant_path" in (payload.get("p3_path_to_usable") or {})
    assert payload.get("horizon_timeline_max_rows") == 20


def test_cli_p3_path_to_usable_invalid_horizon_rows_exit_2() -> None:
    result = CliRunner().invoke(
        app,
        ["validate", "p3-path-to-usable", "--horizon-rows", "0"],
    )
    assert result.exit_code == 2
    assert "horizon-rows" in (result.stderr or result.stdout).lower()
