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
    rows_newer = int(dry.get("rows_newer_than_cache_total") or 0)
    expected_freshness = str(dry.get("expected_freshness_improvement") or "")
    no_freshness_gain = rows_newer == 0 or expected_freshness == "none_identified"
    ready = dry_pass and schema_valid and not prohibited and not no_freshness_gain
    if dry_pass and schema_valid and not prohibited and no_freshness_gain:
        import_benefit = "low"
        actual_import_recommended = False
        defer_reason = "no_rows_newer_than_cache"
    elif ready:
        import_benefit = "high" if rows_newer > 10 else "medium"
        actual_import_recommended = True
        defer_reason = None
    else:
        import_benefit = "none"
        actual_import_recommended = False
        defer_reason = "dry_run_or_schema_not_pass"

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
    if no_freshness_gain and dry_pass:
        risks.append("no_rows_newer_than_cache")

    package_status = "not_ready"
    if ready:
        package_status = "ready_for_user_approval"
    elif dry_pass and schema_valid and no_freshness_gain:
        package_status = "defer_import_low_benefit"

    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "package_status": package_status,
        "import_benefit": import_benefit,
        "actual_import_recommended": actual_import_recommended,
        "defer_reason": defer_reason,
        "rows_newer_than_cache_total": rows_newer,
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
            "rows_newer_than_cache"
            if rows_newer > 0
            else "none_identified"
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
        f"- import_benefit: {import_benefit}",
        f"- actual_import_recommended: {str(actual_import_recommended).lower()}",
        f"- rows_newer_than_cache_total: {rows_newer}",
        f"- schema_valid: {str(schema_valid).lower()}",
        f"- prohibited_columns_detected: {str(prohibited).lower()}",
        f"- dry_run_status: {payload['dry_run_status']}",
        "- execute_import: false",
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
            "```bash",
            payload["actual_import_command_candidate"],
            "```",
            "",
        ]
    )
    return ManualDataActualImportApprovalPackageResult(markdown_text="\n".join(lines), json_payload=payload)
