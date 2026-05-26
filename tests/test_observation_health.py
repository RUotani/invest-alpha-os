"""Tests for read-only observation health report (Wave B)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.observation.us_peer_sync_note import build_us_peer_sync_observation_note
from invis_alpha_os.observation.us_signal_note import build_us_signal_observation_note
from invis_alpha_os.product.observation_health import (
    _dedupe_next_commands,
    build_observation_health_report,
    format_observation_health_markdown,
)
from invis_alpha_os.signals.peer_sync import peer_sync_status_explanation


def _patch_outputs_dir(monkeypatch: pytest.MonkeyPatch, outputs: Path) -> None:
    import invis_alpha_os.config.paths as config_paths
    import invis_alpha_os.product.observation_health as observation_health
    import invis_alpha_os.product.portfolio_observation_summary as portfolio_summary
    import invis_alpha_os.product.portfolio_readiness as portfolio_readiness

    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(observation_health, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(portfolio_summary, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(portfolio_readiness, "OUTPUTS_DIR", outputs)


def test_dedupe_next_commands() -> None:
    assert _dedupe_next_commands(["a", "b", "a", "c"]) == ["a", "b", "c"]


def test_observation_health_next_commands_deduped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    obs = outputs / "observation_log" / "observation_log.jsonl"
    svc = ObservationService(observation_path=obs, outcome_path=tmp_path / "outcome.jsonl")
    note = build_us_signal_observation_note({"status": "ok", "momentum_label": "neutral", "last_date": "2024-04-10"})
    svc.log_observation("MSFT", note)
    _patch_outputs_dir(monkeypatch, outputs)

    import invis_alpha_os.data.us_daily_bars_cache as usc
    from invis_alpha_os.data.us_daily_bars_cache import save_us_daily_bars_cache
    from invis_alpha_os.signals.momentum import load_bars_json_file

    repo = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)
    bars = load_bars_json_file(repo / "tests" / "fixtures" / "us_daily_bars" / "MSFT.json")
    save_us_daily_bars_cache(
        "MSFT",
        [dict(b) for b in bars],
        asset_class="us_equity",
        source="local_fixture",
        fetched_at="2026-05-24T12:00:00+00:00",
        generated_at="2026-05-24T12:00:05+00:00",
    )

    report = build_observation_health_report(path_base=tmp_path, observation_path=obs)
    cmds = report.next_commands
    assert len(cmds) == len(set(cmds))
    assert cmds.count(".venv/bin/python -m invis_alpha_os.cli.main log us-signals-summary") == 1
    assert any("jp-peer-sync-readiness" in c for c in cmds)


def test_observation_health_thin_forward_adds_post_refresh_smoke(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import invis_alpha_os.product.post_p10_refresh_smoke as smoke_mod
    import invis_alpha_os.product.us_forward_return_validation as fwd_mod

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    obs = outputs / "observation_log" / "observation_log.jsonl"
    svc = ObservationService(observation_path=obs, outcome_path=tmp_path / "outcome.jsonl")
    note = build_us_signal_observation_note({"status": "ok", "momentum_label": "neutral", "last_date": "2024-04-10"})
    svc.log_observation("MSFT", note)
    _patch_outputs_dir(monkeypatch, outputs)

    monkeypatch.setattr(
        fwd_mod,
        "compute_us_forward_returns",
        lambda **kwargs: {
            "rows_matched": 3,
            "sample_quality": {"status": "thin", "reason": "below threshold"},
        },
    )
    monkeypatch.setattr(
        smoke_mod,
        "build_post_refresh_hints_light",
        lambda **kwargs: {"docs_163_hard_pass": True, "skip_pattern": "mixed"},
    )

    report = build_observation_health_report(path_base=tmp_path, observation_path=obs)
    assert any("post-refresh-smoke" in c for c in report.next_commands)
    assert any("p3-horizon-timeline" in c and "horizon-rows 100" in c for c in report.next_commands)
    assert not any(
        c.startswith("weekly-us-observation --write-observation-log") for c in report.next_commands
    )


def test_peer_sync_status_explanation_known() -> None:
    assert "observation" in peer_sync_status_explanation("in_sync").lower()
    assert "cache" in peer_sync_status_explanation("missing_cache").lower()


def test_observation_health_missing_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    _patch_outputs_dir(monkeypatch, outputs)
    report = build_observation_health_report(path_base=tmp_path)
    d = report.to_dict()
    assert d["us_signals"]["status"] == "missing"
    assert d["log_integrity"]["status"] == "missing"
    assert any("write-observation-log" in c for c in d["next_commands"])


def test_observation_health_malformed_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    obs = outputs / "observation_log" / "observation_log.jsonl"
    obs.write_text("{not json\n", encoding="utf-8")
    _patch_outputs_dir(monkeypatch, outputs)
    report = build_observation_health_report(path_base=tmp_path, observation_path=obs)
    assert report.log_integrity["json_parse_errors"] == 1


def test_observation_health_with_us_signal_row(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    obs = outputs / "observation_log" / "observation_log.jsonl"
    svc = ObservationService(observation_path=obs, outcome_path=tmp_path / "outcome.jsonl")
    note = build_us_signal_observation_note({"status": "ok", "momentum_label": "neutral"})
    svc.log_observation("MSFT", note)
    _patch_outputs_dir(monkeypatch, outputs)
    report = build_observation_health_report(path_base=tmp_path, observation_path=obs)
    assert report.us_signals["us_signal_rows"] == 1


def test_observation_health_markdown_repeat_signals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from invis_alpha_os.product.observation_health import format_observation_health_markdown

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    obs = outputs / "observation_log" / "observation_log.jsonl"
    svc = ObservationService(observation_path=obs, outcome_path=tmp_path / "outcome.jsonl")
    note = build_us_signal_observation_note({"status": "ok", "momentum_label": "neutral", "last_date": "2024-04-10"})
    svc.log_observation("MSFT", note)
    svc.log_observation("MSFT", note)
    _patch_outputs_dir(monkeypatch, outputs)
    report = build_observation_health_report(path_base=tmp_path, observation_path=obs)
    md = format_observation_health_markdown(report)
    assert "repeat_signal_count" in md
    assert "Portfolio readiness" in md
    assert "research_checklist" in md.lower() or "Research checklist" in md


def test_observation_health_markdown_p1_linkage_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from invis_alpha_os.product.observation_health import format_observation_health_markdown

    outputs = tmp_path / "outputs"
    (outputs / "shadow_portfolio").mkdir(parents=True)
    shadow = outputs / "shadow_portfolio" / "positions.jsonl"
    shadow.write_text(
        '{"id":"s1","symbol":"MSFT","quantity":1.0,"thesis_evidence_ids":[],"tags":[]}\n',
        encoding="utf-8",
    )
    _patch_outputs_dir(monkeypatch, outputs)
    report = build_observation_health_report(path_base=tmp_path)
    md = format_observation_health_markdown(report)
    assert "p1_linkage_hint" in md


def test_observation_health_enriched_forward_checklist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import invis_alpha_os.data.us_daily_bars_cache as usc

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    obs = outputs / "observation_log" / "observation_log.jsonl"
    svc = ObservationService(observation_path=obs, outcome_path=tmp_path / "outcome.jsonl")
    note = build_us_signal_observation_note({"status": "ok", "momentum_label": "neutral", "last_date": "2024-04-10"})
    svc.log_observation("MSFT", note)
    _patch_outputs_dir(monkeypatch, outputs)
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

    report = build_observation_health_report(path_base=tmp_path, observation_path=obs)
    categories = {
        item.get("category")
        for item in report.us_signals.get("research_checklist") or []
        if isinstance(item, dict)
    }
    assert (
        "thin_forward_validation" in categories
        or "forward_fresh_log" in categories
        or "repeat_signal" in categories
    )


def test_observation_health_tier1_missing_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from invis_alpha_os.product.observation_health import format_observation_health_markdown

    outputs = tmp_path / "outputs"
    outputs.mkdir()
    _patch_outputs_dir(monkeypatch, outputs)
    report = build_observation_health_report(path_base=tmp_path)
    md = format_observation_health_markdown(report)
    if report.tier1_missing:
        assert "tier-1 cache gaps" in md
        assert report.tier1_missing[0] in md


def test_observation_health_includes_peer_sync_forward(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import invis_alpha_os.data.us_daily_bars_cache as usc
    from invis_alpha_os.data.us_daily_bars_cache import save_us_daily_bars_cache
    from invis_alpha_os.signals.momentum import load_bars_json_file

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    obs = outputs / "observation_log" / "observation_log.jsonl"
    _patch_outputs_dir(monkeypatch, outputs)
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)

    repo = Path(__file__).resolve().parents[1]
    bars = load_bars_json_file(repo / "tests" / "fixtures" / "us_daily_bars" / "MSFT.json")
    event_date = bars[-21]["date"][:10]
    save_us_daily_bars_cache(
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
    obs.write_text(
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

    report = build_observation_health_report(path_base=tmp_path, observation_path=obs)
    assert report.peer_sync_forward is not None
    assert report.peer_sync_forward["rows_matched"] == 1
    assert report.peer_sync_forward["peer_sync_at_t"]["status"] == "joined"

    md = format_observation_health_markdown(report)
    assert "Peer sync forward" in md
    assert "rows_matched: 1" in md

    payload = report.to_dict()
    assert payload["peer_sync_forward"]["rows_matched"] == 1


def test_cli_snapshot_observation_health(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    import invis_alpha_os.cli.main as cli_main

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    (outputs / "observation_log" / "observation_log.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setattr(cli_main, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(cli_main, "OUTPUTS_DIR", outputs)
    runner = CliRunner()
    result = runner.invoke(cli_main.app, ["snapshot", "observation-health", "--format", "json"])
    assert result.exit_code == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert "us_signals" in payload
    assert "repeat_summary" in payload
    assert "repeat_by_symbol" in payload["repeat_summary"]
    assert "post_refresh_hints" in payload


def test_observation_health_post_refresh_hints_in_markdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from invis_alpha_os.product.observation_health import format_observation_health_markdown

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    (outputs / "observation_log" / "observation_log.jsonl").write_text("", encoding="utf-8")
    _patch_outputs_dir(monkeypatch, outputs)
    report = build_observation_health_report(path_base=tmp_path)
    md = format_observation_health_markdown(report)
    assert "Post-refresh hints" in md


def test_observation_health_forward_p3_actions_in_markdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from invis_alpha_os.product.observation_health import format_observation_health_markdown

    outputs = tmp_path / "outputs"
    (outputs / "observation_log").mkdir(parents=True)
    (outputs / "observation_log" / "observation_log.jsonl").write_text("", encoding="utf-8")
    _patch_outputs_dir(monkeypatch, outputs)
    report = build_observation_health_report(path_base=tmp_path)
    md = format_observation_health_markdown(report)
    hints = report.post_refresh_hints or {}
    if hints.get("recommended_actions"):
        assert "forward_p3_action" in md
