"""Tests for docs/154 portfolio readiness rubric (read-only)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.observation.us_signal_note import build_us_signal_observation_note
from invis_alpha_os.product.portfolio_readiness import evaluate_portfolio_readiness


def _patch_outputs(monkeypatch: pytest.MonkeyPatch, outputs: Path) -> None:
    import invis_alpha_os.config.paths as config_paths
    import invis_alpha_os.product.portfolio_readiness as readiness_mod

    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(readiness_mod, "OUTPUTS_DIR", outputs)


def test_portfolio_readiness_default_path_base_does_not_crash() -> None:
    report = evaluate_portfolio_readiness()
    assert "milestones" in report
    assert report.get("state_percent_human_accepted") == 40


def test_portfolio_readiness_loads_human_acceptance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "portfolio_observation_acceptance.yaml").write_text(
        "human_accepted_percent: 25\naccepted_tier: P0\n",
        encoding="utf-8",
    )
    _patch_outputs(monkeypatch, tmp_path / "outputs")
    report = evaluate_portfolio_readiness(path_base=tmp_path)
    assert report["state_percent_human_accepted"] == 25
    assert report["state_percent_locked"] is False


def test_portfolio_readiness_p1_passes_with_resolved_links(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    (outputs / "shadow_portfolio").mkdir(parents=True)
    obs = outputs / "observation_log" / "observation_log.jsonl"
    shadow = outputs / "shadow_portfolio" / "positions.jsonl"
    svc = ObservationService(observation_path=obs, outcome_path=tmp_path / "outcome.jsonl")
    note = build_us_signal_observation_note(
        {"status": "ok", "momentum_label": "neutral", "last_date": "2026-05-22"}
    )
    entry = svc.log_observation("MSFT", note)
    shadow.write_text(
        json.dumps(
            {
                "id": "shadow-msft-1",
                "symbol": "MSFT",
                "quantity": 1.0,
                "thesis_evidence_ids": [entry.id],
                "tags": ["theme:observe-only"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    _patch_outputs(monkeypatch, outputs)
    report = evaluate_portfolio_readiness(path_base=tmp_path, observation_path=obs, shadow_path=shadow)
    p1 = next(m for m in report["milestones"] if m["id"] == "P1")
    assert p1["passed"] is True
    assert report.get("p1_linkage_hint") is None
    assert report["accepted_tier"] in {"P0+P1", "P0-P2", "P0-P3"}


def test_portfolio_readiness_p1_linkage_hint_when_unlinked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outputs = tmp_path / "outputs"
    (outputs / "shadow_portfolio").mkdir(parents=True)
    shadow = outputs / "shadow_portfolio" / "positions.jsonl"
    shadow.write_text(
        '{"id":"s1","symbol":"MSFT","quantity":1.0,"thesis_evidence_ids":[],"tags":[]}\n',
        encoding="utf-8",
    )
    _patch_outputs(monkeypatch, outputs)
    report = evaluate_portfolio_readiness(path_base=tmp_path, shadow_path=shadow)
    assert report.get("p1_linkage_hint")
    p1 = next(m for m in report["milestones"] if m["id"] == "P1")
    assert p1["passed"] is False


def test_portfolio_readiness_shadow_seed_hint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    examples = tmp_path / "config" / "examples"
    examples.mkdir(parents=True)
    (examples / "shadow_portfolio_positions.example.jsonl").write_text(
        '{"id":"s1","symbol":"MSFT","quantity":1.0,"thesis_evidence_ids":[]}\n',
        encoding="utf-8",
    )
    _patch_outputs(monkeypatch, tmp_path / "outputs")
    report = evaluate_portfolio_readiness(path_base=tmp_path)
    assert report.get("shadow_seed_hint")


def test_portfolio_readiness_p0_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    _patch_outputs(monkeypatch, outputs)
    report = evaluate_portfolio_readiness(path_base=tmp_path)
    assert report["accepted_tier"] == "P0"
    assert report["accepted_tier_label"] == "P0 only (CLI ready)"
    assert report["suggested_percent"] == 25
    assert report["state_percent_locked"] is True
    assert report.get("state_percent_human_accepted") is None
    p1 = next(m for m in report["milestones"] if m["id"] == "P1")
    assert p1["passed"] is False
    assert p1["label"] == "Observation linkage"
    assert report["next_milestone"]["id"] == "P1"


def test_portfolio_readiness_p3_blocked_on_stale_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import invis_alpha_os.data.us_daily_bars_cache as usc

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    obs = outputs / "observation_log" / "observation_log.jsonl"
    svc = ObservationService(observation_path=obs, outcome_path=tmp_path / "outcome.jsonl")
    note = build_us_signal_observation_note(
        {"status": "ok", "momentum_label": "neutral", "last_date": "2026-05-22"}
    )
    svc.log_observation("MSFT", note)
    _patch_outputs(monkeypatch, outputs)
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

    report = evaluate_portfolio_readiness(path_base=tmp_path, observation_path=obs)
    p3 = next(m for m in report["milestones"] if m["id"] == "P3")
    assert p3["passed"] is False
    assert "cache" in p3["detail"].lower() or "empty" in p3["detail"].lower() or "thin" in p3["detail"].lower()


def test_compute_us_signal_weekly_trend_growing() -> None:
    from invis_alpha_os.product.weekly_us_observation import compute_us_signal_weekly_trend

    rows = [
        {"created_at": "2026-05-10T12:00:00+00:00"},
        {"created_at": "2026-05-17T12:00:00+00:00"},
        {"created_at": "2026-05-18T12:00:00+00:00"},
    ]
    trend = compute_us_signal_weekly_trend(rows)
    assert trend["status"] in {"growing", "flat", "insufficient_history"}
    assert trend["latest_week_count"] >= 1
