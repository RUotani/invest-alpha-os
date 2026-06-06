"""User-facing weekly report one-page summary (fixture/sample only)."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from invis_alpha_os.config.paths import ROOT_DIR
from invis_alpha_os.product.portfolio_data_quality_review_v109 import (
    build_portfolio_data_quality_review_v109,
    render_portfolio_data_quality_review_summary_lines_v109,
)

_DEFAULT_SAMPLE = ROOT_DIR / "reports-private" / "sample_outputs" / "chatgpt_one_page_summary_sample.md"

SUGGESTED_CHATGPT_QUESTIONS_V12: tuple[str, ...] = (
    "285Aは過熱後でも深掘り価値がありますか？",
    "現金比率11.7%で新規個別株を買うべきですか？",
    "AAPL/QQQは既存INDEXと重複しすぎですか？",
    "今週は買うべきか、調査だけにすべきですか？",
)


@dataclass(frozen=True)
class WeeklyReportUserSummary:
    source: str
    report_date: str
    body_markdown: str
    safety_notes: tuple[str, ...]


def build_weekly_report_user_summary(
    *,
    source: str = "sample",
    sample_path: Path | None = None,
    report_date: str = "2026-06-06",
) -> WeeklyReportUserSummary:
    if source == "sample":
        path = sample_path or _DEFAULT_SAMPLE
        if not path.is_file():
            raise ValueError(f"sample file not found: {path}")
        body = path.read_text(encoding="utf-8")
    elif source == "composed":
        quality_lines = render_portfolio_data_quality_review_summary_lines_v109(
            build_portfolio_data_quality_review_v109()
        )
        body = "\n".join(
            [
                "# Weekly Report One-Page Summary",
                "",
                "## 1. 今週の結論",
                "",
                "今週は候補確認とポートフォリオ制約の点検を優先します。これは売買指示ではありません。",
                "",
                "## 2. 候補上位",
                "",
                "| 優先 | 候補 | 扱い | 理由 |",
                "|---:|---|---|---|",
                "| 1 | 285A キオクシア | 深掘り / 追いかけ禁止 | 半導体・メモリ市況とモメンタムを確認 |",
                "| 2 | AAPL | 材料確認 | 大型株として既存INDEXとの重複を確認 |",
                "| 3 | QQQ | 指数環境確認 | Nasdaq全体のリスクオン確認 |",
                "",
                "## 3. ポートフォリオ制約",
                "",
                "- 現金比率11.7%は最低目安15%未満。新規個別株より現金回復を優先。",
                "- 個別株比率19.6%は目安10〜15%より多め。個別株追加は慎重。",
                "- 株式系合計67.8%はリスク資産寄り。AAPL/QQQは既存INDEXとの重複確認が必要。",
                "",
                "## 4. 深掘りしたい論点",
                "",
                "- 285Aの急騰が業績・需給で説明できるか。",
                "- AAPL/QQQが既存保有と重複しすぎていないか。",
                "- 候補の反証（過熱、決算前、veto）が消えているか。",
                "",
                "## 5. 見送り条件",
                "",
                "- 20日で50%以上の急騰が続き、押し目や材料確認がない。",
                "- 決算前で不確実性が高い。",
                "- vetoやデータ不足が残っている。",
                "- 現金比率が15%未満のまま個別株を増やす必要がある。",
                "",
                "## 6. ChatGPTに聞きたい質問",
                "",
                *[f"- {question}" for question in SUGGESTED_CHATGPT_QUESTIONS_V12],
                "",
                "## Portfolio / Quality 補足",
                *[f"- {line}" for line in quality_lines],
                "",
                f"report_date: {report_date}",
            ]
        )
    else:
        raise ValueError(f"unsupported source: {source}")
    return WeeklyReportUserSummary(
        source=source,
        report_date=report_date,
        body_markdown=body,
        safety_notes=(
            "source-only / fixture-only — 売買指示ではありません",
            "live HTTP / cache write / actual import / broker / real email: 未実行",
        ),
    )


def render_weekly_report_user_summary_markdown(summary: WeeklyReportUserSummary) -> str:
    return summary.body_markdown


def format_weekly_report_user_summary_json(summary: WeeklyReportUserSummary) -> str:
    return json.dumps(
        {
            "source": summary.source,
            "report_date": summary.report_date,
            "body_markdown": summary.body_markdown,
            "safety_notes": list(summary.safety_notes),
        },
        ensure_ascii=False,
        indent=2,
    )
