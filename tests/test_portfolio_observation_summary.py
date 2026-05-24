"""Read-only portfolio ↔ observation summary (no writes)."""

from __future__ import annotations

from pathlib import Path

import pytest

from invis_alpha_os.core.jsonl_store import JsonlStore
from invis_alpha_os.core.models import ObservationLogEntry, ShadowPosition
from invis_alpha_os.product.portfolio_observation_summary import (
    build_portfolio_observation_summary,
    format_portfolio_observation_summary_markdown,
)


def test_build_portfolio_observation_summary_links(tmp_path: Path) -> None:
    obs_path = tmp_path / "observation_log.jsonl"
    shadow_path = tmp_path / "positions.jsonl"
    obs_store = JsonlStore(
        path=obs_path,
        encode=lambda x: {
            "id": x.id,
            "created_at": x.created_at,
            "symbol": x.symbol,
            "note": x.note,
            "evidence_ids": x.evidence_ids,
            "tags": x.tags,
        },
        decode=lambda d: ObservationLogEntry(
            id=d["id"],
            created_at=d.get("created_at"),
            symbol=d.get("symbol"),
            note=d.get("note", ""),
            evidence_ids=list(d.get("evidence_ids", [])),
            tags=list(d.get("tags", [])),
        ),
    )
    row = ObservationLogEntry(symbol="AAPL", note="test")
    obs_store.append(row)

    sh_store = JsonlStore(
        path=shadow_path,
        encode=lambda x: {
            "id": x.id,
            "created_at": x.created_at,
            "symbol": x.symbol,
            "quantity": x.quantity,
            "entry_price": x.entry_price,
            "entry_date": x.entry_date,
            "thesis_evidence_ids": x.thesis_evidence_ids,
            "tags": x.tags,
            "extra": x.extra,
        },
        decode=lambda d: ShadowPosition(
            id=d["id"],
            created_at=d.get("created_at"),
            symbol=d.get("symbol", ""),
            quantity=float(d.get("quantity", 0)),
            thesis_evidence_ids=list(d.get("thesis_evidence_ids", [])),
            tags=list(d.get("tags", [])),
            extra=dict(d.get("extra", {})),
        ),
    )
    sh_store.append(
        ShadowPosition(
            symbol="AAPL",
            quantity=1.0,
            thesis_evidence_ids=[row.id, "missing-id"],
            tags=["theme:ai"],
        )
    )

    summary = build_portfolio_observation_summary(
        path_base=tmp_path,
        shadow_path=shadow_path,
        observation_path=obs_path,
    )
    assert summary.shadow_position_count == 1
    assert summary.observation_row_count == 1
    assert summary.positions_with_resolved_links == 1
    assert "missing-id" in summary.unresolved_evidence_ids
    md = format_portfolio_observation_summary_markdown(summary)
    assert "AAPL" in md
    assert summary.by_symbol.get("AAPL") == 1
    assert summary.by_tag.get("theme:ai") == 1


def test_cli_snapshot_portfolio_observation_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    from invis_alpha_os.cli.main import app

    monkeypatch.setattr("invis_alpha_os.cli.main.ROOT_DIR", tmp_path)
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.OUTPUTS_DIR",
        tmp_path / "outputs",
    )
    out = tmp_path / "outputs"
    (out / "shadow_portfolio").mkdir(parents=True)
    (out / "observation_log").mkdir(parents=True)
    (out / "shadow_portfolio" / "positions.jsonl").write_text("", encoding="utf-8")
    (out / "observation_log" / "observation_log.jsonl").write_text("", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app, ["snapshot", "portfolio-observation-summary", "--format", "json"]
    )
    assert result.exit_code == 0
    assert "shadow_position_count" in result.stdout
