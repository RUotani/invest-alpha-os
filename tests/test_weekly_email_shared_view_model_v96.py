from __future__ import annotations

from invis_alpha_os.product.weekly_email_shared_view_model_v96 import (
    build_weekly_shared_view_model_v96,
    extract_weekly_shared_view_model_from_copy_v96,
    render_weekly_shared_view_model_email_text_v96,
    render_weekly_shared_view_model_markdown_v96,
)


def test_v96_shared_view_model_build_and_render() -> None:
    model = build_weekly_shared_view_model_v96(
        score_veto_summary_lines=("Score/Veto: 監視1",),
        pipeline_summary_lines=("候補パイプライン: 入力3",),
        monthly_input_summary_lines=("Monthly Input: 判定 WARN",),
    )
    md_lines = render_weekly_shared_view_model_markdown_v96(model)
    joined = "\n".join(md_lines)
    assert "## Shared Summary（v96）" in joined
    assert "Score / Veto（共有要約）" in joined
    assert "候補パイプライン（共有要約）" in joined
    assert "Monthly Input Consistency（共有要約）" in joined
    assert "これは売買指示ではなく" in joined


def test_v96_extract_and_email_compact_share_same_source() -> None:
    copy_body = """<<< COPY FROM HERE >>>
- 候補パイプライン: 入力3 / coverage不足1 / score未達1 / veto0 / 深掘り可能1
- 主因: coverage不足。次確認: 価格・出来高・期間・score内訳・veto理由。
- Score/Veto: 深掘り候補1 / 監視1 / veto確認0 / score補完1 / 高優先レビュー0。
- これは実行指示ではなく、根拠補完と安全確認の分類です。
- Monthly Input: 判定 WARN / 対象月 2026-05
- Monthly Guardrail: 現金11.7% / 個別株19.6%
<<< COPY TO HERE >>>"""
    model = extract_weekly_shared_view_model_from_copy_v96(copy_body)
    email_lines = render_weekly_shared_view_model_email_text_v96(model)
    assert any("候補パイプライン" in x for x in email_lines)
    assert any("Score/Veto" in x for x in email_lines)
    assert any("Monthly Input" in x for x in email_lines)
    assert any("売買指示" in x for x in email_lines)
