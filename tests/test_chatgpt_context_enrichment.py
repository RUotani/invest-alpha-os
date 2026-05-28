from __future__ import annotations

from invis_alpha_os.reports.chatgpt_context_enrichment import build_context_enrichment


def test_build_context_enrichment() -> None:
    payload = {
        "candidates": [
            {
                "ticker": "AAPL",
                "freshness": "最新圏",
                "returns": {"d5": 0.03, "d60": 0.12},
                "moving_averages": {"dist_ma25_pct": 0.05, "dist_ma75_pct": 0.1, "dist_ma200_pct": 0.2},
                "range_52w": {"dist_high_pct": -0.01},
                "volume": {"ratio20": 1.2},
            }
        ]
    }
    result = build_context_enrichment(report_date="2026-05-27", context_json_payload=payload)
    assert "Trap Analysis" in result.markdown_text
    assert "AAPL" in result.markdown_text
    assert result.json_payload["trap_analysis"][0]["ticker"] == "AAPL"


def test_build_context_enrichment_reduces_placeholder_text() -> None:
    payload = {
        "candidates": [
            {
                "ticker": "5801",
                "freshness": "最新圏",
                "returns": {"d5": 0.2, "d20": 0.97, "d60": 1.04},
                "moving_averages": {"dist_ma25_pct": 0.18, "dist_ma75_pct": 0.22, "dist_ma200_pct": 0.4},
                "range_52w": {"dist_high_pct": -0.09},
                "volume": {"ratio20": 0.8},
                "momentum_rationale": ["電力・エネルギーインフラテーマ"],
                "counter_evidence": ["20D/60D急伸による過熱"],
                "next_checks": ["押し目形成の有無"],
            }
        ]
    }
    result = build_context_enrichment(report_date="2026-05-27", context_json_payload=payload)
    assert "追加入力待ち" not in result.markdown_text
