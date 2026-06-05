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
                f"# Weekly Report User Summary — {report_date}",
                "",
                "## 今週の結論（fixture）",
                "- 新規買いを急がず、現金比率と個別株比率のguardrailを優先確認する。",
                "- 候補銘柄は「買い指示」ではなく、調査・監視・整理候補として扱う。",
                "- actual import / broker連携 / cache write は引き続き NO-GO。",
                "",
                "## Portfolio / Quality",
                *[f"- {line}" for line in quality_lines],
                "",
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
