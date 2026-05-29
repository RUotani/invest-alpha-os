"""J-Quants gated refresh approval package (no live HTTP, no cache write)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from invis_alpha_os.reports.jquants_env_file_discovery import REQUIRED_JQUANTS_KEYS
from invis_alpha_os.reports.manual_data_schema_guard import DEFAULT_TARGET_TICKERS_CSV

APPROVAL_PHRASE = "J-Quants gated refreshを実行してよい"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class JQuantsGatedRefreshApprovalPackageResult:
    markdown_text: str
    json_payload: dict[str, Any]


def build_jquants_gated_refresh_approval_package(
    *,
    report_date: str,
    targets_csv: str = DEFAULT_TARGET_TICKERS_CSV,
    env_discovery: dict[str, Any],
    preflight: dict[str, Any],
) -> JQuantsGatedRefreshApprovalPackageResult:
    targets = [t.strip() for t in targets_csv.split(",") if t.strip()]
    credentials_available = bool(preflight.get("credentials_available"))
    required_keys_present = bool(env_discovery.get("required_keys_present"))
    missing_keys = list(env_discovery.get("missing_required_keys") or [])
    refresh_recommended = bool(preflight.get("refresh_recommended"))
    contract_risk = str(preflight.get("contract_limited_risk", "unknown"))

    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "credentials_available": credentials_available,
        "required_keys_present": required_keys_present,
        "missing_keys": missing_keys,
        "required_key_names": list(REQUIRED_JQUANTS_KEYS),
        "target_tickers": targets,
        "cache_latest_by_ticker": {
            row["ticker"]: row.get("cache_latest_date")
            for row in preflight.get("per_ticker", [])
            if isinstance(row, dict)
        },
        "max_gap_days": preflight.get("max_gap_days"),
        "expected_new_rows": preflight.get("expected_new_rows"),
        "contract_limited_risk": contract_risk,
        "refresh_recommended": refresh_recommended,
        "live_http_required": True,
        "cache_write_required": True,
        "requires_user_approval": True,
        "required_approval_phrase": APPROVAL_PHRASE,
        "candidate_command": (
            ".venv/bin/python -m invis_alpha_os.cli.main debug jquants-watchlist-bars-cache "
            f"--from-date <computed> --to-date {report_date} --live --write-cache "
            "(blocked until approval; exact flags per runbook)"
        ),
        "rollback_cleanup_note": (
            "Refresh writes sanitized JSON under outputs/market_data/jquants_daily_bars/. "
            "Rollback via git checkout of those paths or restore from backup; not executed in v29."
        ),
        "safety_checklist": {
            "jquants_live_http": False,
            "cache_write": False,
            "actual_refresh": False,
            "actual_import": False,
            "secrets_printed": False,
        },
        "package_status": (
            "ready_for_refresh_approval"
            if refresh_recommended and required_keys_present and credentials_available
            else "not_ready"
        ),
    }
    lines = [
        "# J-Quants Gated Refresh Approval Package",
        "",
        f"- package_status: {payload['package_status']}",
        f"- refresh_recommended: {str(refresh_recommended).lower()}",
        f"- credentials_available: {str(credentials_available).lower()}",
        f"- required_keys_present: {str(required_keys_present).lower()}",
        f"- max_gap_days: {preflight.get('max_gap_days')}",
        f"- contract_limited_risk: {contract_risk}",
        f"- expected_new_rows: {preflight.get('expected_new_rows')}",
        "",
        "## Required approval phrase",
        "",
        "```text",
        APPROVAL_PHRASE,
        "```",
        "",
        "## Safety checklist (v29)",
        "",
        "- J-Quants live HTTP: not executed",
        "- cache write: not executed",
        "- actual refresh: not executed",
        "",
    ]
    if missing_keys:
        lines.extend(["## Missing keys", "", f"- {', '.join(missing_keys)}", ""])
    return JQuantsGatedRefreshApprovalPackageResult(markdown_text="\n".join(lines), json_payload=payload)
