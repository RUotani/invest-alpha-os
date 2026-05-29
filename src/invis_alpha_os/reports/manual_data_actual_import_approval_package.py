"""Actual import approval gate package (dry-run pass required; import not executed)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

APPROVAL_PHRASE = "manual JP bars actual importを実行してよい"


@dataclass(frozen=True)
class ManualDataActualImportApprovalPackageResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_manual_data_actual_import_approval_package(
    *,
    report_date: str,
    discovery_payload: dict[str, Any],
    schema_payload: dict[str, Any] | None,
    dry_run_payload: dict[str, Any] | None,
) -> ManualDataActualImportApprovalPackageResult:
    selected = discovery_payload.get("selected_candidate") or {}
    schema = schema_payload or {}
    dry = dry_run_payload or {}
    dry_pass = dry.get("dry_run_status") == "pass"
    schema_valid = bool(schema.get("schema_valid"))
    prohibited = bool(schema.get("prohibited_columns_detected"))
    ready = dry_pass and schema_valid and not prohibited

    coverage = schema.get("target_ticker_coverage") or []
    date_range: dict[str, Any] = {}
    if coverage:
        mins = [c.get("date_min") for c in coverage if c.get("date_min")]
        maxs = [c.get("date_max") for c in coverage if c.get("date_max")]
        date_range = {"date_min": min(mins) if mins else None, "date_max": max(maxs) if maxs else None}

    risks: list[str] = []
    if prohibited:
        risks.append("prohibited_columns_detected")
    if not schema_valid:
        risks.append("schema_not_valid")
    if not dry_pass:
        risks.append("dry_run_not_pass")
    missing_tickers = [c["ticker"] for c in coverage if c.get("status") == "missing"]
    if missing_tickers:
        risks.append(f"missing_tickers:{','.join(missing_tickers)}")

    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "package_status": "ready_for_user_approval" if ready else "not_ready",
        "selected_file": {
            "filename": selected.get("filename"),
            "directory_label": selected.get("directory_label"),
            "path_redacted": True,
            "redacted_header_summary": selected.get("redacted_header_summary"),
            "schema_ohlcv_candidate": selected.get("schema_ohlcv_candidate"),
        }
        if selected
        else None,
        "schema_valid": schema_valid,
        "prohibited_columns_detected": prohibited,
        "target_ticker_coverage": coverage,
        "date_range": date_range,
        "expected_freshness_improvement": (
            "JP watchlist bars may move from cache_missing/stale toward data_present after approved import"
            if ready
            else "unknown until schema validation and dry-run pass"
        ),
        "actual_import_command_candidate": (
            ".venv/bin/python -m invis_alpha_os.cli.main "
            f"weekly-candidate-brief-manual-data-import-flow --report-date {report_date} "
            "--execute-import"
            if ready
            else "blocked until dry_run_status=pass and user approval phrase"
        ),
        "rollback_cleanup_note": (
            "Dry-run used working-dir artifacts only. After approved import, review outputs/manual_data "
            "and revert cache writes only via documented rollback (not executed in this pack)."
        ),
        "risks": risks,
        "safety_checklist": {
            "actual_import": False,
            "cache_write": False,
            "live_http": False,
            "broker_raw_printed": False,
            "manual_raw_printed": False,
        },
        "required_approval_phrase": APPROVAL_PHRASE,
        "dry_run_status": dry.get("dry_run_status", "not_run"),
        "execute_import": False,
        "contents_printed": False,
    }

    lines = [
        "# Manual Data Actual Import Approval Package",
        "",
        f"- package_status: {payload['package_status']}",
        f"- schema_valid: {str(schema_valid).lower()}",
        f"- prohibited_columns_detected: {str(prohibited).lower()}",
        f"- dry_run_status: {payload['dry_run_status']}",
        f"- execute_import: false",
        "",
        "## Required approval phrase",
        "",
        "```text",
        APPROVAL_PHRASE,
        "```",
        "",
        "## Risks",
        "",
    ]
    if risks:
        for risk in risks:
            lines.append(f"- {risk}")
    else:
        lines.append("- (none identified)")
    lines.extend(
        [
            "",
            "## Command candidate (do not run without approval)",
            "",
            f"```bash",
            payload["actual_import_command_candidate"],
            "```",
            "",
        ]
    )
    return ManualDataActualImportApprovalPackageResult(markdown_text="\n".join(lines), json_payload=payload)
