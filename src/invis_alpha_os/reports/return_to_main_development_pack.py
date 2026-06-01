"""Source-only v77 return-to-main-development packs.

These reports close the DCA side line and return focus to weekly report
assurance, cache-write readiness, actual-import quarantine, portfolio strategy
observation, and ChatGPT handoff. They do not execute live/provider/cache/import
or trading operations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import ROOT_DIR
from invis_alpha_os.data.cache_path_preflight_approval_package import DEFAULT_CANDIDATE_CACHE_PATH
from invis_alpha_os.reports.long_run_development_progress_snapshot import (
    build_long_run_development_progress_snapshot,
)
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_actual_import_readiness_boundary_report,
    build_provider_context_pack_block,
)
from invis_alpha_os.reports.redacted_position_snapshot_input_pack import (
    build_redacted_position_snapshot_template,
    build_redacted_position_strategy_pack,
)
from invis_alpha_os.reports.weekly_workflow_post_merge_observation_plan import (
    EXPECTED_ARTIFACT_NAME,
    EXPECTED_CRON_UTC,
    WORKFLOW_PATH,
    build_weekly_workflow_post_merge_observation_plan,
)


def _safety_summary() -> dict[str, bool]:
    return {
        "provider_live_access_executed": False,
        "live_http_executed": False,
        "tiingo_api_call_executed": False,
        "stooq_yahoo_polygon_live_fetch_executed": False,
        "cache_write_executed": False,
        "cache_directory_created": False,
        "actual_refresh_import_executed": False,
        "manual_actual_import_executed": False,
        "broker_api_access_executed": False,
        "broker_login_executed": False,
        "raw_broker_export_parsed": False,
        "raw_broker_data_persisted": False,
        "raw_ohlcv_api_persistence_executed": False,
        "reports_private_raw_data_written": False,
        "git_tracked_raw_data_written": False,
        "env_secret_displayed": False,
        "workflow_files_modified": False,
        "dependency_pyproject_changed": False,
        "github_settings_changed": False,
        "trading_action_executed": False,
        "order_placement_executed": False,
        "manual_workflow_dispatch_executed": False,
    }


def _payload_base(report_date: str, *, report_name: str, pack_version: str = "v77") -> dict[str, Any]:
    return {
        "pack_version": pack_version,
        "report_name": report_name,
        "source_only": True,
        "report_date": report_date,
    }


def _workflow_source_status(repo_root: Path) -> dict[str, Any]:
    workflow_file = repo_root / WORKFLOW_PATH
    text = workflow_file.read_text(encoding="utf-8") if workflow_file.is_file() else ""
    return {
        "workflow_path": str(WORKFLOW_PATH),
        "workflow_exists_on_main_expected": True,
        "workflow_exists_in_source": workflow_file.is_file(),
        "expected_cron_utc": EXPECTED_CRON_UTC,
        "expected_cron_found": f'cron: "{EXPECTED_CRON_UTC}"' in text,
        "corresponding_jst_schedule": "Saturday 07:00 JST",
        "workflow_dispatch_expected": True,
        "workflow_dispatch_found": "workflow_dispatch:" in text,
        "artifact_name_expected": EXPECTED_ARTIFACT_NAME,
        "artifact_name_found": EXPECTED_ARTIFACT_NAME in text,
        "workflow_direct_change_required_by_v77": False,
    }


def build_weekly_scheduled_run_observation_pack(
    *,
    report_date: str,
    repo_root: Path = ROOT_DIR,
) -> dict[str, Any]:
    v73b = build_weekly_workflow_post_merge_observation_plan(report_date=report_date, repo_root=repo_root)
    workflow = _workflow_source_status(repo_root)
    source_ready = all(
        (
            workflow["workflow_exists_in_source"],
            workflow["expected_cron_found"],
            workflow["workflow_dispatch_found"],
            workflow["artifact_name_found"],
        )
    )
    return {
        **_payload_base(report_date, report_name="weekly_scheduled_run_observation_pack"),
        "weekly_report_status": {
            "v73_workflow_merged": True,
            "next_run_target": v73b["next_run_target"],
            "workflow_source_status": workflow,
            "readiness_verdict": (
                "ready_to_observe_next_scheduled_run_without_dispatch"
                if source_ready
                else "not_ready_workflow_source_mismatch"
            ),
        },
        "operator_next_saturday_checklist": (
            "confirm scheduled run appears after the expected UTC time",
            "confirm workflow conclusion is success",
            "download artifact named weekly-candidate-brief",
            "confirm markdown/copy/operator status files exist in artifact",
            "do not press Run workflow without separate approval",
        ),
        "failure_triage_path": v73b["failure_triage_path"],
        "manual_backfill_path": v73b["manual_backfill_decision_path"],
        "safety_summary": _safety_summary(),
    }


def build_cache_write_pilot_preexecution_readiness_snapshot(
    *,
    report_date: str,
    candidate_cache_path: str = DEFAULT_CANDIDATE_CACHE_PATH,
) -> dict[str, Any]:
    provider = build_provider_context_pack_block(report_date=report_date)
    return {
        **_payload_base(report_date, report_name="cache_write_pilot_preexecution_readiness_snapshot"),
        "candidate_cache_path": candidate_cache_path,
        "consolidated_inputs": {
            "v67": provider["cache_write_readiness_gate_status"],
            "v68": provider["cache_write_operator_signoff_sheet_status"],
            "v69": provider["cache_path_preflight_approval_package_status"],
            "v69B": provider["cache_purge_inventory_dryrun_contract_status"],
            "v70": provider["cache_write_pilot_approval_packet_status"],
            "v70B": provider["cache_write_pilot_result_review_gate_status"],
            "v70C": provider["actual_import_readiness_boundary_status"],
        },
        "readiness_summary": {
            "cache_write_approved": False,
            "cache_write_executed": False,
            "actual_import_approved": False,
            "provider_live_access_approved": False,
            "required_future_cache_write_phrase": "cache writeを実行してよい",
            "required_future_actual_import_phrase": "actual refresh/importを実行してよい",
            "next_human_decision": "whether to issue a scoped future cache-write pilot approval phrase",
        },
        "future_cursor_preflight_checklist": (
            "confirm SIGNOFF-16 remains accepted by human",
            "confirm candidate cache path is private/local and outside source and reports-private",
            "confirm purge/inventory dry-run contract is accepted",
            "confirm redacted manifest schema and stop conditions",
            "confirm exact future cache-write approval phrase exists in the runtime context",
            "confirm actual import remains separately unapproved",
        ),
        "safety_summary": _safety_summary(),
    }


def build_actual_import_quarantine_followthrough_matrix(
    *,
    report_date: str,
    candidate_cache_path: str = DEFAULT_CANDIDATE_CACHE_PATH,
) -> dict[str, Any]:
    _markdown, boundary_payload = build_actual_import_readiness_boundary_report(
        report_date=report_date,
        candidate_cache_path=candidate_cache_path,
    )
    boundary = boundary_payload["actual_import_readiness_boundary"]
    return {
        **_payload_base(report_date, report_name="actual_import_quarantine_followthrough_matrix"),
        "candidate_cache_path": candidate_cache_path,
        "quarantine_boundary": boundary["quarantine_boundary"],
        "followthrough_matrix": (
            {
                "gate": "cache_write_result_review",
                "required_status_before_actual_import": "passed_or_explicitly_reviewed",
                "current_status": boundary["readiness_verdict"]["cache_write_pilot_result_review_readiness"],
                "execution_allowed_now": False,
            },
            {
                "gate": "redacted_manifest",
                "required_status_before_actual_import": "available_and_reviewed",
                "current_status": "not_available_until_future_pilot",
                "execution_allowed_now": False,
            },
            {
                "gate": "data_quality_acceptance",
                "required_status_before_actual_import": "pass",
                "current_status": "not_run",
                "execution_allowed_now": False,
            },
            {
                "gate": "actual_import_approval_phrase",
                "required_status_before_actual_import": "issued_separately",
                "current_status": "not_issued",
                "execution_allowed_now": False,
            },
            {
                "gate": "purge_rollback_verification",
                "required_status_before_actual_import": "available",
                "current_status": "source_contract_only",
                "execution_allowed_now": False,
            },
        ),
        "readiness_verdict": boundary["readiness_verdict"],
        "actual_import_prerequisites": boundary["actual_import_prerequisites"],
        "safety_summary": _safety_summary(),
    }


def build_portfolio_strategy_observation_report(
    *,
    report_date: str,
    symbols_csv: str = "6501.T,7203.T,AAPL,NVDA,GLDM",
) -> dict[str, Any]:
    snapshot_payload = build_redacted_position_snapshot_template(report_date=report_date, symbols_csv=symbols_csv)
    strategy = build_redacted_position_strategy_pack(
        report_date=report_date,
        redacted_snapshot=snapshot_payload["redacted_snapshot_template"],
        symbols_csv=symbols_csv,
    )
    return {
        **_payload_base(report_date, report_name="portfolio_strategy_observation_report"),
        "portfolio_strategy_status": {
            "observation_only": True,
            "uses_generic_position_guard": True,
            "dca_feature_deepening": False,
            "buy_sell_execution_recommendation_allowed": False,
        },
        "framing": {
            "core_satellite": "separate core holdings, satellite positions, and watchlist entries before action discussion",
            "cash_buffer_warning": "cash buffer must be sufficient before any add discussion",
            "individual_stock_weight_warning": "position_weight_pct must remain below max_position_weight_pct",
            "high_beta_leverage_bucket_note": "high-beta or leveraged themes require stricter sizing and thesis review",
        },
        "generic_position_guard": {
            "symbols": [row["symbol"] for row in strategy["rows"]],
            "rows": strategy["rows"],
        },
        "chatgpt_paste_ready_strategy_summary": (
            "Use this observation-only portfolio strategy report to discuss core/satellite framing, cash buffer, "
            "position weight, high-beta exposure, and generic guard blockers. Do not provide buy/sell execution "
            "instructions or broker actions."
        ),
        "safety_summary": _safety_summary(),
    }


def build_chatgpt_main_development_handoff_summary(
    *,
    report_date: str,
    candidate_cache_path: str = DEFAULT_CANDIDATE_CACHE_PATH,
) -> dict[str, Any]:
    weekly = build_weekly_scheduled_run_observation_pack(report_date=report_date)
    cache = build_cache_write_pilot_preexecution_readiness_snapshot(
        report_date=report_date,
        candidate_cache_path=candidate_cache_path,
    )
    actual = build_actual_import_quarantine_followthrough_matrix(
        report_date=report_date,
        candidate_cache_path=candidate_cache_path,
    )
    portfolio = build_portfolio_strategy_observation_report(report_date=report_date)
    progress = build_long_run_development_progress_snapshot(report_date=report_date)
    return {
        **_payload_base(report_date, report_name="chatgpt_main_development_handoff_summary"),
        "summary": {
            "v73_workflow_merged_next_run_observation_required": True,
            "v76_dca_line_closed_generic_guard_only": True,
            "cache_write_pilot_approved": False,
            "actual_import_approved": False,
            "next_main_development_decision_points": (
                "observe next scheduled weekly candidate brief run",
                "decide whether to issue scoped cache-write pilot approval later",
                "keep actual import quarantined until post-pilot acceptance",
                "use portfolio strategy report as observation-only context",
            ),
        },
        "weekly_report_observation_status": weekly["weekly_report_status"],
        "cache_write_readiness_status": cache["readiness_summary"],
        "actual_import_readiness_status": actual["readiness_verdict"],
        "portfolio_strategy_reporting_status": portfolio["portfolio_strategy_status"],
        "development_progress_snapshot": progress,
        "hard_gates": progress["hard_gate_status"],
        "copy_ready_chatgpt_summary": (
            "v77 completed: returned from DCA/nanpin side work to the main development line. "
            "Weekly report scheduled-run observation is the first priority; cache-write pilot remains not approved; "
            "actual import remains quarantined and not approved; portfolio strategy reporting is observation-only; "
            "provider live access/live HTTP/cache write/broker access/raw data/env secrets/workflow changes/trading were not executed."
        ),
        "safety_summary": _safety_summary(),
    }


def _format_table(rows: tuple[dict[str, Any], ...] | list[dict[str, Any]], columns: tuple[str, ...]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return lines


def format_return_to_main_pack_markdown(payload: dict[str, Any]) -> str:
    name = payload["report_name"]
    title = name.replace("_", " ").title()
    lines = [
        f"# {title} v77",
        "",
        "## Verdict",
        f"- report_name: {name}",
        f"- report_date: {payload['report_date']}",
        f"- source_only: {str(payload['source_only']).lower()}",
        "",
    ]
    if name == "weekly_scheduled_run_observation_pack":
        status = payload["weekly_report_status"]
        workflow = status["workflow_source_status"]
        lines.extend(
            [
                "## Weekly Report Observation Status",
                f"- readiness_verdict: {status['readiness_verdict']}",
                f"- workflow_exists_in_source: {str(workflow['workflow_exists_in_source']).lower()}",
                f"- expected_cron_utc: `{workflow['expected_cron_utc']}`",
                f"- corresponding_jst_schedule: {workflow['corresponding_jst_schedule']}",
                f"- workflow_dispatch_found: {str(workflow['workflow_dispatch_found']).lower()}",
                f"- artifact_name_expected: {workflow['artifact_name_expected']}",
                "",
                "## Operator Checklist",
            ]
        )
        lines.extend(f"- {item}" for item in payload["operator_next_saturday_checklist"])
    elif name == "cache_write_pilot_preexecution_readiness_snapshot":
        summary = payload["readiness_summary"]
        lines.extend(
            [
                "## Cache-Write Readiness Status",
                f"- candidate_cache_path: `{payload['candidate_cache_path']}`",
                f"- cache_write_approved: {str(summary['cache_write_approved']).lower()}",
                f"- actual_import_approved: {str(summary['actual_import_approved']).lower()}",
                f"- provider_live_access_approved: {str(summary['provider_live_access_approved']).lower()}",
                f"- required_future_cache_write_phrase: {summary['required_future_cache_write_phrase']}",
                f"- next_human_decision: {summary['next_human_decision']}",
                "",
                "## Future Cursor Preflight Checklist",
            ]
        )
        lines.extend(f"- {item}" for item in payload["future_cursor_preflight_checklist"])
    elif name == "actual_import_quarantine_followthrough_matrix":
        lines.extend(["## Actual Import Follow-Through Matrix"])
        lines.extend(_format_table(list(payload["followthrough_matrix"]), ("gate", "current_status", "execution_allowed_now")))
    elif name == "portfolio_strategy_observation_report":
        framing = payload["framing"]
        lines.extend(
            [
                "## Portfolio Strategy Reporting Status",
                f"- observation_only: {str(payload['portfolio_strategy_status']['observation_only']).lower()}",
                f"- uses_generic_position_guard: {str(payload['portfolio_strategy_status']['uses_generic_position_guard']).lower()}",
                f"- core_satellite: {framing['core_satellite']}",
                f"- cash_buffer_warning: {framing['cash_buffer_warning']}",
                f"- individual_stock_weight_warning: {framing['individual_stock_weight_warning']}",
                f"- high_beta_leverage_bucket_note: {framing['high_beta_leverage_bucket_note']}",
                "",
                "## Generic Position Guard",
            ]
        )
        lines.extend(
            _format_table(
                list(payload["generic_position_guard"]["rows"]),
                ("symbol", "generic_guard_label", "cash_buffer_status", "thesis_status"),
            )
        )
    elif name == "chatgpt_main_development_handoff_summary":
        summary = payload["summary"]
        lines.extend(
            [
                "## Main Development Handoff",
                f"- v73_workflow_merged_next_run_observation_required: {str(summary['v73_workflow_merged_next_run_observation_required']).lower()}",
                f"- v76_dca_line_closed_generic_guard_only: {str(summary['v76_dca_line_closed_generic_guard_only']).lower()}",
                f"- cache_write_pilot_approved: {str(summary['cache_write_pilot_approved']).lower()}",
                f"- actual_import_approved: {str(summary['actual_import_approved']).lower()}",
                "",
                "## Next Decision Points",
            ]
        )
        lines.extend(f"- {item}" for item in summary["next_main_development_decision_points"])
        lines.extend(["", "## Short Summary to Paste to ChatGPT", payload["copy_ready_chatgpt_summary"]])
    lines.extend(["", "## Safety Summary"])
    for key, value in payload["safety_summary"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def format_return_to_main_pack_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_return_to_main_pack_outputs(
    *,
    out_dir: Path,
    report_date: str,
    stem: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / f"{stem}.md"
        json_path = root / f"{stem}.json"
        md_path.write_text(markdown_text, encoding="utf-8")
        json_path.write_text(format_return_to_main_pack_json(json_payload) + "\n", encoding="utf-8")
        paths[f"{label}_{stem}_md"] = md_path
        paths[f"{label}_{stem}_json"] = json_path
    return paths
