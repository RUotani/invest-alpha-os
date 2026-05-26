"""Product P4: weekly US observation cycle (cache-only; no HTTP)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.product.weekly_us_observation import (
    build_us_watchlist_signals_manifest,
    format_weekly_us_observation_markdown,
    run_weekly_us_observation_cycle,
    summarize_us_observation_log,
    us_cache_expansion_report,
)

REPO = Path(__file__).resolve().parents[1]
FIX_MSFT_ROWS = REPO / "tests" / "fixtures" / "us_daily_bars" / "MSFT.json"


@pytest.fixture(autouse=True)
def _block_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("product weekly tests must not use live HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)


@pytest.fixture
def mini_us_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    import invis_alpha_os.cli.main as cli_main
    import invis_alpha_os.config.paths as paths
    import invis_alpha_os.data.us_daily_bars_cache as usc
    import invis_alpha_os.product.weekly_us_observation as weekly

    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir(parents=True)
    cache_dir = outputs_dir / "market_data" / "us_daily_bars"
    monkeypatch.setattr(cli_main, "OUTPUTS_DIR", outputs_dir)
    monkeypatch.setattr(paths, "OUTPUTS_DIR", outputs_dir)
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs_dir)
    monkeypatch.setattr(weekly, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(cli_main, "ROOT_DIR", tmp_path)

    def _one_symbol_watchlist() -> list[str]:
        return ["MSFT"]

    monkeypatch.setattr(
        "invis_alpha_os.config.us_watchlist.load_us_watchlist_tickers",
        _one_symbol_watchlist,
    )
    monkeypatch.setattr(
        "invis_alpha_os.product.weekly_us_observation.load_us_watchlist_tickers",
        _one_symbol_watchlist,
    )

    from invis_alpha_os.data.us_daily_bars_cache import save_us_daily_bars_cache
    from invis_alpha_os.signals.momentum import load_bars_json_file

    bars = load_bars_json_file(FIX_MSFT_ROWS)
    save_us_daily_bars_cache(
        "MSFT",
        [dict(b) for b in bars],
        asset_class="us_equity",
        source="local_fixture",
        fetched_at="2026-05-23T12:00:00+00:00",
        generated_at="2026-05-23T12:00:05+00:00",
    )
    assert (cache_dir / "MSFT.json").is_file()
    return tmp_path


def test_build_manifest_lists_missing_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.product.weekly_us_observation.load_us_watchlist_tickers",
        lambda: ["MSFT", "ZZZZ"],
    )
    m = build_us_watchlist_signals_manifest(path_base=tmp_path)
    assert m["entries"] == []
    assert "ZZZZ" in m["missing_cache_symbols"]


def test_weekly_cycle_and_observation_log(mini_us_cache: Path) -> None:
    manifest = mini_us_cache / "signals" / "weekly.json"
    svc = ObservationService(
        observation_path=mini_us_cache / "observation_log" / "observation_log.jsonl",
        outcome_path=mini_us_cache / "outcome.jsonl",
    )
    result = run_weekly_us_observation_cycle(
        path_base=mini_us_cache,
        manifest_out=manifest,
        write_observation_log=True,
        observation_service=svc,
    )
    assert result.batch_previews.get("status") == "ok"
    assert result.quality.get("signals_ok") == 1
    assert result.observation_write_stats is not None
    assert result.observation_write_stats.get("logged") == 1
    md = format_weekly_us_observation_markdown(result, path_base=mini_us_cache)
    assert "Observation log write (this run)" in md
    assert "logged: 1" in md
    assert "## US forward resolution breakdown" in md
    assert "insufficient_future" in md
    summary = summarize_us_observation_log(svc.observation_path)
    assert summary["us_signal_rows"] == 1
    assert summary["rows"][0]["symbol"] == "MSFT"
    assert "research_checklist" in summary
    assert isinstance(summary["research_checklist"], list)
    assert all(isinstance(x, dict) and "category" in x for x in summary["research_checklist"])
    assert "not buy/sell advice" in svc.observation_path.read_text(encoding="utf-8")


def test_weekly_dry_run_reads_existing_observation_log(mini_us_cache: Path) -> None:
    from invis_alpha_os.observation.us_signal_note import build_us_signal_observation_note

    obs = mini_us_cache / "outputs" / "observation_log" / "observation_log.jsonl"
    obs.parent.mkdir(parents=True, exist_ok=True)
    svc = ObservationService(observation_path=obs, outcome_path=mini_us_cache / "outcome.jsonl")
    note = build_us_signal_observation_note({"status": "ok", "momentum_label": "neutral", "last_date": "2024-04-10"})
    svc.log_observation("MSFT", note)

    result = run_weekly_us_observation_cycle(path_base=mini_us_cache, write_observation_log=False)
    assert result.observation_log is not None
    assert result.observation_log.get("us_signal_rows") == 1
    assert "weekly_trend" in result.observation_log
    assert result.duplicate_week_preflight is not None
    assert result.duplicate_week_preflight.get("would_duplicate_count", 0) >= 1
    md = format_weekly_us_observation_markdown(result, path_base=mini_us_cache)
    assert "Duplicate ISO-week write preflight" in md
    if result.p3_path_preflight:
        assert "## P3 path preflight" in md
        assert result.p3_path_preflight.get("dominant_path")


def test_cli_weekly_dry_run(mini_us_cache: Path) -> None:
    result = CliRunner().invoke(app, ["weekly-us-observation", "--dry-run", "--format", "json"])
    assert result.exit_code == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["quality"]["signals_ok"] == 1


def test_cli_weekly_dry_run_includes_ops_smoke_hint(mini_us_cache: Path) -> None:
    result = CliRunner().invoke(app, ["weekly-us-observation", "--dry-run", "--format", "markdown"])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "validate ops-smoke" in result.stdout


def test_cli_weekly_skip_duplicate_requires_write() -> None:
    result = CliRunner().invoke(app, ["weekly-us-observation", "--skip-duplicate-iso-week"])
    assert result.exit_code == 2
    assert "requires --write-observation-log" in result.stderr + result.stdout


def test_cli_weekly_with_peer_sync(mini_us_cache: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.cli.main as cli_main

    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "peer_map.yaml").write_text(
        'peer_map:\n  MSFT:\n    - MSFT\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_main, "CONFIG_DIR", cfg)
    result = CliRunner().invoke(
        app,
        ["weekly-us-observation", "--dry-run", "--with-peer-sync", "--format", "json"],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload.get("peer_sync") is not None
    assert "pairs" in payload["peer_sync"]


def test_weekly_write_includes_peer_sync_log(
    mini_us_cache: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import invis_alpha_os.config.paths as config_paths

    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "peer_map.yaml").write_text("peer_map:\n  MSFT:\n    - MSFT\n", encoding="utf-8")
    monkeypatch.setattr(config_paths, "CONFIG_DIR", cfg)
    manifest = mini_us_cache / "signals" / "weekly.json"
    obs = mini_us_cache / "outputs" / "observation_log" / "observation_log.jsonl"
    obs.parent.mkdir(parents=True, exist_ok=True)
    svc = ObservationService(observation_path=obs, outcome_path=mini_us_cache / "outcome.jsonl")
    result = run_weekly_us_observation_cycle(
        path_base=mini_us_cache,
        manifest_out=manifest,
        write_observation_log=True,
        observation_service=svc,
        include_peer_sync=True,
    )
    assert result.observation_write_stats is not None
    assert result.peer_sync_write_stats is not None
    assert result.peer_sync_write_stats.get("logged", 0) >= 1
    text = obs.read_text(encoding="utf-8")
    assert "us_peer_sync" in text


def test_weekly_cycle_include_peer_sync(
    mini_us_cache: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import invis_alpha_os.config.paths as config_paths

    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "peer_map.yaml").write_text(
        'peer_map:\n  MSFT:\n    - MSFT\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config_paths, "CONFIG_DIR", cfg)
    result = run_weekly_us_observation_cycle(
        path_base=mini_us_cache,
        include_peer_sync=True,
    )
    assert result.peer_sync is not None
    assert isinstance(result.peer_sync.get("pairs"), list)


def test_us_cache_expansion_report_smoke(mini_us_cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.product.weekly_us_observation.load_us_watchlist_tickers",
        lambda: ["MSFT"],
    )
    report = us_cache_expansion_report(path_base=mini_us_cache, discover_limit=5)
    assert report["cache_file_count"] == 1
