from __future__ import annotations

from invis_alpha_os.reports.chatgpt_trap_analysis import analyze_candidate_traps


def test_analyze_candidate_traps_basic() -> None:
    candidate = {
        "ticker": "285A",
        "freshness": "最新圏",
        "returns": {"d5": 0.01, "d60": -0.12},
        "moving_averages": {"dist_ma25_pct": -0.02, "dist_ma75_pct": -0.08, "dist_ma200_pct": -0.2},
        "range_52w": {"dist_high_pct": -0.3},
        "volume": {"ratio20": 1.6},
    }
    out = analyze_candidate_traps(candidate)
    assert out["ticker"] == "285A"
    assert out["value_trap_risk"]["level"] in {"中", "高"}
    assert isinstance(out["upside_thesis"], list)
