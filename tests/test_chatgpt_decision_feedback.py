from __future__ import annotations

from invis_alpha_os.reports.chatgpt_decision_feedback import build_decision_feedback_template
from invis_alpha_os.reports.chatgpt_forward_validation_seed import build_forward_validation_seed


def test_build_decision_feedback_template() -> None:
    payload = {"candidates": [{"ticker": "285A", "name": "Kioxia"}]}
    result = build_decision_feedback_template(report_date="2026-05-27", context_json_payload=payload)
    assert "週次判断フィードバックテンプレート" in result.markdown_text
    assert "285A" in result.markdown_text
    assert result.json_payload["candidates"][0]["ticker"] == "285A"


def test_build_forward_validation_seed() -> None:
    payload = {
        "candidates": [
            {
                "rank": 1,
                "ticker": "AAPL",
                "name": "Apple",
                "market": "US",
                "classification": "top_pick",
                "timing": "要確認",
                "latest_close": 180.0,
                "latest_bar_date": "2026-05-27",
                "freshness": "fresh",
                "returns": {"d5": 1.0},
                "moving_averages": {},
                "range_52w": {},
                "volume": {},
                "momentum_rationale": ["理由"],
                "counter_evidence": ["反証"],
                "next_checks": ["次確認"],
            }
        ]
    }
    result = build_forward_validation_seed(report_date="2026-05-27", context_json_payload=payload)
    assert result.json_payload["evaluation_dates"]["plus_4w"] == "2026-06-24"
    assert result.json_payload["evaluation_dates"]["plus_12w"] == "2026-08-19"
    assert result.json_payload["evaluation_dates"]["plus_26w"] == "2026-11-25"
    assert "AAPL" in result.markdown_text
