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
    jp_cache_refresh_dry_run_markdown: str | None = None,
    jp_cache_refresh_dry_run_json_payload: dict[str, Any] | None = None,
    cache_refresh_postcheck_markdown: str | None = None,
    cache_refresh_postcheck_json_payload: dict[str, Any] | None = None,
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
        if cache_refresh_postcheck_markdown is not None:
            post_md = latest / "cache_refresh_postcheck.md"
            post_md.write_text(cache_refresh_postcheck_markdown, encoding="utf-8")
            paths["latest_cache_refresh_postcheck_md"] = post_md
        if cache_refresh_postcheck_json_payload is not None:
            post_json = latest / "cache_refresh_postcheck.json"
            post_json.write_text(json.dumps(cache_refresh_postcheck_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths["latest_cache_refresh_postcheck_json"] = post_json
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
        if cache_refresh_postcheck_markdown is not None:
            post_md = arc / "cache_refresh_postcheck.md"
            post_md.write_text(cache_refresh_postcheck_markdown, encoding="utf-8")
            paths["archive_cache_refresh_postcheck_md"] = post_md
        if cache_refresh_postcheck_json_payload is not None:
            post_json = arc / "cache_refresh_postcheck.json"
            post_json.write_text(json.dumps(cache_refresh_postcheck_json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths["archive_cache_refresh_postcheck_json"] = post_json
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
    jp_cache_refresh_dry_run_markdown: str | None = None,
    jp_cache_refresh_dry_run_json_payload: dict[str, Any] | None = None,
    cache_refresh_postcheck_markdown: str | None = None,
    cache_refresh_postcheck_json_payload: dict[str, Any] | None = None,
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

