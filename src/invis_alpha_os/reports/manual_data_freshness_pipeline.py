"""Integrated manual JP bars freshness pipeline (BT–BX, dry-run only)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.cache_refresh_readiness import build_cache_refresh_readiness_report
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.manual_data_discovery import build_manual_data_discovery
from invis_alpha_os.reports.manual_data_export_assistant import build_manual_data_export_assistant
from invis_alpha_os.reports.manual_data_freshness_context import (
    apply_manual_freshness_to_cache_readiness,
    apply_manual_freshness_to_context,
)
from invis_alpha_os.reports.manual_data_import_flow_dry_run import build_manual_data_import_flow_dry_run
from invis_alpha_os.reports.manual_data_schema_guard import (
    DEFAULT_TARGET_TICKERS_CSV,
    build_manual_data_schema_validation,
)


@dataclass(frozen=True)
class ManualDataFreshnessPipelineResult:
    discovery: Any
    schema_validation: Any | None
    import_flow_dry_run: Any | None
    export_assistant: Any
    context_pack: Any
    cache_readiness: Any
    summary: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_manual_data_freshness_pipeline(
    *,
    report_date: str,
    repo_root: Path,
    report_dir: Path,
    targets_csv: str = DEFAULT_TARGET_TICKERS_CSV,
    working_dir: Path | None = None,
) -> ManualDataFreshnessPipelineResult:
    work = working_dir or (repo_root / "outputs" / "manual_data" / "working" / report_date)
    work.mkdir(parents=True, exist_ok=True)

    discovery = build_manual_data_discovery(report_date=report_date, repo_root=repo_root)
    schema_result = None
    dry_run_result = None
    export_reason = "manual_file_not_found"

    selected_path = discovery.selected_path
    if selected_path is not None and discovery.json_payload.get("safe_to_parse"):
        export_reason = "manual_file_found"
        schema_result = build_manual_data_schema_validation(
            input_path=selected_path,
            targets_csv=targets_csv,
            report_date=report_date,
        )
        if schema_result.json_payload.get("schema_valid") and not schema_result.json_payload.get(
            "prohibited_columns_detected"
        ):
            dry_run_result = build_manual_data_import_flow_dry_run(
                input_path=selected_path,
                targets_csv=targets_csv,
                report_date=report_date,
                repo_root=repo_root,
                working_dir=work,
                schema_payload=schema_result.json_payload.get("validation") or schema_result.json_payload,
            )
        else:
            export_reason = "schema_not_valid"
    elif discovery.json_payload.get("candidates_found", 0) > 0:
        export_reason = "manual_file_unsafe"

    export_assistant = build_manual_data_export_assistant(
        report_date=report_date,
        targets_csv=targets_csv,
        reason=export_reason,
    )

    context_pack = build_chatgpt_context_pack(report_date=report_date, report_dir=report_dir)
    pipeline_payload: dict[str, Any] = {
        "discovery": discovery.json_payload,
        "schema_validation": schema_result.json_payload if schema_result else {},
        "import_flow_dry_run": dry_run_result.json_payload if dry_run_result else {},
        "export_assistant": export_assistant.json_payload,
        "next_action": discovery.json_payload.get("next_required_action", ""),
    }
    context_pack = type(context_pack)(
        markdown_text=context_pack.markdown_text,
        json_payload=apply_manual_freshness_to_context(context_pack.json_payload, pipeline_payload),
    )

    cache_readiness = build_cache_refresh_readiness_report(
        report_date=report_date,
        repo_root=repo_root,
        context_json_payload=context_pack.json_payload,
    )
    cache_readiness = type(cache_readiness)(
        markdown_text=cache_readiness.markdown_text,
        json_payload=apply_manual_freshness_to_cache_readiness(
            cache_readiness.json_payload,
            pipeline_payload,
        ),
    )

    manual_detected = bool(discovery.json_payload.get("manual_file_detected"))
    schema_valid = bool(schema_result and schema_result.json_payload.get("schema_valid"))
    dry_pass = bool(dry_run_result and dry_run_result.json_payload.get("dry_run_status") == "pass")

    summary = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "manual_file_detected": manual_detected,
        "schema_valid": schema_valid,
        "prohibited_columns_detected": bool(
            schema_result and schema_result.json_payload.get("prohibited_columns_detected")
        ),
        "execute_import": False,
        "actual_import": False,
        "cache_write": False,
        "dry_run_status": dry_run_result.json_payload.get("dry_run_status") if dry_run_result else "not_run",
        "export_assistant_generated": True,
        "template_generated": True,
        "actual_import_gate_status": "pending_user_approval",
        "next_action": pipeline_payload.get("next_action"),
        "pipeline_version": "v23_bt_bx",
    }

    return ManualDataFreshnessPipelineResult(
        discovery=discovery,
        schema_validation=schema_result,
        import_flow_dry_run=dry_run_result,
        export_assistant=export_assistant,
        context_pack=context_pack,
        cache_readiness=cache_readiness,
        summary=summary,
    )


def write_manual_data_freshness_outputs(
    *,
    out_dir: Path,
    report_date: str,
    result: ManualDataFreshnessPipelineResult,
) -> dict[str, Path]:
    latest = out_dir / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    yyyy = report_date[:4]
    archive = out_dir / "archive" / yyyy / report_date
    archive.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    def _write_pair(basename: str, md: str, payload: dict[str, Any]) -> None:
        for root, label in ((latest, "latest"), (archive, "archive")):
            md_path = root / f"{basename}.md"
            json_path = root / f"{basename}.json"
            md_path.write_text(md, encoding="utf-8")
            json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths[f"{label}_{basename}_md"] = md_path
            paths[f"{label}_{basename}_json"] = json_path

    _write_pair("manual_data_discovery", result.discovery.markdown_text, result.discovery.json_payload)
    if result.schema_validation is not None:
        _write_pair(
            "manual_data_schema_validation",
            result.schema_validation.markdown_text,
            result.schema_validation.json_payload,
        )
    if result.import_flow_dry_run is not None:
        _write_pair(
            "manual_data_import_flow_dry_run",
            result.import_flow_dry_run.markdown_text,
            result.import_flow_dry_run.json_payload,
        )
    _write_pair(
        "manual_data_export_assistant",
        result.export_assistant.markdown_text,
        result.export_assistant.json_payload,
    )
    tpl = latest / "manual_jp_bars_template.csv"
    tpl.write_text(result.export_assistant.template_csv_text, encoding="utf-8")
    paths["latest_manual_jp_bars_template_csv"] = tpl
    arc_tpl = archive / "manual_jp_bars_template.csv"
    arc_tpl.write_text(result.export_assistant.template_csv_text, encoding="utf-8")
    paths["archive_manual_jp_bars_template_csv"] = arc_tpl

    _write_pair("chatgpt_invest_context_pack", result.context_pack.markdown_text, result.context_pack.json_payload)
    _write_pair(
        "cache_refresh_readiness",
        result.cache_readiness.markdown_text,
        result.cache_readiness.json_payload,
    )
    summary_path = latest / "manual_data_freshness_pipeline_summary.json"
    summary_path.write_text(json.dumps(result.summary, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["latest_manual_data_freshness_pipeline_summary_json"] = summary_path
    return paths


def sync_manual_data_freshness_to_reports_repo(
    *,
    reports_repo_path: Path,
    repo_root: Path,
    report_date: str,
    result: ManualDataFreshnessPipelineResult,
) -> dict[str, Path]:
    if reports_repo_path.resolve() == repo_root.resolve():
        raise ValueError("reports-repo-path must differ from source repo")
    latest = reports_repo_path / "latest"
    weekly = reports_repo_path / "weekly" / report_date[:4] / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    def _sync_file(basename: str, content: str, *, is_json: bool = False) -> None:
        for root, label in ((latest, "reports_latest"), (weekly, "reports_weekly")):
            path = root / basename
            path.write_text(content, encoding="utf-8")
            paths[f"{label}_{path.name}"] = path

    pairs = [
        ("manual_data_discovery.md", result.discovery.markdown_text, False),
        ("manual_data_discovery.json", json.dumps(result.discovery.json_payload, ensure_ascii=False, indent=2), False),
        (
            "manual_data_export_assistant.md",
            result.export_assistant.markdown_text,
            False,
        ),
        (
            "manual_data_export_assistant.json",
            json.dumps(result.export_assistant.json_payload, ensure_ascii=False, indent=2),
            False,
        ),
        ("chatgpt_invest_context_pack.md", result.context_pack.markdown_text, False),
        (
            "chatgpt_invest_context_pack.json",
            json.dumps(result.context_pack.json_payload, ensure_ascii=False, indent=2),
            False,
        ),
        ("cache_refresh_readiness.md", result.cache_readiness.markdown_text, False),
        (
            "cache_refresh_readiness.json",
            json.dumps(result.cache_readiness.json_payload, ensure_ascii=False, indent=2),
            False,
        ),
        (
            "manual_data_freshness_pipeline_summary.json",
            json.dumps(result.summary, ensure_ascii=False, indent=2),
            False,
        ),
    ]
    if result.schema_validation is not None:
        pairs.extend(
            [
                ("manual_data_schema_validation.md", result.schema_validation.markdown_text, False),
                (
                    "manual_data_schema_validation.json",
                    json.dumps(result.schema_validation.json_payload, ensure_ascii=False, indent=2),
                    False,
                ),
            ]
        )
    if result.import_flow_dry_run is not None:
        pairs.extend(
            [
                ("manual_data_import_flow_dry_run.md", result.import_flow_dry_run.markdown_text, False),
                (
                    "manual_data_import_flow_dry_run.json",
                    json.dumps(result.import_flow_dry_run.json_payload, ensure_ascii=False, indent=2),
                    False,
                ),
            ]
        )
    for basename, content, _ in pairs:
        _sync_file(basename, content)
    for root, label in ((latest, "reports_latest"), (weekly, "reports_weekly")):
        tpl = root / "manual_jp_bars_template.csv"
        tpl.write_text(result.export_assistant.template_csv_text, encoding="utf-8")
        paths[f"{label}_manual_jp_bars_template_csv"] = tpl
    return paths
