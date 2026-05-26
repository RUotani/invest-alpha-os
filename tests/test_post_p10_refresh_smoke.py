"""Tests for post-P10 refresh smoke summary (docs/163)."""

from __future__ import annotations

from pathlib import Path

import pytest

from invis_alpha_os.product.post_p10_refresh_smoke import (
    build_post_p10_refresh_smoke_summary,
    format_post_p10_refresh_smoke_markdown,
    forward_p3_recommended_actions,
)
from invis_alpha_os.product.us_forward_return_validation import (
    classify_forward_skip_pattern,
    forward_p3_progress,
)


def test_classify_forward_skip_pattern_fresh_log() -> None:
    assert (
        classify_forward_skip_pattern(
            {"insufficient_future_bars": 10},
            signal_rows=10,
        )
        == "fresh_log"
    )


def test_forward_p3_progress_label() -> None:
    p = forward_p3_progress(6)
    assert p["samples_needed_for_usable"] == 4
    assert "6/10" in p["progress_label"]
    p_ok = forward_p3_progress(12)
    assert p_ok["samples_needed_for_usable"] == 0
    assert "usable" in p_ok["progress_label"]


def test_forward_p3_recommended_actions_mixed() -> None:
    actions = forward_p3_recommended_actions(
        skip_pattern="mixed",
        tier1_missing=[],
        stale_skips=16,
        forward_matched=0,
    )
    joined = " ".join(actions)
    assert "weekly" in joined.lower() or "gated" in joined.lower()
    assert "stale" in joined.lower() or "cache refresh" in joined.lower()


def test_forward_p3_recommended_actions_insufficient_future_dominant() -> None:
    actions = forward_p3_recommended_actions(
        skip_pattern="mixed",
        tier1_missing=[],
        forward_matched=3,
        resolution_outcomes={
            "insufficient_future_bars": 200,
            "cache_stale_event_after_cache_end": 10,
            "matched": 3,
        },
    )
    joined = " ".join(actions)
    assert "insufficient_future_bars" in joined


def test_forward_p3_recommended_actions_partial_matched() -> None:
    actions = forward_p3_recommended_actions(
        skip_pattern="mixed",
        tier1_missing=[],
        forward_matched=3,
        peer_sync_matched=8,
        stale_skip_by_symbol=[{"symbol": "MSFT", "count": 1}],
    )
    joined = " ".join(actions)
    assert "3/10" in joined
    assert "usable (8 matched)" in joined or "8/10" in joined
    assert "MSFT" in joined


def test_forward_p3_recommended_actions_low_as_of_share() -> None:
    actions = forward_p3_recommended_actions(
        skip_pattern="mixed",
        tier1_missing=[],
        forward_matched=3,
        insufficient_future_share=0.95,
        event_date_source_as_of_share=0.2,
    )
    joined = " ".join(actions)
    assert "event_date_source_as_of_share" in joined
    assert "created_at" in joined


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
    assert "us_forward" in report
    assert "peer_sync_forward" in report
    assert report["us_forward"]["rows_matched"] == report["forward_validation"]["rows_matched"]
    assert report.get("observation_log_lines") == 0
    md = format_post_p10_refresh_smoke_markdown(report)
    assert "Post-P10 refresh smoke" in md
    assert "recommended" in md or report.get("recommended_actions")
