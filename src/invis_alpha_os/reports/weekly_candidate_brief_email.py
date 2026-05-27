"""Weekly Candidate Brief -> Gmail preview/test-send drafts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape


@dataclass(frozen=True)
class WeeklyCandidateBriefEmailDraft:
    subject: str
    text_body: str
    html_body: str | None = None


def build_weekly_candidate_brief_email_subject(report_date: str) -> str:
    return f"[TEST][invest-alpha-os] Weekly Candidate Brief {report_date}"


def _render_copy_markdown_as_simple_html(copy_body: str) -> str:
    blocks: list[str] = []
    in_list = False
    for raw in copy_body.splitlines():
        line = raw.strip()
        if not line:
            if in_list:
                blocks.append("</ul>")
                in_list = False
            continue
        if line.startswith("### "):
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<h3>{escape(line[4:])}</h3>")
            continue
        if line.startswith("## "):
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<h2>{escape(line[3:])}</h2>")
            continue
        if line.startswith("# "):
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<h1>{escape(line[2:])}</h1>")
            continue
        if line.startswith("- "):
            if not in_list:
                blocks.append("<ul>")
                in_list = True
            blocks.append(f"<li>{escape(line[2:])}</li>")
            continue
        if in_list:
            blocks.append("</ul>")
            in_list = False
        blocks.append(f"<p>{escape(line)}</p>")
    if in_list:
        blocks.append("</ul>")
    return "\n".join(blocks)


def build_weekly_candidate_brief_email_draft(*, report_date: str, copy_body: str) -> WeeklyCandidateBriefEmailDraft:
    """Build Weekly Candidate Brief email body for preview/test send."""

    body_core = copy_body.strip()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    footer = "観測・深掘り候補の整理です。売買推奨・投資助言・発注指示ではありません。"
    header_lines = [
        "TEST EMAIL",
        f"report date: {report_date}",
        f"generated at: {generated_at}",
        "disclaimer: this is not investment advice; observation and validation use only.",
        "",
    ]
    body = "\n".join(header_lines) + body_core
    if footer not in body_core:
        body = f"{body}\n\n---\n{footer}\n"
    if not body.endswith("\n"):
        body += "\n"
    html_body = (
        "<html><body style='margin:0;padding:0;background:#f8fafc;color:#111827;'>"
        "<div style='max-width:680px;margin:0 auto;padding:16px;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.6;'>"
        "<div style='background:#fff3cd;border:1px solid #ffe69c;border-radius:8px;padding:12px;margin-bottom:12px;'>"
        "<strong>TEST EMAIL</strong><br>"
        f"report date: {escape(report_date)}<br>"
        f"generated at: {escape(generated_at)}<br>"
        "disclaimer: this is not investment advice; observation and validation use only."
        "</div>"
        f"{_render_copy_markdown_as_simple_html(body_core)}"
        "<hr style='border:none;border-top:1px solid #e5e7eb;margin:16px 0;'>"
        f"<p style='font-size:13px;color:#4b5563;'>{escape(footer)}</p>"
        "</div></body></html>"
    )
    return WeeklyCandidateBriefEmailDraft(
        subject=build_weekly_candidate_brief_email_subject(report_date),
        text_body=body,
        html_body=html_body,
    )
