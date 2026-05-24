"""JP peer_sync in validate peer-sync + observation forward UX."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from invis_alpha_os.product.jp_peer_sync_loader import try_load_bars_for_peer_sync
from invis_alpha_os.product.peer_sync_cache_only import build_peer_sync_cache_only_report
from invis_alpha_os.product.peer_sync_forward_validation import compute_peer_sync_forward_join
from invis_alpha_os.product.us_forward_return_validation import _sample_quality
from invis_alpha_os.signals.momentum import DailyBar


def _jp_bars(n: int = 40) -> list[DailyBar]:
    return [
        {
            "date": f"2026-01-{i + 1:02d}",
            "open": 1000 + i,
            "high": 1001 + i,
            "low": 999 + i,
            "close": 1000 + i,
            "volume": 1000.0,
        }
        for i in range(n)
    ]


def test_build_peer_sync_report_includes_jp_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import invis_alpha_os.config.paths as config_paths
    import invis_alpha_os.data.jquants_daily_bars_cache as jqc
    from invis_alpha_os.data.jquants_daily_bars_cache import save_jquants_daily_bars_cache

    outputs = tmp_path / "outputs"
    outputs.mkdir()
    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(jqc, "OUTPUTS_DIR", outputs)

    for code in ("7011", "7012"):
        save_jquants_daily_bars_cache(
            code,
            [dict(b) for b in _jp_bars()],
            source="local_fixture",
            fetched_at="2026-05-24T12:00:00+00:00",
            generated_at="2026-05-24T12:00:05+00:00",
        )

    cfg = tmp_path / "config"
    cfg.mkdir()
    peer_map = cfg / "peer_map.yaml"
    peer_map.write_text(
        'peer_map:\n  "7011":\n    - "7012"\n  AAPL:\n    - MSFT\n',
        encoding="utf-8",
    )

    report = build_peer_sync_cache_only_report(path_base=tmp_path, peer_map_path=peer_map)
    anchors = {row.get("anchor_symbol") for row in report.pairs}
    assert "7011" in anchors
    jp_pair = next(r for r in report.pairs if r.get("anchor_symbol") == "7011")
    assert jp_pair.get("status") != "missing_cache"


def test_sample_quality_fresh_logs_reason() -> None:
    sq = _sample_quality(
        0,
        skipped_reasons={"insufficient_future_bars": 16},
        signal_rows=16,
    )
    assert sq["status"] == "empty"
    assert "too recent" in sq["reason"]


def test_peer_sync_forward_missing_log_graceful(tmp_path: Path) -> None:
    missing = tmp_path / "observation_log.jsonl"
    report = compute_peer_sync_forward_join(observation_path=missing)
    assert report["peer_sync_at_t"]["status"] == "missing_observation_log"
    assert report["rows_matched"] == 0


def test_cli_peer_sync_forward_missing_log_exit_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    import invis_alpha_os.cli.main as cli_main

    outputs = tmp_path / "outputs"
    outputs.mkdir()
    monkeypatch.setattr(cli_main, "OUTPUTS_DIR", outputs)

    runner = CliRunner()
    result = runner.invoke(cli_main.app, ["validate", "peer-sync-forward-returns"])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "missing_observation_log" in result.stdout


def test_try_load_bars_jp_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.config.paths as config_paths
    import invis_alpha_os.data.jquants_daily_bars_cache as jqc
    from invis_alpha_os.data.jquants_daily_bars_cache import save_jquants_daily_bars_cache

    outputs = tmp_path / "outputs"
    outputs.mkdir()
    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(jqc, "OUTPUTS_DIR", outputs)
    save_jquants_daily_bars_cache(
        "7011",
        [dict(b) for b in _jp_bars()],
        source="local_fixture",
        fetched_at="2026-05-24T12:00:00+00:00",
        generated_at="2026-05-24T12:00:05+00:00",
    )
    loaded = try_load_bars_for_peer_sync("7011")
    assert loaded is not None
    assert loaded[1] == "jp_cache"
