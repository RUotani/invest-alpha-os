from __future__ import annotations

from invis_alpha_os.reports.weekly_candidate_brief_quant_metrics import compute_candidate_quant_metrics


def _bars(n: int) -> list[dict[str, float | str]]:
    out: list[dict[str, float | str]] = []
    for i in range(n):
        close = 100.0 + i
        out.append(
            {
                "date": f"2026-01-{(i % 28) + 1:02d}",
                "open": close - 1.0,
                "high": close + 1.0,
                "low": close - 2.0,
                "close": close,
                "volume": 1000.0 + i * 10.0,
            }
        )
    return out


def test_quant_metrics_computes_ma_return_52w_volume(monkeypatch) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.reports.weekly_candidate_brief_quant_metrics._load_bars",
        lambda symbol, market: (_bars(260), "cache:test"),
    )
    qm = compute_candidate_quant_metrics(symbol="AAPL", market="US", report_date="2026-05-27")
    assert qm.latest_close is not None
    assert qm.ma_25 is not None
    assert qm.ma_75 is not None
    assert qm.ma_200 is not None
    assert qm.ret_5d_pct is not None
    assert qm.ret_20d_pct is not None
    assert qm.ret_60d_pct is not None
    assert qm.high_52w is not None
    assert qm.low_52w is not None
    assert qm.volume_ratio_20d is not None
    assert qm.missing_reason is None or "partial 52W range" not in qm.missing_reason


def test_quant_metrics_marks_insufficient_bars(monkeypatch) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.reports.weekly_candidate_brief_quant_metrics._load_bars",
        lambda symbol, market: (_bars(84), "cache:test"),
    )
    qm = compute_candidate_quant_metrics(symbol="7203", market="JP", report_date="2026-05-27")
    assert qm.ma_200 is None
    assert qm.ret_60d_pct is not None
    assert qm.missing_reason is not None
    assert "データ本数不足（200日移動平均線" in qm.missing_reason


def test_quant_metrics_accepts_lowercase_jp_market(monkeypatch) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.reports.weekly_candidate_brief_quant_metrics.load_jquants_daily_bars_cache",
        lambda symbol: (_bars(260), {}) if symbol == "5802" else None,
    )
    qm = compute_candidate_quant_metrics(symbol="5802", market="jp", report_date="2026-05-27")
    assert qm.latest_close is not None
    assert qm.source.startswith("cache:jquants_daily_bars:")
    assert qm.freshness_classification is not None


def test_quant_metrics_resolves_jp_symbol_suffix_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.reports.weekly_candidate_brief_quant_metrics.load_jquants_daily_bars_cache",
        lambda symbol: (_bars(260), {}) if symbol == "5802" else None,
    )
    qm = compute_candidate_quant_metrics(symbol="5802.T", market="jp", report_date="2026-05-27")
    assert qm.latest_close is not None
    assert qm.source.endswith(":5802")


def test_quant_metrics_missing_reason_has_tried_symbols() -> None:
    qm = compute_candidate_quant_metrics(symbol="ZZZZ", market="jp", report_date="2026-05-27")
    assert qm.latest_close is None
    assert qm.missing_reason is not None
    assert "tried=" in qm.missing_reason
    assert qm.freshness_classification == "cache_missing"
