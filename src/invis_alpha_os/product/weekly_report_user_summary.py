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

SUGGESTED_CHATGPT_QUESTIONS_V161: tuple[str, ...] = (
    "285Aは追いかけ禁止の過熱代表として、周辺・出遅れ候補はどこを見るべきですか？",
    "現金比率11.7%で新規個別株を増やすべきですか？",
    "初動候補0件の週は、何を優先して調査すべきですか？",
    "データ鮮度不足の候補はいつ再評価できますか？",
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
                "初動候補は0件。過熱銘柄で無理に埋めません。これは売買指示ではありません。",
                "",
                "- 状態: 初動候補は0件。過熱銘柄で無理に埋めません。",
                "- 最大リスク: 現金不足 / 個別株多め / 急騰後の過熱",
                "- 今週やる/やらない: やる: guardrailとデータ鮮度確認 / やらない: 根拠不足の新規追加",
                "",
                "## 2. 候補の扱い",
                "",
                "| 区分 | 件数 | 代表 | 扱い |",
                "|---|---:|---|---|",
                "| 投資妙味候補（初動・深掘り） | 0 | — | 該当なし |",
                "| 過熱代表 / Do Not Chase | 1 | 285A キオクシア | 追いかけ禁止 / 周辺・出遅れ候補を探す |",
                "| データ鮮度不足 | 5 | 6857 ほか | 深掘り・監視候補に昇格させない |",
                "",
                "## 3. ポートフォリオ制約",
                "",
                "- 現金比率11.7%は最低目安15%未満。新規個別株より現金回復を優先。",
                "- 個別株比率19.6%は目安10〜15%より多め。個別株追加は慎重。",
                "- 株式系合計67.8%はリスク資産寄り。新規追加は抑制。",
                "",
                "## 4. 深掘りしたい論点",
                "",
                "- 285Aはテーマ代表として観測し、周辺・出遅れ候補の起点にできるか。",
                "- 鮮度不足候補はデータ更新後に再評価できるか。",
                "- guardrail下で新規リスクを増やさない判断が一貫しているか。",
                "",
                "## 5. 見送り条件",
                "",
                "- 20日で50%以上の急騰が続き、押し目や材料確認がない（285Aは該当）。",
                "- 決算前で不確実性が高い。",
                "- vetoやデータ不足が残っている。",
                "- 現金比率が15%未満のまま個別株を増やす必要がある。",
                "",
                "## 6. ChatGPTに聞きたい質問",
                "",
                *[f"- {question}" for question in SUGGESTED_CHATGPT_QUESTIONS_V161],
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
