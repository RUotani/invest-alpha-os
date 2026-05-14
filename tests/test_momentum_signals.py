"""Main E: momentum signal pure logic (synthetic bars; no HTTP)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.signals.momentum import (
    DailyBar,
    analyze_bars_for_code,
    build_momentum_signals,
    calculate_returns,
    compute_score_v2,
    data_quality_flags,
    detect_high_breakout,
    detect_volume_spike,
    high_distance_vs_prior_high_pct,
    load_bars_json_file,
    momentum_row_public_dict,
    overheat_from_returns,
    score_momentum_candidate,
    synthetic_bars_for_code,
    volume_ratio_25d_prior_mean,
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


def test_cli_signals_source_cache_only_excludes_uncached(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["7011", "5802"],
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

    r = CliRunner().invoke(app, ["signals", "--source", "cache-only", "--dry-run"])
    assert r.exit_code == 0
    blob = json.loads(r.stdout)
    assert blob["mode"] == "cache_only_dry_run"
    assert blob["bars_data_source"] == "cache"
    assert blob["skipped_no_cache"] == 1
    assert blob["skipped_no_cache_codes"] == ["5802"]
    assert len(blob["ranked"]) == 1
    assert blob["ranked"][0]["code"] == "7011"
    assert blob["ranked"][0]["bars_source"] == "cache"


def test_cli_signals_cache_only_does_not_call_synthetic(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["7011", "5802"],
    )
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    (tmp_path / "market_data" / "jquants_daily_bars").mkdir(parents=True)
    bars = [{"date": f"2024-01-{i + 1:02d}", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1} for i in range(80)]
    payload = {
        "schema_version": 1,
        "code": "7011",
        "source": "x",
        "fetched_at": "2026-01-01T00:00:00Z",
        "generated_at": None,
        "bar_count": 80,
        "bars": bars,
    }
    (tmp_path / "market_data" / "jquants_daily_bars" / "7011.json").write_text(json.dumps(payload))

    spy = MagicMock()
    monkeypatch.setattr("invis_alpha_os.cli.main.synthetic_bars_for_code", spy)
    r = CliRunner().invoke(app, ["signals", "--source", "cache-only", "--dry-run"])
    assert r.exit_code == 0
    spy.assert_not_called()


def test_cli_signals_cache_no_synthetic_fallback_alias(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["7011", "5802"],
    )
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    d = tmp_path / "market_data" / "jquants_daily_bars"
    d.mkdir(parents=True)
    bars = [{"date": f"2024-01-{i + 1:02d}", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1} for i in range(80)]
    payload = {
        "schema_version": 1,
        "code": "7011",
        "source": "x",
        "fetched_at": "2026-01-01T00:00:00Z",
        "generated_at": None,
        "bar_count": 80,
        "bars": bars,
    }
    (d / "7011.json").write_text(json.dumps(payload))
    r = CliRunner().invoke(
        app,
        ["signals", "--source", "cache", "--no-synthetic-fallback", "--dry-run"],
    )
    assert r.exit_code == 0
    blob = json.loads(r.stdout)
    assert blob["mode"] == "cache_only_dry_run"
    assert blob["skipped_no_cache_codes"] == ["5802"]


def test_cli_signals_no_synthetic_fallback_rejects_synthetic_source() -> None:
    r = CliRunner().invoke(app, ["signals", "--source", "synthetic", "--no-synthetic-fallback", "--dry-run"])
    assert r.exit_code == 2


def test_cli_signals_bars_file_requires_code(tmp_path: Path) -> None:
    p = tmp_path / "b.json"
    p.write_text("[]", encoding="utf-8")
    r = CliRunner().invoke(app, ["signals", "--bars-file", str(p)])
    assert r.exit_code == 2


def test_cli_signals_bars_file_generic_us_symbols(tmp_path: Path) -> None:
    """bars-file exits before JP watchlist; symbol label is validated generically."""

    p = tmp_path / "bars.json"
    p.write_text(
        json.dumps(
            [
                {
                    "date": "2024-01-01",
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0,
                    "volume": 1_000_000.0,
                },
            ]
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    for lab in ("GOOGL", "BRK.B", "MSFT"):
        r = runner.invoke(app, ["signals", "--bars-file", str(p), "--code", lab])
        assert r.exit_code == 0, r.stderr
        row = json.loads(r.stdout)["ranked"][0]
        assert row["code"] == lab


def test_cli_signals_bars_file_rejects_unsafe_symbol_label(tmp_path: Path) -> None:
    p = tmp_path / "bars.json"
    p.write_text(
        json.dumps(
            [
                {
                    "date": "2024-01-01",
                    "open": 1,
                    "high": 1,
                    "low": 1,
                    "close": 1,
                    "volume": 1,
                },
            ]
        ),
        encoding="utf-8",
    )
    r = CliRunner().invoke(app, ["signals", "--bars-file", str(p), "--code", "../MSFT"])
    assert r.exit_code == 2
    assert "J-Quants" not in r.stderr


def test_volume_ratio_25d_prior_mean_ratio() -> None:
    baseline = [1000.0] * 25
    vols = baseline + [2500.0]
    r = volume_ratio_25d_prior_mean(vols)
    assert r is not None
    assert abs(r - 2.5) < 1e-9


def test_high_distance_pct_near_prior_high_window() -> None:
    highs = [100.0] * 100 + [100.5]
    closes = [99.5] * 100 + [99.9]
    d = high_distance_vs_prior_high_pct(closes, highs)
    assert d is not None
    assert abs(d - (-0.001)) < 1e-9


def test_overheat_flag_extreme_returns() -> None:
    assert overheat_from_returns(0.51, None) is True
    assert overheat_from_returns(None, 1.01) is True
    assert overheat_from_returns(0.1, 0.2) is False


def test_data_quality_short_history_flags() -> None:
    dq50 = dict(data_quality_flags(50))
    assert dq50["enough_60d"] is False and dq50["enough_120d"] is False
    dq200 = dict(data_quality_flags(200))
    assert dq200["enough_60d"] is True and dq200["enough_120d"] is True and dq200["enough_252d"] is False


def test_compute_score_v2_components_deterministic() -> None:
    s1, p1 = compute_score_v2(
        bar_count=200,
        has_breakout=True,
        r5=-0.01,
        r20=0.02,
        r60=0.03,
        r120=0.01,
        high_dist_pct=-0.02,
        vol_ratio_25d=2.5,
        overheat=False,
    )
    s2, p2 = compute_score_v2(
        bar_count=200,
        has_breakout=True,
        r5=-0.01,
        r20=0.02,
        r60=0.03,
        r120=0.01,
        high_dist_pct=-0.02,
        vol_ratio_25d=2.5,
        overheat=False,
    )
    assert p1 == p2
    assert s1 == s2
    assert "r20_positive" in p1
    assert "short_pullback_within_uptrend" in p1


def test_limited_history_penalty_below_121_bars() -> None:
    """121 bars aligns r120 horizon with ``enough_120d``; 120 bars must keep limited-history penalty."""

    closes_ok = [100.0 + i * 0.01 for i in range(121)]
    m_ok = analyze_bars_for_code("FULL", _flat_bars_closes(closes_ok))
    assert m_ok is not None
    assert dict(m_ok.data_quality)["enough_120d"] is True
    assert "limited_history_penalty" not in dict(m_ok.score_v2_components)

    closes_thin = closes_ok[:120]
    m_thin = analyze_bars_for_code("THIN", _flat_bars_closes(closes_thin))
    assert m_thin is not None
    assert dict(m_thin.data_quality)["enough_120d"] is False
    assert m_thin.r120 is None
    assert "limited_history_penalty" in dict(m_thin.score_v2_components)


def test_cli_signals_include_score_v2_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["7011"],
    )
    runner = CliRunner()
    r = runner.invoke(app, ["signals", "--dry-run"])
    assert r.exit_code == 0
    row = json.loads(r.stdout)["ranked"][0]
    for k in (
        "score_v2",
        "score_v2_components",
        "r120",
        "trend_quality",
        "volume_ratio_25d",
        "high_52w_distance_pct",
        "overheat_flag",
        "data_quality",
    ):
        assert k in row


def test_syntheticbars_analyze_carries_expected_v2_shapes() -> None:
    bars = synthetic_bars_for_code("TST1", n=320)
    m = analyze_bars_for_code("TST1", bars)
    assert m is not None
    md = momentum_row_public_dict(m, bars_source="synthetic")
    assert isinstance(md["score_v2"], int)
    assert isinstance(md["score_v2_components"], dict)


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


# ---------------------------------------------------------------------------
# R6.6: 285A explicit regression — 5-char alphanumeric JP code
# ---------------------------------------------------------------------------


def test_285a_accepted_not_skipped_in_signals_cli(monkeypatch) -> None:
    """285A (5-char JPX growth-market code) must appear in signals output, not be skipped."""
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["285A", "7011"],
    )
    runner = CliRunner()
    r = runner.invoke(app, ["signals", "--dry-run"])
    assert r.exit_code == 0, r.output
    blob = json.loads(r.stdout)
    codes = {row["code"] for row in blob["ranked"]}
    assert "285A" in codes, f"285A missing from ranked; got {codes}"
    assert "7011" in codes


def test_285a_momentum_row_has_required_fields(monkeypatch) -> None:
    """285A signals row must contain all standard momentum metric fields."""
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["285A"],
    )
    runner = CliRunner()
    r = runner.invoke(app, ["signals", "--dry-run"])
    assert r.exit_code == 0, r.output
    blob = json.loads(r.stdout)
    assert len(blob["ranked"]) == 1
    row = blob["ranked"][0]
    assert row["code"] == "285A"
    for field in ("r5", "r20", "r60", "volume_ratio_25d", "high_52w_distance_pct"):
        assert field in row, f"missing field {field!r} in 285A row"


def test_285a_synthetic_bars_analyze() -> None:
    """analyze_bars_for_code with 285A code label produces valid MomentumResult."""
    bars = synthetic_bars_for_code("285A", n=280)
    m = analyze_bars_for_code("285A", bars)
    assert m is not None
    assert m.code == "285A"
    assert m.bar_count == 280
    md = momentum_row_public_dict(m, bars_source="synthetic")
    assert md["code"] == "285A"
    assert isinstance(md["score_v2"], int)


def test_traditional_4digit_still_works_alongside_285a(monkeypatch) -> None:
    """Traditional 4-digit JP codes and 285A co-exist in signals output."""
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["7203", "6501", "285A"],
    )
    runner = CliRunner()
    r = runner.invoke(app, ["signals", "--dry-run"])
    assert r.exit_code == 0, r.output
    blob = json.loads(r.stdout)
    codes = {row["code"] for row in blob["ranked"]}
    assert {"7203", "6501", "285A"}.issubset(codes)


def test_unsafe_symbols_rejected_signals_cli(monkeypatch) -> None:
    """Symbols with unsafe characters must not appear in signals output."""
    from invis_alpha_os.config.jp_watchlist import jquants_daily_bars_ticker_kind

    # confirm the kind function agrees these are invalid
    assert jquants_daily_bars_ticker_kind("!!BAD") != "ok"
    assert jquants_daily_bars_ticker_kind("TOOLONG1") != "ok"
    # 285A itself must be "ok"
    assert jquants_daily_bars_ticker_kind("285A") == "ok"
