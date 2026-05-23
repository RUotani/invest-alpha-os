"""Product P4: weekly US observation cycle (cache-only; no HTTP)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.product.weekly_us_observation import (
    build_us_watchlist_signals_manifest,
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
    summary = summarize_us_observation_log(svc.observation_path)
    assert summary["us_signal_rows"] == 1
    assert summary["rows"][0]["symbol"] == "MSFT"
    assert "research_checklist" in summary
    assert isinstance(summary["research_checklist"], list)
    assert "not buy/sell advice" in svc.observation_path.read_text(encoding="utf-8")


def test_cli_weekly_dry_run(mini_us_cache: Path) -> None:
    result = CliRunner().invoke(app, ["weekly-us-observation", "--dry-run", "--format", "json"])
    assert result.exit_code == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["quality"]["signals_ok"] == 1


def test_us_cache_expansion_report_smoke(mini_us_cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.product.weekly_us_observation.load_us_watchlist_tickers",
        lambda: ["MSFT"],
    )
    report = us_cache_expansion_report(path_base=mini_us_cache, discover_limit=5)
    assert report["cache_file_count"] == 1
