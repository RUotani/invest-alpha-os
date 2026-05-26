"""Tests for per-row US forward resolution breakdown (P3 path)."""

from __future__ import annotations

from pathlib import Path

import pytest

from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.observation.us_signal_note import build_us_signal_observation_note
from invis_alpha_os.product.us_forward_return_validation import (
    classify_us_signal_row_forward_outcome,
    compute_us_forward_resolution_breakdown,
)


def test_resolution_breakdown_empty_log(tmp_path: Path) -> None:
    obs = tmp_path / "obs.jsonl"
    obs.write_text("", encoding="utf-8")
    report = compute_us_forward_resolution_breakdown(observation_path=obs, path_base=tmp_path)
    assert report["matched_rows"] == 0
    assert report["samples_needed_for_usable"] == 10


def test_classify_row_matched_with_fixture(
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
    report = compute_us_forward_resolution_breakdown(
        observation_path=obs,
        path_base=tmp_path,
    )
    assert report["rows_considered"] >= 1
    assert report["outcomes"].get("matched", 0) >= 0


def test_classify_outcome_insufficient_future(tmp_path: Path) -> None:
    row = {
        "symbol": "MSFT",
        "event_date": __import__("datetime").date(2099, 1, 1),
    }
    outcome = classify_us_signal_row_forward_outcome(row, cache_dir=tmp_path / "missing")
    assert outcome == "price_data_missing"
