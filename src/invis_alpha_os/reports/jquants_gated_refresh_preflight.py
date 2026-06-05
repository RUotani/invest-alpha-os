"""J-Quants gated refresh preflight (read-only; no live HTTP, no cache write)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from invis_alpha_os.reports.data_contract_limit import assess_data_contract_limit
from invis_alpha_os.reports.jquants_date_range import (
    contract_dates_from_env,
    is_effective_refresh_range,
    latest_bar_dates_for_targets,
    resolve_refresh_date_range,
)
from invis_alpha_os.reports.jquants_preflight import assess_jquants_credentials
from invis_alpha_os.reports.manual_data_schema_guard import DEFAULT_TARGET_TICKERS_CSV


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_targets(targets_csv: str) -> list[str]:
    return [part.strip() for part in targets_csv.split(",") if part.strip()]


def _gap_days(report_date: str, latest_bar: str | None) -> int | None:
    if not latest_bar:
        return None
    try:
        rd = date.fromisoformat(report_date)
        ld = date.fromisoformat(latest_bar)
        return (rd - ld).days
    except ValueError:
        return None


@dataclass(frozen=True)
class JQuantsGatedRefreshPreflightResult:
    markdown_text: str
    json_payload: dict[str, Any]


def build_jquants_gated_refresh_preflight(
    *,
    report_date: str,
    targets_csv: str = DEFAULT_TARGET_TICKERS_CSV,
    env: dict[str, str] | None = None,
) -> JQuantsGatedRefreshPreflightResult:
    env_map = dict(os.environ) if env is None else env
    targets = _parse_targets(targets_csv)
    creds = assess_jquants_credentials(env_map)
    contract = contract_dates_from_env(env_map)
    date_range = resolve_refresh_date_range(env_map, allow_date_clamp=True).as_dict()
    latest_by_ticker = latest_bar_dates_for_targets(targets)

    per_ticker: list[dict[str, Any]] = []
    max_gap = 0
    contract_limited_count = 0
    for ticker in targets:
        latest = latest_by_ticker.get(ticker)
        gap = _gap_days(report_date, latest)
        if gap is not None and gap > max_gap:
            max_gap = gap
        contract_diag = assess_data_contract_limit(
            latest_bar_date=latest,
            report_date=report_date,
            contract_to=contract.get("data_available_to"),
            freshness_classification="data_update_required",
        )
        limited = bool(contract_diag.get("data_contract_limited"))
        if limited:
            contract_limited_count += 1
        clamped_to = str(date_range.get("clamped_to_date") or "")
        effective = is_effective_refresh_range(clamped_to, latest) if clamped_to else False
        per_ticker.append(
            {
                "ticker": ticker,
                "cache_latest_date": latest,
                "gap_days_to_report_date": gap,
                "data_contract_limited": limited,
                "refresh_may_extend_latest": effective,
            }
        )

    credentials_available = bool(creds.get("api_key_present")) and bool(creds.get("jquants_enabled"))
    if contract_limited_count >= len(targets):
        contract_risk = "high"
    elif contract_limited_count > 0:
        contract_risk = "medium"
    else:
        contract_risk = "low"

    refresh_allowed = bool(creds.get("refresh_allowed"))
    if not refresh_allowed:
        expected_new_rows = "none"
        refresh_recommended = False
    elif contract_risk == "high":
        expected_new_rows = "none"
        refresh_recommended = False
    elif max_gap > 30 and any(row.get("refresh_may_extend_latest") for row in per_ticker):
        expected_new_rows = "likely"
        refresh_recommended = True
    elif max_gap > 7:
        expected_new_rows = "unknown"
        refresh_recommended = credentials_available and contract_risk != "high"
    else:
        expected_new_rows = "none"
        refresh_recommended = False

    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "targets": targets,
        "per_ticker": per_ticker,
        "max_gap_days": max_gap,
        "credentials_available": credentials_available,
        "refresh_allowed_config": refresh_allowed,
        "refresh_recommended": refresh_recommended,
        "expected_new_rows": expected_new_rows,
        "contract_limited_risk": contract_risk,
        "requires_user_approval": True,
        "approval_phrase_candidate": "J-Quants gated refreshを実行してよい",
        "data_available_to": contract.get("data_available_to"),
        "data_available_to_present": contract.get("data_available_to_present"),
        "requested_to_date": date_range.get("requested_to_date"),
        "clamped_to_date": date_range.get("clamped_to_date"),
        "date_range_clamp_required": date_range.get("date_range_clamp_required"),
        "live_http_executed": False,
        "cache_write_executed": False,
        "secrets_printed": False,
    }
    lines = [
        "# J-Quants Gated Refresh Preflight",
        "",
        f"- refresh_recommended: {str(refresh_recommended).lower()}",
        f"- expected_new_rows: {expected_new_rows}",
        f"- contract_limited_risk: {contract_risk}",
        f"- max_gap_days: {max_gap}",
        f"- credentials_available: {str(credentials_available).lower()}",
        "- requires_user_approval: true",
        "",
        "| ticker | cache_latest | gap_days | contract_limited | may_extend |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in per_ticker:
        lines.append(
            f"| {row['ticker']} | {row.get('cache_latest_date') or '-'} | "
            f"{row.get('gap_days_to_report_date') if row.get('gap_days_to_report_date') is not None else '-'} | "
            f"{str(row.get('data_contract_limited', False)).lower()} | "
            f"{str(row.get('refresh_may_extend_latest', False)).lower()} |"
        )
    lines.append("")
    return JQuantsGatedRefreshPreflightResult(markdown_text="\n".join(lines), json_payload=payload)
