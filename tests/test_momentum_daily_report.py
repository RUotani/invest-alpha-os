"""Main I: daily report momentum sections — cache-only vs mixed (no HTTP, no cache writes)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from invis_alpha_os.reports.momentum_daily import (
    classify_watch_note,
    render_momentum_cache_only_for_wire_codes,
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


def _flat_bar_rows(closes: list[float]) -> list[dict]:
    rows: list[dict] = []
    for i, c in enumerate(closes):
        rows.append(
            {
                "date": f"2024-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",
                "open": c,
                "high": c,
                "low": c,
                "close": c,
                "volume": 1000.0,
            }
        )
    return rows


def _write_payload_bars(tmp_path: Path, code: str, bars: list[dict]) -> None:
    cache_dir = tmp_path / "market_data" / "jquants_daily_bars"
    cache_dir.mkdir(parents=True, exist_ok=True)
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
    assert "| Watch |" in md
    assert "| HiDist |" in md and "| VolR |" in md and "| Flag |" in md
    assert "Momentum Score v2 table (concise legend)" in md
    assert "**HiDist:**" in md and "**VolR:**" in md
    assert "### Observations — Momentum (cache-only)" in md
    i_obs = md.index("### Observations — Momentum (cache-only)")
    i_act = md.index("### Action Watchlist — Momentum (observation only)")
    assert i_obs < i_act
    assert "### Action Watchlist — Momentum (observation only)" in md
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


def test_mixed_section_all_rows_cache_no_synthetic_diagnostics_sentence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(
        "invis_alpha_os.reports.momentum_daily.load_jp_watchlist_tickers",
        lambda: ["7011"],
    )
    _write_min_cache(tmp_path, "7011")
    md = render_momentum_signals_mixed_section()
    assert "## Momentum Signals — Mixed / System Validation" in md
    assert "**All rows are cache-backed.**" in md
    assert "Synthetic fallback tickers:" not in md


def test_mixed_section_keeps_fallback_warnings_when_synthetic_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(
        "invis_alpha_os.reports.momentum_daily.load_jp_watchlist_tickers",
        lambda: ["7011", "5802"],
    )
    _write_min_cache(tmp_path, "7011")
    md = render_momentum_signals_mixed_section()
    assert "**Synthetic fallback tickers:**" in md
    assert "diagnostics only" in md.lower()
    assert "**All rows are cache-backed.**" not in md


def test_cache_only_lists_overheat_codes_in_observations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(
        "invis_alpha_os.reports.momentum_daily.load_jp_watchlist_tickers",
        lambda: ["OH11", "ST11"],
    )
    oh = [100.0] * 219 + [100.0 + (i - 218) * (150.0 / 61) for i in range(219, 280)]
    st = [100.0 + i * 0.1 for i in range(280)]
    _write_payload_bars(tmp_path, "OH11", _flat_bar_rows(oh))
    _write_payload_bars(tmp_path, "ST11", _flat_bar_rows(st))
    md = render_momentum_signals_cache_only_section()
    line = next(ln for ln in md.splitlines() if ln.startswith("- **Overheat watch:**"))
    assert "OH11" in line


def test_pullback_watch_note_and_observation_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(
        "invis_alpha_os.reports.momentum_daily.load_jp_watchlist_tickers",
        lambda: ["PB11", "ZX11"],
    )
    pb: list[float] = []
    for i in range(125):
        pb.append(50.0 + i * 0.8)
    peak = pb[-1]
    pb.extend([peak * 0.99, peak * 0.985, peak * 0.98, peak * 0.975, peak * 0.97])
    zx = [100.0 + i * 0.05 for i in range(280)]
    _write_payload_bars(tmp_path, "PB11", _flat_bar_rows(pb))
    _write_payload_bars(tmp_path, "ZX11", _flat_bar_rows(zx))

    md = render_momentum_signals_cache_only_section()
    row_pb = next(
        ln for ln in md.splitlines() if ln.startswith("| ") and "| PB11 |" in ln and "Rank | Code |" not in ln
    )
    assert "| pullback_in_uptrend |" in row_pb
    ob = next(ln for ln in md.splitlines() if ln.startswith("- **Pullback within uptrend:**"))
    assert "PB11" in ob


def test_classify_watch_note_pullback_vs_quality() -> None:
    from invis_alpha_os.signals.momentum import build_momentum_signals

    pb = [50.0 + i * 0.8 for i in range(125)]
    peak = pb[-1]
    pb.extend([peak * 0.99, peak * 0.985, peak * 0.98, peak * 0.975, peak * 0.97])
    zx = [100.0 + i * 0.05 for i in range(280)]
    ranked = build_momentum_signals({"PB": _flat_bar_rows(pb), "ZX": _flat_bar_rows(zx)})
    by = {m.code: classify_watch_note(ranked, m) for m in ranked}
    assert by["PB"] == "pullback_in_uptrend"
    assert by["ZX"] == "quality_trend"


def test_action_watchlist_not_in_mixed_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(
        "invis_alpha_os.reports.momentum_daily.load_jp_watchlist_tickers",
        lambda: ["7011"],
    )
    _write_min_cache(tmp_path, "7011")
    mx = render_momentum_signals_mixed_section()
    assert "### Action Watchlist — Momentum (observation only)" not in mx


def test_action_watchlist_buckets_and_rank_order_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(
        "invis_alpha_os.reports.momentum_daily.load_jp_watchlist_tickers",
        lambda: ["LH11", "WK11", "OH11", "ST11", "PB11", "ZX11"],
    )

    _write_min_cache(tmp_path, "LH11", n=80)

    zx = [100.0 + i * 0.05 for i in range(280)]
    _write_payload_bars(tmp_path, "ZX11", _flat_bar_rows(zx))

    oh = [100.0] * 219 + [100.0 + (i - 218) * (150.0 / 61) for i in range(219, 280)]
    st = [100.0 + i * 0.1 for i in range(280)]
    _write_payload_bars(tmp_path, "OH11", _flat_bar_rows(oh))
    _write_payload_bars(tmp_path, "ST11", _flat_bar_rows(st))

    pb = [50.0 + i * 0.8 for i in range(125)]
    peak = pb[-1]
    pb.extend([peak * 0.99, peak * 0.985, peak * 0.98, peak * 0.975, peak * 0.97])
    _write_payload_bars(tmp_path, "PB11", _flat_bar_rows(pb))

    _write_payload_bars(tmp_path, "WK11", _flat_bar_rows([100.0] * 280))

    md = render_momentum_signals_cache_only_section()

    assert "#### Monitor strength / quality trend" in md
    mon_seg = md[md.index("#### Monitor strength / quality trend") :]
    nl = mon_seg.find("\n#### ", len("#### "))
    assert nl != -1
    mon_blk = mon_seg[:nl]
    assert "ST11, ZX11" in mon_blk

    blk = md[md.index("#### Overheat / chase-risk watch") :]
    nx = blk.find("\n#### ", len("#### "))
    assert "**Codes:** OH11" in blk[:nx]

    blk = md[md.index("#### Pullback within uptrend") :]
    nx = blk.find("\n#### ", len("#### "))
    assert "**Codes:** PB11" in blk[:nx]

    blk = md[md.index("#### Weak or mixed trend") :]
    nx = blk.find("\n#### ", len("#### "))
    assert "**Codes:** WK11" in blk[:nx]

    blk = md[md.index("#### Limited history") :]
    assert "**Codes:** LH11" in blk[:120]

    act = md[
        md.index("### Action Watchlist — Momentum (observation only)") :
        md.index("### Action Watchlist — Momentum (observation only)") + 3000
    ]
    alc = act.lower()
    assert " buy" not in alc
    assert " sell" not in alc
    assert "entry" not in alc
    assert "target price" not in alc
    assert "should purchase" not in alc


def test_render_cache_only_via_wire_codes_without_jp_watchlist_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spy = MagicMock(side_effect=RuntimeError("load_jp_watchlist_tickers must not run"))
    monkeypatch.setattr(
        "invis_alpha_os.reports.momentum_daily.load_jp_watchlist_tickers",
        spy,
    )
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    cache_dir = tmp_path / "market_data" / "jquants_daily_bars"
    cache_dir.mkdir(parents=True)
    bars = [{"date": "2024-01-01", "open": 1, "high": 1.1, "low": 0.9, "close": 1, "volume": 100}]
    payload = {
        "schema_version": 1,
        "code": "7011",
        "source": "unit",
        "fetched_at": "2026-01-01T00:00:00+00:00",
        "generated_at": None,
        "bar_count": 1,
        "bars": bars,
    }
    (cache_dir / "7011.json").write_text(json.dumps(payload), encoding="utf-8")

    md = render_momentum_cache_only_for_wire_codes(
        ["7011"],
        intro_banner_lines=[
            "(test banner)",
            "",
        ],
        trailing_note_before_table_lines=["", "*tail*", ""],
    )
    assert "## Momentum Signals — Cache Only" in md
    assert "(test banner)" in md
    assert "*tail*" in md
    assert "### Action Watchlist — Momentum (observation only)" in md
    spy.assert_not_called()


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
    assert "| Rank | Code | Sv2 | Key |" in md and "| Watch | Bars src |" in md
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
    assert len(cells) == 12
