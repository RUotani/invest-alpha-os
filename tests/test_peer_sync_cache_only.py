"""Tests for cache-only peer_sync report."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from invis_alpha_os.product.peer_sync_cache_only import (
    _summary_counts,
    build_peer_sync_cache_only_report,
    format_peer_sync_cache_only_json,
    format_peer_sync_cache_only_markdown,
)


def test_summary_counts() -> None:
    pairs = [
        {"status": "in_sync"},
        {"status": "in_sync"},
        {"status": "missing_cache"},
    ]
    assert _summary_counts(pairs) == {"in_sync": 2, "missing_cache": 1}


def test_build_peer_sync_cache_only_report_missing_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import invis_alpha_os.data.us_daily_bars_cache as usc
    import invis_alpha_os.product.peer_sync_cache_only as psc

    outputs = tmp_path / "outputs"
    outputs.mkdir()
    cfg = tmp_path / "config"
    cfg.mkdir()
    peer_map = cfg / "peer_map.yaml"
    peer_map.write_text('peer_map:\n  MSFT:\n    - GOOGL\n', encoding="utf-8")
    monkeypatch.setattr(psc, "CONFIG_DIR", cfg)
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)

    repo = Path(__file__).resolve().parents[1]
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

    report = build_peer_sync_cache_only_report(path_base=tmp_path, peer_map_path=peer_map)
    assert len(report.pairs) == 1
    assert report.pairs[0]["status"] == "missing_cache"
    assert report.summary.get("missing_cache") == 1
    md = format_peer_sync_cache_only_markdown(report)
    assert "Peer sync (cache-only)" in md
    assert "missing_cache" in md


def test_build_peer_sync_cache_only_report_with_us_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import invis_alpha_os.data.us_daily_bars_cache as usc
    import invis_alpha_os.product.peer_sync_cache_only as psc

    outputs = tmp_path / "outputs"
    outputs.mkdir()
    cfg = tmp_path / "config"
    cfg.mkdir()
    peer_map = cfg / "peer_map.yaml"
    peer_map.write_text('peer_map:\n  MSFT:\n    - MSFT\n', encoding="utf-8")
    monkeypatch.setattr(psc, "CONFIG_DIR", cfg)
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)

    repo = Path(__file__).resolve().parents[1]
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

    report = build_peer_sync_cache_only_report(path_base=tmp_path, peer_map_path=peer_map)
    assert len(report.pairs) == 1
    assert report.pairs[0]["status"] in {"in_sync", "diverged_peer_outperform", "diverged_peer_underperform", "insufficient_data"}
    payload = json.loads(format_peer_sync_cache_only_json(report))
    assert payload["summary"]
    assert payload["next_commands"]
