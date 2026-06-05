"""Manual data dry-run preflight without actual import."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.manual_csv_discovery import _search_roots
from invis_alpha_os.reports.manual_data_discovery import (
    EXACT_CANDIDATE_NAMES,
    build_manual_data_discovery,
)
from invis_alpha_os.reports.manual_data_dry_run_readiness import build_manual_data_dry_run_readiness
from invis_alpha_os.reports.manual_data_import_flow import build_manual_data_import_flow

ACTUAL_IMPORT_PROHIBITED = True


@dataclass(frozen=True)
class ManualDataDryRunPreflightResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _expected_directory_labels() -> list[str]:
    labels: list[str] = []
    for root in _search_roots():
        try:
            labels.append(str(root.relative_to(Path.home())).replace("\\", "/"))
        except ValueError:
            labels.append("outside_home")
    return labels


def _build_dry_run_command(*, input_path: str, targets_csv: str) -> str:
    return (
        ".venv/bin/python -m invis_alpha_os.cli.main "
        "weekly-candidate-brief-manual-data-import-flow "
        f'--input-path "{input_path}" '
        f"--targets {targets_csv} "
        "--execute-import false"
    )


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
    selected = str(discovery.selected_path) if discovery.selected_path else None
    dry_run_input = input_path or selected or "<untracked-path>/manual_jp_bars.csv"
    dry_run_command = _build_dry_run_command(input_path=dry_run_input, targets_csv=targets_csv)

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

    next_step = (
        "run_import_flow_dry_run_with_selected_path"
        if discovery.selected_path
        else "place_untracked_manual_jp_bars_file"
    )
    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "contents_printed": False,
        "candidates_found": discovery.json_payload.get("candidates_found", 0),
        "selected_path": selected,
        "xlsx_supported": discovery.json_payload.get("xlsx_supported", False),
        "expected_filenames": list(EXACT_CANDIDATE_NAMES),
        "preferred_filenames": readiness.json_payload.get("expected_filenames", []),
        "expected_directory_labels": _expected_directory_labels(),
        "required_targets": readiness.json_payload.get("required_targets", []),
        "required_columns": readiness.json_payload.get("required_columns", []),
        "prohibited_columns": readiness.json_payload.get("prohibited_columns", []),
        "readiness": readiness.json_payload,
        "import_flow_dry_run": flow_result,
        "actual_import_executed": False,
        "actual_import_prohibited": ACTUAL_IMPORT_PROHIBITED,
        "cache_write_executed": False,
        "dry_run_command": dry_run_command,
        "execute_import_flag": False,
        "next_step": next_step,
        "next_commands": {
            "after_file_placed": dry_run_command,
            "actual_import_gate": (
                "weekly-candidate-brief-manual-data-import-flow "
                "--input-path <untracked-path> --targets "
                f"{targets_csv} --execute-import true  # human approval required"
            ),
        },
    }
    lines = [
        "# Manual Data Dry-Run Preflight",
        "",
        f"- candidates_found: {payload['candidates_found']}",
        f"- xlsx_supported: {str(payload['xlsx_supported']).lower()}",
        "- actual_import_executed: false",
        "- actual_import_prohibited: true",
        "",
        "## Expected file names",
        "",
    ]
    for name in payload["expected_filenames"]:
        lines.append(f"- {name}")
    lines.extend(["", "## Expected directories (labels only)", ""])
    for label in payload["expected_directory_labels"]:
        lines.append(f"- ~/{label}")
    lines.extend(
        [
            "",
            "## Required columns",
            "",
            ", ".join(payload["required_columns"]),
            "",
            "## Prohibited columns",
            "",
            ", ".join(payload["prohibited_columns"]),
            "",
            "## Dry-run command (execute-import false)",
            "",
            "```bash",
            dry_run_command,
            "```",
            "",
            "## Actual import",
            "",
            "Actual import is prohibited in this preflight. Use `--execute-import false` only until human approval.",
            "",
        ]
    )
    return ManualDataDryRunPreflightResult(markdown_text="\n".join(lines), json_payload=payload)
