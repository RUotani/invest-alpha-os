"""Decision feedback template for weekly context pack."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DecisionFeedbackTemplateResult:
    markdown_text: str
    json_payload: dict[str, Any]


def build_decision_feedback_template(
    *,
    report_date: str,
    context_json_payload: dict[str, Any],
) -> DecisionFeedbackTemplateResult:
    candidates = context_json_payload.get("candidates")
    rows = [x for x in candidates if isinstance(x, dict)] if isinstance(candidates, list) else []

    md_lines: list[str] = [
        "# 週次判断フィードバックテンプレート",
        "",
        f"- レポート日: {report_date}",
        "",
    ]
    json_candidates: list[dict[str, Any]] = []
    for row in rows:
        ticker = str(row.get("ticker", "")).strip()
        name = str(row.get("name", "")).strip()
        title = f"{ticker} — {name}" if name else ticker
        md_lines.extend(
            [
                f"## {title}",
                "",
                "### 人間判断",
                "- 判断:",
                "  - [ ] 深掘りする",
                "  - [ ] 監視継続",
                "  - [ ] 押し目待ち",
                "  - [ ] ブレイクアウト待ち",
                "  - [ ] 見送り",
                "  - [ ] データ不足",
                "",
                "### 判断理由",
                "-",
                "",
                "### 実際の行動",
                "- [ ] 何もしない",
                "- [ ] ウォッチリスト追加",
                "- [ ] 追加調査",
                "- [ ] 打診",
                "- [ ] 既存保有の確認",
                "- [ ] その他:",
                "",
                "### 無効化条件",
                "-",
                "",
                "### 次回確認日",
                "-",
                "",
                "### メモ",
                "-",
                "",
            ]
        )
        json_candidates.append(
            {
                "ticker": ticker,
                "name": name,
                "decision": "",
                "reason": "",
                "action": "",
                "invalidation": "",
                "next_review_date": "",
                "memo": "",
            }
        )

    return DecisionFeedbackTemplateResult(
        markdown_text="\n".join(md_lines),
        json_payload={"report_date": report_date, "candidates": json_candidates},
    )
