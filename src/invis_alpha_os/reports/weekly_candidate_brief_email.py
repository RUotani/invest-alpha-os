"""Weekly Candidate Brief → Gmail preview drafts (dry-run only; no API send)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WeeklyCandidateBriefEmailDraft:
    subject: str
    text_body: str
    html_body: str | None = None


def build_weekly_candidate_brief_email_subject(report_date: str) -> str:
    return f"[invest-alpha-os] Weekly Candidate Brief {report_date}"


def build_weekly_candidate_brief_email_draft(*, report_date: str, copy_body: str) -> WeeklyCandidateBriefEmailDraft:
    """Build preview email: copy-only markdown as plain-text body."""

    body = copy_body.strip()
    footer = "観測・深掘り候補の整理です。売買推奨・投資助言・発注指示ではありません。"
    if footer not in body:
        body = f"{body}\n\n---\n{footer}\n"
    if not body.endswith("\n"):
        body += "\n"
    return WeeklyCandidateBriefEmailDraft(
        subject=build_weekly_candidate_brief_email_subject(report_date),
        text_body=body,
        html_body=None,
    )
