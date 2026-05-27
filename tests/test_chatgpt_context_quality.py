from __future__ import annotations

from invis_alpha_os.reports.chatgpt_context_quality import build_context_pack_quality_audit


def test_build_context_pack_quality_audit_basic() -> None:
    payload = {
        "report_date": "2026-05-27",
        "generated_at": "2026-05-27T00:00:00Z",
        "summary": {},
        "research_queue": {},
        "candidates": [
            {
                "rank": 1,
                "ticker": "285A",
                "name": "Sample",
                "classification": "top_pick",
                "freshness": "fresh",
                "latest_close": 123.4,
                "momentum_rationale": ["理由あり"],
                "counter_evidence": ["反証あり"],
                "next_checks": ["次確認あり"],
                "chatgpt_questions": ["質問あり"],
                "sources": ["cache"],
            }
        ],
    }
    result = build_context_pack_quality_audit(
        report_date="2026-05-27",
        context_json_payload=payload,
        context_markdown_text="# 見出し\n- レポート日: 2026-05-27\n",
    )
    assert result.json_payload["candidate_count"] == 1
    assert result.json_payload["grade"] in {"A", "B"}
    assert "品質監査" in result.markdown_text


def test_build_context_pack_quality_audit_detects_missing() -> None:
    payload = {"report_date": "2026-05-27", "candidates": [{"ticker": "AAPL"}]}
    result = build_context_pack_quality_audit(
        report_date="2026-05-27",
        context_json_payload=payload,
        context_markdown_text="## Summary\n- label: test\n",
    )
    assert result.json_payload["required_sections_missing"]
    assert result.json_payload["empty_momentum_count"] == 1
