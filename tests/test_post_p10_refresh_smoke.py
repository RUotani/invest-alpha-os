"""Tests for post-P10 refresh smoke summary (docs/163)."""

from __future__ import annotations

from pathlib import Path

import pytest

from invis_alpha_os.product.post_p10_refresh_smoke import (
    build_post_p10_refresh_smoke_summary,
    format_post_p10_refresh_smoke_markdown,
)
from invis_alpha_os.product.us_forward_return_validation import classify_forward_skip_pattern


def test_classify_forward_skip_pattern_fresh_log() -> None:
    assert (
        classify_forward_skip_pattern(
            {"insufficient_future_bars": 10},
            signal_rows=10,
        )
        == "fresh_log"
    )


def test_classify_forward_skip_pattern_stale_cache() -> None:
    assert (
        classify_forward_skip_pattern(
            {"cache_stale_event_after_cache_end": 8},
            signal_rows=10,
        )
        == "stale_cache"
    )


def test_post_refresh_smoke_builds_checks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.config.paths as config_paths
    import invis_alpha_os.product.post_p10_refresh_smoke as smoke_mod

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    (outputs / "market_data" / "us_daily_bars").mkdir(parents=True)
    (outputs / "observation_log" / "observation_log.jsonl").write_text("", encoding="utf-8")
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "peer_map.yaml").write_text("peer_map:\n  MSFT:\n    - MSFT\n", encoding="utf-8")
    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(config_paths, "CONFIG_DIR", cfg)
    monkeypatch.setattr(smoke_mod, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(
        smoke_mod,
        "build_us_universe_expansion_report",
        lambda **_kw: {"tier_1_missing_refresh_order": []},
    )

    report = build_post_p10_refresh_smoke_summary(path_base=tmp_path)
    assert report["observation_only"] is True
    assert isinstance(report.get("checks"), list)
    md = format_post_p10_refresh_smoke_markdown(report)
    assert "Post-P10 refresh smoke" in md
