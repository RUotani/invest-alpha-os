"""Weekly Candidate Brief -> Gmail preview/test-send drafts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
import re

from invis_alpha_os.reports.weekly_candidate_brief_quant_metrics import (
    compute_candidate_quant_metrics,
    fmt_num,
    fmt_pct,
)

_TABLE_ROW_RE = re.compile(
    r"^\|\s*(?P<rank>\d+)\s*\|\s*(?P<symbol>[^|]+)\|\s*(?P<name>[^|]+)\|\s*(?P<market>[^|]+)\|\s*(?P<kind>[^|]+)\|\s*(?P<reason>[^|]+)\|\s*$"
)


@dataclass(frozen=True)
class WeeklyCandidateBriefEmailDraft:
    subject: str
    text_body: str
    html_body: str | None = None


def build_weekly_candidate_brief_email_subject(report_date: str) -> str:
    return f"[TEST][invest-alpha-os] Weekly Candidate Brief {report_date}"


@dataclass(frozen=True)
class CandidateDigest:
    rank: int
    symbol: str
    name: str
    market: str
    kind: str
    short_reason: str
    counter_evidence: str
    next_checks: str


def _parse_top_candidates(copy_body: str) -> list[CandidateDigest]:
    lines = [x.rstrip() for x in copy_body.splitlines()]
    by_rank: dict[int, dict[str, str]] = {}
    in_table = False
    in_memo = False
    current_rank: int | None = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("| Rank |"):
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            m = _TABLE_ROW_RE.match(line)
            if not m:
                continue
            r = int(m.group("rank"))
            by_rank[r] = {
                "symbol": m.group("symbol").strip(),
                "name": m.group("name").strip(),
                "market": m.group("market").strip(),
                "kind": m.group("kind").strip(),
                "reason": m.group("reason").strip(),
                "counter": "not available in cache",
                "next": "requires next data refresh",
            }
            continue
        if line.startswith("## 候補別メモ"):
            in_memo = True
            in_table = False
            continue
        if in_memo and line.startswith("### "):
            m = re.match(r"^###\s*(\d+)\.\s*", line)
            current_rank = int(m.group(1)) if m else None
            continue
        if in_memo and current_rank is not None and line.startswith("- 反証:"):
            if current_rank in by_rank:
                by_rank[current_rank]["counter"] = line.split(":", 1)[1].strip() or "not available in cache"
            continue
        if in_memo and current_rank is not None and line.startswith("- 次確認:"):
            if current_rank in by_rank:
                by_rank[current_rank]["next"] = line.split(":", 1)[1].strip() or "requires next data refresh"

    out: list[CandidateDigest] = []
    for r in sorted(by_rank.keys()):
        row = by_rank[r]
        out.append(
            CandidateDigest(
                rank=r,
                symbol=row["symbol"],
                name=row["name"],
                market=row["market"],
                kind=row["kind"],
                short_reason=row["reason"],
                counter_evidence=row["counter"],
                next_checks=row["next"],
            )
        )
    return out


def _build_rich_text_body(*, report_date: str, generated_at: str, candidates: list[CandidateDigest]) -> str:
    lines: list[str] = [
        "TEST EMAIL",
        f"report date: {report_date}",
        f"generated at: {generated_at}",
        "disclaimer: this is not investment advice; observation and validation use only.",
        "",
        "## Executive Summary",
        f"- top candidates: {len(candidates)}",
        "- primary objective: candidate screening for next research checks",
        "- safety: observation-only; no execution instructions",
        "",
        "## Top Candidates",
    ]
    if not candidates:
        lines.extend(["- no candidates in copy body", ""])
    for c in candidates:
        qm = compute_candidate_quant_metrics(symbol=c.symbol, market=c.market, report_date=report_date)
        momentum_q: list[str] = []
        counter_q: list[str] = []
        if qm.dist_ma_25_pct is not None and qm.dist_ma_25_pct > 0:
            momentum_q.append("close above 25D MA")
        if qm.dist_ma_75_pct is not None and qm.dist_ma_75_pct > 0:
            momentum_q.append("close above 75D MA")
        if qm.ret_20d_pct is not None and qm.ret_20d_pct > 0:
            momentum_q.append("20D return positive")
        if qm.ret_60d_pct is not None and qm.ret_60d_pct > 0:
            momentum_q.append("60D return positive")
        if qm.volume_ratio_20d is not None and qm.volume_ratio_20d >= 1.5:
            momentum_q.append("volume ratio above 1.5x")
        if qm.dist_ma_25_pct is not None and qm.dist_ma_25_pct < 0:
            counter_q.append("close below 25D MA")
        if qm.dist_ma_25_pct is not None and qm.dist_ma_25_pct > 0.12:
            counter_q.append("distance vs 25D MA > +12% (pullback risk)")
        if qm.ret_60d_pct is not None and qm.ret_60d_pct < 0:
            counter_q.append("60D return negative")
        if qm.freshness_label.startswith("stale"):
            counter_q.append(qm.freshness_label)
        if qm.missing_reason:
            counter_q.append(qm.missing_reason)
        lines.extend(
            [
                "",
                f"### {c.rank}. {c.symbol} — {c.name}",
                f"- Market: {c.market}",
                f"- Candidate Type: {c.kind}",
                f"- Short reason: {c.short_reason}",
                "",
                "#### Moving Average Context",
                f"- 25D MA: {fmt_num(qm.ma_25)} (dist {fmt_pct(qm.dist_ma_25_pct)})",
                f"- 75D MA: {fmt_num(qm.ma_75)} (dist {fmt_pct(qm.dist_ma_75_pct)})",
                f"- 200D MA: {fmt_num(qm.ma_200)} (dist {fmt_pct(qm.dist_ma_200_pct)})",
                "- Interpretation: MA context is cache-only and should be validated with freshness label",
                "",
                "#### Quant Snapshot",
                f"- Latest Close: {fmt_num(qm.latest_close)}",
                f"- Latest Bar Date: {qm.latest_bar_date or 'not available in cache'}",
                f"- Data Freshness: {qm.freshness_label}",
                f"- Returns: 5D {fmt_pct(qm.ret_5d_pct)}, 20D {fmt_pct(qm.ret_20d_pct)}, 60D {fmt_pct(qm.ret_60d_pct)}",
                f"- 52W Range: high {fmt_num(qm.high_52w)} ({fmt_pct(qm.dist_52w_high_pct)} from high), low {fmt_num(qm.low_52w)} ({fmt_pct(qm.dist_52w_low_pct)} from low)",
                f"- Volume: latest {fmt_num(qm.latest_volume, 0)}, 20D avg {fmt_num(qm.avg_volume_20d, 0)}, ratio {fmt_num(qm.volume_ratio_20d)}x",
                "",
                "#### Momentum Rationale",
                f"- {c.short_reason}",
                f"- quant support: {', '.join(momentum_q) if momentum_q else 'not available in cache'}",
                "- trend persistence to be validated with next cache refresh",
                "",
                "#### Counter Evidence",
                f"- {c.counter_evidence}",
                f"- quant risk: {', '.join(counter_q[:2]) if counter_q else 'not available in cache'}",
                "- insufficient bars may hide trend deterioration risk",
                "",
                "#### Next Checks",
                f"- {c.next_checks}",
                "- validate latest bar freshness before deep-dive",
                "",
                "#### Sources",
                f"- market data source: {qm.source}",
                "- signal source: weekly candidate brief score + momentum labels",
                f"- report date: {report_date}",
                f"- generated at: {generated_at}",
                f"- missing data reason: {qm.missing_reason or 'none'}",
            ]
        )
    lines.extend(
        [
            "",
            "## Footer / Safety Notes",
            "- observation and validation only",
            "- this email is a test rendering for Gmail UI review",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _build_rich_html_body(*, report_date: str, generated_at: str, candidates: list[CandidateDigest], footer: str) -> str:
    parts: list[str] = [
        "<html><body style='margin:0;padding:0;background:#f8fafc;color:#111827;'>",
        "<div style='max-width:680px;margin:0 auto;padding:16px;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.55;'>",
        "<div style='background:#fff3cd;border:1px solid #ffe69c;border-radius:8px;padding:12px;margin-bottom:12px;'>",
        "<strong>TEST EMAIL</strong><br>",
        f"report date: {escape(report_date)}<br>",
        f"generated at: {escape(generated_at)}<br>",
        "disclaimer: this is not investment advice; observation and validation use only.",
        "</div>",
        "<h2 style='margin:10px 0 6px;'>Executive Summary</h2>",
        f"<p style='margin:0 0 10px;'>top candidates: {len(candidates)} / observation-only candidate screening</p>",
        "<h2 style='margin:14px 0 8px;'>Top Candidates</h2>",
    ]
    if not candidates:
        parts.append("<p>no candidates in copy body</p>")
    for c in candidates:
        qm = compute_candidate_quant_metrics(symbol=c.symbol, market=c.market, report_date=report_date)
        parts.extend(
            [
                "<div style='background:#ffffff;border:1px solid #e5e7eb;border-radius:10px;padding:12px;margin:10px 0;'>",
                f"<h3 style='margin:0 0 6px;'>{c.rank}. {escape(c.symbol)} - {escape(c.name)}</h3>",
                f"<p style='margin:0 0 8px;'><strong>Market:</strong> {escape(c.market)} / <strong>Type:</strong> {escape(c.kind)}</p>",
                f"<p style='margin:0 0 8px;'><strong>Short reason:</strong> {escape(c.short_reason)}</p>",
                "<h4 style='margin:8px 0 4px;'>Moving Average Context</h4>",
                f"<ul style='margin:0 0 8px 18px;padding:0;'><li>25D MA: {escape(fmt_num(qm.ma_25))} (dist {escape(fmt_pct(qm.dist_ma_25_pct))})</li><li>75D MA: {escape(fmt_num(qm.ma_75))} (dist {escape(fmt_pct(qm.dist_ma_75_pct))})</li><li>200D MA: {escape(fmt_num(qm.ma_200))} (dist {escape(fmt_pct(qm.dist_ma_200_pct))})</li><li>Interpretation: MA context is cache-only and should be validated with freshness label</li></ul>",
                "<h4 style='margin:8px 0 4px;'>Quant Snapshot</h4>",
                f"<ul style='margin:0 0 8px 18px;padding:0;'><li>Latest Close: {escape(fmt_num(qm.latest_close))}</li><li>Latest Bar Date: {escape(qm.latest_bar_date or 'not available in cache')}</li><li>Data Freshness: {escape(qm.freshness_label)}</li><li>Returns: 5D {escape(fmt_pct(qm.ret_5d_pct))}, 20D {escape(fmt_pct(qm.ret_20d_pct))}, 60D {escape(fmt_pct(qm.ret_60d_pct))}</li><li>52W Range: high {escape(fmt_num(qm.high_52w))} ({escape(fmt_pct(qm.dist_52w_high_pct))} from high), low {escape(fmt_num(qm.low_52w))} ({escape(fmt_pct(qm.dist_52w_low_pct))} from low)</li><li>Volume: latest {escape(fmt_num(qm.latest_volume, 0))}, 20D avg {escape(fmt_num(qm.avg_volume_20d, 0))}, ratio {escape(fmt_num(qm.volume_ratio_20d))}x</li></ul>",
                "<h4 style='margin:8px 0 4px;'>Momentum Rationale</h4>",
                f"<ul style='margin:0 0 8px 18px;padding:0;'><li>{escape(c.short_reason)}</li><li>trend persistence to be validated with next cache refresh</li></ul>",
                "<h4 style='margin:8px 0 4px;'>Counter Evidence</h4>",
                f"<ul style='margin:0 0 8px 18px;padding:0;'><li>{escape(c.counter_evidence)}</li><li>insufficient bars may hide trend deterioration risk</li></ul>",
                "<h4 style='margin:8px 0 4px;'>Next Checks</h4>",
                f"<ul style='margin:0 0 8px 18px;padding:0;'><li>{escape(c.next_checks)}</li><li>validate latest bar freshness before deep-dive</li></ul>",
                "<h4 style='margin:8px 0 4px;'>Sources</h4>",
                f"<ul style='margin:0 0 8px 18px;padding:0;'><li>market data source: {escape(qm.source)}</li><li>signal source: weekly candidate brief score + momentum labels</li><li>report date: {escape(report_date)}</li><li>generated at: {escape(generated_at)}</li><li>missing data reason: {escape(qm.missing_reason or 'none')}</li></ul>",
                "</div>",
            ]
        )
    parts.extend(
        [
            "<h2 style='margin:14px 0 8px;'>Footer / Safety Notes</h2>",
            f"<p style='font-size:13px;color:#4b5563;'>{escape(footer)}</p>",
            "</div></body></html>",
        ]
    )
    return "".join(parts)


def _render_copy_markdown_as_simple_html(copy_body: str) -> str:
    blocks: list[str] = []
    for raw in copy_body.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("### "):
            blocks.append(f"<h3>{escape(line[4:])}</h3>")
            continue
        if line.startswith("## "):
            blocks.append(f"<h2>{escape(line[3:])}</h2>")
            continue
        if line.startswith("# "):
            blocks.append(f"<h1>{escape(line[2:])}</h1>")
            continue
        if line.startswith("- "):
            blocks.append(f"<p>- {escape(line[2:])}</p>")
            continue
        blocks.append(f"<p>{escape(line)}</p>")
    return "\n".join(blocks)


def build_weekly_candidate_brief_email_draft(*, report_date: str, copy_body: str) -> WeeklyCandidateBriefEmailDraft:
    """Build Weekly Candidate Brief email body for preview/test send."""

    body_core = copy_body.strip()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    footer = "観測・深掘り候補の整理です。売買推奨・投資助言・発注指示ではありません。"
    candidates = _parse_top_candidates(body_core)
    body = _build_rich_text_body(report_date=report_date, generated_at=generated_at, candidates=candidates)
    if footer not in body:
        body = f"{body.rstrip()}\n\n---\n{footer}\n"
    html_body = _build_rich_html_body(
        report_date=report_date,
        generated_at=generated_at,
        candidates=candidates,
        footer=footer,
    )
    if not candidates:
        html_body = html_body.replace("</div></body></html>", f"{_render_copy_markdown_as_simple_html(body_core)}</div></body></html>")
    return WeeklyCandidateBriefEmailDraft(
        subject=build_weekly_candidate_brief_email_subject(report_date),
        text_body=body,
        html_body=html_body,
    )
