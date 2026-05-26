"""Tests for combined forward P3 status bundle (read-only)."""

from __future__ import annotations

from pathlib import Path

import pytest

from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.observation.us_signal_note import build_us_signal_observation_note
from invis_alpha_os.product.forward_p3_status import (
    build_forward_p3_status_bundle,
    format_forward_p3_status_markdown,
)


def test_forward_p3_status_empty_log(tmp_path: Path) -> None:
    obs = tmp_path / "obs.jsonl"
    obs.write_text("", encoding="utf-8")
    report = build_forward_p3_status_bundle(path_base=tmp_path, observation_path=obs)
    assert report["observation_only"] is True
    assert report["us_forward"]["rows_matched"] == 0
    md = format_forward_p3_status_markdown(report)
    assert "Forward P3 status" in md


def test_forward_p3_status_with_signal_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import invis_alpha_os.config.paths as config_paths
    import invis_alpha_os.data.us_daily_bars_cache as usc
    from invis_alpha_os.data.us_daily_bars_cache import save_us_daily_bars_cache
    from invis_alpha_os.signals.momentum import load_bars_json_file

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    obs = outputs / "observation_log" / "observation_log.jsonl"
    svc = ObservationService(observation_path=obs, outcome_path=tmp_path / "outcome.jsonl")
    note = build_us_signal_observation_note(
        {"status": "ok", "momentum_label": "neutral", "last_date": "2024-04-10"}
    )
    svc.log_observation("MSFT", note)
    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)
    repo = Path(__file__).resolve().parents[1]
    bars = load_bars_json_file(repo / "tests" / "fixtures" / "us_daily_bars" / "MSFT.json")
    save_us_daily_bars_cache(
        "MSFT",
        [dict(b) for b in bars],
        asset_class="us_equity",
        source="local_fixture",
        fetched_at="2026-05-24T12:00:00+00:00",
        generated_at="2026-05-24T12:00:05+00:00",
    )
    report = build_forward_p3_status_bundle(path_base=tmp_path, observation_path=obs)
    assert "p3_progress" in report["us_forward"]
    assert report["us_forward"]["rows_matched"] >= 0
    assert report.get("observation_log_lines") == 1
    assert isinstance(report.get("recommended_actions"), list)


def test_forward_p3_status_markdown_includes_recommended_actions(tmp_path: Path) -> None:
    obs = tmp_path / "obs.jsonl"
    obs.write_text("", encoding="utf-8")
    report = build_forward_p3_status_bundle(path_base=tmp_path, observation_path=obs)
    md = format_forward_p3_status_markdown(report)
    assert "Recommended actions" in md or report["us_forward"]["rows_matched"] == 0


def test_forward_p3_status_includes_stall_diagnosis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import invis_alpha_os.config.paths as config_paths
    import invis_alpha_os.data.us_daily_bars_cache as usc
    from invis_alpha_os.data.us_daily_bars_cache import save_us_daily_bars_cache
    from invis_alpha_os.signals.momentum import load_bars_json_file

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    obs = outputs / "observation_log" / "observation_log.jsonl"
    svc = ObservationService(observation_path=obs, outcome_path=tmp_path / "outcome.jsonl")
    note = build_us_signal_observation_note(
        {"status": "ok", "momentum_label": "neutral", "last_date": "2024-04-10"}
    )
    svc.log_observation("MSFT", note)
    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)
    repo = Path(__file__).resolve().parents[1]
    bars = load_bars_json_file(repo / "tests" / "fixtures" / "us_daily_bars" / "MSFT.json")
    save_us_daily_bars_cache(
        "MSFT",
        [dict(b) for b in bars],
        asset_class="us_equity",
        source="local_fixture",
        fetched_at="2026-05-24T12:00:00+00:00",
        generated_at="2026-05-24T12:00:05+00:00",
    )
    report = build_forward_p3_status_bundle(path_base=tmp_path, observation_path=obs)
    stall = report.get("p3_stall_diagnosis") or {}
    assert stall.get("p3_bucket_counts")
    md = format_forward_p3_status_markdown(report)
    assert "## P3 stall diagnosis" in md
    assert "### P3 buckets" in md
    assert stall.get("why_matched_stuck", {}).get("headline")
    summary = report.get("p3_us_forward_summary") or {}
    assert summary.get("matched_normal") is not None
    assert "p3_buckets" in summary
    assert "## P3 US forward portfolio summary" in md
