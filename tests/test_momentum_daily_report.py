"""Main I: daily report momentum sections — cache-only vs mixed (no HTTP, no cache writes)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from invis_alpha_os.reports.momentum_daily import (
    render_momentum_signals_cache_only_section,
    render_momentum_signals_mixed_section,
)


def _write_min_cache(tmp_path: Path, code: str, n: int = 80) -> None:
    cache_dir = tmp_path / "market_data" / "jquants_daily_bars"
    cache_dir.mkdir(parents=True)
    bars = []
    for i in range(n):
        c = 1000.0 + i * 0.1
        bars.append(
            {
                "date": f"2024-01-{(i % 28) + 1:02d}",
                "open": c,
                "high": c + 1.0,
                "low": c - 1.0,
                "close": c,
                "volume": 5000.0,
            }
        )
    payload = {
        "schema_version": 1,
        "code": code,
        "source": "jquants_v2_equities_bars_daily",
        "fetched_at": "2026-01-01T00:00:00+00:00",
        "generated_at": None,
        "bar_count": len(bars),
        "bars": bars,
    }
    (cache_dir / f"{code}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_cache_only_heading_and_skipped_note(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(
        "invis_alpha_os.reports.momentum_daily.load_jp_watchlist_tickers",
        lambda: ["7011", "5802"],
    )
    _write_min_cache(tmp_path, "7011")

    md = render_momentum_signals_cache_only_section()
    assert "## Momentum Signals — Cache Only" in md
    assert "Momentum Score v2" in md
    assert "| Sv2 |" in md
    assert "| HiDist |" in md and "| VolR |" in md and "| Risk |" in md
    assert "No synthetic bars" in md or "**No synthetic bars**" in md
    assert "**Skipped (no local cache file):**" in md
    assert "5802" in md
    assert "| 7011 |" in md
    assert "| synthetic |" not in md
    assert "Observation only" in md


def test_cache_only_does_not_call_synthetic_bars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(
        "invis_alpha_os.reports.momentum_daily.load_jp_watchlist_tickers",
        lambda: ["7011", "5802"],
    )
    _write_min_cache(tmp_path, "7011")
    spy = MagicMock()
    monkeypatch.setattr("invis_alpha_os.reports.momentum_daily.synthetic_bars_for_code", spy)
    render_momentum_signals_cache_only_section()
    spy.assert_not_called()


def test_mixed_section_keeps_fallback_warnings_and_heading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(
        "invis_alpha_os.reports.momentum_daily.load_jp_watchlist_tickers",
        lambda: ["7011"],
    )
    _write_min_cache(tmp_path, "7011")
    md = render_momentum_signals_mixed_section()
    assert "## Momentum Signals — Mixed / System Validation" in md
    assert "Synthetic fallback" in md
    assert "not actionable" in md.lower()


def test_daily_report_cache_only_before_mixed_section(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Integration: full daily markdown order — cache-only block precedes mixed."""
    from typer.testing import CliRunner

    from invis_alpha_os.cli.main import app
    from invis_alpha_os.config.paths import OUTPUTS_DIR
    from invis_alpha_os.utils.date_utils import today_jst_iso

    monkeypatch.setattr("invis_alpha_os.reports.jquants_watchlist_daily.ROOT_DIR", tmp_path)
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_FROM", "2024-01-01")
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_TO", "2025-12-31")

    r = CliRunner().invoke(app, ["daily"])
    assert r.exit_code == 0
    body = (OUTPUTS_DIR / "reports" / "daily" / f"{today_jst_iso()}.md").read_text(encoding="utf-8")
    i_co = body.index("## Momentum Signals — Cache Only")
    i_mx = body.index("## Momentum Signals — Mixed / System Validation")
    assert i_co < i_mx


def test_cache_only_ranking_row_has_stable_column_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Multiple legacy labels → Key must use comma separators (no stray table pipes)."""

    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(
        "invis_alpha_os.reports.momentum_daily.load_jp_watchlist_tickers",
        lambda: ["7011"],
    )
    cache_dir = tmp_path / "market_data" / "jquants_daily_bars"
    cache_dir.mkdir(parents=True)
    n = 280
    bars = []
    for i in range(n):
        c = 500.0 + i * 0.01
        h = c + 0.05
        v = 5000.0
        if i == n - 1:
            v = 20_000.0
            h = c + 50.0
        bars.append(
            {
                "date": f"2023-{(i % 12) + 1:02d}-15",
                "open": c,
                "high": h,
                "low": c - 1.0,
                "close": c if i < n - 1 else h,
                "volume": v,
            }
        )
    payload = {
        "schema_version": 1,
        "code": "7011",
        "source": "jquants_v2_equities_bars_daily",
        "fetched_at": "2026-01-01T00:00:00+00:00",
        "generated_at": None,
        "bar_count": len(bars),
        "bars": bars,
    }
    (cache_dir / "7011.json").write_text(json.dumps(payload), encoding="utf-8")

    md = render_momentum_signals_cache_only_section()
    assert "| Rank | Code | Sv2 | Key |" in md
    rows = [
        ln
        for ln in md.splitlines()
        if ln.startswith("| ")
        and "7011" in ln
        and ln.rstrip().endswith("| cache |")
        and "Rank | Code |" not in ln
        and ln.strip().startswith("| 1 ")
    ]
    assert len(rows) == 1
    cells = [c.strip() for c in rows[0].strip().split("|") if c.strip() != ""]
    assert len(cells) == 11
