"""Build trap-analysis enrichment artifacts from context pack."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invis_alpha_os.reports.chatgpt_trap_analysis import analyze_candidate_traps


@dataclass(frozen=True)
class ContextEnrichmentResult:
    markdown_text: str
    json_payload: dict[str, Any]


def build_context_enrichment(*, report_date: str, context_json_payload: dict[str, Any]) -> ContextEnrichmentResult:
    candidates = context_json_payload.get("candidates")
    rows = [x for x in candidates if isinstance(x, dict)] if isinstance(candidates, list) else []
    analyses = [analyze_candidate_traps(row) for row in rows]

    md_lines: list[str] = [
        "# Trap Analysis",
        "",
        f"- report_date: {report_date}",
        "",
    ]
    for item in analyses:
        md_lines.extend(
            [
                f"## {item['ticker']}",
                "### 罠分析",
                f"- バリュートラップ懸念: {item['value_trap_risk']['level']}",
                f"- 高値掴み懸念: {item['overheat_risk']['level']}",
                f"- 早売り懸念: {item['early_sell_risk']['level']}",
                f"- 売り遅れ懸念: {item['late_sell_risk']['level']}",
                "",
                "### 上がる要因",
                *[f"- {s}" for s in item["upside_thesis"]],
                "",
                "### 下がる要因",
                *[f"- {s}" for s in item["downside_thesis"]],
                "",
                "### 無効化条件",
                *[f"- {s}" for s in item["invalidation_conditions"]],
                "",
                "### データ鮮度リスク",
                f"- stale日数: {item.get('freshness_risk', {}).get('stale_days')}",
                f"- タイミング判断への影響: {item.get('freshness_risk', {}).get('timing_impact')}",
                "",
            ]
        )
    return ContextEnrichmentResult(
        markdown_text="\n".join(md_lines).rstrip() + "\n",
        json_payload={"report_date": report_date, "trap_analysis": analyses},
    )
