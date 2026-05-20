"""Daily operator bundle → email draft (observation-only; no trading advice)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

_DISCLAIMER = (
    "Observation only — not buy/sell advice. No automatic trading. "
    "US cache preview default remains off unless explicitly opted in."
)


@dataclass(frozen=True)
class DailyEmailDraft:
    subject: str
    text_body: str
    html_body: str
    bundle_dir: Path
    report_date: str
    freshness_summary: str | None = None


def _read_optional(path: Path) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def _extract_freshness(signals_md: str, operator_summary: str) -> str | None:
    for blob in (signals_md, operator_summary):
        m = re.search(r"stale\s*\*?\*?\s*0|stale\s+0", blob, re.I)
        if m:
            fe = re.search(r"fresh_enough\s*\*?\*?\s*16|fresh_enough\s+16", blob, re.I)
            if fe:
                return "stale 0 / fresh_enough 16"
    m2 = re.search(r"stale_count['\"]?\s*:\s*0", signals_md)
    if m2:
        return "stale 0 (see bundle for details)"
    return None


def build_daily_email_from_bundle(
    bundle_dir: Path,
    *,
    main_commit: str | None = None,
    report_date: str | None = None,
) -> DailyEmailDraft:
    bundle_dir = bundle_dir.resolve()
    run_date = report_date or bundle_dir.name
    operator_summary = _read_optional(bundle_dir / "operator_summary.md")
    daily_preview = _read_optional(bundle_dir / "daily_us_cache_preview.md")
    signals_preview = _read_optional(bundle_dir / "signals_us_cache_preview.md")
    chatgpt_prompt = _read_optional(bundle_dir / "chatgpt_investment_consultation_prompt.md")

    freshness = _extract_freshness(signals_preview, operator_summary)
    if freshness:
        subject = f"[invest-alpha-os] Daily Observation Report {run_date} — {freshness}"
    else:
        subject = f"[invest-alpha-os] Daily Observation Report {run_date}"

    commit_line = f"- main: `{main_commit}`\n" if main_commit else ""
    text_parts = [
        f"Daily Observation Report — {run_date}",
        "",
        _DISCLAIMER,
        "",
        "## Meta",
        f"- date: {run_date}",
        commit_line.rstrip(),
        f"- bundle: `{bundle_dir}`",
        "",
        "## Operator summary",
        operator_summary.strip() or "(operator_summary.md not found)",
        "",
        "## Daily US cache preview (opt-in)",
        daily_preview.strip() or "(daily_us_cache_preview.md not found)",
        "",
        "## Signals US cache preview (opt-in)",
        signals_preview.strip() or "(signals_us_cache_preview.md not found)",
        "",
        "## How to use in ChatGPT",
        "Paste sections from chatgpt_investment_consultation_prompt.md or this email into ChatGPT. "
        "Ask for observation, deep-dive candidates, and next steps limited to research / watch / alert — not trading orders.",
        "",
        "---",
        chatgpt_prompt[:2000] + ("…" if len(chatgpt_prompt) > 2000 else "") if chatgpt_prompt else "",
    ]
    text_body = "\n".join(p for p in text_parts if p is not None)

    html_body = (
        f"<html><body><h1>Daily Observation Report — {run_date}</h1>"
        f"<p><em>{_DISCLAIMER}</em></p>"
        f"<pre>{_html_escape(text_body[:120000])}</pre></body></html>"
    )

    return DailyEmailDraft(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        bundle_dir=bundle_dir,
        report_date=run_date,
        freshness_summary=freshness,
    )


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
