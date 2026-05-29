"""Gated manual CSV import execution for JP daily bars cache."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.config.env_bool import strict_confirm_flag_truthy
from invis_alpha_os.data.jquants_daily_bars_cache import (
    load_jquants_daily_bars_cache,
    save_jquants_daily_bars_cache,
    utc_now_iso,
)
from invis_alpha_os.reports.manual_csv_import_plan import DUPLICATE_POLICY, build_manual_csv_import_plan
from invis_alpha_os.reports.manual_csv_validation import validate_manual_csv_file

MANUAL_CSV_ALLOWED_TARGETS: frozenset[str] = frozenset({"5802", "6645", "5801", "285A", "5803"})
REQUIRED_PROVIDER = "manual_csv"
REQUIRED_SCOPE = "JP_ONLY"

REQUIRED_GATES: tuple[str, ...] = (
    "ALLOW_CACHE_WRITE",
    "CONFIRM_CACHE_WRITE",
    "CONFIRM_MANUAL_CSV_IMPORT",
)


@dataclass(frozen=True)
class ManualCsvImportExecuteResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_targets_csv(targets_csv: str) -> list[str]:
    return [part.strip() for part in targets_csv.split(",") if part.strip()]


def merge_bars_for_import(
    existing_rows: list[dict[str, Any]],
    incoming_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_date: dict[str, dict[str, Any]] = {str(row["date"]): row for row in existing_rows}
    for row in incoming_rows:
        by_date[str(row["date"])] = row
    return [by_date[key] for key in sorted(by_date.keys())]


def validate_manual_csv_gates(
    *,
    env: dict[str, str],
    targets: list[str],
    provider: str,
    scope: str,
    execute_import: bool,
) -> tuple[str, list[str]]:
    target_set = frozenset(targets)
    if provider.strip().lower() != REQUIRED_PROVIDER:
        return "refused_provider_mismatch", [f"provider={provider}"]
    if scope.strip().upper() != REQUIRED_SCOPE:
        return "refused_scope_mismatch", [f"scope={scope}"]
    if not target_set.issubset(MANUAL_CSV_ALLOWED_TARGETS):
        return "refused_target_mismatch", [f"targets={sorted(target_set)}"]
    if not execute_import:
        return "planned_dry_run_only", []
    missing: list[str] = []
    if env.get("ALLOW_CACHE_WRITE", "").strip() != "1":
        missing.append("ALLOW_CACHE_WRITE")
    for gate in REQUIRED_GATES:
        if gate == "ALLOW_CACHE_WRITE":
            continue
        if not strict_confirm_flag_truthy(env.get(gate)):
            missing.append(gate)
    if env.get("CONFIRM_PROVIDER", "").strip().lower() != REQUIRED_PROVIDER:
        missing.append("CONFIRM_PROVIDER")
    if env.get("CONFIRM_SCOPE", "").strip().upper() != REQUIRED_SCOPE:
        missing.append("CONFIRM_SCOPE")
    expected_targets = ",".join(sorted(targets))
    if env.get("CONFIRM_TARGETS", "").strip() != expected_targets:
        missing.append("CONFIRM_TARGETS")
    if missing:
        return "refused_missing_gates", missing
    return "ok", []


def build_manual_csv_import_execute(
    *,
    csv_path: Path,
    targets_csv: str,
    report_date: str,
    provider: str = REQUIRED_PROVIDER,
    scope: str = REQUIRED_SCOPE,
    execute_import: bool = False,
    env: dict[str, str] | None = None,
) -> ManualCsvImportExecuteResult:
    env_map = env or {}
    targets = _parse_targets_csv(targets_csv)
    gate_status, gate_detail = validate_manual_csv_gates(
        env=env_map,
        targets=targets,
        provider=provider,
        scope=scope,
        execute_import=execute_import,
    )
    plan = build_manual_csv_import_plan(csv_path=csv_path, targets_csv=targets_csv, report_date=report_date)

    if gate_status != "ok" and execute_import:
        payload = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "provider": provider,
            "scope": scope,
            "targets": targets,
            "status": gate_status,
            "overall_status": "gate_refused",
            "gate_detail": gate_detail,
            "dry_run_only": False,
            "cache_write_executed": False,
            "actual_import_executed": False,
            "duplicate_policy": DUPLICATE_POLICY,
            "importable": plan.json_payload.get("importable"),
            "rows_newer_than_cache_total": plan.json_payload.get("rows_newer_than_cache_total"),
        }
        lines = [
            "# Manual CSV Import Execute Refused",
            "",
            f"- status: {gate_status}",
            f"- gate_detail: {', '.join(gate_detail)}",
            "",
        ]
        return ManualCsvImportExecuteResult(markdown_text="\n".join(lines), json_payload=payload)

    if not execute_import:
        payload = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "provider": provider,
            "scope": scope,
            "targets": targets,
            "status": gate_status,
            "overall_status": "planned_dry_run_only",
            "dry_run_only": True,
            "cache_write_executed": False,
            "actual_import_executed": False,
            "duplicate_policy": DUPLICATE_POLICY,
            "importable": plan.json_payload.get("importable"),
            "rows_newer_than_cache_total": plan.json_payload.get("rows_newer_than_cache_total"),
            "per_ticker": plan.json_payload.get("per_ticker", []),
            "cache_write_targets": [
                f"outputs/market_data/jquants_daily_bars/{t}.json" for t in plan.json_payload.get("targets", [])
            ],
        }
        lines = [
            "# Manual CSV Import Execute Dry-Run",
            "",
            f"- importable: {str(payload['importable']).lower()}",
            f"- rows_newer_than_cache_total: {payload['rows_newer_than_cache_total']}",
            f"- duplicate_policy: {DUPLICATE_POLICY}",
            "- cache_write_executed: false",
            "- actual_import_executed: false",
            "",
        ]
        return ManualCsvImportExecuteResult(markdown_text="\n".join(lines), json_payload=payload)

    if not plan.json_payload.get("importable"):
        payload = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "overall_status": "not_importable",
            "status": "not_importable",
            "cache_write_executed": False,
            "actual_import_executed": False,
            "importable": False,
            "rows_newer_than_cache_total": plan.json_payload.get("rows_newer_than_cache_total"),
        }
        return ManualCsvImportExecuteResult(
            markdown_text="# Manual CSV Import Execute Refused\n\n- not_importable: true\n",
            json_payload=payload,
        )

    validation = validate_manual_csv_file(
        csv_path=csv_path,
        targets_csv=targets_csv,
        report_date=report_date,
    )
    symbol_results: list[dict[str, Any]] = []
    fetched_at = utc_now_iso()
    for ticker_row in plan.json_payload.get("per_ticker", []):
        ticker = str(ticker_row.get("ticker", "")).strip()
        if ticker_row.get("rows_newer_than_cache", 0) <= 0:
            symbol_results.append(
                {
                    "ticker": ticker,
                    "status": "skipped_no_new_rows",
                    "rows_written": 0,
                    "cache_write_executed": False,
                }
            )
            continue
        loaded = load_jquants_daily_bars_cache(ticker)
        existing: list[dict[str, Any]] = []
        cache_latest: str | None = None
        if loaded:
            bars, _meta = loaded
            existing = [dict(b) for b in bars]
            cache_latest = str(bars[-1]["date"]) if bars else None
        all_csv = validation.rows_by_ticker.get(ticker, [])
        to_merge = [r for r in all_csv if cache_latest is None or r["date"] > cache_latest]
        if not to_merge:
            symbol_results.append(
                {
                    "ticker": ticker,
                    "status": "skipped_no_new_rows",
                    "rows_written": 0,
                    "cache_write_executed": False,
                }
            )
            continue
        merged = merge_bars_for_import(existing, to_merge)
        path = save_jquants_daily_bars_cache(
            ticker,
            merged,
            source="manual_csv",
            fetched_at=fetched_at,
        )
        symbol_results.append(
            {
                "ticker": ticker,
                "status": "success",
                "rows_written": len(to_merge),
                "cache_written_to": str(path.name),
                "cache_write_executed": True,
            }
        )

    overall = "success" if any(r.get("status") == "success" for r in symbol_results) else "no_op"
    payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "provider": provider,
        "scope": scope,
        "targets": targets,
        "status": overall,
        "overall_status": overall,
        "dry_run_only": False,
        "cache_write_executed": any(r.get("cache_write_executed") for r in symbol_results),
        "actual_import_executed": True,
        "duplicate_policy": DUPLICATE_POLICY,
        "symbol_results": symbol_results,
        "rows_newer_than_cache_total": plan.json_payload.get("rows_newer_than_cache_total"),
    }
    lines = [
        "# Manual CSV Import Execute Result",
        "",
        f"- overall_status: {overall}",
        f"- cache_write_executed: {str(payload['cache_write_executed']).lower()}",
        "",
        "## Per ticker",
    ]
    for row in symbol_results:
        lines.append(
            f"- {row['ticker']}: {row['status']} rows_written={row.get('rows_written', 0)} "
            f"cache={row.get('cache_written_to', '-')}"
        )
    lines.append("")
    return ManualCsvImportExecuteResult(markdown_text="\n".join(lines), json_payload=payload)
