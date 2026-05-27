"""Tests for read-only risk veto observation log summary."""

from __future__ import annotations

import json
from pathlib import Path

from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.observation.us_signal_note import build_us_signal_observation_note
from invis_alpha_os.product.risk_veto_observation_summary import (
    format_risk_veto_observation_summary_markdown,
    summarize_risk_veto_observation_log,
)


def test_summarize_risk_veto_missing_log(tmp_path: Path) -> None:
    summary = summarize_risk_veto_observation_log(tmp_path / "missing.jsonl")
    assert summary["status"] == "missing"
    assert summary["veto_triggered_rows"] == 0


def test_summarize_risk_veto_counts_triggered_rows(tmp_path: Path) -> None:
    obs = tmp_path / "observation_log.jsonl"
    svc = ObservationService(observation_path=obs, outcome_path=tmp_path / "outcome.jsonl")
    note_ok = build_us_signal_observation_note(
        {"status": "ok", "momentum_label": "neutral"},
        veto_triggered=False,
    )
    note_veto = build_us_signal_observation_note(
        {"status": "ok", "momentum_label": "weak"},
        veto_triggered=True,
        veto_rules=["low_volume", "285A_test"],
    )
    svc.log_observation("MSFT", note_ok)
    svc.log_observation("285A", note_veto)

    summary = summarize_risk_veto_observation_log(obs)
    assert summary["status"] == "ok"
    assert summary["us_signal_rows_scanned"] == 2
    assert summary["veto_triggered_rows"] == 1
    assert "285A" in summary["veto_symbols"]
    md = format_risk_veto_observation_summary_markdown(summary)
    assert "## Risk veto" in md
    assert "veto_triggered_rows: 1" in md


def test_summarize_risk_veto_malformed_line_skipped(tmp_path: Path) -> None:
    obs = tmp_path / "observation_log.jsonl"
    obs.write_text("{not json\n", encoding="utf-8")
    summary = summarize_risk_veto_observation_log(obs)
    assert summary["us_signal_rows_scanned"] == 0
