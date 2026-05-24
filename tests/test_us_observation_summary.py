"""Tests for US observation usefulness report (cache-only)."""

from __future__ import annotations

from pathlib import Path

import pytest

from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.observation.us_signal_note import build_us_signal_observation_note
from invis_alpha_os.reports.us_observation_summary import (
    build_us_observation_usefulness_payload,
    render_us_observation_summary_markdown,
)


def test_us_observation_summary_missing_log(tmp_path: Path) -> None:
    payload = build_us_observation_usefulness_payload(path_base=tmp_path)
    assert payload["observation_summary"]["status"] == "missing"
    md = render_us_observation_summary_markdown(path_base=tmp_path)
    assert "observation_log: missing" in md


def test_us_observation_summary_enriched_checklist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import invis_alpha_os.data.us_daily_bars_cache as usc

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    obs = outputs / "observation_log" / "observation_log.jsonl"
    svc = ObservationService(observation_path=obs, outcome_path=tmp_path / "outcome.jsonl")
    note = build_us_signal_observation_note({"status": "ok", "momentum_label": "neutral", "last_date": "2024-04-10"})
    svc.log_observation("MSFT", note)
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

    payload = build_us_observation_usefulness_payload(path_base=tmp_path)
    obs_summary = payload["observation_summary"]
    assert obs_summary["us_signal_rows"] == 1
    categories = {item.get("category") for item in obs_summary.get("research_checklist") or []}
    assert "thin_forward_validation" in categories or obs_summary.get("weekly_trend")
