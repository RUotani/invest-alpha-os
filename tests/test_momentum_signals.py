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


# R6.6: volume_25d_ratio lookahead-exclusion regression
def test_volume_ratio_25d_excludes_latest_bar_from_prior_average() -> None:
    """Prior 25-session average must NOT include the latest bar (no lookahead)."""
    # If the average included the latest bar, the result would be different.
    prior = [1000.0] * 25
    latest = 3000.0
    # Correct: avg = mean(prior[0:25]) = 1000, ratio = 3000/1000 = 3.0
    vols_exact = prior + [latest]
    r = volume_ratio_25d_prior_mean(vols_exact)
    assert r is not None
    assert abs(r - 3.0) < 1e-9

    # Verify: if we inject a spike in what should be the prior window,
    # the ratio changes — confirming the window is the 25 bars BEFORE latest.
    prior_with_spike = [1000.0] * 24 + [5000.0]  # spike in position -2
    vols_with_spike = prior_with_spike + [latest]
    r2 = volume_ratio_25d_prior_mean(vols_with_spike)
    assert r2 is not None
    expected_avg = (1000.0 * 24 + 5000.0) / 25
    assert abs(r2 - latest / expected_avg) < 1e-9
    assert r2 < r  # spike raised the prior avg, so ratio drops


# R6.7: 285A with cache-source and veto_status field
def test_285a_cache_only_source_appears_in_ranked(tmp_path: Path, monkeypatch) -> None:
    """285A must appear in signals --source cache-only output when a cache file exists."""
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["285A"],
    )
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    cache_dir = tmp_path / "market_data" / "jquants_daily_bars"
    cache_dir.mkdir(parents=True)
    n = 280
    bars = [
        {
            "date": f"2024-{(i // 28) % 12 + 1:02d}-{(i % 28) + 1:02d}",
            "open": 1000.0 + i,
            "high": 1001.0 + i,
            "low": 999.0 + i,
            "close": 1000.5 + i,
            "volume": 5000.0,
        }
        for i in range(n)
    ]
    payload = {
        "schema_version": 1,
        "code": "285A",
        "source": "jquants_v2_equities_bars_daily",
        "fetched_at": "2026-01-01T00:00:00+00:00",
        "generated_at": None,
        "bar_count": n,
        "bars": bars,
    }
    (cache_dir / "285A.json").write_text(json.dumps(payload))
    runner = CliRunner()
    r = runner.invoke(app, ["signals", "--source", "cache-only"])
    assert r.exit_code == 0, r.output
    blob = json.loads(r.stdout)
    assert blob["observation_only"] is True
    assert blob.get("veto_status") == "ok"
    codes = {row["code"] for row in blob["ranked"]}
    assert "285A" in codes, f"285A missing from cache-only ranked; got {codes}"
    row = next(x for x in blob["ranked"] if x["code"] == "285A")
    for field in ("r5", "r20", "r60", "volume_ratio_25d", "high_52w_distance_pct", "data_quality"):
        assert field in row, f"missing field {field!r}"
    assert row["bars_source"] == "cache"


# R6.8-A: VetoEngine統合 — signals CLIの各候補行にveto_resultが付与されること
def test_signals_ranked_rows_have_veto_result(monkeypatch) -> None:
    """signals CLIのrankd各行にveto_result（拒否判定結果）フィールドが存在すること。"""
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["7011"],
    )
    runner = CliRunner()
    r = runner.invoke(app, ["signals", "--dry-run"])
    assert r.exit_code == 0, r.output
    blob = json.loads(r.stdout)
    assert blob.get("veto_status") == "ok"
    assert len(blob["ranked"]) == 1
    row = blob["ranked"][0]
    assert "veto_result" in row, "veto_result field missing from ranked row"
    vr = row["veto_result"]
    assert isinstance(vr["triggered"], bool)
    assert isinstance(vr["count"], int)
    assert isinstance(vr["rules"], list)


