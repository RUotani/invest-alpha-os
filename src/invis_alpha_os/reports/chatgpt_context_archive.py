"""Archive helpers for ChatGPT context pack outputs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_context_pack_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
    write_latest: bool,
    write_archive: bool,
    quality_audit_markdown: str | None = None,
    feedback_template_markdown: str | None = None,
    decision_seed_markdown: str | None = None,
    decision_seed_json_payload: dict[str, Any] | None = None,
    trap_analysis_markdown: str | None = None,
    trap_analysis_json_payload: dict[str, Any] | None = None,
    cache_refresh_readiness_markdown: str | None = None,
    cache_refresh_readiness_json_payload: dict[str, Any] | None = None,
    cache_refresh_execution_plan_markdown: str | None = None,
    cache_refresh_execution_plan_json_payload: dict[str, Any] | None = None,
    cache_refresh_execute_dry_run_markdown: str | None = None,
    cache_refresh_execute_dry_run_json_payload: dict[str, Any] | None = None,
    cache_refresh_execute_result_markdown: str | None = None,
    cache_refresh_execute_result_json_payload: dict[str, Any] | None = None,
    jp_cache_refresh_dry_run_markdown: str | None = None,
    jp_cache_refresh_dry_run_json_payload: dict[str, Any] | None = None,
    jquants_preflight_markdown: str | None = None,
    jquants_preflight_json_payload: dict[str, Any] | None = None,
    cache_refresh_postcheck_markdown: str | None = None,
    cache_refresh_postcheck_json_payload: dict[str, Any] | None = None,
    jp_alternative_provider_readiness_markdown: str | None = None,
    jp_alternative_provider_readiness_json_payload: dict[str, Any] | None = None,
    jp_alternative_provider_execution_plan_markdown: str | None = None,
    jp_alternative_provider_execution_plan_json_payload: dict[str, Any] | None = None,
    manual_csv_validation_markdown: str | None = None,
    manual_csv_validation_json_payload: dict[str, Any] | None = None,
    manual_csv_import_plan_markdown: str | None = None,
    manual_csv_import_plan_json_payload: dict[str, Any] | None = None,
    manual_csv_import_result_markdown: str | None = None,
    manual_csv_import_result_json_payload: dict[str, Any] | None = None,
    manual_csv_template_markdown: str | None = None,
    manual_csv_template_csv_text: str | None = None,
    manual_csv_discovery_markdown: str | None = None,
    manual_csv_discovery_json_payload: dict[str, Any] | None = None,
    manual_csv_normalization_markdown: str | None = None,
    manual_csv_normalization_json_payload: dict[str, Any] | None = None,
    manual_csv_import_flow_markdown: str | None = None,
    manual_csv_import_flow_json_payload: dict[str, Any] | None = None,
    manual_csv_export_request_markdown: str | None = None,
    manual_csv_export_request_json_payload: dict[str, Any] | None = None,
) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    yyyy = report_date[:4]
    if write_latest:
        latest = out_dir / "latest"
        latest.mkdir(parents=True, exist_ok=True)
        md = latest / "chatgpt_invest_context_pack.md"
        js = latest / "chatgpt_invest_context_pack.json"
        idx = latest / "index.md"
        md.write_text(markdown_text, encoding="utf-8")
        js.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        idx.write_text(
            "\n".join(
                [
                    "# 最新Context Pack",
                    "",
                    f"- レポート日: {report_date}",
                    f"- 生成日時: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
                    "- 本文: `chatgpt_invest_context_pack.md`",
                    "- JSON: `chatgpt_invest_context_pack.json`",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        paths["latest_md"] = md
        paths["latest_json"] = js
        paths["latest_index"] = idx
        if quality_audit_markdown is not None:
            qa = latest / "context_pack_quality_audit.md"
            qa.write_text(quality_audit_markdown, encoding="utf-8")
            paths["latest_quality_audit"] = qa
        if feedback_template_markdown is not None:
            fb = latest / "decision_feedback_template.md"
            fb.write_text(feedback_template_markdown, encoding="utf-8")
            paths["latest_feedback_template"] = fb
        if trap_analysis_markdown is not None:
            trap_md = latest / "trap_analysis.md"
            trap_md.write_text(trap_analysis_markdown, encoding="utf-8")
            paths["latest_trap_analysis_md"] = trap_md
        if trap_analysis_json_payload is not None:
            trap_json = latest / "trap_analysis.json"
            trap_json.write_text(json.dumps(trap_analysis_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths["latest_trap_analysis_json"] = trap_json
        if cache_refresh_readiness_markdown is not None:
            ready_md = latest / "cache_refresh_readiness.md"
            ready_md.write_text(cache_refresh_readiness_markdown, encoding="utf-8")
            paths["latest_cache_refresh_readiness_md"] = ready_md
        if cache_refresh_readiness_json_payload is not None:
            ready_json = latest / "cache_refresh_readiness.json"
            ready_json.write_text(
                json.dumps(cache_refresh_readiness_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            paths["latest_cache_refresh_readiness_json"] = ready_json
        if cache_refresh_execution_plan_markdown is not None:
            plan_md = latest / "cache_refresh_execution_plan.md"
            plan_md.write_text(cache_refresh_execution_plan_markdown, encoding="utf-8")
            paths["latest_cache_refresh_execution_plan_md"] = plan_md
        if cache_refresh_execution_plan_json_payload is not None:
            plan_json = latest / "cache_refresh_execution_plan.json"
            plan_json.write_text(
                json.dumps(cache_refresh_execution_plan_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            paths["latest_cache_refresh_execution_plan_json"] = plan_json
        if cache_refresh_execute_dry_run_markdown is not None:
            execute_md = latest / "cache_refresh_execute_dry_run.md"
            execute_md.write_text(cache_refresh_execute_dry_run_markdown, encoding="utf-8")
            paths["latest_cache_refresh_execute_dry_run_md"] = execute_md
        if cache_refresh_execute_dry_run_json_payload is not None:
            execute_json = latest / "cache_refresh_execute_dry_run.json"
            execute_json.write_text(
                json.dumps(cache_refresh_execute_dry_run_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            paths["latest_cache_refresh_execute_dry_run_json"] = execute_json
        if cache_refresh_execute_result_markdown is not None:
            result_md = latest / "cache_refresh_execute_result.md"
            result_md.write_text(cache_refresh_execute_result_markdown, encoding="utf-8")
            paths["latest_cache_refresh_execute_result_md"] = result_md
        if cache_refresh_execute_result_json_payload is not None:
            result_json = latest / "cache_refresh_execute_result.json"
            result_json.write_text(
                json.dumps(cache_refresh_execute_result_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            paths["latest_cache_refresh_execute_result_json"] = result_json
        if jp_cache_refresh_dry_run_markdown is not None:
            jp_md = latest / "jp_cache_refresh_dry_run.md"
            jp_md.write_text(jp_cache_refresh_dry_run_markdown, encoding="utf-8")
            paths["latest_jp_cache_refresh_dry_run_md"] = jp_md
        if jp_cache_refresh_dry_run_json_payload is not None:
            jp_json = latest / "jp_cache_refresh_dry_run.json"
            jp_json.write_text(
                json.dumps(jp_cache_refresh_dry_run_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            paths["latest_jp_cache_refresh_dry_run_json"] = jp_json
        if jquants_preflight_markdown is not None:
            pre_md = latest / "jquants_preflight.md"
            pre_md.write_text(jquants_preflight_markdown, encoding="utf-8")
            paths["latest_jquants_preflight_md"] = pre_md
        if jquants_preflight_json_payload is not None:
            pre_json = latest / "jquants_preflight.json"
            pre_json.write_text(json.dumps(jquants_preflight_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths["latest_jquants_preflight_json"] = pre_json
        if cache_refresh_postcheck_markdown is not None:
            post_md = latest / "cache_refresh_postcheck.md"
            post_md.write_text(cache_refresh_postcheck_markdown, encoding="utf-8")
            paths["latest_cache_refresh_postcheck_md"] = post_md
        if cache_refresh_postcheck_json_payload is not None:
            post_json = latest / "cache_refresh_postcheck.json"
            post_json.write_text(json.dumps(cache_refresh_postcheck_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths["latest_cache_refresh_postcheck_json"] = post_json
        if jp_alternative_provider_readiness_markdown is not None:
            alt_md = latest / "jp_alternative_provider_readiness.md"
            alt_md.write_text(jp_alternative_provider_readiness_markdown, encoding="utf-8")
            paths["latest_jp_alternative_provider_readiness_md"] = alt_md
        if jp_alternative_provider_readiness_json_payload is not None:
            alt_json = latest / "jp_alternative_provider_readiness.json"
            alt_json.write_text(
                json.dumps(jp_alternative_provider_readiness_json_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            paths["latest_jp_alternative_provider_readiness_json"] = alt_json
        if jp_alternative_provider_execution_plan_markdown is not None:
            plan_md = latest / "jp_alternative_provider_execution_plan.md"
            plan_md.write_text(jp_alternative_provider_execution_plan_markdown, encoding="utf-8")
            paths["latest_jp_alternative_provider_execution_plan_md"] = plan_md
        if jp_alternative_provider_execution_plan_json_payload is not None:
            plan_json = latest / "jp_alternative_provider_execution_plan.json"
            plan_json.write_text(
                json.dumps(jp_alternative_provider_execution_plan_json_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            paths["latest_jp_alternative_provider_execution_plan_json"] = plan_json
        if manual_csv_validation_markdown is not None:
            val_md = latest / "manual_csv_validation.md"
            val_md.write_text(manual_csv_validation_markdown, encoding="utf-8")
            paths["latest_manual_csv_validation_md"] = val_md
        if manual_csv_validation_json_payload is not None:
            val_json = latest / "manual_csv_validation.json"
            val_json.write_text(json.dumps(manual_csv_validation_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths["latest_manual_csv_validation_json"] = val_json
        if manual_csv_import_plan_markdown is not None:
            imp_md = latest / "manual_csv_import_plan.md"
            imp_md.write_text(manual_csv_import_plan_markdown, encoding="utf-8")
            paths["latest_manual_csv_import_plan_md"] = imp_md
        if manual_csv_import_plan_json_payload is not None:
            imp_json = latest / "manual_csv_import_plan.json"
            imp_json.write_text(json.dumps(manual_csv_import_plan_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths["latest_manual_csv_import_plan_json"] = imp_json
        if manual_csv_import_result_markdown is not None:
            res_md = latest / "manual_csv_import_result.md"
            res_md.write_text(manual_csv_import_result_markdown, encoding="utf-8")
            paths["latest_manual_csv_import_result_md"] = res_md
        if manual_csv_import_result_json_payload is not None:
            res_json = latest / "manual_csv_import_result.json"
            res_json.write_text(json.dumps(manual_csv_import_result_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths["latest_manual_csv_import_result_json"] = res_json
        if manual_csv_template_markdown is not None:
            tpl_md = latest / "manual_csv_template.md"
            tpl_md.write_text(manual_csv_template_markdown, encoding="utf-8")
            paths["latest_manual_csv_template_md"] = tpl_md
        if manual_csv_template_csv_text is not None:
            tpl_csv = latest / "manual_csv_template.csv"
            tpl_csv.write_text(manual_csv_template_csv_text, encoding="utf-8")
            paths["latest_manual_csv_template_csv"] = tpl_csv
        if manual_csv_discovery_markdown is not None:
            disc_md = latest / "manual_csv_discovery.md"
            disc_md.write_text(manual_csv_discovery_markdown, encoding="utf-8")
            paths["latest_manual_csv_discovery_md"] = disc_md
        if manual_csv_discovery_json_payload is not None:
            disc_json = latest / "manual_csv_discovery.json"
            disc_json.write_text(
                json.dumps(manual_csv_discovery_json_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            paths["latest_manual_csv_discovery_json"] = disc_json
        if manual_csv_normalization_markdown is not None:
            norm_md = latest / "manual_csv_normalization.md"
            norm_md.write_text(manual_csv_normalization_markdown, encoding="utf-8")
            paths["latest_manual_csv_normalization_md"] = norm_md
        if manual_csv_normalization_json_payload is not None:
            norm_json = latest / "manual_csv_normalization.json"
            norm_json.write_text(
                json.dumps(manual_csv_normalization_json_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            paths["latest_manual_csv_normalization_json"] = norm_json
        if manual_csv_import_flow_markdown is not None:
            flow_md = latest / "manual_csv_import_flow.md"
            flow_md.write_text(manual_csv_import_flow_markdown, encoding="utf-8")
            paths["latest_manual_csv_import_flow_md"] = flow_md
        if manual_csv_import_flow_json_payload is not None:
            flow_json = latest / "manual_csv_import_flow.json"
            flow_json.write_text(
                json.dumps(manual_csv_import_flow_json_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            paths["latest_manual_csv_import_flow_json"] = flow_json
        if manual_csv_export_request_markdown is not None:
            req_md = latest / "manual_csv_export_request.md"
            req_md.write_text(manual_csv_export_request_markdown, encoding="utf-8")
            paths["latest_manual_csv_export_request_md"] = req_md
        if manual_csv_export_request_json_payload is not None:
            req_json = latest / "manual_csv_export_request.json"
            req_json.write_text(
                json.dumps(manual_csv_export_request_json_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            paths["latest_manual_csv_export_request_json"] = req_json
    if write_archive:
        arc = out_dir / "archive" / yyyy / report_date
        arc.mkdir(parents=True, exist_ok=True)
        md = arc / "chatgpt_invest_context_pack.md"
        js = arc / "chatgpt_invest_context_pack.json"
        meta = arc / "metadata.json"
        md.write_text(markdown_text, encoding="utf-8")
        js.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        meta.write_text(
            json.dumps(
                {
                    "report_date": report_date,
                    "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "source": "weekly_candidate_brief",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        paths["archive_md"] = md
        paths["archive_json"] = js
        paths["archive_metadata"] = meta
        if quality_audit_markdown is not None:
            qa = arc / "context_pack_quality_audit.md"
            qa.write_text(quality_audit_markdown, encoding="utf-8")
            paths["archive_quality_audit"] = qa
        if feedback_template_markdown is not None:
            fb = arc / "decision_feedback_template.md"
            fb.write_text(feedback_template_markdown, encoding="utf-8")
            paths["archive_feedback_template"] = fb
        if trap_analysis_markdown is not None:
            trap_md = arc / "trap_analysis.md"
            trap_md.write_text(trap_analysis_markdown, encoding="utf-8")
            paths["archive_trap_analysis_md"] = trap_md
        if trap_analysis_json_payload is not None:
            trap_json = arc / "trap_analysis.json"
            trap_json.write_text(json.dumps(trap_analysis_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths["archive_trap_analysis_json"] = trap_json
        if cache_refresh_readiness_markdown is not None:
            ready_md = arc / "cache_refresh_readiness.md"
            ready_md.write_text(cache_refresh_readiness_markdown, encoding="utf-8")
            paths["archive_cache_refresh_readiness_md"] = ready_md
        if cache_refresh_readiness_json_payload is not None:
            ready_json = arc / "cache_refresh_readiness.json"
            ready_json.write_text(
                json.dumps(cache_refresh_readiness_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            paths["archive_cache_refresh_readiness_json"] = ready_json
        if cache_refresh_execution_plan_markdown is not None:
            plan_md = arc / "cache_refresh_execution_plan.md"
            plan_md.write_text(cache_refresh_execution_plan_markdown, encoding="utf-8")
            paths["archive_cache_refresh_execution_plan_md"] = plan_md
        if cache_refresh_execution_plan_json_payload is not None:
            plan_json = arc / "cache_refresh_execution_plan.json"
            plan_json.write_text(
                json.dumps(cache_refresh_execution_plan_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            paths["archive_cache_refresh_execution_plan_json"] = plan_json
        if cache_refresh_execute_dry_run_markdown is not None:
            execute_md = arc / "cache_refresh_execute_dry_run.md"
            execute_md.write_text(cache_refresh_execute_dry_run_markdown, encoding="utf-8")
            paths["archive_cache_refresh_execute_dry_run_md"] = execute_md
        if cache_refresh_execute_dry_run_json_payload is not None:
            execute_json = arc / "cache_refresh_execute_dry_run.json"
            execute_json.write_text(
                json.dumps(cache_refresh_execute_dry_run_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            paths["archive_cache_refresh_execute_dry_run_json"] = execute_json
        if cache_refresh_execute_result_markdown is not None:
            result_md = arc / "cache_refresh_execute_result.md"
            result_md.write_text(cache_refresh_execute_result_markdown, encoding="utf-8")
            paths["archive_cache_refresh_execute_result_md"] = result_md
        if cache_refresh_execute_result_json_payload is not None:
            result_json = arc / "cache_refresh_execute_result.json"
            result_json.write_text(
                json.dumps(cache_refresh_execute_result_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            paths["archive_cache_refresh_execute_result_json"] = result_json
        if jp_cache_refresh_dry_run_markdown is not None:
            jp_md = arc / "jp_cache_refresh_dry_run.md"
            jp_md.write_text(jp_cache_refresh_dry_run_markdown, encoding="utf-8")
            paths["archive_jp_cache_refresh_dry_run_md"] = jp_md
        if jp_cache_refresh_dry_run_json_payload is not None:
            jp_json = arc / "jp_cache_refresh_dry_run.json"
            jp_json.write_text(
                json.dumps(jp_cache_refresh_dry_run_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            paths["archive_jp_cache_refresh_dry_run_json"] = jp_json
        if jquants_preflight_markdown is not None:
            pre_md = arc / "jquants_preflight.md"
            pre_md.write_text(jquants_preflight_markdown, encoding="utf-8")
            paths["archive_jquants_preflight_md"] = pre_md
        if jquants_preflight_json_payload is not None:
            pre_json = arc / "jquants_preflight.json"
            pre_json.write_text(json.dumps(jquants_preflight_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths["archive_jquants_preflight_json"] = pre_json
        if cache_refresh_postcheck_markdown is not None:
            post_md = arc / "cache_refresh_postcheck.md"
            post_md.write_text(cache_refresh_postcheck_markdown, encoding="utf-8")
            paths["archive_cache_refresh_postcheck_md"] = post_md
        if cache_refresh_postcheck_json_payload is not None:
            post_json = arc / "cache_refresh_postcheck.json"
            post_json.write_text(json.dumps(cache_refresh_postcheck_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths["archive_cache_refresh_postcheck_json"] = post_json
        if jp_alternative_provider_readiness_markdown is not None:
            alt_md = arc / "jp_alternative_provider_readiness.md"
            alt_md.write_text(jp_alternative_provider_readiness_markdown, encoding="utf-8")
            paths["archive_jp_alternative_provider_readiness_md"] = alt_md
        if jp_alternative_provider_readiness_json_payload is not None:
            alt_json = arc / "jp_alternative_provider_readiness.json"
            alt_json.write_text(
                json.dumps(jp_alternative_provider_readiness_json_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            paths["archive_jp_alternative_provider_readiness_json"] = alt_json
        if jp_alternative_provider_execution_plan_markdown is not None:
            plan_md = arc / "jp_alternative_provider_execution_plan.md"
            plan_md.write_text(jp_alternative_provider_execution_plan_markdown, encoding="utf-8")
            paths["archive_jp_alternative_provider_execution_plan_md"] = plan_md
        if jp_alternative_provider_execution_plan_json_payload is not None:
            plan_json = arc / "jp_alternative_provider_execution_plan.json"
            plan_json.write_text(
                json.dumps(jp_alternative_provider_execution_plan_json_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            paths["archive_jp_alternative_provider_execution_plan_json"] = plan_json
        if manual_csv_validation_markdown is not None:
            val_md = arc / "manual_csv_validation.md"
            val_md.write_text(manual_csv_validation_markdown, encoding="utf-8")
            paths["archive_manual_csv_validation_md"] = val_md
        if manual_csv_validation_json_payload is not None:
            val_json = arc / "manual_csv_validation.json"
            val_json.write_text(json.dumps(manual_csv_validation_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths["archive_manual_csv_validation_json"] = val_json
        if manual_csv_import_plan_markdown is not None:
            imp_md = arc / "manual_csv_import_plan.md"
            imp_md.write_text(manual_csv_import_plan_markdown, encoding="utf-8")
            paths["archive_manual_csv_import_plan_md"] = imp_md
        if manual_csv_import_plan_json_payload is not None:
            imp_json = arc / "manual_csv_import_plan.json"
            imp_json.write_text(json.dumps(manual_csv_import_plan_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths["archive_manual_csv_import_plan_json"] = imp_json
        if manual_csv_import_result_markdown is not None:
            res_md = arc / "manual_csv_import_result.md"
            res_md.write_text(manual_csv_import_result_markdown, encoding="utf-8")
            paths["archive_manual_csv_import_result_md"] = res_md
        if manual_csv_import_result_json_payload is not None:
            res_json = arc / "manual_csv_import_result.json"
            res_json.write_text(json.dumps(manual_csv_import_result_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths["archive_manual_csv_import_result_json"] = res_json
        if manual_csv_template_markdown is not None:
            tpl_md = arc / "manual_csv_template.md"
            tpl_md.write_text(manual_csv_template_markdown, encoding="utf-8")
            paths["archive_manual_csv_template_md"] = tpl_md
        if manual_csv_template_csv_text is not None:
            tpl_csv = arc / "manual_csv_template.csv"
            tpl_csv.write_text(manual_csv_template_csv_text, encoding="utf-8")
            paths["archive_manual_csv_template_csv"] = tpl_csv
        if manual_csv_discovery_markdown is not None:
            disc_md = arc / "manual_csv_discovery.md"
            disc_md.write_text(manual_csv_discovery_markdown, encoding="utf-8")
            paths["archive_manual_csv_discovery_md"] = disc_md
        if manual_csv_discovery_json_payload is not None:
            disc_json = arc / "manual_csv_discovery.json"
            disc_json.write_text(
                json.dumps(manual_csv_discovery_json_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            paths["archive_manual_csv_discovery_json"] = disc_json
        if manual_csv_normalization_markdown is not None:
            norm_md = arc / "manual_csv_normalization.md"
            norm_md.write_text(manual_csv_normalization_markdown, encoding="utf-8")
            paths["archive_manual_csv_normalization_md"] = norm_md
        if manual_csv_normalization_json_payload is not None:
            norm_json = arc / "manual_csv_normalization.json"
            norm_json.write_text(
                json.dumps(manual_csv_normalization_json_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            paths["archive_manual_csv_normalization_json"] = norm_json
        if manual_csv_import_flow_markdown is not None:
            flow_md = arc / "manual_csv_import_flow.md"
            flow_md.write_text(manual_csv_import_flow_markdown, encoding="utf-8")
            paths["archive_manual_csv_import_flow_md"] = flow_md
        if manual_csv_import_flow_json_payload is not None:
            flow_json = arc / "manual_csv_import_flow.json"
            flow_json.write_text(
                json.dumps(manual_csv_import_flow_json_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            paths["archive_manual_csv_import_flow_json"] = flow_json
        if manual_csv_export_request_markdown is not None:
            req_md = arc / "manual_csv_export_request.md"
            req_md.write_text(manual_csv_export_request_markdown, encoding="utf-8")
            paths["archive_manual_csv_export_request_md"] = req_md
        if manual_csv_export_request_json_payload is not None:
            req_json = arc / "manual_csv_export_request.json"
            req_json.write_text(
                json.dumps(manual_csv_export_request_json_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            paths["archive_manual_csv_export_request_json"] = req_json
    if decision_seed_markdown is not None or decision_seed_json_payload is not None:
        seed = out_dir / "validation" / "seeds" / yyyy / report_date
        seed.mkdir(parents=True, exist_ok=True)
        if decision_seed_markdown is not None:
            md_path = seed / "decision_seed.md"
            md_path.write_text(decision_seed_markdown, encoding="utf-8")
            paths["validation_seed_md"] = md_path
        if decision_seed_json_payload is not None:
            js_path = seed / "decision_seed.json"
            js_path.write_text(
                json.dumps(decision_seed_json_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            paths["validation_seed_json"] = js_path
    return paths


def sync_to_reports_repo(
    *,
    reports_repo_path: Path,
    repo_root: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
    quality_audit_markdown: str | None = None,
    feedback_template_markdown: str | None = None,
    decision_seed_markdown: str | None = None,
    decision_seed_json_payload: dict[str, Any] | None = None,
    trap_analysis_markdown: str | None = None,
    trap_analysis_json_payload: dict[str, Any] | None = None,
    cache_refresh_readiness_markdown: str | None = None,
    cache_refresh_readiness_json_payload: dict[str, Any] | None = None,
    cache_refresh_execution_plan_markdown: str | None = None,
    cache_refresh_execution_plan_json_payload: dict[str, Any] | None = None,
    cache_refresh_execute_dry_run_markdown: str | None = None,
    cache_refresh_execute_dry_run_json_payload: dict[str, Any] | None = None,
    cache_refresh_execute_result_markdown: str | None = None,
    cache_refresh_execute_result_json_payload: dict[str, Any] | None = None,
    jp_cache_refresh_dry_run_markdown: str | None = None,
    jp_cache_refresh_dry_run_json_payload: dict[str, Any] | None = None,
    jquants_preflight_markdown: str | None = None,
    jquants_preflight_json_payload: dict[str, Any] | None = None,
    cache_refresh_postcheck_markdown: str | None = None,
    cache_refresh_postcheck_json_payload: dict[str, Any] | None = None,
    jp_alternative_provider_readiness_markdown: str | None = None,
    jp_alternative_provider_readiness_json_payload: dict[str, Any] | None = None,
    jp_alternative_provider_execution_plan_markdown: str | None = None,
    jp_alternative_provider_execution_plan_json_payload: dict[str, Any] | None = None,
    manual_csv_validation_markdown: str | None = None,
    manual_csv_validation_json_payload: dict[str, Any] | None = None,
    manual_csv_import_plan_markdown: str | None = None,
    manual_csv_import_plan_json_payload: dict[str, Any] | None = None,
    manual_csv_import_result_markdown: str | None = None,
    manual_csv_import_result_json_payload: dict[str, Any] | None = None,
    manual_csv_template_markdown: str | None = None,
    manual_csv_template_csv_text: str | None = None,
    manual_csv_discovery_markdown: str | None = None,
    manual_csv_discovery_json_payload: dict[str, Any] | None = None,
    manual_csv_normalization_markdown: str | None = None,
    manual_csv_normalization_json_payload: dict[str, Any] | None = None,
    manual_csv_import_flow_markdown: str | None = None,
    manual_csv_import_flow_json_payload: dict[str, Any] | None = None,
    manual_csv_export_request_markdown: str | None = None,
    manual_csv_export_request_json_payload: dict[str, Any] | None = None,
) -> dict[str, Path]:
    if reports_repo_path.resolve() == repo_root.resolve():
        raise ValueError("reports-repo-path が本体repoと同一です")
    if not reports_repo_path.is_dir():
        raise FileNotFoundError(f"reports repo path が見つかりません: {reports_repo_path}")
    latest = reports_repo_path / "latest"
    weekly = reports_repo_path / "weekly" / report_date[:4] / report_date
    validation_seed = reports_repo_path / "validation" / "seeds" / report_date[:4] / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    validation_seed.mkdir(parents=True, exist_ok=True)
    latest_md = latest / "chatgpt_invest_context_pack.md"
    latest_json = latest / "chatgpt_invest_context_pack.json"
    latest_idx = latest / "index.md"
    weekly_md = weekly / "chatgpt_invest_context_pack.md"
    weekly_json = weekly / "chatgpt_invest_context_pack.json"
    latest_md.write_text(markdown_text, encoding="utf-8")
    latest_json.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    weekly_md.write_text(markdown_text, encoding="utf-8")
    weekly_json.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_idx.write_text(f"# 最新Context Pack\n\n- レポート日: {report_date}\n", encoding="utf-8")
    paths: dict[str, Path] = {
        "reports_latest_md": latest_md,
        "reports_latest_json": latest_json,
        "reports_latest_index": latest_idx,
        "reports_weekly_md": weekly_md,
        "reports_weekly_json": weekly_json,
    }
    if quality_audit_markdown is not None:
        latest_qa = latest / "context_pack_quality_audit.md"
        weekly_qa = weekly / "context_pack_quality_audit.md"
        latest_qa.write_text(quality_audit_markdown, encoding="utf-8")
        weekly_qa.write_text(quality_audit_markdown, encoding="utf-8")
        paths["reports_latest_quality_audit"] = latest_qa
        paths["reports_weekly_quality_audit"] = weekly_qa
    if feedback_template_markdown is not None:
        latest_fb = latest / "decision_feedback_template.md"
        weekly_fb = weekly / "decision_feedback_template.md"
        latest_fb.write_text(feedback_template_markdown, encoding="utf-8")
        weekly_fb.write_text(feedback_template_markdown, encoding="utf-8")
        paths["reports_latest_feedback_template"] = latest_fb
        paths["reports_weekly_feedback_template"] = weekly_fb
    if decision_seed_markdown is not None:
        seed_md = validation_seed / "decision_seed.md"
        seed_md.write_text(decision_seed_markdown, encoding="utf-8")
        paths["reports_validation_seed_md"] = seed_md
    if decision_seed_json_payload is not None:
        seed_json = validation_seed / "decision_seed.json"
        seed_json.write_text(
            json.dumps(decision_seed_json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        paths["reports_validation_seed_json"] = seed_json
    if trap_analysis_markdown is not None:
        latest_trap_md = latest / "trap_analysis.md"
        weekly_trap_md = weekly / "trap_analysis.md"
        latest_trap_md.write_text(trap_analysis_markdown, encoding="utf-8")
        weekly_trap_md.write_text(trap_analysis_markdown, encoding="utf-8")
        paths["reports_latest_trap_analysis_md"] = latest_trap_md
        paths["reports_weekly_trap_analysis_md"] = weekly_trap_md
    if trap_analysis_json_payload is not None:
        latest_trap_json = latest / "trap_analysis.json"
        weekly_trap_json = weekly / "trap_analysis.json"
        latest_trap_json.write_text(json.dumps(trap_analysis_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        weekly_trap_json.write_text(json.dumps(trap_analysis_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["reports_latest_trap_analysis_json"] = latest_trap_json
        paths["reports_weekly_trap_analysis_json"] = weekly_trap_json
    if cache_refresh_readiness_markdown is not None:
        latest_ready_md = latest / "cache_refresh_readiness.md"
        weekly_ready_md = weekly / "cache_refresh_readiness.md"
        latest_ready_md.write_text(cache_refresh_readiness_markdown, encoding="utf-8")
        weekly_ready_md.write_text(cache_refresh_readiness_markdown, encoding="utf-8")
        paths["reports_latest_cache_refresh_readiness_md"] = latest_ready_md
        paths["reports_weekly_cache_refresh_readiness_md"] = weekly_ready_md
    if cache_refresh_readiness_json_payload is not None:
        latest_ready_json = latest / "cache_refresh_readiness.json"
        weekly_ready_json = weekly / "cache_refresh_readiness.json"
        latest_ready_json.write_text(
            json.dumps(cache_refresh_readiness_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        weekly_ready_json.write_text(
            json.dumps(cache_refresh_readiness_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        paths["reports_latest_cache_refresh_readiness_json"] = latest_ready_json
        paths["reports_weekly_cache_refresh_readiness_json"] = weekly_ready_json
    if cache_refresh_execution_plan_markdown is not None:
        latest_plan_md = latest / "cache_refresh_execution_plan.md"
        weekly_plan_md = weekly / "cache_refresh_execution_plan.md"
        latest_plan_md.write_text(cache_refresh_execution_plan_markdown, encoding="utf-8")
        weekly_plan_md.write_text(cache_refresh_execution_plan_markdown, encoding="utf-8")
        paths["reports_latest_cache_refresh_execution_plan_md"] = latest_plan_md
        paths["reports_weekly_cache_refresh_execution_plan_md"] = weekly_plan_md
    if cache_refresh_execution_plan_json_payload is not None:
        latest_plan_json = latest / "cache_refresh_execution_plan.json"
        weekly_plan_json = weekly / "cache_refresh_execution_plan.json"
        latest_plan_json.write_text(
            json.dumps(cache_refresh_execution_plan_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        weekly_plan_json.write_text(
            json.dumps(cache_refresh_execution_plan_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        paths["reports_latest_cache_refresh_execution_plan_json"] = latest_plan_json
        paths["reports_weekly_cache_refresh_execution_plan_json"] = weekly_plan_json
    if cache_refresh_execute_dry_run_markdown is not None:
        latest_execute_md = latest / "cache_refresh_execute_dry_run.md"
        weekly_execute_md = weekly / "cache_refresh_execute_dry_run.md"
        latest_execute_md.write_text(cache_refresh_execute_dry_run_markdown, encoding="utf-8")
        weekly_execute_md.write_text(cache_refresh_execute_dry_run_markdown, encoding="utf-8")
        paths["reports_latest_cache_refresh_execute_dry_run_md"] = latest_execute_md
        paths["reports_weekly_cache_refresh_execute_dry_run_md"] = weekly_execute_md
    if cache_refresh_execute_dry_run_json_payload is not None:
        latest_execute_json = latest / "cache_refresh_execute_dry_run.json"
        weekly_execute_json = weekly / "cache_refresh_execute_dry_run.json"
        latest_execute_json.write_text(
            json.dumps(cache_refresh_execute_dry_run_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        weekly_execute_json.write_text(
            json.dumps(cache_refresh_execute_dry_run_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        paths["reports_latest_cache_refresh_execute_dry_run_json"] = latest_execute_json
        paths["reports_weekly_cache_refresh_execute_dry_run_json"] = weekly_execute_json
    if cache_refresh_execute_result_markdown is not None:
        latest_result_md = latest / "cache_refresh_execute_result.md"
        weekly_result_md = weekly / "cache_refresh_execute_result.md"
        latest_result_md.write_text(cache_refresh_execute_result_markdown, encoding="utf-8")
        weekly_result_md.write_text(cache_refresh_execute_result_markdown, encoding="utf-8")
        paths["reports_latest_cache_refresh_execute_result_md"] = latest_result_md
        paths["reports_weekly_cache_refresh_execute_result_md"] = weekly_result_md
    if cache_refresh_execute_result_json_payload is not None:
        latest_result_json = latest / "cache_refresh_execute_result.json"
        weekly_result_json = weekly / "cache_refresh_execute_result.json"
        latest_result_json.write_text(
            json.dumps(cache_refresh_execute_result_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        weekly_result_json.write_text(
            json.dumps(cache_refresh_execute_result_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        paths["reports_latest_cache_refresh_execute_result_json"] = latest_result_json
        paths["reports_weekly_cache_refresh_execute_result_json"] = weekly_result_json
    if jp_cache_refresh_dry_run_markdown is not None:
        latest_jp_md = latest / "jp_cache_refresh_dry_run.md"
        weekly_jp_md = weekly / "jp_cache_refresh_dry_run.md"
        latest_jp_md.write_text(jp_cache_refresh_dry_run_markdown, encoding="utf-8")
        weekly_jp_md.write_text(jp_cache_refresh_dry_run_markdown, encoding="utf-8")
        paths["reports_latest_jp_cache_refresh_dry_run_md"] = latest_jp_md
        paths["reports_weekly_jp_cache_refresh_dry_run_md"] = weekly_jp_md
    if jp_cache_refresh_dry_run_json_payload is not None:
        latest_jp_json = latest / "jp_cache_refresh_dry_run.json"
        weekly_jp_json = weekly / "jp_cache_refresh_dry_run.json"
        latest_jp_json.write_text(
            json.dumps(jp_cache_refresh_dry_run_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        weekly_jp_json.write_text(
            json.dumps(jp_cache_refresh_dry_run_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        paths["reports_latest_jp_cache_refresh_dry_run_json"] = latest_jp_json
        paths["reports_weekly_jp_cache_refresh_dry_run_json"] = weekly_jp_json
    if jquants_preflight_markdown is not None:
        latest_pre_md = latest / "jquants_preflight.md"
        weekly_pre_md = weekly / "jquants_preflight.md"
        latest_pre_md.write_text(jquants_preflight_markdown, encoding="utf-8")
        weekly_pre_md.write_text(jquants_preflight_markdown, encoding="utf-8")
        paths["reports_latest_jquants_preflight_md"] = latest_pre_md
        paths["reports_weekly_jquants_preflight_md"] = weekly_pre_md
    if jquants_preflight_json_payload is not None:
        latest_pre_json = latest / "jquants_preflight.json"
        weekly_pre_json = weekly / "jquants_preflight.json"
        latest_pre_json.write_text(json.dumps(jquants_preflight_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        weekly_pre_json.write_text(json.dumps(jquants_preflight_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["reports_latest_jquants_preflight_json"] = latest_pre_json
        paths["reports_weekly_jquants_preflight_json"] = weekly_pre_json
    if cache_refresh_postcheck_markdown is not None:
        latest_post_md = latest / "cache_refresh_postcheck.md"
        weekly_post_md = weekly / "cache_refresh_postcheck.md"
        latest_post_md.write_text(cache_refresh_postcheck_markdown, encoding="utf-8")
        weekly_post_md.write_text(cache_refresh_postcheck_markdown, encoding="utf-8")
        paths["reports_latest_cache_refresh_postcheck_md"] = latest_post_md
        paths["reports_weekly_cache_refresh_postcheck_md"] = weekly_post_md
    if cache_refresh_postcheck_json_payload is not None:
        latest_post_json = latest / "cache_refresh_postcheck.json"
        weekly_post_json = weekly / "cache_refresh_postcheck.json"
        latest_post_json.write_text(
            json.dumps(cache_refresh_postcheck_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        weekly_post_json.write_text(
            json.dumps(cache_refresh_postcheck_json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        paths["reports_latest_cache_refresh_postcheck_json"] = latest_post_json
        paths["reports_weekly_cache_refresh_postcheck_json"] = weekly_post_json
    if jp_alternative_provider_readiness_markdown is not None:
        latest_alt_md = latest / "jp_alternative_provider_readiness.md"
        weekly_alt_md = weekly / "jp_alternative_provider_readiness.md"
        latest_alt_md.write_text(jp_alternative_provider_readiness_markdown, encoding="utf-8")
        weekly_alt_md.write_text(jp_alternative_provider_readiness_markdown, encoding="utf-8")
        paths["reports_latest_jp_alternative_provider_readiness_md"] = latest_alt_md
        paths["reports_weekly_jp_alternative_provider_readiness_md"] = weekly_alt_md
    if jp_alternative_provider_readiness_json_payload is not None:
        latest_alt_json = latest / "jp_alternative_provider_readiness.json"
        weekly_alt_json = weekly / "jp_alternative_provider_readiness.json"
        latest_alt_json.write_text(
            json.dumps(jp_alternative_provider_readiness_json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        weekly_alt_json.write_text(
            json.dumps(jp_alternative_provider_readiness_json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        paths["reports_latest_jp_alternative_provider_readiness_json"] = latest_alt_json
        paths["reports_weekly_jp_alternative_provider_readiness_json"] = weekly_alt_json
    if jp_alternative_provider_execution_plan_markdown is not None:
        latest_plan_md = latest / "jp_alternative_provider_execution_plan.md"
        weekly_plan_md = weekly / "jp_alternative_provider_execution_plan.md"
        latest_plan_md.write_text(jp_alternative_provider_execution_plan_markdown, encoding="utf-8")
        weekly_plan_md.write_text(jp_alternative_provider_execution_plan_markdown, encoding="utf-8")
        paths["reports_latest_jp_alternative_provider_execution_plan_md"] = latest_plan_md
        paths["reports_weekly_jp_alternative_provider_execution_plan_md"] = weekly_plan_md
    if jp_alternative_provider_execution_plan_json_payload is not None:
        latest_plan_json = latest / "jp_alternative_provider_execution_plan.json"
        weekly_plan_json = weekly / "jp_alternative_provider_execution_plan.json"
        latest_plan_json.write_text(
            json.dumps(jp_alternative_provider_execution_plan_json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        weekly_plan_json.write_text(
            json.dumps(jp_alternative_provider_execution_plan_json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        paths["reports_latest_jp_alternative_provider_execution_plan_json"] = latest_plan_json
        paths["reports_weekly_jp_alternative_provider_execution_plan_json"] = weekly_plan_json
    if manual_csv_validation_markdown is not None:
        latest_val_md = latest / "manual_csv_validation.md"
        weekly_val_md = weekly / "manual_csv_validation.md"
        latest_val_md.write_text(manual_csv_validation_markdown, encoding="utf-8")
        weekly_val_md.write_text(manual_csv_validation_markdown, encoding="utf-8")
        paths["reports_latest_manual_csv_validation_md"] = latest_val_md
        paths["reports_weekly_manual_csv_validation_md"] = weekly_val_md
    if manual_csv_validation_json_payload is not None:
        latest_val_json = latest / "manual_csv_validation.json"
        weekly_val_json = weekly / "manual_csv_validation.json"
        latest_val_json.write_text(json.dumps(manual_csv_validation_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        weekly_val_json.write_text(json.dumps(manual_csv_validation_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["reports_latest_manual_csv_validation_json"] = latest_val_json
        paths["reports_weekly_manual_csv_validation_json"] = weekly_val_json
    if manual_csv_import_plan_markdown is not None:
        latest_imp_md = latest / "manual_csv_import_plan.md"
        weekly_imp_md = weekly / "manual_csv_import_plan.md"
        latest_imp_md.write_text(manual_csv_import_plan_markdown, encoding="utf-8")
        weekly_imp_md.write_text(manual_csv_import_plan_markdown, encoding="utf-8")
        paths["reports_latest_manual_csv_import_plan_md"] = latest_imp_md
        paths["reports_weekly_manual_csv_import_plan_md"] = weekly_imp_md
    if manual_csv_import_plan_json_payload is not None:
        latest_imp_json = latest / "manual_csv_import_plan.json"
        weekly_imp_json = weekly / "manual_csv_import_plan.json"
        latest_imp_json.write_text(json.dumps(manual_csv_import_plan_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        weekly_imp_json.write_text(json.dumps(manual_csv_import_plan_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["reports_latest_manual_csv_import_plan_json"] = latest_imp_json
        paths["reports_weekly_manual_csv_import_plan_json"] = weekly_imp_json
    if manual_csv_import_result_markdown is not None:
        latest_res_md = latest / "manual_csv_import_result.md"
        weekly_res_md = weekly / "manual_csv_import_result.md"
        latest_res_md.write_text(manual_csv_import_result_markdown, encoding="utf-8")
        weekly_res_md.write_text(manual_csv_import_result_markdown, encoding="utf-8")
        paths["reports_latest_manual_csv_import_result_md"] = latest_res_md
        paths["reports_weekly_manual_csv_import_result_md"] = weekly_res_md
    if manual_csv_import_result_json_payload is not None:
        latest_res_json = latest / "manual_csv_import_result.json"
        weekly_res_json = weekly / "manual_csv_import_result.json"
        latest_res_json.write_text(json.dumps(manual_csv_import_result_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        weekly_res_json.write_text(json.dumps(manual_csv_import_result_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["reports_latest_manual_csv_import_result_json"] = latest_res_json
        paths["reports_weekly_manual_csv_import_result_json"] = weekly_res_json
    if manual_csv_template_markdown is not None:
        latest_tpl_md = latest / "manual_csv_template.md"
        weekly_tpl_md = weekly / "manual_csv_template.md"
        latest_tpl_md.write_text(manual_csv_template_markdown, encoding="utf-8")
        weekly_tpl_md.write_text(manual_csv_template_markdown, encoding="utf-8")
        paths["reports_latest_manual_csv_template_md"] = latest_tpl_md
        paths["reports_weekly_manual_csv_template_md"] = weekly_tpl_md
    if manual_csv_template_csv_text is not None:
        latest_tpl_csv = latest / "manual_csv_template.csv"
        weekly_tpl_csv = weekly / "manual_csv_template.csv"
        latest_tpl_csv.write_text(manual_csv_template_csv_text, encoding="utf-8")
        weekly_tpl_csv.write_text(manual_csv_template_csv_text, encoding="utf-8")
        paths["reports_latest_manual_csv_template_csv"] = latest_tpl_csv
        paths["reports_weekly_manual_csv_template_csv"] = weekly_tpl_csv
    if manual_csv_discovery_markdown is not None:
        latest_disc_md = latest / "manual_csv_discovery.md"
        weekly_disc_md = weekly / "manual_csv_discovery.md"
        latest_disc_md.write_text(manual_csv_discovery_markdown, encoding="utf-8")
        weekly_disc_md.write_text(manual_csv_discovery_markdown, encoding="utf-8")
        paths["reports_latest_manual_csv_discovery_md"] = latest_disc_md
        paths["reports_weekly_manual_csv_discovery_md"] = weekly_disc_md
    if manual_csv_discovery_json_payload is not None:
        latest_disc_json = latest / "manual_csv_discovery.json"
        weekly_disc_json = weekly / "manual_csv_discovery.json"
        latest_disc_json.write_text(
            json.dumps(manual_csv_discovery_json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        weekly_disc_json.write_text(
            json.dumps(manual_csv_discovery_json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        paths["reports_latest_manual_csv_discovery_json"] = latest_disc_json
        paths["reports_weekly_manual_csv_discovery_json"] = weekly_disc_json
    if manual_csv_normalization_markdown is not None:
        latest_norm_md = latest / "manual_csv_normalization.md"
        weekly_norm_md = weekly / "manual_csv_normalization.md"
        latest_norm_md.write_text(manual_csv_normalization_markdown, encoding="utf-8")
        weekly_norm_md.write_text(manual_csv_normalization_markdown, encoding="utf-8")
        paths["reports_latest_manual_csv_normalization_md"] = latest_norm_md
        paths["reports_weekly_manual_csv_normalization_md"] = weekly_norm_md
    if manual_csv_normalization_json_payload is not None:
        latest_norm_json = latest / "manual_csv_normalization.json"
        weekly_norm_json = weekly / "manual_csv_normalization.json"
        latest_norm_json.write_text(
            json.dumps(manual_csv_normalization_json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        weekly_norm_json.write_text(
            json.dumps(manual_csv_normalization_json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        paths["reports_latest_manual_csv_normalization_json"] = latest_norm_json
        paths["reports_weekly_manual_csv_normalization_json"] = weekly_norm_json
    if manual_csv_import_flow_markdown is not None:
        latest_flow_md = latest / "manual_csv_import_flow.md"
        weekly_flow_md = weekly / "manual_csv_import_flow.md"
        latest_flow_md.write_text(manual_csv_import_flow_markdown, encoding="utf-8")
        weekly_flow_md.write_text(manual_csv_import_flow_markdown, encoding="utf-8")
        paths["reports_latest_manual_csv_import_flow_md"] = latest_flow_md
        paths["reports_weekly_manual_csv_import_flow_md"] = weekly_flow_md
    if manual_csv_import_flow_json_payload is not None:
        latest_flow_json = latest / "manual_csv_import_flow.json"
        weekly_flow_json = weekly / "manual_csv_import_flow.json"
        latest_flow_json.write_text(
            json.dumps(manual_csv_import_flow_json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        weekly_flow_json.write_text(
            json.dumps(manual_csv_import_flow_json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        paths["reports_latest_manual_csv_import_flow_json"] = latest_flow_json
        paths["reports_weekly_manual_csv_import_flow_json"] = weekly_flow_json
    if manual_csv_export_request_markdown is not None:
        latest_req_md = latest / "manual_csv_export_request.md"
        weekly_req_md = weekly / "manual_csv_export_request.md"
        latest_req_md.write_text(manual_csv_export_request_markdown, encoding="utf-8")
        weekly_req_md.write_text(manual_csv_export_request_markdown, encoding="utf-8")
        paths["reports_latest_manual_csv_export_request_md"] = latest_req_md
        paths["reports_weekly_manual_csv_export_request_md"] = weekly_req_md
    if manual_csv_export_request_json_payload is not None:
        latest_req_json = latest / "manual_csv_export_request.json"
        weekly_req_json = weekly / "manual_csv_export_request.json"
        latest_req_json.write_text(
            json.dumps(manual_csv_export_request_json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        weekly_req_json.write_text(
            json.dumps(manual_csv_export_request_json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        paths["reports_latest_manual_csv_export_request_json"] = latest_req_json
        paths["reports_weekly_manual_csv_export_request_json"] = weekly_req_json
    return paths


def sync_validation_outputs_to_reports_repo(
    *,
    reports_repo_path: Path,
    repo_root: Path,
    validation_results_dir: Path,
    dashboard_markdown: str | None = None,
    dashboard_json_payload: dict[str, Any] | None = None,
) -> dict[str, Path]:
    if reports_repo_path.resolve() == repo_root.resolve():
        raise ValueError("reports-repo-path が本体repoと同一です")
    if not reports_repo_path.is_dir():
        raise FileNotFoundError(f"reports repo path が見つかりません: {reports_repo_path}")
    results_dst = reports_repo_path / "validation" / "results"
    latest_dst = reports_repo_path / "latest"
    results_dst.mkdir(parents=True, exist_ok=True)
    latest_dst.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for src in sorted(validation_results_dir.glob("**/result_*.json")):
        relative = src.relative_to(validation_results_dir)
        # Normalize stray nested "results/" paths from old runs.
        if relative.parts and relative.parts[0] == "results":
            relative = Path(*relative.parts[1:])
        if not relative.parts:
            continue
        dst = results_dst / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        paths[f"validation_result_{relative.stem}"] = dst
    if dashboard_markdown is not None:
        md1 = results_dst / "validation_dashboard.md"
        md2 = latest_dst / "validation_dashboard.md"
        md1.write_text(dashboard_markdown, encoding="utf-8")
        md2.write_text(dashboard_markdown, encoding="utf-8")
        paths["validation_dashboard_md"] = md1
        paths["latest_validation_dashboard_md"] = md2
    if dashboard_json_payload is not None:
        js = results_dst / "validation_dashboard.json"
        js.write_text(json.dumps(dashboard_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["validation_dashboard_json"] = js
    return paths

