"""Manual data acquisition UX pack orchestrator (v25 BY–CA)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.manual_data_actual_import_approval_package import (
    build_manual_data_actual_import_approval_package,
)
from invis_alpha_os.reports.manual_data_dropzone import (
    build_manual_data_dropzone_status,
    default_dropzone_path,
    ensure_dropzone_assets,
)
from invis_alpha_os.reports.manual_data_dropzone import manual_data_search_roots
from invis_alpha_os.reports.manual_data_freshness_pipeline import (
    ManualDataFreshnessPipelineResult,
    build_manual_data_freshness_pipeline,
    sync_manual_data_freshness_to_reports_repo,
    write_manual_data_freshness_outputs,
)
from invis_alpha_os.reports.manual_data_paste_intake import build_manual_data_paste_intake_readiness
from invis_alpha_os.reports.manual_data_recent_candidates import build_manual_data_recent_candidates_report


@dataclass(frozen=True)
class ManualDataAcquisitionUxPackResult:
    dropzone_status: Any
    recent_candidates: Any
    paste_intake: Any
    pipeline: ManualDataFreshnessPipelineResult
    approval_package: Any
    summary: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_manual_data_acquisition_ux_pack(
    *,
    report_date: str,
    repo_root: Path,
    report_dir: Path,
    extra_discovery_paths: list[Path] | None = None,
) -> ManualDataAcquisitionUxPackResult:
    dropzone = default_dropzone_path()
    ensure_dropzone_assets(dropzone=dropzone)
    dropzone_status = build_manual_data_dropzone_status(report_date=report_date, dropzone=dropzone)
    recent = build_manual_data_recent_candidates_report(
        report_date=report_date,
        roots=manual_data_search_roots(),
    )
    paste = build_manual_data_paste_intake_readiness(
        report_date=report_date,
        repo_root=repo_root,
        dropzone=dropzone,
    )
    extra = list(extra_discovery_paths or [])
    if paste.materialized_path is not None:
        extra.append(paste.materialized_path.parent)

    pipeline = build_manual_data_freshness_pipeline(
        report_date=report_date,
        repo_root=repo_root,
        report_dir=report_dir,
        working_dir=repo_root / "outputs" / "manual_data" / "working" / report_date,
        extra_discovery_paths=extra,
        paste_materialized_path=paste.materialized_path,
    )
    approval = build_manual_data_actual_import_approval_package(
        report_date=report_date,
        discovery_payload=pipeline.discovery.json_payload,
        schema_payload=pipeline.schema_validation.json_payload if pipeline.schema_validation else None,
        dry_run_payload=pipeline.import_flow_dry_run.json_payload if pipeline.import_flow_dry_run else None,
    )

    summary = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "ux_pack_version": "v25_by_ca",
        "dropzone_created": dropzone_status.json_payload.get("dropzone_exists"),
        "manual_file_detected": pipeline.summary.get("manual_file_detected"),
        "schema_validation_executed": pipeline.schema_validation is not None,
        "dry_run_executed": pipeline.import_flow_dry_run is not None,
        "dry_run_status": pipeline.summary.get("dry_run_status"),
        "paste_intake_ready": paste.json_payload.get("readiness_status") == "ready_for_pipeline",
        "approval_package_status": approval.json_payload.get("package_status"),
        "actual_import": False,
        "cache_write": False,
        "next_single_action": dropzone_status.json_payload.get("next_single_action"),
    }
    return ManualDataAcquisitionUxPackResult(
        dropzone_status=dropzone_status,
        recent_candidates=recent,
        paste_intake=paste,
        pipeline=pipeline,
        approval_package=approval,
        summary=summary,
    )


def write_manual_data_acquisition_ux_outputs(
    *,
    out_dir: Path,
    report_date: str,
    result: ManualDataAcquisitionUxPackResult,
) -> dict[str, Path]:
    paths = {}
    latest = out_dir / "latest"
    yyyy = report_date[:4]
    archive = out_dir / "archive" / yyyy / report_date
    latest.mkdir(parents=True, exist_ok=True)
    archive.mkdir(parents=True, exist_ok=True)

    def _pair(basename: str, md: str, payload: dict[str, Any]) -> None:
        for root, label in ((latest, "latest"), (archive, "archive")):
            md_path = root / f"{basename}.md"
            json_path = root / f"{basename}.json"
            md_path.write_text(md, encoding="utf-8")
            json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths[f"{label}_{basename}_md"] = md_path
            paths[f"{label}_{basename}_json"] = json_path

    _pair("manual_data_dropzone_status", result.dropzone_status.markdown_text, result.dropzone_status.json_payload)
    _pair(
        "manual_data_acquisition_ux_pack",
        _ux_pack_markdown(result),
        {**result.summary, "recent_candidates": result.recent_candidates.json_payload},
    )
    _pair(
        "manual_data_paste_intake_readiness",
        result.paste_intake.markdown_text,
        result.paste_intake.json_payload,
    )
    _pair(
        "manual_data_actual_import_approval_package",
        result.approval_package.markdown_text,
        result.approval_package.json_payload,
    )
    summary_path = latest / "manual_data_acquisition_ux_pack_summary.json"
    summary_path.write_text(json.dumps(result.summary, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["latest_manual_data_acquisition_ux_pack_summary_json"] = summary_path
    return paths


def _ux_pack_markdown(result: ManualDataAcquisitionUxPackResult) -> str:
    s = result.summary
    return "\n".join(
        [
            "# Manual Data Acquisition UX Pack",
            "",
            f"- manual_file_detected: {str(s.get('manual_file_detected')).lower()}",
            f"- dry_run_status: {s.get('dry_run_status')}",
            f"- approval_package_status: {s.get('approval_package_status')}",
            f"- next_single_action: {s.get('next_single_action')}",
            "",
        ]
    )


def sync_manual_data_acquisition_ux_to_reports_repo(
    *,
    reports_repo_path: Path,
    report_date: str,
    result: ManualDataAcquisitionUxPackResult,
    repo_root: Path,
) -> dict[str, Path]:
    paths = sync_manual_data_freshness_to_reports_repo(
        reports_repo_path=reports_repo_path,
        repo_root=repo_root,
        report_date=report_date,
        result=result.pipeline,
    )
    latest = reports_repo_path / "latest"
    weekly = reports_repo_path / "weekly" / report_date[:4] / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)

    extras = [
        ("manual_data_dropzone_status.md", result.dropzone_status.markdown_text),
        ("manual_data_dropzone_status.json", json.dumps(result.dropzone_status.json_payload, ensure_ascii=False, indent=2)),
        ("manual_data_acquisition_ux_pack.md", _ux_pack_markdown(result)),
        (
            "manual_data_acquisition_ux_pack.json",
            json.dumps(
                {**result.summary, "recent_candidates": result.recent_candidates.json_payload},
                ensure_ascii=False,
                indent=2,
            ),
        ),
        ("manual_data_paste_intake_readiness.md", result.paste_intake.markdown_text),
        (
            "manual_data_paste_intake_readiness.json",
            json.dumps(result.paste_intake.json_payload, ensure_ascii=False, indent=2),
        ),
        ("manual_data_actual_import_approval_package.md", result.approval_package.markdown_text),
        (
            "manual_data_actual_import_approval_package.json",
            json.dumps(result.approval_package.json_payload, ensure_ascii=False, indent=2),
        ),
        (
            "manual_data_acquisition_ux_pack_summary.json",
            json.dumps(result.summary, ensure_ascii=False, indent=2),
        ),
    ]
    for basename, content in extras:
        for root, label in ((latest, "reports_latest"), (weekly, "reports_weekly")):
            path = root / basename
            path.write_text(content, encoding="utf-8")
            paths[f"{label}_{basename}"] = path
    return paths
