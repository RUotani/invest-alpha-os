"""Tests for read-only portfolio exposure by signal/veto bucket."""

from __future__ import annotations

from pathlib import Path

from invis_alpha_os.core.jsonl_store import JsonlStore
from invis_alpha_os.core.models import ShadowPosition
from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.observation.us_signal_note import build_us_signal_observation_note
from invis_alpha_os.product.portfolio_exposure_by_signal_veto import (
    VETO_BUCKET_CLEAR,
    VETO_BUCKET_UNKNOWN,
    VETO_BUCKET_VETO,
    build_observation_report_usefulness_hints,
    build_portfolio_exposure_by_signal_veto,
    format_portfolio_exposure_weekly_one_liner,
    format_portfolio_exposure_by_signal_veto_markdown,
    latest_us_signal_context_by_symbol,
)


def test_latest_us_signal_context_285a_veto(tmp_path: Path) -> None:
    obs = tmp_path / "observation_log.jsonl"
    svc = ObservationService(observation_path=obs, outcome_path=tmp_path / "outcome.jsonl")
    note = build_us_signal_observation_note(
        {"status": "ok", "momentum_label": "weak"},
        veto_triggered=True,
        veto_rules=["low_volume"],
    )
    svc.log_observation("285A", note)
    ctx = latest_us_signal_context_by_symbol(obs)
    assert ctx["285A"]["veto_bucket"] == VETO_BUCKET_VETO
    assert ctx["285A"]["momentum_label"] == "weak"


def test_portfolio_exposure_buckets(tmp_path: Path) -> None:
    obs = tmp_path / "observation_log.jsonl"
    shadow = tmp_path / "positions.jsonl"
    svc = ObservationService(observation_path=obs, outcome_path=tmp_path / "outcome.jsonl")
    svc.log_observation(
        "MSFT",
        build_us_signal_observation_note(
            {"status": "ok", "momentum_label": "neutral"},
            veto_triggered=False,
        ),
    )
    svc.log_observation(
        "285A",
        build_us_signal_observation_note(
            {"status": "ok", "momentum_label": "weak"},
            veto_triggered=True,
        ),
    )
    store = JsonlStore(
        path=shadow,
        encode=lambda x: {
            "id": x.id,
            "created_at": x.created_at,
            "symbol": x.symbol,
            "quantity": x.quantity,
            "thesis_evidence_ids": x.thesis_evidence_ids,
            "tags": x.tags,
            "extra": x.extra,
        },
        decode=lambda d: ShadowPosition(
            id=d["id"],
            symbol=d.get("symbol", ""),
            quantity=float(d.get("quantity", 0)),
            thesis_evidence_ids=list(d.get("thesis_evidence_ids", [])),
            tags=list(d.get("tags", [])),
            extra=dict(d.get("extra", {})),
        ),
    )
    store.append(ShadowPosition(symbol="MSFT", quantity=10.0))
    store.append(ShadowPosition(symbol="285A", quantity=5.0))
    store.append(ShadowPosition(symbol="UNKNOWN", quantity=1.0))

    report = build_portfolio_exposure_by_signal_veto(
        path_base=tmp_path,
        shadow_path=shadow,
        observation_path=obs,
    )
    assert report["shadow_position_count"] == 3
    by_veto = report["by_veto_bucket"]
    assert by_veto[VETO_BUCKET_VETO]["position_count"] == 1
    assert by_veto[VETO_BUCKET_CLEAR]["position_count"] == 1
    assert by_veto[VETO_BUCKET_UNKNOWN]["position_count"] == 1
    md = format_portfolio_exposure_by_signal_veto_markdown(report)
    assert "## Portfolio exposure" in md
    assert "285A" in md or "weak" in md


def test_format_portfolio_exposure_weekly_one_liner_empty() -> None:
    assert format_portfolio_exposure_weekly_one_liner({"shadow_position_count": 0}) == ""


def test_format_portfolio_exposure_weekly_one_liner() -> None:
    line = format_portfolio_exposure_weekly_one_liner(
        {
            "shadow_position_count": 2,
            "by_veto_bucket": {
                VETO_BUCKET_VETO: {"position_count": 1},
                VETO_BUCKET_CLEAR: {"position_count": 1},
            },
        }
    )
    assert line.startswith("- portfolio_exposure:")
    assert "veto_triggered=1" in line


def test_report_usefulness_hints_include_exposure_cli() -> None:
    hints = build_observation_report_usefulness_hints(
        shadow_position_count=2,
        p3_samples_needed=9,
    )
    assert any("portfolio-exposure-by-signal-veto" in h for h in hints)
    assert any("p3-path-to-usable" in h for h in hints)
    assert any("forward-p3-status" in h for h in hints)
    assert any("ops-smoke" in h for h in hints)


def test_portfolio_exposure_empty_shadow(tmp_path: Path) -> None:
    obs = tmp_path / "observation_log.jsonl"
    obs.write_text("", encoding="utf-8")
    shadow = tmp_path / "positions.jsonl"
    shadow.write_text("", encoding="utf-8")
    report = build_portfolio_exposure_by_signal_veto(
        path_base=tmp_path,
        shadow_path=shadow,
        observation_path=obs,
    )
    assert report["status"] == "empty"
