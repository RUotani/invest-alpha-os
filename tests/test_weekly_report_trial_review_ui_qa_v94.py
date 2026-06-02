from __future__ import annotations

import json

from invis_alpha_os.product.weekly_candidate_brief_v0 import (
    WeeklyCandidateBriefV0,
    format_weekly_candidate_brief_v0_copy,
    format_weekly_candidate_brief_v0_json,
)
from invis_alpha_os.reports.weekly_candidate_brief_email import build_weekly_candidate_brief_email_draft


def _fixture_brief() -> WeeklyCandidateBriefV0:
    return WeeklyCandidateBriefV0(
        report_date="2026-06-02",
        generated_at_jp="fixture-only",
        generated_at_us="fixture-only",
        jp_scope="fixture-only",
        us_scope="fixture-only",
        macro_summary="fixture-only trial",
    )


def test_v94_score_veto_markdown_json_and_email_are_consistent() -> None:
    brief = _fixture_brief()
    copy_body = format_weekly_candidate_brief_v0_copy(brief)
    payload = json.loads(format_weekly_candidate_brief_v0_json(brief))
    draft = build_weekly_candidate_brief_email_draft(report_date="2026-06-02", copy_body=copy_body)

    rows = {row["symbol"]: row for row in payload["score_veto_pipeline"]}

    assert rows["GRID_A"]["pipeline_stage"] == "veto_blocked"
    assert rows["ROBO_B"]["pipeline_stage"] == "watch"
    assert rows["CASH_D"]["score_band"] == "HIGH_CONVICTION_REVIEW"
    assert rows["CASH_D"]["pipeline_stage"] == "high_conviction_review"
    assert rows["HYPE_E"]["pipeline_stage"] == "veto_blocked"

    assert "| GRID_A | BLOCKED | 58.75 | HARD: missing_evidence | veto_blocked | veto確認 |" in copy_body
    assert "| ROBO_B | DEEP_DIVE | 65.25 | SOFT: duplicate_exposure | watch | 追加確認 |" in copy_body
    assert "| CASH_D | HIGH_CONVICTION_REVIEW | 87.25 | - | high_conviction_review | 高優先レビュー |" in copy_body
    assert "HARD: missing_evidence, portfolio_constraint_breach +6" in copy_body
    assert "- Score/Veto: 深掘り候補0 / 監視2 / veto確認2 / score補完0 / 高優先レビュー1。" in copy_body
    assert "- これは実行指示ではなく、根拠補完と安全確認の分類です。" in copy_body
    assert "## Shared Summary（v96）" in copy_body
    assert "## 候補0件の理由メモ" in copy_body

    assert "## Score / Veto（短縮）" in draft.text_body
    assert "Score/Veto: 深掘り候補0 / 監視2 / veto確認2 / score補完0 / 高優先レビュー1。" in draft.text_body
    assert "HARD: missing_evidence, portfolio_constraint_breach +6" not in draft.text_body
    assert draft.html_body is not None
    assert "Score / Veto（短縮）" in draft.html_body
    assert "Score/Veto: 深掘り候補0 / 監視2 / veto確認2 / score補完0 / 高優先レビュー1。" in draft.html_body


def test_v94_trial_output_remains_execution_safe() -> None:
    copy_body = format_weekly_candidate_brief_v0_copy(_fixture_brief())
    draft = build_weekly_candidate_brief_email_draft(report_date="2026-06-02", copy_body=copy_body)

    assert "実行指示ではなく" in copy_body
    assert "実行指示ではなく" in draft.text_body
    assert "注文実行" not in copy_body
    assert "注文実行" not in draft.text_body
    assert "今すぐ購入" not in copy_body
    assert "今すぐ購入" not in draft.text_body
