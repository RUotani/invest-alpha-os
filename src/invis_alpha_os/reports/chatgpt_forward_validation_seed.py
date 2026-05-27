"""Forward validation seed builder for weekly decision tracking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any


@dataclass(frozen=True)
class ForwardValidationSeedResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _add_weeks(iso_date: str, weeks: int) -> str:
    base = date.fromisoformat(iso_date)
    return (base + timedelta(days=weeks * 7)).isoformat()


def build_forward_validation_seed(
    *,
    report_date: str,
    context_json_payload: dict[str, Any],
) -> ForwardValidationSeedResult:
    eval_dates = {
        "plus_4w": _add_weeks(report_date, 4),
        "plus_12w": _add_weeks(report_date, 12),
        "plus_26w": _add_weeks(report_date, 26),
    }
    candidates = context_json_payload.get("candidates")
    rows = [x for x in candidates if isinstance(x, dict)] if isinstance(candidates, list) else []

    out_candidates: list[dict[str, Any]] = []
    md_lines: list[str] = [
        "# Forward Validation Decision Seed",
        "",
        f"- report_date: {report_date}",
        f"- +4w: {eval_dates['plus_4w']}",
        f"- +12w: {eval_dates['plus_12w']}",
        f"- +26w: {eval_dates['plus_26w']}",
        "",
    ]
    for row in rows:
        ticker = str(row.get("ticker", "")).strip()
        item = {
            "ticker": ticker,
            "name": str(row.get("name", "")).strip(),
            "market": str(row.get("market", "")).strip(),
            "rank": row.get("rank"),
            "classification": str(row.get("classification", "")).strip(),
            "timing": str(row.get("timing", "")).strip(),
            "latest_close_at_report": row.get("latest_close"),
            "latest_bar_date": str(row.get("latest_bar_date", "")).strip(),
            "freshness": str(row.get("freshness", "")).strip(),
            "quant_snapshot": {
                "returns": row.get("returns") or {},
                "moving_averages": row.get("moving_averages") or {},
                "range_52w": row.get("range_52w") or {},
                "volume": row.get("volume") or {},
                "missing_data_reasons": row.get("missing_data_reasons") or [],
            },
            "momentum_rationale": row.get("momentum_rationale") or [],
            "counter_evidence": row.get("counter_evidence") or [],
            "next_checks": row.get("next_checks") or [],
            "human_feedback": {
                "decision": "",
                "reason": "",
                "action": "",
                "invalidation": "",
                "next_review_date": "",
                "memo": "",
            },
            "future_results": {"plus_4w": None, "plus_12w": None, "plus_26w": None},
        }
        out_candidates.append(item)
        md_lines.extend(
            [
                f"## {ticker} — {item['name']}",
                f"- classification: {item['classification']}",
                f"- timing: {item['timing']}",
                f"- latest_close_at_report: {item['latest_close_at_report']}",
                f"- latest_bar_date: {item['latest_bar_date']}",
                f"- +4w review: {eval_dates['plus_4w']}",
                f"- +12w review: {eval_dates['plus_12w']}",
                f"- +26w review: {eval_dates['plus_26w']}",
                "",
            ]
        )

    payload: dict[str, Any] = {
        "report_date": report_date,
        "evaluation_dates": eval_dates,
        "candidates": out_candidates,
    }
    return ForwardValidationSeedResult(markdown_text="\n".join(md_lines), json_payload=payload)
