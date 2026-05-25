"""Tests for read-only validate ops-smoke report."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from invis_alpha_os.product.ops_smoke_report import (
    _signal_quality_snapshot_status,
    _watchlist_manifest_status,
    build_ops_smoke_report,
    format_ops_smoke_markdown,
)


def test_watchlist_manifest_status_helpers() -> None:
    assert _watchlist_manifest_status(0, 0) == "fail"
    assert _watchlist_manifest_status(1, 1) == "warn"
    assert _watchlist_manifest_status(2, 0) == "ok"


def test_signal_quality_snapshot_status_helpers() -> None:
    assert _signal_quality_snapshot_status(0, 0) == "fail"
    assert _signal_quality_snapshot_status(1, 2) == "fail"
    assert _signal_quality_snapshot_status(2, 2) == "ok"


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
    monkeypatch.setattr(
        "invis_alpha_os.product.observation_health.build_us_universe_expansion_report",
        lambda **_kw: {"tier_1_missing_refresh_order": []},
    )
    return tmp_path


def test_build_ops_smoke_report_fails_zero_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import invis_alpha_os.config.paths as config_paths
    import invis_alpha_os.product.ops_smoke_report as ops_mod

    outputs = tmp_path / "outputs"
    outputs.mkdir()
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "peer_map.yaml").write_text("peer_map: {}\n", encoding="utf-8")
    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(config_paths, "CONFIG_DIR", cfg)
    monkeypatch.setattr(ops_mod, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(
        "invis_alpha_os.product.weekly_us_observation.load_us_watchlist_tickers",
        lambda: [],
    )
    report = build_ops_smoke_report(path_base=tmp_path)
    manifest = next(c for c in report.checks if c.name == "watchlist_manifest")
    assert manifest.status == "fail"
    assert not report.all_ok


def test_build_ops_smoke_report_warns_missing_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    (cfg / "peer_map.yaml").write_text("peer_map: {}\n", encoding="utf-8")
    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(config_paths, "CONFIG_DIR", cfg)
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(ops_mod, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(psc, "CONFIG_DIR", cfg)
    monkeypatch.setattr(weekly, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(
        "invis_alpha_os.product.weekly_us_observation.load_us_watchlist_tickers",
        lambda: ["MSFT", "AMD"],
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
    report = build_ops_smoke_report(path_base=tmp_path)
    manifest = next(c for c in report.checks if c.name == "watchlist_manifest")
    assert manifest.status == "warn"
    assert report.manifest_entries == 1


def test_build_ops_smoke_report_fails_partial_signal_quality(
    mini_us_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import invis_alpha_os.product.ops_smoke_report as ops_mod

    monkeypatch.setattr(
        ops_mod,
        "us_signal_quality_snapshot",
        lambda **kwargs: {
            "symbol_count": 2,
            "signals_ok": 1,
            "rows": [],
        },
    )
    report = build_ops_smoke_report(path_base=mini_us_cache)
    quality = next(c for c in report.checks if c.name == "signal_quality_snapshot")
    assert quality.status == "fail"
    assert not report.all_ok


def test_ops_smoke_markdown_links_weekly_one_pager(mini_us_cache: Path) -> None:
    report = build_ops_smoke_report(path_base=mini_us_cache)
    md = format_ops_smoke_markdown(report)
    assert "docs/160_product_weekly_operator_one_pager.md" in md
    assert any("evidence-manifest" in cmd for cmd in report.next_commands)
    assert any("post-refresh-smoke" in cmd for cmd in report.next_commands)


def test_build_ops_smoke_report_ok(mini_us_cache: Path) -> None:
    report = build_ops_smoke_report(path_base=mini_us_cache)
    assert report.all_ok
    assert report.manifest_entries >= 1
    assert report.signals_ok >= 1
    payload = report.to_dict()
    assert payload["strict_taxonomy"]["taxonomy"] == "PASS"


def test_build_ops_smoke_report_warns_repeat_signals(
    mini_us_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import invis_alpha_os.product.ops_smoke_report as ops_mod

    obs_path = mini_us_cache / "outputs" / "observation_log" / "observation_log.jsonl"
    obs_path.parent.mkdir(parents=True, exist_ok=True)
    from invis_alpha_os.observation.service import ObservationService
    from invis_alpha_os.observation.us_signal_note import build_us_signal_observation_note

    svc = ObservationService(observation_path=obs_path, outcome_path=mini_us_cache / "outcome.jsonl")
    note = build_us_signal_observation_note({"status": "ok", "momentum_label": "uptrend", "last_date": "2024-04-10"})
    svc.log_observation("MSFT", note)
    svc.log_observation("MSFT", note)
    monkeypatch.setattr(ops_mod, "OUTPUTS_DIR", mini_us_cache / "outputs")

    report = build_ops_smoke_report(path_base=mini_us_cache)
    health_check = next(c for c in report.checks if c.name == "observation_health")
    assert health_check.status == "warn"
    assert "repeat_signals=" in health_check.detail


def test_build_ops_smoke_report_warns_stale_forward_cache(
    mini_us_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import invis_alpha_os.product.observation_health as oh_mod
    import invis_alpha_os.product.ops_smoke_report as ops_mod

    obs_path = mini_us_cache / "outputs" / "observation_log" / "observation_log.jsonl"
    obs_path.parent.mkdir(parents=True, exist_ok=True)
    from invis_alpha_os.observation.service import ObservationService
    from invis_alpha_os.observation.us_signal_note import build_us_signal_observation_note

    svc = ObservationService(observation_path=obs_path, outcome_path=mini_us_cache / "outcome.jsonl")
    note = build_us_signal_observation_note(
        {"status": "ok", "momentum_label": "uptrend", "last_date": "2026-05-22"}
    )
    svc.log_observation("MSFT", note)
    outputs = mini_us_cache / "outputs"
    monkeypatch.setattr(ops_mod, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(oh_mod, "OUTPUTS_DIR", outputs)

    report = build_ops_smoke_report(path_base=mini_us_cache)
    health_check = next(c for c in report.checks if c.name == "observation_health")
    assert health_check.status == "warn"
    assert "forward_stale_cache=1" in health_check.detail


def test_cli_validate_ops_smoke_strict_exits_on_warn(
    mini_us_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    import invis_alpha_os.cli.main as cli_main
    import invis_alpha_os.product.observation_health as oh_mod
    import invis_alpha_os.product.ops_smoke_report as ops_mod

    obs_path = mini_us_cache / "outputs" / "observation_log" / "observation_log.jsonl"
    obs_path.parent.mkdir(parents=True, exist_ok=True)
    from invis_alpha_os.observation.service import ObservationService
    from invis_alpha_os.observation.us_signal_note import build_us_signal_observation_note

    svc = ObservationService(observation_path=obs_path, outcome_path=mini_us_cache / "outcome.jsonl")
    note = build_us_signal_observation_note({"status": "ok", "momentum_label": "uptrend", "last_date": "2026-05-22"})
    svc.log_observation("MSFT", note)
    svc.log_observation("MSFT", note)
    outputs = mini_us_cache / "outputs"
    monkeypatch.setattr(cli_main, "ROOT_DIR", mini_us_cache)
    monkeypatch.setattr(cli_main, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(cli_main, "CONFIG_DIR", mini_us_cache / "config")
    monkeypatch.setattr(ops_mod, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(oh_mod, "OUTPUTS_DIR", outputs)

    runner = CliRunner()
    result = runner.invoke(cli_main.app, ["validate", "ops-smoke", "--format", "json", "--strict"])
    assert result.exit_code == 2, result.stdout + result.stderr
    assert "taxonomy=" in result.stderr
    assert "ops-smoke --strict:" in result.stderr


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