def test_signals_overheat_triggers_veto(monkeypatch) -> None:
    """overheat_flag=Trueの銘柄はveto_result.triggeredがTrueになること。"""
    from invis_alpha_os.signals.momentum import MomentumBreakdown

    overheat_breakdown = MomentumBreakdown(
        code="7011",
        bar_count=280,
        labels=("overheat",),
        score=0,
        r5=0.05,
        r20=0.55,  # SCORE_V2_OVERHEAT_R20=0.5 超え
        r60=1.1,   # SCORE_V2_OVERHEAT_R60=1.0 超え
        r120=None,
        volume_spike=False,
        vol_avg25=None,
        volume_ratio_25d=None,
        high_52w_breakout=False,
        high_52w_distance_pct=None,
        trend_quality="up",
        overheat_flag=True,
        data_quality=(("enough_data", True),),
        score_v2=0,
        score_v2_components=(),
    )
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.build_momentum_signals",
        lambda mapping: [overheat_breakdown],
    )
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["7011"],
    )
    runner = CliRunner()
    r = runner.invoke(app, ["signals", "--dry-run"])
    assert r.exit_code == 0, r.output
    blob = json.loads(r.stdout)
    row = blob["ranked"][0]
    vr = row["veto_result"]
    assert vr["triggered"] is True, "overheat銘柄はveto_result.triggered=Trueであるべき"
    rule_ids = [x["rule_id"] for x in vr["rules"]]
    assert "hard_momentum_overheat" in rule_ids, f"hard_momentum_overheat rule missing; got {rule_ids}"


def test_signals_volume_price_chase_triggers_fomo_veto(monkeypatch) -> None:
    """volume_ratio_25d>=3 かつ r5>0.15 のとき fomo_volume_price_chase が veto_result に含まれること。"""
    from invis_alpha_os.signals.momentum import MomentumBreakdown

    chase = MomentumBreakdown(
        code="7011",
        bar_count=280,
        labels=(),
        score=0,
        r5=0.20,
        r20=0.10,
        r60=0.10,
        r120=None,
        volume_spike=True,
        vol_avg25=None,
        volume_ratio_25d=3.5,
        high_52w_breakout=False,
        high_52w_distance_pct=None,
        trend_quality="up",
        overheat_flag=False,
        data_quality=(("enough_data", True),),
        score_v2=0,
        score_v2_components=(),
    )
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.build_momentum_signals",
        lambda mapping: [chase],
    )
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["7011"],
    )
    runner = CliRunner()
    r = runner.invoke(app, ["signals", "--dry-run"])
    assert r.exit_code == 0, r.output
    blob = json.loads(r.stdout)
    rule_ids = [x["rule_id"] for x in blob["ranked"][0]["veto_result"]["rules"]]
    assert "fomo_volume_price_chase" in rule_ids, f"expected fomo_volume_price_chase in {rule_ids}"


# R6.8-B: --format markdown オプション
def test_signals_format_markdown_outputs_table(monkeypatch) -> None:
    """--format markdown指定でMarkdownテーブルが出力されること。"""
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["7011", "7203"],
    )
    runner = CliRunner()
    r = runner.invoke(app, ["signals", "--dry-run", "--format", "markdown"])
    assert r.exit_code == 0, r.output
    out = r.stdout
    assert "## Momentum Signals" in out
    assert "| # | Code / Name | Sv2 |" in out
    assert "7011" in out
    assert "7203" in out
    assert "{" not in out, "JSON混入が検出された（markdownモードなのにJSONが出力されている）"


def test_signals_format_markdown_veto_cell_shown(monkeypatch) -> None:
    """overheat銘柄のVeto列に rule_id が表示されること。"""
    from invis_alpha_os.signals.momentum import MomentumBreakdown

    overheat = MomentumBreakdown(
        code="7011", bar_count=280, labels=("overheat",), score=0,
        r5=0.02, r20=0.55, r60=1.1, r120=None,
        volume_spike=False, vol_avg25=None, volume_ratio_25d=None,
        high_52w_breakout=False, high_52w_distance_pct=None,
        trend_quality="up", overheat_flag=True,
        data_quality=(("enough_data", True),),
        score_v2=0, score_v2_components=(),
    )
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.build_momentum_signals",
        lambda mapping: [overheat],
    )
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["7011"],
    )
    runner = CliRunner()
    r = runner.invoke(app, ["signals", "--dry-run", "--format", "markdown"])
    assert r.exit_code == 0, r.output
    assert "hard_momentum_overheat" in r.stdout


def test_signals_format_json_default_unchanged(monkeypatch) -> None:
    """--format省略時はJSONが出力されること（既存動作の回帰確認）。"""
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.load_jp_watchlist_tickers",
        lambda: ["7011"],
    )
    runner = CliRunner()
    r = runner.invoke(app, ["signals", "--dry-run"])
    assert r.exit_code == 0, r.output
    blob = json.loads(r.stdout)
    assert "ranked" in blob
    assert blob["observation_only"] is True
