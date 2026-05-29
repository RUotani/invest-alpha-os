"""Manual data dry-run preflight without actual import."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.manual_data_discovery import build_manual_data_discovery
from invis_alpha_os.reports.manual_data_dry_run_readiness import build_manual_data_dry_run_readiness
from invis_alpha_os.reports.manual_data_import_flow import build_manual_data_import_flow


@dataclass(frozen=True)
class ManualDataDryRunPreflightResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_manual_data_dry_run_preflight(
    *,
    report_date: str,
    repo_root: Path,
    targets_csv: str = "5802,6645,5801,285A,5803",
    input_path: str | None = None,
) -> ManualDataDryRunPreflightResult:
    discovery = build_manual_data_discovery(report_date=report_date, repo_root=repo_root)
    readiness = build_manual_data_dry_run_readiness(
        report_date=report_date,
        repo_root=repo_root,
        targets_csv=targets_csv,
    )
    flow_result: dict[str, Any] | None = None
    if input_path:
        flow = build_manual_data_import_flow(
            input_path=Path(input_path),
            targets_csv=targets_csv,
            report_date=report_date,
            provider="manual_csv",
            scope="JP_ONLY",
            execute_import=False,
            repo_root=repo_root,
            working_dir=repo_root / "outputs" / "manual_data_preflight_work",
        )
        flow_result = flow.json_payload

    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "contents_printed": False,
        "candidates_found": discovery.json_payload.get("candidates_found", 0),
        "selected_path": str(discovery.selected_path) if discovery.selected_path else None,
        "xlsx_supported": discovery.json_payload.get("xlsx_supported", False),
        "readiness": readiness.json_payload,
        "import_flow_dry_run": flow_result,
        "actual_import_executed": False,
        "cache_write_executed": False,
        "next_step": (
            "place_untracked_manual_jp_bars_file"
            if not discovery.selected_path
            else "run_import_flow_dry_run_with_selected_path"
        ),
    }
    lines = [
        "# Manual Data Dry-Run Preflight",
        "",
        f"- candidates_found: {payload['candidates_found']}",
        f"- xlsx_supported: {str(payload['xlsx_supported']).lower()}",
        f"- actual_import_executed: false",
        "",
        "## Command",
        "",
        "```bash",
        readiness.json_payload["dry_run_command"],
        "```",
        "",
    ]
    return ManualDataDryRunPreflightResult(markdown_text="\n".join(lines), json_payload=payload)
