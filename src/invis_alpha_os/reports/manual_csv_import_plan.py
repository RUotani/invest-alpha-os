"""Dry-run manual CSV import plan comparing CSV rows to JP cache state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.data.jquants_daily_bars_cache import load_jquants_daily_bars_cache
from invis_alpha_os.reports.manual_csv_validation import validate_manual_csv_file

DUPLICATE_POLICY = "csv_overwrites_same_date_on_import"


@dataclass(frozen=True)
class ManualCsvImportPlanResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cache_latest(ticker: str) -> str | None:
    loaded = load_jquants_daily_bars_cache(ticker)
    if not loaded:
        return None
    bars, _meta = loaded
    return str(bars[-1]["date"]).strip() if bars else None


def build_manual_csv_import_plan(
    *,
    csv_path: Path,
    targets_csv: str,
    report_date: str,
) -> ManualCsvImportPlanResult:
    validation = validate_manual_csv_file(
        csv_path=csv_path,
        targets_csv=targets_csv,
        report_date=report_date,
    )
    per_ticker: list[dict[str, Any]] = []
    total_new_rows = 0
    importable = validation.json_payload.get("validated", False)

    for ticker in validation.json_payload.get("targets", []):
        bars = validation.rows_by_ticker.get(ticker, [])
        cache_latest = _cache_latest(ticker)
        dates = [b["date"] for b in bars]
        newer = [b for b in bars if cache_latest is None or b["date"] > cache_latest]
        would_improve = bool(newer) and (cache_latest is None or max(dates) > cache_latest)
        if cache_latest and dates:
            would_improve = would_improve or max(dates) > cache_latest
        total_new_rows += len(newer)
        per_ticker.append(
            {
                "ticker": ticker,
                "row_count": len(bars),
                "date_min": min(dates) if dates else None,
                "date_max": max(dates) if dates else None,
                "cache_latest_bar_date": cache_latest,
                "rows_newer_than_cache": len(newer),
                "would_improve_stale": would_improve,
            }
        )

    if not validation.json_payload.get("validated"):
        importable = False
    elif total_new_rows <= 0:
        importable = False

    payload: dict[str, Any] = {
        "provider": "manual_csv",
        "report_date": report_date,
        "generated_at": _now_iso(),
        "validated": validation.json_payload.get("validated"),
        "importable": importable,
        "dry_run_only": True,
        "cache_write_executed": False,
        "actual_import_executed": False,
        "targets": validation.json_payload.get("targets", []),
        "row_count": validation.json_payload.get("row_count"),
        "rows_newer_than_cache_total": total_new_rows,
        "duplicate_policy": DUPLICATE_POLICY,
        "per_ticker": per_ticker,
        "cache_write_gates_required": [
            "ALLOW_CACHE_WRITE",
            "CONFIRM_CACHE_WRITE",
            "CONFIRM_MANUAL_CSV_IMPORT",
            "CONFIRM_PROVIDER",
            "CONFIRM_SCOPE",
            "CONFIRM_TARGETS",
        ],
        "postcheck_flow": [
            "weekly-candidate-brief-chatgpt-context",
            "weekly-candidate-brief-cache-refresh-readiness",
            "weekly-candidate-brief-cache-refresh-postcheck",
        ],
        "validation_errors": validation.json_payload.get("errors", []),
        "validation_warnings": validation.json_payload.get("warnings", []),
    }

    lines = [
        "# Manual CSV Import Plan",
        "",
        "## メタ情報",
        f"- provider: manual_csv",
        f"- validated: {str(payload['validated']).lower()}",
        f"- importable: {str(payload['importable']).lower()}",
        f"- rows_newer_than_cache_total: {total_new_rows}",
        f"- duplicate_policy: {DUPLICATE_POLICY}",
        "- cache_write_executed: false",
        "- actual_import_executed: false",
        "",
        "## 銘柄別",
        "| ticker | csv_rows | cache_latest | rows_newer | would_improve_stale | date_min | date_max |",
        "| --- | ---: | --- | ---: | --- | --- | --- |",
    ]
    for row in per_ticker:
        lines.append(
            f"| {row['ticker']} | {row['row_count']} | {row['cache_latest_bar_date'] or '-'} | "
            f"{row['rows_newer_than_cache']} | {str(row['would_improve_stale']).lower()} | "
            f"{row['date_min'] or '-'} | {row['date_max'] or '-'} |"
        )
    lines.extend(
        [
            "",
            "## Cache writeゲート",
            f"- required: {', '.join(payload['cache_write_gates_required'])}",
            "",
        ]
    )
    return ManualCsvImportPlanResult(markdown_text="\n".join(lines), json_payload=payload)
