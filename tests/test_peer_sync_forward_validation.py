"""Peer sync × forward return join (read-only; cache-only)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.observation.us_peer_sync_note import build_us_peer_sync_observation_note
from invis_alpha_os.product.jp_peer_sync_loader import (
    build_jp_peer_sync_readiness_report,
    classify_peer_map_symbol,
    try_load_bars_for_peer_sync,
)
from invis_alpha_os.product.peer_sync_forward_validation import (
    compute_peer_sync_forward_join,
    format_peer_sync_forward_markdown,
)
from invis_alpha_os.product.us_forward_return_validation import compute_us_forward_returns
from invis_alpha_os.signals.momentum import load_bars_json_file


REPO = Path(__file__).resolve().parents[1]
FIX_MSFT = REPO / "tests" / "fixtures" / "us_daily_bars" / "MSFT.json"


@pytest.fixture(autouse=True)
def _block_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))


def test_classify_peer_map_symbol() -> None:
    assert classify_peer_map_symbol("7011") == "jp"
    assert classify_peer_map_symbol("AAPL") == "us"


def test_peer_sync_forward_join_msft(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.data.us_daily_bars_cache as usc

    outputs = tmp_path / "outputs"
    outputs.mkdir()
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)

    bars = load_bars_json_file(FIX_MSFT)
    event_date = bars[-21]["date"][:10]
    usc.save_us_daily_bars_cache(
        "MSFT",
        [dict(b) for b in bars],
        asset_class="us_equity",
        source="local_fixture",
        fetched_at="2026-05-24T12:00:00+00:00",
        generated_at="2026-05-24T12:00:05+00:00",
    )

    note = build_us_peer_sync_observation_note(
        {
            "anchor_symbol": "MSFT",
            "peer_symbol": "GOOGL",
            "status": "diverged_peer_outperform",
            "return_spread": -0.04,
        }
    )
    obs_path = outputs / "observation_log" / "observation_log.jsonl"
    obs_path.parent.mkdir(parents=True)
    obs_path.write_text(
        json.dumps(
            {
                "id": "ps-1",
                "created_at": f"{event_date}T09:00:00+00:00",
                "symbol": "MSFT",
                "note": note,
                "evidence_ids": [],
                "tags": [],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    report = compute_peer_sync_forward_join(observation_path=obs_path, horizons=(5, 20))
    assert report["rows_matched"] == 1
    assert report["peer_sync_at_t"]["status"] == "joined"
    assert "diverged_peer_outperform" in report["by_peer_sync_status"]
    md = format_peer_sync_forward_markdown(report)
    assert "Peer sync × forward returns" in md


def test_us_forward_returns_includes_peer_sync_block(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.data.us_daily_bars_cache as usc

    outputs = tmp_path / "outputs"
    cache_dir = outputs / "us_daily_bars"
    cache_dir.mkdir(parents=True)
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)

    bars = load_bars_json_file(FIX_MSFT)
    event_date = bars[-21]["date"][:10]
    usc.save_us_daily_bars_cache(
        "MSFT",
        [dict(b) for b in bars],
        asset_class="us_equity",
        source="local_fixture",
        fetched_at="2026-05-24T12:00:00+00:00",
        generated_at="2026-05-24T12:00:05+00:00",
    )

    obs_path = outputs / "observation_log" / "observation_log.jsonl"
    obs_path.parent.mkdir(parents=True)
    us_note = (
        "us_signal observation_only momentum=positive status=active "
        "veto_triggered=false not buy/sell advice"
    )
    ps_note = build_us_peer_sync_observation_note(
        {"anchor_symbol": "MSFT", "peer_symbol": "GOOGL", "status": "in_sync"}
    )
    obs_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "u1",
                        "created_at": f"{event_date}T09:00:00+00:00",
                        "symbol": "MSFT",
                        "note": us_note,
                        "evidence_ids": [],
                        "tags": [],
                    }
                ),
                json.dumps(
                    {
                        "id": "p1",
                        "created_at": f"{event_date}T10:00:00+00:00",
                        "symbol": "MSFT",
                        "note": ps_note,
                        "evidence_ids": [],
                        "tags": [],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = compute_us_forward_returns(observation_path=obs_path, cache_dir=cache_dir)
    assert "peer_sync_forward" in report
    assert report["peer_sync_forward"]["peer_sync_at_t"]["status"] == "joined"


def test_jp_peer_sync_readiness_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.config.paths as config_paths
    import invis_alpha_os.data.jquants_daily_bars_cache as jqc
    import invis_alpha_os.data.us_daily_bars_cache as usc

    outputs = tmp_path / "outputs"
    outputs.mkdir()
    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(jqc, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)

    cfg = tmp_path / "config"
    cfg.mkdir()
    peer_map = cfg / "peer_map.yaml"
    peer_map.write_text(
        'peer_map:\n  "7011":\n    - "7012"\n  AAPL:\n    - MSFT\n',
        encoding="utf-8",
    )
    report = build_jp_peer_sync_readiness_report(path_base=tmp_path, peer_map_path=peer_map)
    assert report["jp_edge_count"] == 1
    assert report["jp_edges_missing"] == 1
    assert report["edges"][0]["anchor"] == "7011"


def test_cli_validate_peer_sync_forward_returns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.cli.main as cli_main

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    (outputs / "observation_log" / "observation_log.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setattr(cli_main, "OUTPUTS_DIR", outputs)

    runner = CliRunner()
    result = runner.invoke(cli_main.app, ["validate", "peer-sync-forward-returns"])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "peer_sync_at_t" in result.stdout or "not_in_observation_log" in result.stdout


def test_try_load_bars_for_peer_sync_us(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.data.us_daily_bars_cache as usc

    outputs = tmp_path / "outputs"
    outputs.mkdir()
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)
    bars = load_bars_json_file(FIX_MSFT)
    usc.save_us_daily_bars_cache(
        "MSFT",
        [dict(b) for b in bars],
        asset_class="us_equity",
        source="local_fixture",
        fetched_at="2026-05-24T12:00:00+00:00",
        generated_at="2026-05-24T12:00:05+00:00",
    )
    loaded = try_load_bars_for_peer_sync("MSFT")
    assert loaded is not None
    assert loaded[1] == "us_cache"
