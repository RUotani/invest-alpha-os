"""Manual data dry-run readiness package (no actual import)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.manual_data_discovery import build_manual_data_discovery
from invis_alpha_os.reports.manual_data_export_package import build_manual_data_export_package
from invis_alpha_os.reports.manual_file_security import (
    MAX_COLUMN_COUNT,
    MAX_FILE_BYTES,
    MAX_ROW_COUNT,
)


@dataclass(frozen=True)
class ManualDataDryRunReadinessResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_manual_data_dry_run_readiness(
    *,
    report_date: str,
    repo_root: Path,
    targets_csv: str = "5802,6645,5801,285A,5803",
) -> ManualDataDryRunReadinessResult:
    discovery = build_manual_data_discovery(report_date=report_date, repo_root=repo_root)
    export_pkg = build_manual_data_export_package(report_date=report_date, targets_csv=targets_csv)
    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "contents_printed": False,
        "candidates_found": discovery.json_payload.get("candidates_found", 0),
        "xlsx_supported": discovery.json_payload.get("xlsx_supported", False),
        "expected_filenames": export_pkg.json_payload.get("preferred_filenames", []),
        "supported_formats": export_pkg.json_payload.get("supported_formats", []),
        "required_targets": export_pkg.json_payload.get("required_targets", []),
        "per_target": export_pkg.json_payload.get("per_target", []),
        "required_columns": export_pkg.json_payload.get("required_columns", []),
        "prohibited_columns": export_pkg.json_payload.get("prohibited_columns", []),
        "privacy_warning": export_pkg.json_payload.get("privacy_warning"),
        "security_guards": {
            "max_file_bytes": MAX_FILE_BYTES,
            "max_row_count": MAX_ROW_COUNT,
            "max_column_count": MAX_COLUMN_COUNT,
            "formula_injection_guard": True,
            "pii_guard": True,
            "path_traversal_guard": True,
        },
        "dry_run_command": (
            "weekly-candidate-brief-manual-data-import-flow "
            "--input-path <untracked-path> --targets 5802,6645,5801,285A,5803 "
            "--execute-import false"
        ),
        "import_gate_command_template": (
            "weekly-candidate-brief-manual-data-import-flow "
            "--input-path <untracked-path> --targets <targets> "
            "--execute-import true  # requires human approval gate"
        ),
        "actual_import_executed": False,
        "cache_write_executed": False,
    }
    lines = [
        "# Manual Data Dry-Run Readiness",
        "",
        f"- candidates_found: {payload['candidates_found']}",
        f"- xlsx_supported: {str(payload['xlsx_supported']).lower()}",
        "",
        "## Expected files",
        "",
    ]
    for name in payload["expected_filenames"]:
        lines.append(f"- {name}")
    lines.extend(
        [
            "",
            "## Dry-run command",
            "",
            "```bash",
            payload["dry_run_command"],
            "```",
            "",
            "## Privacy",
            "",
            f"- {payload['privacy_warning']}",
            "",
        ]
    )
    return ManualDataDryRunReadinessResult(markdown_text="\n".join(lines), json_payload=payload)
