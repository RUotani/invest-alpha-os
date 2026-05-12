"""Main E: momentum signal pure logic (synthetic bars; no HTTP)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.signals.momentum import (
    DailyBar,
    analyze_bars_for_code,
    build_momentum_signals,
    calculate_returns,
    detect_high_breakout,
    detect_volume_spike,
    load_bars_json_file,
    score_momentum_candidate,
)


def _flat_bars_closes(closes: list[float]) -> list[DailyBar]:
    out: list[DailyBar] = []
    for i, c in enumerate(closes):
        out.append(
            {
                "date": f"2024-01-{i+1:02d}",
                "open": c,
                "high": c,
                "low": c,
                "close": c,
                "volume": 1000.0,
            }
        )
    return out


def test_volume_spike_latest_three_times_prior_average() -> None:
    vols = [1000.0] * 25 + [3000.0]
    spike, avg = detect_volume_spike(vols, multiplier=3.0, lookback=25)
    assert avg == 1000.0
    assert spike is True


def test_returns_5_20_60() -> None:
    # monotone increasing: all positive returns
    closes = [100.0 + i * 0.5 for i in range(70)]
    r = calculate_returns(closes, (5, 20, 60))
    assert r[5] is not None and r[5] > 0
    assert r[20] is not None and r[20] > 0
    assert r[60] is not None and r[60] > 0


def test_high_breakout_last_close_above_prior_window() -> None:
    n = 260
    highs = [100.0] * (n - 1) + [110.0]
    closes = [99.0] * (n - 1) + [110.0]
    ok, ph = detect_high_breakout(highs, closes, prior_days=252)
    assert ph == 100.0
    assert ok is True


def test_score_ordering_prefers_breakout_then_volume() -> None:
    s1, _ = score_momentum_candidate(has_breakout=True, has_vol_spike=False, r20=0.01, r60=0.01)
    s2, _ = score_momentum_candidate(has_breakout=False, has_vol_spike=True, r20=0.01, r60=0.01)
    assert s1 > s2


def test_analyze_bars_labels_volume_and_breakout() -> None:
    n = 280
    bars: list[DailyBar] = []
    for i in range(n):
        c = 500.0 + i * 0.01
        h = c + 0.05
        v = 5000.0
        if i >= n - 26:
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
    m = analyze_bars_for_code("7011", bars)
    assert m is not None
    assert "volume_25d_spike" in m.labels
    assert "high_52w_breakout" in m.labels


def test_build_momentum_signals_ranks_by_score() -> None:
    short = _flat_bars_closes([100.0] * 15)
    long_ = _flat_bars_closes([100.0 + i * 0.1 for i in range(70)])
    rnk = build_momentum_signals({"SHORT": short, "LONG": long_})
    assert [x.code for x in rnk] == ["LONG", "SHORT"]


def test_cli_signals_dry_run_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["7011", "7203"],
    )
    runner = CliRunner()
    r = runner.invoke(app, ["signals", "--dry-run"])
    assert r.exit_code == 0
    blob = json.loads(r.stdout)
    assert blob["mode"] == "synthetic_dry_run"
    assert blob["bars_data_source"] == "synthetic"
    assert blob["observation_only"] is True
    assert len(blob["ranked"]) == 2
    assert {row["code"] for row in blob["ranked"]} == {"7011", "7203"}


def test_cli_signals_source_cache_uses_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["7011"],
    )
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)

    cache_dir = tmp_path / "market_data" / "jquants_daily_bars"
    cache_dir.mkdir(parents=True)
    bars = []
    for i in range(80):
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
        "code": "7011",
        "source": "jquants_v2_equities_bars_daily",
        "fetched_at": "2026-01-01T00:00:00+00:00",
        "generated_at": None,
        "bar_count": len(bars),
        "bars": bars,
    }
    (cache_dir / "7011.json").write_text(json.dumps(payload), encoding="utf-8")

    r = CliRunner().invoke(app, ["signals", "--source", "cache", "--dry-run"])
    assert r.exit_code == 0
    blob = json.loads(r.stdout)
    assert blob["bars_data_source"] == "cache"
    assert blob["ranked"][0]["bars_source"] == "cache"
    assert blob["ranked"][0]["bar_count"] == 80


def test_cli_signals_bars_file_requires_code(tmp_path: Path) -> None:
    p = tmp_path / "b.json"
    p.write_text("[]", encoding="utf-8")
    r = CliRunner().invoke(app, ["signals", "--bars-file", str(p)])
    assert r.exit_code == 2


def test_load_bars_json_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "x.json"
    series = [
        {"date": "2024-01-01", "open": 1, "high": 1.1, "low": 0.9, "close": 1.05, "volume": 100},
        {"date": "2024-01-02", "open": 1.05, "high": 1.2, "low": 1.0, "close": 1.15, "volume": 100},
    ]
    p.write_text(json.dumps(series), encoding="utf-8")
    bars = load_bars_json_file(p)
    m = analyze_bars_for_code("7011", bars)
    assert m is not None
    assert m.bar_count == 2
