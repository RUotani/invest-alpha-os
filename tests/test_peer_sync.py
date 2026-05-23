"""Tests for observation-only peer_sync (cache-only; no HTTP)."""

from __future__ import annotations

from pathlib import Path

import pytest

from invis_alpha_os.signals.momentum import DailyBar
from invis_alpha_os.signals.peer_sync import (
    align_close_series,
    evaluate_peer_map,
    evaluate_peer_pair,
    load_peer_map,
    trailing_correlation,
    trailing_return_spread,
)


def _bars(closes: list[float], start: str = "2026-01-01") -> list[DailyBar]:
    out: list[DailyBar] = []
    y, m, d = (int(start[0:4]), int(start[5:7]), int(start[8:10]))
    for i, c in enumerate(closes):
        day = d + i
        month = m
        year = y
        while day > 28:
            day -= 28
            month += 1
            if month > 12:
                month = 1
                year += 1
        date = f"{year:04d}-{month:02d}-{day:02d}"
        out.append(
            {
                "date": date,
                "open": c,
                "high": c,
                "low": c,
                "close": c,
                "volume": 1.0,
            }
        )
    return out


def test_load_peer_map(tmp_path: Path) -> None:
    cfg = tmp_path / "peer_map.yaml"
    cfg.write_text(
        'peer_map:\n  AAPL:\n    - MSFT\n    - GOOGL\n',
        encoding="utf-8",
    )
    m = load_peer_map(cfg)
    assert m == {"AAPL": ["MSFT", "GOOGL"]}


def test_align_close_series_intersection() -> None:
    a = _bars([100, 101, 102], start="2026-01-01")
    b = _bars([200, 201], start="2026-01-02")
    ac, bc = align_close_series(a, b)
    assert len(ac) == len(bc) == 2
    assert ac[0] == 101 and bc[0] == 200


def test_trailing_return_spread_and_correlation() -> None:
    anchor = [100 + i for i in range(30)]
    peer = [200 + i * 0.5 for i in range(30)]
    spread = trailing_return_spread(anchor, peer, window=20)
    assert spread is not None
    assert spread > 0
    ret_a = [0.01 + (i % 3) * 0.0001 for i in range(25)]
    ret_b = [0.01 + (i % 3) * 0.0001 for i in range(25)]
    corr = trailing_correlation(ret_a, ret_b, window=20)
    assert corr is not None
    assert corr > 0.99


def test_evaluate_peer_pair_in_sync() -> None:
    closes = [100 + i * 0.5 for i in range(40)]
    a = _bars(closes)
    b = _bars([x * 2 for x in closes])
    result = evaluate_peer_pair("AAPL", "MSFT", a, b, window_days=20)
    assert result.status == "in_sync"
    assert result.return_spread is not None
    assert abs(result.return_spread) < 0.01


def test_evaluate_peer_pair_diverged() -> None:
    a = _bars([100 + i * 2 for i in range(40)])
    b = _bars([100 + i * 0.1 for i in range(40)])
    result = evaluate_peer_pair("AAPL", "MSFT", a, b, window_days=20)
    assert result.status == "diverged_anchor_outperform"


def test_evaluate_peer_map_missing_cache() -> None:
    bars = {"AAPL": _bars([100 + i for i in range(30)])}
    rows = evaluate_peer_map({"AAPL": ["MSFT"]}, bars, window_days=20)
    assert len(rows) == 1
    assert rows[0].status == "missing_cache"


def test_cli_validate_peer_sync(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    from invis_alpha_os.cli.main import app

    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "peer_map.yaml").write_text(
        'peer_map:\n  AAA:\n    - BBB\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("invis_alpha_os.cli.main.CONFIG_DIR", cfg)
    monkeypatch.setattr("invis_alpha_os.cli.main.ROOT_DIR", tmp_path)

    runner = CliRunner()
    result = runner.invoke(app, ["validate", "peer-sync", "--format", "json"])
    assert result.exit_code == 0
    assert "pairs" in result.stdout
