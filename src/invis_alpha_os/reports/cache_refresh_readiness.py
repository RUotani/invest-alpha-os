"""Read-only cache refresh readiness report builder."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.data_contract_limit import assess_data_contract_limit
from invis_alpha_os.reports.jquants_date_range import contract_dates_from_env


@dataclass(frozen=True)
class CacheRefreshReadinessResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _provider_candidate(market: str) -> str:
    norm = (market or "").strip().upper()
    if norm == "JP":
        return "jquants"
    if norm in {"US", "ETF"}:
        return "us_daily_bars"
    return "unknown"


def _priority(*, freshness_label: str, stale_days: int | None, timing: str) -> tuple[str, str]:
    if freshness_label == "data_update_required" or (stale_days is not None and stale_days > 30):
        return "high", "stale_daysが30日超、またはdata_update_required"
    if freshness_label == "stale" or (stale_days is not None and stale_days > 7):
        return "medium", "stale_daysが8日以上"
    if freshness_label == "partial_history" or timing == "data_insufficient":
        return "low", "部分履歴不足またはdata_insufficient"
    return "none", "refresh不要"


def _extract_stale_candidates(context_json_payload: dict[str, Any], *, report_date: str) -> list[dict[str, Any]]:
    rows = context_json_payload.get("candidates")
    candidates = [x for x in rows if isinstance(x, dict)] if isinstance(rows, list) else []
    out: list[dict[str, Any]] = []
    for row in candidates:
        ticker = str(row.get("ticker", "")).strip()
        if not ticker:
            continue
        freshness = str(row.get("freshness_classification", "")).strip() or "unknown"
        stale_days_raw = row.get("stale_days")
        stale_days = stale_days_raw if isinstance(stale_days_raw, int) else None
        timing = str(row.get("timing", "")).strip()
        if freshness not in {"stale", "data_update_required", "cache_missing", "partial_history"}:
            continue
        prio, reason = _priority(freshness_label=freshness, stale_days=stale_days, timing=timing)
        contract_limit = assess_data_contract_limit(
            latest_bar_date=str(row.get("latest_bar_date", "")).strip() or None,
            report_date=report_date,
            contract_to=contract_dates_from_env(dict(os.environ)).get("data_available_to"),
            freshness_classification=freshness,
        )
        out.append(
            {
                "ticker": ticker,
                "market": str(row.get("market", "")).strip().upper() or "UNKNOWN",
                "stale_days": stale_days,
                "latest_bar_date": row.get("latest_bar_date"),
                "freshness_label": freshness,
                "missing_reason": ", ".join(row.get("missing_data_reasons") or []) or None,
                "provider_candidate": _provider_candidate(str(row.get("market", ""))),
                "refresh_priority": prio,
                "reason": reason,
                "timing_warnings": row.get("timing_warnings") or [],
                **contract_limit,
            }
        )
    out.sort(key=lambda x: ({"high": 0, "medium": 1, "low": 2, "none": 3}.get(x["refresh_priority"], 9), -(x.get("stale_days") or -1)))
    return out


def _scan_gate_diagnostics(repo_root: Path) -> dict[str, Any]:
    targets = [
        repo_root / "src" / "invis_alpha_os" / "cli" / "main.py",
        repo_root / "src" / "invis_alpha_os" / "data",
    ]
    blobs: list[str] = []
    for target in targets:
        if target.is_file():
            blobs.append(target.read_text(encoding="utf-8"))
            continue
        if target.is_dir():
            for f in target.rglob("*.py"):
                try:
                    blobs.append(f.read_text(encoding="utf-8"))
                except OSError:
                    continue
    text = "\n".join(blobs)
    command_names: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if '@app.command("' in line:
            start = line.find('@app.command("') + len('@app.command("')
            end = line.find('"', start)
            if end > start:
                name = line[start:end]
                if any(k in name for k in ("cache", "jquants", "discover", "signals")) and name not in command_names:
                    command_names.append(name)
    return {
        "live_http_gate_present": ("confirm_live_http_required" in text) or ("live_http" in text),
        "cache_write_gate_present": "refused_cache_write" in text,
        "dry_run_default": ("--dry-run" in text) or ("dry_run" in text),
        "required_env_candidates": sorted(
            {
                tok
                for tok in ("ALLOW_LIVE_HTTP", "CONFIRM_LIVE_HTTP", "GMAIL_ALLOW_INTERACTIVE_OAUTH")
                if tok in text
            }
        ),
        "required_confirm_candidates": sorted(
            {
                tok
                for tok in ("confirm_live_http_required", "refused_cache_write")
                if tok in text
            }
        ),
        "known_cli_candidates": command_names[:20],
    }


def build_cache_refresh_readiness_report(
    *,
    report_date: str,
    repo_root: Path,
    context_json_payload: dict[str, Any] | None,
    trap_json_payload: dict[str, Any] | None = None,
) -> CacheRefreshReadinessResult:
    _ = trap_json_payload
    context_payload = context_json_payload if isinstance(context_json_payload, dict) else {}
    stale_candidates = _extract_stale_candidates(context_payload, report_date=report_date)
    diagnostics = _scan_gate_diagnostics(repo_root)
    payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "dry_run_only": True,
        "live_http_executed": False,
        "cache_write_executed": False,
        "stale_candidates": stale_candidates,
        "gate_diagnostics": diagnostics,
        "notes": [
            "このレポートはread-only診断です。",
            "実refresh/live HTTP/cache writeは実行していません。",
        ],
    }
    lines = [
        "# Cache Refresh Readiness Report",
        "",
        "## メタ情報",
        f"- report_date: {report_date}",
        f"- generated_at: {payload['generated_at']}",
        "- dry_run_only: true",
        "- live_http_executed: false",
        "- cache_write_executed: false",
        "",
        "## 要更新候補",
        "| ticker | market | stale_days | latest_bar_date | freshness | provider候補 | refresh優先度 | 理由 |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- |",
    ]
    if not stale_candidates:
        lines.append("| (none) | - | - | - | - | - | - | stale候補なし |")
    for row in stale_candidates[:50]:
        lines.append(
            f"| {row['ticker']} | {row['market']} | {row['stale_days']} | {row['latest_bar_date']} | {row['freshness_label']} | {row['provider_candidate']} | {row['refresh_priority']} | {row['reason']} |"
        )
    lines.extend(
        [
            "",
            "## ゲート診断",
            f"- live HTTP gate: {diagnostics['live_http_gate_present']}",
            f"- cache write gate: {diagnostics['cache_write_gate_present']}",
            f"- dry-run default: {diagnostics['dry_run_default']}",
            f"- required env: {', '.join(diagnostics['required_env_candidates']) or '(none)'}",
            f"- required confirm: {', '.join(diagnostics['required_confirm_candidates']) or '(none)'}",
            f"- known CLI候補: {', '.join(diagnostics['known_cli_candidates']) or '(none)'}",
            "",
            "## 次に人間が確認すべきこと",
            "- high優先度stale銘柄の更新範囲（JP/US/ETF）を確定する",
            "- refresh実行前にlive HTTP/cache writeの明示ゲート条件を確定する",
            "- 実refreshは別PRでdry-run既定のまま段階的に有効化する",
            "",
        ]
    )
    return CacheRefreshReadinessResult(markdown_text="\n".join(lines), json_payload=payload)
