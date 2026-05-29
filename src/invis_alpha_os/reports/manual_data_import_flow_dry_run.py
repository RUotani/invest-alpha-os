"""Dry-run manual data import flow report (execute_import=false, no cache write)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.manual_data_import_flow import build_manual_data_import_flow
from invis_alpha_os.reports.manual_data_schema_guard import DEFAULT_TARGET_TICKERS_CSV


@dataclass(frozen=True)
class ManualDataImportFlowDryRunResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_manual_data_import_flow_dry_run(
    *,
    input_path: Path,
    targets_csv: str = DEFAULT_TARGET_TICKERS_CSV,
    report_date: str,
    repo_root: Path,
    working_dir: Path,
    provider: str = "manual_jp_bars",
    scope: str = "jp_watchlist",
    schema_payload: dict[str, Any] | None = None,
) -> ManualDataImportFlowDryRunResult:
    flow = build_manual_data_import_flow(
        input_path=input_path,
        targets_csv=targets_csv,
        report_date=report_date,
        provider=provider,
        scope=scope,
        execute_import=False,
        repo_root=repo_root,
        working_dir=working_dir,
    )
    dry_status = "pass"
    if flow.json_payload.get("overall_status") not in {"dry_run_complete", "success"}:
        dry_status = "blocked"
    blockers: list[str] = []
    if not flow.json_payload.get("importable"):
        blockers.append("not_importable")
    steps = flow.json_payload.get("steps") or {}
    if isinstance(steps, dict):
        validation = steps.get("validation") or {}
        if isinstance(validation, dict) and validation.get("errors"):
            blockers.append("validation_errors")

    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "execute_import": False,
        "actual_import": False,
        "cache_write": False,
        "dry_run_status": dry_status,
        "overall_status": flow.json_payload.get("overall_status"),
        "importable": flow.json_payload.get("importable"),
        "rows_newer_than_cache_total": flow.json_payload.get("rows_newer_than_cache_total"),
        "target_tickers_present": flow.json_payload.get("targets", []),
        "date_min": (schema_payload or {}).get("date_min"),
        "date_max": (schema_payload or {}).get("date_max"),
        "row_count": (schema_payload or {}).get("row_count"),
        "expected_freshness_improvement": "rows_newer_than_cache"
        if flow.json_payload.get("rows_newer_than_cache_total")
        else "none_identified",
        "blockers": blockers,
        "actual_import_gate_status": "pending_user_approval",
        "next_gate": "manual JP bars actual importを実行してよい",
        "flow": flow.json_payload,
        "contents_printed": False,
    }
    lines = [
        "# Manual Data Import Flow Dry Run",
        "",
        f"- dry_run_status: {dry_status}",
        f"- execute_import: false",
        f"- actual_import: false",
        f"- cache_write: false",
        f"- overall_status: {flow.json_payload.get('overall_status')}",
        f"- importable: {flow.json_payload.get('importable')}",
        f"- rows_newer_than_cache_total: {flow.json_payload.get('rows_newer_than_cache_total')}",
        f"- actual_import_gate_status: pending_user_approval",
        "",
    ]
    return ManualDataImportFlowDryRunResult(markdown_text="\n".join(lines), json_payload=payload)
