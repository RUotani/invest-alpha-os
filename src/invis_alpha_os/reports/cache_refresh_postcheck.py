"""Post-refresh validation harness (read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class CacheRefreshPostcheckResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _candidate_map(payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}
    rows = payload.get("candidates")
    if not isinstance(rows, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker", "")).strip()
        if ticker:
            out[ticker] = row
    return out


def _stale_map(readiness_payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(readiness_payload, dict):
        return {}
    rows = readiness_payload.get("stale_candidates")
    if not isinstance(rows, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker", "")).strip()
        if ticker:
            out[ticker] = row
    return out


def _plan_map(plan_payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(plan_payload, dict):
        return {}
    rows = plan_payload.get("targets")
    if not isinstance(rows, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker", "")).strip()
        if ticker:
            out[ticker] = row
    return out


def build_cache_refresh_postcheck(
    *,
    report_date: str,
    before_context_json_payload: dict[str, Any] | None,
    after_context_json_payload: dict[str, Any] | None,
    before_readiness_json_payload: dict[str, Any] | None,
    after_readiness_json_payload: dict[str, Any] | None,
    before_plan_json_payload: dict[str, Any] | None = None,
    after_plan_json_payload: dict[str, Any] | None = None,
) -> CacheRefreshPostcheckResult:
    before_candidates = _candidate_map(before_context_json_payload)
    after_candidates = _candidate_map(after_context_json_payload)
    before_stale = _stale_map(before_readiness_json_payload)
    after_stale = _stale_map(after_readiness_json_payload)
    before_plan = _plan_map(before_plan_json_payload)
    after_plan = _plan_map(after_plan_json_payload)
    tickers = sorted(set(before_candidates) | set(after_candidates) | set(before_stale) | set(after_stale))
    rows: list[dict[str, Any]] = []
    for ticker in tickers:
        b = before_candidates.get(ticker, {})
        a = after_candidates.get(ticker, {})
        b_stale = before_stale.get(ticker, {})
        a_stale = after_stale.get(ticker, {})
        rows.append(
            {
                "ticker": ticker,
                "before_freshness": b.get("freshness_classification"),
                "after_freshness": a.get("freshness_classification"),
                "before_stale_days": b.get("stale_days"),
                "after_stale_days": a.get("stale_days"),
                "readiness_before": ticker in before_stale,
                "readiness_after": ticker in after_stale,
                "execution_plan_before": ticker in before_plan,
                "execution_plan_after": ticker in after_plan,
            }
        )
    payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "dry_run_only": True,
        "live_http_executed": False,
        "cache_write_executed": False,
        "actual_refresh_executed": False,
        "comparison_rows": rows,
    }
    lines = [
        "# Cache Refresh Postcheck",
        "",
        "## メタ情報",
        f"- report_date: {report_date}",
        f"- generated_at: {payload['generated_at']}",
        "- dry_run_only: true",
        "- live_http_executed: false",
        "- cache_write_executed: false",
        "- actual_refresh_executed: false",
        "",
        "## 比較",
        "| ticker | before_freshness | after_freshness | before_stale_days | after_stale_days | readiness_before | readiness_after | plan_before | plan_after |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- | --- |",
    ]
    if not rows:
        lines.append("| (none) | - | - | - | - | false | false | false | false |")
    for row in rows:
        lines.append(
            "| {ticker} | {before_freshness} | {after_freshness} | {before_stale_days} | {after_stale_days} | {readiness_before} | {readiness_after} | {execution_plan_before} | {execution_plan_after} |".format(
                **row
            )
        )
    lines.append("")
    return CacheRefreshPostcheckResult(markdown_text="\n".join(lines), json_payload=payload)
