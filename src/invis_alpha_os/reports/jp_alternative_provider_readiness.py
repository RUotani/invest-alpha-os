"""Read-only inventory of JP alternative data providers when J-Quants is contract-limited."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.data.jquants_daily_bars_cache import load_jquants_daily_bars_cache
from invis_alpha_os.reports.data_contract_limit import assess_data_contract_limit
from invis_alpha_os.reports.jquants_date_range import contract_dates_from_env

_REPO_SCAN_ROOTS = ("src/invis_alpha_os/data", "src/invis_alpha_os/reports")
_PROVIDER_MARKERS: dict[str, tuple[str, ...]] = {
    "jquants": ("jquants_client.py", "jquants_daily_bars_cache"),
    "stooq": ("us_stooq_daily_csv", "stooq_live_preview"),
    "manual_csv": ("manual_csv", "csv_import"),
    "local_csv": ("local_csv",),
    "yfinance": ("yfinance",),
    "alpha_vantage": ("alpha_vantage",),
}


@dataclass(frozen=True)
class JpAlternativeProviderReadinessResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _repo_has_marker(repo_root: Path, markers: tuple[str, ...]) -> bool:
    for rel_root in _REPO_SCAN_ROOTS:
        root = repo_root / rel_root
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            name = path.name
            if any(marker in name for marker in markers):
                return True
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if any(marker in text for marker in markers):
                return True
    return False


def _parse_targets_csv(targets_csv: str) -> list[str]:
    return [part.strip() for part in targets_csv.split(",") if part.strip()]


def _jquants_contract_limited(
    *,
    targets: list[str],
    report_date: str,
    env: dict[str, str],
) -> bool:
    contract_to = contract_dates_from_env(env).get("data_available_to")
    if not contract_to:
        return False
    for ticker in targets:
        loaded = load_jquants_daily_bars_cache(ticker)
        if not loaded:
            continue
        bars, _meta = loaded
        latest = str(bars[-1]["date"]).strip() if bars else None
        diag = assess_data_contract_limit(
            latest_bar_date=latest,
            report_date=report_date,
            contract_to=contract_to,
            freshness_classification="data_update_required",
        )
        if diag.get("data_contract_limited"):
            return True
    return False


def _build_candidates(repo_root: Path) -> list[dict[str, Any]]:
    jquants_impl = _repo_has_marker(repo_root, _PROVIDER_MARKERS["jquants"])
    stooq_impl = _repo_has_marker(repo_root, _PROVIDER_MARKERS["stooq"])
    manual_impl = _repo_has_marker(repo_root, _PROVIDER_MARKERS["manual_csv"])
    local_impl = _repo_has_marker(repo_root, _PROVIDER_MARKERS["local_csv"])
    return [
        {
            "provider": "manual_csv",
            "available": True,
            "implemented_in_repo": manual_impl,
            "live_http_required": False,
            "cache_write_required": True,
            "terms_risk": "low",
            "priority": "high",
            "reason": "Manual export can update JP daily bars without provider API contract extension",
        },
        {
            "provider": "local_csv",
            "available": True,
            "implemented_in_repo": local_impl,
            "live_http_required": False,
            "cache_write_required": True,
            "terms_risk": "low",
            "priority": "high",
            "reason": "Local CSV drop-in path for broker exports (readiness/plan only until importer lands)",
        },
        {
            "provider": "jquants",
            "available": jquants_impl,
            "implemented_in_repo": jquants_impl,
            "live_http_required": True,
            "cache_write_required": True,
            "terms_risk": "medium",
            "priority": "medium",
            "reason": "Existing JP provider; contract end may block further refresh without plan upgrade",
        },
        {
            "provider": "stooq",
            "available": stooq_impl,
            "implemented_in_repo": stooq_impl,
            "live_http_required": True,
            "cache_write_required": True,
            "terms_risk": "medium",
            "priority": "low",
            "reason": "Implemented for US preview; JP symbol coverage and terms must be validated before use",
        },
        {
            "provider": "yfinance",
            "available": False,
            "implemented_in_repo": _repo_has_marker(repo_root, _PROVIDER_MARKERS["yfinance"]),
            "live_http_required": True,
            "cache_write_required": True,
            "terms_risk": "medium",
            "priority": "low",
            "reason": "Mentioned in docs only; not wired for JP cache refresh in this repo",
        },
        {
            "provider": "scraping",
            "available": False,
            "implemented_in_repo": False,
            "live_http_required": True,
            "cache_write_required": True,
            "terms_risk": "high",
            "priority": "none",
            "reason": "Explicitly out of scope (terms unknown / prohibited for automation)",
        },
    ]


def build_jp_alternative_provider_readiness(
    *,
    report_date: str,
    targets_csv: str,
    repo_root: Path,
    env: dict[str, str] | None = None,
) -> JpAlternativeProviderReadinessResult:
    env_map = env if env is not None else dict(os.environ)
    targets = _parse_targets_csv(targets_csv)
    candidates = _build_candidates(repo_root)
    contract_limited = _jquants_contract_limited(targets=targets, report_date=report_date, env=env_map)
    recommended = next((c for c in candidates if c["priority"] == "high" and c["available"]), None)
    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "target_market": "JP",
        "targets": targets,
        "jquants_contract_limited": contract_limited,
        "alternative_candidates": candidates,
        "recommended_provider": recommended["provider"] if recommended else "manual_csv",
        "dry_run_only": True,
        "live_http_executed": False,
        "cache_write_executed": False,
        "actual_refresh_executed": False,
        "notes": [
            "Read-only readiness inventory; no provider calls executed.",
            "Prefer manual_csv/local_csv before enabling new live HTTP providers.",
        ],
    }
    lines = [
        "# JP Alternative Provider Readiness",
        "",
        "## メタ情報",
        f"- report_date: {report_date}",
        f"- generated_at: {payload['generated_at']}",
        "- target_market: JP",
        f"- targets: {', '.join(targets)}",
        f"- jquants_contract_limited: {str(contract_limited).lower()}",
        f"- recommended_provider: {payload['recommended_provider']}",
        "- dry_run_only: true",
        "",
        "## 候補",
        "| provider | available | implemented | live_http | cache_write | terms_risk | priority | reason |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in candidates:
        lines.append(
            f"| {row['provider']} | {str(row['available']).lower()} | {str(row['implemented_in_repo']).lower()} | "
            f"{str(row['live_http_required']).lower()} | {str(row['cache_write_required']).lower()} | "
            f"{row['terms_risk']} | {row['priority']} | {row['reason']} |"
        )
    lines.extend(["", "## 次アクション", "- 人手CSV export → gated import PR（live HTTPなし）", ""])
    return JpAlternativeProviderReadinessResult(markdown_text="\n".join(lines), json_payload=payload)
