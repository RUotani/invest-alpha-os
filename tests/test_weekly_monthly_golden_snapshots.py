from __future__ import annotations

import json

from invis_alpha_os.portfolio.monthly_decision_sheet_v84 import build_monthly_decision_sheet_v84_markdown
from invis_alpha_os.product.weekly_candidate_brief_v0 import (
    WeeklyCandidateBriefV0,
    format_weekly_candidate_brief_v0_copy,
    format_weekly_candidate_brief_v0_json,
    format_weekly_candidate_brief_v0_markdown,
)


def _weekly_fixture() -> WeeklyCandidateBriefV0:
    return WeeklyCandidateBriefV0(
        report_date="2026-06-06",
        generated_at_jp="fixture-jp",
        generated_at_us="fixture-us",
        jp_scope="fixture-jp-scope",
        us_scope="fixture-us-scope",
        macro_summary="fixture macro summary",
    )


def _headings(markdown: str) -> tuple[str, ...]:
    return tuple(line for line in markdown.splitlines() if line.startswith("#"))


def _assert_ordered_subset(lines: tuple[str, ...], expected: tuple[str, ...]) -> None:
    cursor = 0
    for expected_line in expected:
        try:
            cursor = lines.index(expected_line, cursor) + 1
        except ValueError:
            raise AssertionError(f"missing ordered heading: {expected_line}") from None


def test_weekly_markdown_golden_section_order_and_decision_markers() -> None:
    markdown = format_weekly_candidate_brief_v0_markdown(_weekly_fixture())

    headings = _headings(markdown)
    _assert_ordered_subset(
        headings,
        (
            "# 週次候補ブリーフ v0.1",
            "## コピー用サマリー",
            "# 週次候補ブリーフ — 2026-06-06",
            "## 今週の結論",
            "## ポートフォリオ制約",
            "## 行動分類",
            "## 候補パイプライン・トレース",
            "## Score / Veto 統合サマリー",
            "## Shared Summary（v96）",
            "## 今週の行動チェックリスト",
            "## 今週のDo / Don't",
            "## 安全メモ",
            "## マクロ環境（ETF proxy）",
            "## 今週の候補 Top 5（横断）",
            "## 急騰候補 Top 3",
        "## 押し目候補 Top 3",
        "## 過熱・避ける候補 Top 3",
        "## データ不足・要注意 Top 3",
            "## テーマハイライト",
            "## 付録（運用）",
            "## 再生成コマンド",
        ),
    )
    for marker in (
        "これは売買指示ではなく",
        "Score / Veto",
        "候補パイプライン",
        "Sanitized / Manual Input",
        "現金11.7%",
        "個別株19.6%",
        "株式系67.8%",
    ):
        assert marker in markdown


def test_weekly_copy_golden_keeps_chatgpt_paste_boundaries_and_action_checklist() -> None:
    copy = format_weekly_candidate_brief_v0_copy(_weekly_fixture())

    assert copy.startswith("<<< COPY FROM HERE >>>")
    assert copy.rstrip().endswith("<<< COPY TO HERE >>>")
    assert "# 週次候補ブリーフ — 2026-06-06" in copy
    assert "## 今週の結論" in copy
    assert "## 今週の行動チェックリスト" in copy
    assert "### 今週やってよいこと" in copy
    assert "### 今週やらないこと" in copy
    assert "### 次に確認すること" in copy
    assert "Score / Veto" in copy
    assert "Pipeline" in copy
    assert "Sanitized / Manual Input" in copy
    assert "これは売買指示ではなく" in copy


def test_weekly_json_golden_keeps_schema_and_pipeline_payload() -> None:
    payload = json.loads(format_weekly_candidate_brief_v0_json(_weekly_fixture()))

    assert payload["schema_version"] == "weekly_candidate_brief.v0.1"
    assert payload["report_date"] == "2026-06-06"
    assert payload["observation_only"] is True
    assert set(payload["sections"]) == {
        "top_picks",
        "rapid_movers",
        "pullbacks",
        "avoid",
        "insufficient",
        "theme_highlights",
    }
    assert payload["score_veto_pipeline"]
    assert {
        "score_band",
        "normalized_score",
        "has_hard_veto",
        "has_soft_veto",
        "veto_keys",
        "pipeline_stage",
        "action_label_ja",
    } <= set(payload["score_veto_pipeline"][0])


def test_monthly_decision_sheet_golden_section_order_and_portfolio_numbers() -> None:
    markdown = build_monthly_decision_sheet_v84_markdown()

    _assert_ordered_subset(
        _headings(markdown),
        (
            "# Monthly Decision Sheet",
            "## 今月の結論",
            "## 判断サマリー",
            "## 今月の意思決定テーブル",
            "## 現金回復ステップ",
            "## 次月への持ち越し",
            "## 配分ギャップ（v82再利用）",
            "## Safety note",
        ),
    )
    for marker in (
        "4327.9万円",
        "508.2万円 / 11.7%",
        "2934.5万円 / 67.8%",
        "846.3万円 / 19.6%",
        "あと 141.0万円",
        "above band +4.6% / +197.1万円",
        "このシートは売買指示ではなく",
    ):
        assert marker in markdown


def test_weekly_monthly_golden_forbidden_action_terms_stay_absent() -> None:
    weekly = format_weekly_candidate_brief_v0_copy(_weekly_fixture())
    monthly = build_monthly_decision_sheet_v84_markdown()

    forbidden = ("買え", "売れ", "必ず購入", "発注", "order placement")
    for text in (weekly, monthly):
        for phrase in forbidden:
            assert phrase not in text
