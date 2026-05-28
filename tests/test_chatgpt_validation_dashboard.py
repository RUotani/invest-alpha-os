from __future__ import annotations

from invis_alpha_os.reports.chatgpt_validation_dashboard import build_validation_dashboard


def test_build_validation_dashboard() -> None:
    rows = {
        "4w": [
            {
                "classification": "深掘り候補",
                "timing": "押し目待ち",
                "candidate_return_pct": 0.08,
                "benchmark_return_pct": 0.03,
                "excess_return_pct": 0.05,
                "result_label": "strong_hit",
                "trap_flags": ["value_trap_risk_low"],
            }
        ],
        "12w": [],
        "26w": [],
    }
    result = build_validation_dashboard(as_of_date="2026-05-28", horizon_rows=rows)
    assert "Forward Validation Dashboard" in result.markdown_text
    assert result.json_payload["sections"]["4w"]["false_positive_count"] == 0

