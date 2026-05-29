"""JP OHLCV freshness source strategy pack (v28, read-only + dry-run only)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.jp_ohlcv_alternative_source_strategy import build_jp_ohlcv_alternative_source_strategy
from invis_alpha_os.reports.jquants_gated_refresh_preflight import build_jquants_gated_refresh_preflight
from invis_alpha_os.reports.manual_data_acquisition_ux_pack import (
    ManualDataAcquisitionUxPackResult,
    build_manual_data_acquisition_ux_pack,
    sync_manual_data_acquisition_ux_to_reports_repo,
    write_manual_data_acquisition_ux_outputs,
)
from invis_alpha_os.reports.manual_data_actual_import_approval_package import (
    build_manual_data_actual_import_approval_package,
)
from invis_alpha_os.reports.manual_data_freshness_context import (
    apply_manual_freshness_to_cache_readiness,
    apply_manual_freshness_to_context,
)
from invis_alpha_os.reports.cache_refresh_readiness import build_cache_refresh_readiness_report
from invis_alpha_os.reports.manual_data_freshness_pipeline import write_manual_data_freshness_outputs
from invis_alpha_os.reports.manual_data_next_source_action import build_manual_data_next_source_action
from invis_alpha_os.reports.manual_data_schema_guard import DEFAULT_TARGET_TICKERS_CSV


@dataclass(frozen=True)
class JpOhlcvFreshnessSourceStrategyResult:
    ux_pack: ManualDataAcquisitionUxPackResult
    jquants_preflight: Any
    alternative_strategy: Any
    next_source_action: Any
    approval_package: Any
    context_pack: Any
    cache_readiness: Any
    summary: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_jp_ohlcv_freshness_source_strategy(
    *,
    report_date: str,
    repo_root: Path,
    report_dir: Path,
    targets_csv: str = DEFAULT_TARGET_TICKERS_CSV,
    env: dict[str, str] | None = None,
) -> JpOhlcvFreshnessSourceStrategyResult:
    env_map = dict(os.environ) if env is None else env
    ux = build_manual_data_acquisition_ux_pack(
        report_date=report_date,
        repo_root=repo_root,
        report_dir=report_dir,
    )
    pipeline = ux.pipeline
    dry_payload = (
        pipeline.import_flow_dry_run.json_payload if pipeline.import_flow_dry_run else {}
    )
    preflight = build_jquants_gated_refresh_preflight(
        report_date=report_date,
        targets_csv=targets_csv,
        env=env_map,
    )
    alternative = build_jp_ohlcv_alternative_source_strategy(
        report_date=report_date,
        targets_csv=targets_csv,
        jquants_preflight=preflight.json_payload,
        dry_run_payload=dry_payload,
    )
    approval = build_manual_data_actual_import_approval_package(
        report_date=report_date,
        discovery_payload=pipeline.discovery.json_payload,
        schema_payload=pipeline.schema_validation.json_payload if pipeline.schema_validation else None,
        dry_run_payload=dry_payload,
    )
    next_action = build_manual_data_next_source_action(
        report_date=report_date,
        jquants_preflight=preflight.json_payload,
        alternative_strategy=alternative.json_payload,
        approval_package=approval.json_payload,
    )
    pipeline_payload: dict[str, Any] = {
        "discovery": pipeline.discovery.json_payload,
        "schema_validation": pipeline.schema_validation.json_payload if pipeline.schema_validation else {},
        "import_flow_dry_run": dry_payload,
        "export_assistant": pipeline.export_assistant.json_payload,
        "next_action": next_action.json_payload.get("next_single_action"),
        "freshness_source_strategy": alternative.json_payload,
        "jquants_preflight": preflight.json_payload,
    }
    context_pack = build_chatgpt_context_pack(report_date=report_date, report_dir=report_dir)
    context_pack = type(context_pack)(
        markdown_text=context_pack.markdown_text,
        json_payload=apply_manual_freshness_to_context(
            context_pack.json_payload,
            pipeline_payload,
            freshness_source_strategy=alternative.json_payload,
            approval_package=approval.json_payload,
        ),
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
            freshness_source_strategy=alternative.json_payload,
            approval_package=approval.json_payload,
        ),
    )
    strategy_summary = {
        "jquants_refresh_recommended": preflight.json_payload.get("refresh_recommended"),
        "contract_limited_risk": preflight.json_payload.get("contract_limited_risk"),
        "next_best_ohlcv_source": alternative.json_payload.get("next_best_ohlcv_source"),
    }
    summary = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "strategy_version": "v28",
        "manual_file_detected": pipeline.summary.get("manual_file_detected"),
        "schema_valid": pipeline.summary.get("schema_valid"),
        "dry_run_status": pipeline.summary.get("dry_run_status"),
        "rows_newer_than_cache_total": approval.json_payload.get("rows_newer_than_cache_total"),
        "actual_import_recommended": approval.json_payload.get("actual_import_recommended"),
        "import_benefit": approval.json_payload.get("import_benefit"),
        "approval_package_status": approval.json_payload.get("package_status"),
        **strategy_summary,
        "actual_import": False,
        "cache_write": False,
        "live_http": False,
    }
    return JpOhlcvFreshnessSourceStrategyResult(
        ux_pack=ux,
        jquants_preflight=preflight,
        alternative_strategy=alternative,
        next_source_action=next_action,
        approval_package=approval,
        context_pack=context_pack,
        cache_readiness=cache_readiness,
        summary=summary,
    )


def write_jp_ohlcv_freshness_source_strategy_outputs(
    *,
    out_dir: Path,
    report_date: str,
    result: JpOhlcvFreshnessSourceStrategyResult,
) -> dict[str, Path]:
    paths = write_manual_data_acquisition_ux_outputs(
        out_dir=out_dir,
        report_date=report_date,
        result=result.ux_pack,
    )
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

    _pair("jquants_gated_refresh_preflight", result.jquants_preflight.markdown_text, result.jquants_preflight.json_payload)
    _pair(
        "jp_ohlcv_alternative_source_strategy",
        result.alternative_strategy.markdown_text,
        result.alternative_strategy.json_payload,
    )
    _pair(
        "manual_data_next_source_action",
        result.next_source_action.markdown_text,
        result.next_source_action.json_payload,
    )
    _pair(
        "manual_data_actual_import_approval_package",
        result.approval_package.markdown_text,
        result.approval_package.json_payload,
    )
    write_manual_data_freshness_outputs(
        out_dir=out_dir,
        report_date=report_date,
        result=result.ux_pack.pipeline,
    )
    summary_path = latest / "jp_ohlcv_freshness_source_strategy_summary.json"
    summary_path.write_text(json.dumps(result.summary, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["latest_jp_ohlcv_freshness_source_strategy_summary_json"] = summary_path
    return paths


def sync_jp_ohlcv_freshness_source_strategy_to_reports_repo(
    *,
    reports_repo_path: Path,
    repo_root: Path,
    report_date: str,
    result: JpOhlcvFreshnessSourceStrategyResult,
) -> dict[str, Path]:
    paths = sync_manual_data_acquisition_ux_to_reports_repo(
        reports_repo_path=reports_repo_path,
        report_date=report_date,
        result=result.ux_pack,
        repo_root=repo_root,
    )
    latest = reports_repo_path / "latest"
    weekly = reports_repo_path / "weekly" / report_date[:4] / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    extras = [
        ("jquants_gated_refresh_preflight.md", result.jquants_preflight.markdown_text),
        ("jquants_gated_refresh_preflight.json", json.dumps(result.jquants_preflight.json_payload, ensure_ascii=False, indent=2)),
        ("jp_ohlcv_alternative_source_strategy.md", result.alternative_strategy.markdown_text),
        (
            "jp_ohlcv_alternative_source_strategy.json",
            json.dumps(result.alternative_strategy.json_payload, ensure_ascii=False, indent=2),
        ),
        ("manual_data_next_source_action.md", result.next_source_action.markdown_text),
        (
            "manual_data_next_source_action.json",
            json.dumps(result.next_source_action.json_payload, ensure_ascii=False, indent=2),
        ),
        (
            "jp_ohlcv_freshness_source_strategy_summary.json",
            json.dumps(result.summary, ensure_ascii=False, indent=2),
        ),
    ]
    for basename, content in extras:
        for root, label in ((latest, "reports_latest"), (weekly, "reports_weekly")):
            path = root / basename
            path.write_text(content, encoding="utf-8")
            paths[f"{label}_{basename}"] = path
    for root, label in ((latest, "reports_latest"), (weekly, "reports_weekly")):
        for basename, content in (
            ("manual_data_actual_import_approval_package.md", result.approval_package.markdown_text),
            (
                "manual_data_actual_import_approval_package.json",
                json.dumps(result.approval_package.json_payload, ensure_ascii=False, indent=2),
            ),
            ("chatgpt_invest_context_pack.md", result.context_pack.markdown_text),
            (
                "chatgpt_invest_context_pack.json",
                json.dumps(result.context_pack.json_payload, ensure_ascii=False, indent=2),
            ),
            ("cache_refresh_readiness.md", result.cache_readiness.markdown_text),
            (
                "cache_refresh_readiness.json",
                json.dumps(result.cache_readiness.json_payload, ensure_ascii=False, indent=2),
            ),
        ):
            path = root / basename
            path.write_text(content, encoding="utf-8")
            paths[f"{label}_{basename}"] = path
    return paths
