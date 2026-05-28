from __future__ import annotations

from invis_alpha_os.reports.chatgpt_market_regime import build_market_regime_v0


def test_build_market_regime_v0_data_insufficient(monkeypatch) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.reports.chatgpt_market_regime.compute_candidate_quant_metrics",
        lambda **_: type("M", (), {"latest_close": None, "ret_20d_pct": None, "ret_60d_pct": None, "dist_ma_75_pct": None, "dist_ma_200_pct": None, "freshness_classification": "cache_missing", "freshness_reason": "missing"})(),
    )
    regime = build_market_regime_v0(report_date="2026-05-27")
    assert regime["label"] == "data_insufficient"


def test_build_market_regime_v0_risk_on(monkeypatch) -> None:
    def _stub(**kwargs):
        _ = kwargs
        return type(
            "M",
            (),
            {
                "latest_close": 100.0,
                "ret_20d_pct": 0.1,
                "ret_60d_pct": 0.2,
                "dist_ma_75_pct": 0.05,
                "dist_ma_200_pct": 0.1,
                "freshness_classification": "fresh",
                "freshness_reason": "ok",
            },
        )()

    monkeypatch.setattr("invis_alpha_os.reports.chatgpt_market_regime.compute_candidate_quant_metrics", _stub)
    regime = build_market_regime_v0(report_date="2026-05-27")
    assert regime["label"] in {"risk_on", "neutral"}
