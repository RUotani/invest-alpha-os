"""Compare JP OHLCV sources without account data (strategy only, no live fetch)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from invis_alpha_os.reports.manual_data_schema_guard import DEFAULT_TARGET_TICKERS_CSV


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _strategy_rows() -> list[dict[str, Any]]:
    return [
        {
            "source": "jquants_gated_refresh",
            "coverage": "JP + 285A",
            "freshness": "high if contract allows",
            "human_effort": "low after approval",
            "live_http": "yes (gated)",
            "risk": "medium",
            "recommendation": "primary_if_contract_ok",
        },
        {
            "source": "yahoo_finance_jp_manual_export",
            "coverage": "JP broad",
            "freshness": "high",
            "human_effort": "medium",
            "live_http": "no (browser export)",
            "risk": "low",
            "recommendation": "fallback_manual",
        },
        {
            "source": "kabutan_minkabu_manual",
            "coverage": "JP",
            "freshness": "medium",
            "human_effort": "medium",
            "live_http": "no",
            "risk": "medium",
            "recommendation": "fallback_manual",
        },
        {
            "source": "jpx_public",
            "coverage": "listed JP",
            "freshness": "official",
            "human_effort": "high",
            "live_http": "no",
            "risk": "low",
            "recommendation": "defer",
        },
        {
            "source": "stooq",
            "coverage": "US-first",
            "freshness": "low for 285A",
            "human_effort": "low",
            "live_http": "yes (gated)",
            "risk": "medium",
            "recommendation": "not_recommended_jp",
        },
        {
            "source": "existing_jquants_cache_export",
            "coverage": "JP + 285A",
            "freshness": "none (already in cache)",
            "human_effort": "none",
            "live_http": "no",
            "risk": "low",
            "recommendation": "done_no_freshness_gain",
        },
    ]


@dataclass(frozen=True)
class JpOhlcvAlternativeSourceStrategyResult:
    markdown_text: str
    json_payload: dict[str, Any]


def build_jp_ohlcv_alternative_source_strategy(
    *,
    report_date: str,
    targets_csv: str = DEFAULT_TARGET_TICKERS_CSV,
    jquants_preflight: dict[str, Any] | None = None,
    dry_run_payload: dict[str, Any] | None = None,
) -> JpOhlcvAlternativeSourceStrategyResult:
    targets = [t.strip() for t in targets_csv.split(",") if t.strip()]
    pre = jquants_preflight or {}
    dry = dry_run_payload or {}
    rows_newer = int(dry.get("rows_newer_than_cache_total") or 0)

    if pre.get("refresh_recommended"):
        next_best = "jquants_gated_refresh"
        rationale = "Material gap vs report_date; credentials/config allow gated refresh"
    elif pre.get("contract_limited_risk") == "high":
        next_best = "yahoo_finance_jp_manual_export"
        rationale = "J-Quants contract likely caps new rows; use account-free manual OHLCV export"
    elif rows_newer == 0:
        next_best = "jquants_gated_refresh"
        rationale = "Cache-export CSV adds no rows; need fresher source before actual import"
    else:
        next_best = "manual_browser_export"
        rationale = "Use OHLCV-only CSV then re-run acquisition ux-pack"

    sources = _strategy_rows()
    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "targets": targets,
        "sources": sources,
        "next_best_ohlcv_source": next_best,
        "strategy_rationale": rationale,
        "rows_newer_than_cache_total": rows_newer,
        "live_http_executed": False,
        "cache_write_executed": False,
    }
    lines = [
        "# JP OHLCV Alternative Source Strategy",
        "",
        f"- next_best_ohlcv_source: {next_best}",
        f"- strategy_rationale: {rationale}",
        "",
        "| source | coverage | freshness | human effort | live HTTP | risk | recommendation |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in sources:
        lines.append(
            f"| {row['source']} | {row['coverage']} | {row['freshness']} | {row['human_effort']} | "
            f"{row['live_http']} | {row['risk']} | {row['recommendation']} |"
        )
    lines.append("")
    return JpOhlcvAlternativeSourceStrategyResult(markdown_text="\n".join(lines), json_payload=payload)
