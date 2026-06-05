from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Optional

import typer

from invis_alpha_os.cli.bars_file_symbol import normalize_generic_bars_file_symbol_label
from invis_alpha_os.config import CONFIG_DIR, OUTPUTS_DIR, load_yaml
from invis_alpha_os.config.env_file_loader import (
    EnvFileLoaderError,
    apply_allowlisted_env_file,
    env_file_load_metadata,
)
from invis_alpha_os.config.paths import ROOT_DIR
from invis_alpha_os.config.jp_watchlist import (
    load_jp_watchlist_tickers,
    normalize_jquants_equity_code,
)
from invis_alpha_os.config.us_watchlist import normalize_us_symbol
from invis_alpha_os.data.jquants_daily_bars_cache import (
    save_jquants_daily_bars_cache,
    try_load_cached_daily_bars,
    utc_now_iso,
)
from invis_alpha_os.data.us_daily_bars_cache import (
    build_us_daily_bars_cache_preview,
    format_us_daily_bars_cache_preview_json,
    format_us_daily_bars_cache_preview_markdown,
    save_us_daily_bars_cache,
)
from invis_alpha_os.data.us_daily_bars_cache_inventory import (
    build_us_daily_bars_cache_inventory,
    format_us_daily_bars_cache_inventory_json,
    format_us_daily_bars_cache_inventory_markdown,
)
from invis_alpha_os.data.us_daily_bars_metrics import (
    build_us_daily_bars_cache_metrics_preview,
    format_us_daily_bars_cache_metrics_json,
    format_us_daily_bars_cache_metrics_markdown,
)
from invis_alpha_os.data.us_cache_signals import (
    attach_us_asset_universe_metadata_to_signals_preview,
    build_us_cache_signals_preview,
    format_us_cache_signals_preview_json,
    format_us_cache_signals_preview_markdown,
)
from invis_alpha_os.data.us_provider_preview import build_us_provider_preview_plan
from invis_alpha_os.data.us_provider_live_preview import (
    stooq_live_preview_sanitized_bars,
    stooq_live_preview_shape_digest,
)
from invis_alpha_os.data.us_provider_cache_preview_batch import (
    render_us_provider_cache_preview_batch_markdown,
    run_stooq_cache_preview_batch,
    symbols_from_us_watchlist_file,
)
from invis_alpha_os.data.us_provider_manual_live_batch_smoke import (
    build_us_provider_manual_live_batch_smoke_payload,
    render_manual_live_batch_smoke_markdown,
)
from invis_alpha_os.data.us_provider_scheduled_ingest_plan import (
    build_us_provider_scheduled_ingest_plan,
    merged_symbols_for_scheduled_ingest_plan,
    render_us_provider_scheduled_ingest_plan_markdown,
)
from invis_alpha_os.data.adapters import (
    EdinetStubAdapter,
    JQuantsClient,
    JQuantsStubAdapter,
    SecStubAdapter,
    YFinanceFallbackAdapter,
)
from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.observation.us_signals_batch import (
    log_us_signals_batch_observations,
    observation_batch_failed,
)
from invis_alpha_os.observation.us_peer_sync_batch import (
    log_peer_sync_snapshot_observations,
    peer_sync_log_failed,
)
from invis_alpha_os.observation.us_peer_sync_summary import summarize_peer_sync_observation_log
from invis_alpha_os.product.peer_sync_cache_only import (
    build_peer_sync_cache_only_report,
    format_peer_sync_cache_only_json,
    format_peer_sync_cache_only_markdown,
)
from invis_alpha_os.product.observation_health import (
    build_observation_health_report,
    format_observation_health_json,
    format_observation_health_markdown,
)
from invis_alpha_os.product.ops_smoke_report import (
    build_ops_smoke_report,
    format_ops_smoke_json,
    format_ops_smoke_markdown,
)
from invis_alpha_os.product.operator_dashboard_summary import (
    build_operator_dashboard_summary,
    format_operator_dashboard_summary_json,
    render_operator_dashboard_summary_markdown,
)
from invis_alpha_os.product.v1_operational_readiness import (
    build_v1_operational_readiness,
    format_v1_operational_readiness_json,
    render_v1_operational_readiness_markdown,
)
from invis_alpha_os.product.ops_smoke_taxonomy import format_strict_taxonomy_stderr_line
from invis_alpha_os.product.portfolio_exposure_by_signal_veto import (
    build_portfolio_exposure_by_signal_veto,
    format_portfolio_exposure_by_signal_veto_markdown,
)
from invis_alpha_os.product.portfolio_observation_summary import (
    build_portfolio_observation_summary,
    format_portfolio_observation_summary_json,
    format_portfolio_observation_summary_markdown,
)
from invis_alpha_os.product.progress_dashboard_consistency import (
    check_progress_dashboard_consistency,
    format_progress_dashboard_consistency_json,
    render_progress_dashboard_consistency_markdown,
)
from invis_alpha_os.product.state_consistency import (
    check_state_consistency,
    format_state_consistency_json,
    render_state_consistency_markdown,
)
from invis_alpha_os.product.raw_input_quarantine_v110 import (
    QuarantineSourceKind,
    RawInputQuarantineManifestV110,
    format_raw_input_quarantine_review_json_v110,
    render_raw_input_quarantine_review_markdown_v110,
    review_raw_input_quarantine_manifest_v110,
)
from invis_alpha_os.product.raw_input_quarantine_review_v111 import (
    build_declared_raw_excel_manifest_fixture_v111,
    build_portfolio_quarantine_cross_review_v111,
    format_portfolio_quarantine_cross_review_json_v111,
    render_portfolio_quarantine_cross_review_markdown_v111,
)
from invis_alpha_os.product.report_ux_language_contract import (
    build_report_ux_language_contract,
    format_report_ux_language_contract_json,
    render_report_ux_language_contract_markdown,
)
from invis_alpha_os.product.sample_output_pack_v112 import render_sample_output_pack_markdown_v112
from invis_alpha_os.product.sample_output_regeneration_contract import (
    build_sample_output_regeneration_contract,
    format_sample_output_regeneration_contract_json,
    render_sample_output_regeneration_contract_markdown,
)
from invis_alpha_os.product.monthly_review_pack_integration import (
    build_monthly_review_pack_integration_result,
    format_monthly_review_pack_integration_json,
    render_monthly_review_pack_integration_markdown,
)
from invis_alpha_os.product.portfolio_data_quality_review_v109 import (
    build_portfolio_data_quality_review_v109,
    format_portfolio_data_quality_review_json_v109,
    render_portfolio_data_quality_review_markdown_v109,
)
from invis_alpha_os.product.us_forward_return_validation import (
    compute_us_forward_returns,
    format_us_forward_return_markdown,
    parse_positive_horizons,
)
from invis_alpha_os.product.peer_sync_forward_validation import (
    compute_peer_sync_forward_join,
    format_peer_sync_forward_markdown,
)
from invis_alpha_os.product.jp_peer_sync_loader import (
    build_jp_peer_sync_readiness_report,
    format_jp_peer_sync_readiness_markdown,
)
from invis_alpha_os.reports.us_observation_summary import render_us_observation_summary_markdown
from invis_alpha_os.product.us_universe_expansion import (
    build_us_universe_expansion_report,
    format_us_universe_expansion_markdown,
)
from invis_alpha_os.product.weekly_us_observation import (
    format_weekly_us_observation_markdown,
    run_weekly_us_observation_cycle,
    build_enriched_us_observation_summary,
    us_cache_expansion_report,
)
from invis_alpha_os.product.weekly_artifact_local_verification import (
    format_weekly_artifact_local_verification_json,
    render_weekly_artifact_local_verification_markdown,
    verify_weekly_candidate_brief_local_artifacts,
)
from invis_alpha_os.product.weekly_report_user_summary import (
    build_weekly_report_user_summary,
    format_weekly_report_user_summary_json,
    render_weekly_report_user_summary_markdown,
)
from invis_alpha_os.product.evidence_manifest import (
    build_evidence_manifest,
    write_evidence_manifest_report,
)
from invis_alpha_os.portfolio.shadow_portfolio import ShadowPortfolioService
from invis_alpha_os.reporting.jquants_smoke_summary import (
    build_watchlist_filename_date_slug,
    build_watchlist_smoke_summary_document,
    save_watchlist_smoke_summary_payload,
)
from invis_alpha_os.reports.jquants_watchlist_daily import render_jquants_watchlist_bars_check_section
from invis_alpha_os.reports.momentum_daily import (
    render_momentum_signals_cache_only_section,
    render_momentum_signals_mixed_section,
    render_us_momentum_cache_only_section,
)
from invis_alpha_os.discovery.jp_universe_scanner import (
    format_jp_discovery_json,
    format_jp_discovery_markdown,
    scan_jp_universe,
)
from invis_alpha_os.discovery.us_universe_scanner import (
    format_us_discovery_json,
    format_us_discovery_markdown,
    scan_us_universe,
)
from invis_alpha_os.reports.daily_email import build_daily_email_from_bundle
from invis_alpha_os.reports.weekly_candidate_brief_email import build_weekly_candidate_brief_email_draft
from invis_alpha_os.reports.weekly_report_schedule_diagnostic import (
    build_weekly_report_schedule_diagnostic,
    format_weekly_report_schedule_diagnostic_json,
    format_weekly_report_schedule_diagnostic_markdown,
    write_weekly_report_schedule_diagnostic_outputs,
)
from invis_alpha_os.reports.scheduled_report_observability import (
    build_scheduled_report_observability,
    format_scheduled_report_observability_json,
    format_scheduled_report_observability_markdown,
    write_scheduled_report_observability_outputs,
)
from invis_alpha_os.reports.weekly_report_recovery_runbook import (
    build_weekly_report_recovery_runbook,
    format_weekly_report_recovery_runbook_json,
    format_weekly_report_recovery_runbook_markdown,
    write_weekly_report_recovery_runbook_outputs,
)
from invis_alpha_os.reports.weekly_report_workflow_approval_package import (
    build_weekly_report_workflow_approval_package,
    format_weekly_report_workflow_approval_package_json,
    format_weekly_report_workflow_approval_package_markdown,
    write_weekly_report_workflow_approval_package_outputs,
)
from invis_alpha_os.reports.weekly_report_local_dryrun_backfill_contract import (
    build_weekly_report_local_dryrun_backfill_contract,
    format_weekly_report_local_dryrun_backfill_contract_json,
    format_weekly_report_local_dryrun_backfill_contract_markdown,
    write_weekly_report_local_dryrun_backfill_contract_outputs,
)
from invis_alpha_os.reports.long_run_operator_preflight import (
    build_long_run_operator_preflight_pack,
    format_long_run_operator_preflight_pack_json,
    format_long_run_operator_preflight_pack_markdown,
    write_long_run_operator_preflight_pack_outputs,
)
from invis_alpha_os.reports.scheduled_report_assurance_snapshot import (
    build_scheduled_report_assurance_snapshot,
    format_scheduled_report_assurance_snapshot_json,
    format_scheduled_report_assurance_snapshot_markdown,
    write_scheduled_report_assurance_snapshot_outputs,
)
from invis_alpha_os.reports.weekly_report_workflow_patch_review_gate import (
    build_weekly_report_workflow_patch_review_gate,
    format_weekly_report_workflow_patch_review_gate_json,
    format_weekly_report_workflow_patch_review_gate_markdown,
    write_weekly_report_workflow_patch_review_gate_outputs,
)
from invis_alpha_os.reports.weekly_report_manual_backfill_command_pack import (
    build_weekly_report_manual_backfill_command_pack,
    format_weekly_report_manual_backfill_command_pack_json,
    format_weekly_report_manual_backfill_command_pack_markdown,
    write_weekly_report_manual_backfill_command_pack_outputs,
)
from invis_alpha_os.reports.scheduled_report_failure_triage_matrix import (
    build_scheduled_report_failure_triage_matrix,
    format_scheduled_report_failure_triage_matrix_json,
    format_scheduled_report_failure_triage_matrix_markdown,
    write_scheduled_report_failure_triage_matrix_outputs,
)
from invis_alpha_os.reports.long_run_development_progress_snapshot import (
    build_long_run_development_progress_snapshot,
    format_long_run_development_progress_snapshot_json,
    format_long_run_development_progress_snapshot_markdown,
    write_long_run_development_progress_snapshot_outputs,
)
from invis_alpha_os.reports.weekly_workflow_post_merge_observation_plan import (
    build_weekly_workflow_post_merge_observation_plan,
    format_weekly_workflow_post_merge_observation_plan_json,
    format_weekly_workflow_post_merge_observation_plan_markdown,
    write_weekly_workflow_post_merge_observation_plan_outputs,
)
from invis_alpha_os.reports.position_aware_dca_decision_pack import (
    DEFAULT_POSITION_GUARD_SYMBOLS,
    build_position_aware_dca_decision_pack,
    format_position_aware_dca_decision_pack_json,
    format_position_aware_dca_decision_pack_markdown,
    write_position_aware_dca_decision_pack_outputs,
)
from invis_alpha_os.reports.redacted_position_snapshot_input_pack import (
    build_redacted_position_human_input_checklist,
    build_redacted_position_snapshot_template,
    build_redacted_position_strategy_pack,
    format_redacted_position_json,
    format_redacted_position_human_input_checklist_markdown,
    format_redacted_position_snapshot_template_markdown,
    format_redacted_position_snapshot_validation_markdown,
    format_redacted_position_strategy_pack_markdown,
    load_redacted_position_snapshot_json,
    validate_redacted_position_snapshot,
    write_redacted_position_outputs,
)
from invis_alpha_os.reports.return_to_main_development_pack import (
    build_actual_import_quarantine_followthrough_matrix,
    build_cache_write_pilot_preexecution_readiness_snapshot,
    build_chatgpt_main_development_handoff_summary,
    build_portfolio_strategy_observation_report,
    build_weekly_scheduled_run_observation_pack,
    format_return_to_main_pack_json,
    format_return_to_main_pack_markdown,
    write_return_to_main_pack_outputs,
)
from invis_alpha_os.reports.monthly_portfolio_strategy_observation_pack import (
    build_monthly_chatgpt_portfolio_review_pack,
    build_monthly_portfolio_allocation_guardrails,
    build_monthly_portfolio_snapshot_template,
    build_portfolio_cleanup_candidate_matrix,
    format_monthly_portfolio_strategy_json,
    format_monthly_portfolio_strategy_markdown,
    load_monthly_portfolio_snapshot_json,
    validate_monthly_portfolio_snapshot,
    write_monthly_portfolio_strategy_outputs,
)
from invis_alpha_os.reports.chatgpt_context_archive import (
    sync_validation_outputs_to_reports_repo,
    sync_to_reports_repo,
    write_context_pack_outputs,
)
from invis_alpha_os.reports.cache_refresh_readiness import build_cache_refresh_readiness_report
from invis_alpha_os.reports.chatgpt_context_quality import build_context_pack_quality_audit
from invis_alpha_os.reports.chatgpt_decision_feedback import build_decision_feedback_template
from invis_alpha_os.reports.chatgpt_context_enrichment import build_context_enrichment
from invis_alpha_os.reports.chatgpt_forward_validation_seed import build_forward_validation_seed
from invis_alpha_os.reports.chatgpt_forward_validation import build_validation_seed, evaluate_validation_seeds
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.cache_refresh_execution_plan import build_cache_refresh_execution_plan
from invis_alpha_os.reports.cache_refresh_execute import build_cache_refresh_execute
from invis_alpha_os.reports.jp_cache_refresh_dry_run import build_jp_cache_refresh_dry_run
from invis_alpha_os.reports.jquants_preflight import build_jquants_preflight
from invis_alpha_os.reports.jp_alternative_provider_readiness import build_jp_alternative_provider_readiness
from invis_alpha_os.reports.jp_alternative_provider_execution_plan import build_jp_alternative_provider_execution_plan
from invis_alpha_os.reports.manual_csv_guards import (
    ManualCsvPathError,
    resolve_manual_csv_path,
    resolve_manual_data_path,
)
from invis_alpha_os.reports.manual_csv_validation import validate_manual_csv_file
from invis_alpha_os.reports.manual_csv_import_plan import build_manual_csv_import_plan
from invis_alpha_os.reports.manual_csv_import_execute import build_manual_csv_import_execute
from invis_alpha_os.reports.manual_csv_discovery import build_manual_csv_discovery
from invis_alpha_os.reports.manual_data_discovery import build_manual_data_discovery
from invis_alpha_os.reports.report_dir_resolution import resolve_weekly_report_dir
from invis_alpha_os.reports.manual_data_export_package import build_manual_data_export_package
from invis_alpha_os.reports.jp_ohlcv_freshness_source_strategy import (
    build_jp_ohlcv_freshness_source_strategy,
    sync_jp_ohlcv_freshness_source_strategy_to_reports_repo,
    write_jp_ohlcv_freshness_source_strategy_outputs,
)
from invis_alpha_os.reports.jquants_env_preflight_refresh_pack import (
    build_jquants_env_preflight_refresh_pack,
    sync_jquants_env_preflight_refresh_pack_to_reports_repo,
    write_jquants_env_preflight_refresh_pack_outputs,
)
from invis_alpha_os.reports.investment_readiness_after_jquants_refresh import (
    build_investment_readiness_v31,
    sync_investment_readiness_v31_to_reports_repo,
    write_investment_readiness_v31_outputs,
)
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    DEFAULT_CANDIDATE_CACHE_PATH,
    build_cache_path_preflight_approval_package_report,
    build_cache_purge_inventory_dryrun_contract_report,
    build_cache_write_pilot_approval_packet_report,
    build_cache_write_pilot_result_review_gate_report,
    build_actual_import_readiness_boundary_report,
    build_cache_write_operator_signoff_sheet_report,
    build_cache_write_readiness_gate_report,
    build_cross_provider_validation_result_review_report,
    build_cross_provider_validation_runbook_report,
    build_tiingo_current_docs_recheck_pack_report,
    build_tiingo_live_fetch_result_review_report,
    build_tiingo_manual_signoff_ledger_report,
    build_ohlcv_provider_automation_core,
    build_ohlcv_provider_approval_package,
    build_ohlcv_provider_approved_execution_runbook,
    build_ohlcv_provider_execution_approval_request,
    build_ohlcv_provider_safe_execution_harness,
    build_ohlcv_provider_coverage_matrix,
    build_ohlcv_provider_registry_strategy,
    build_us_ohlcv_pilot_approval_bundle_report,
    build_us_ohlcv_provider_selection_matrix_report,
    build_us_provider_current_evidence_pack_report,
    write_ohlcv_provider_automation_core_outputs,
    write_ohlcv_provider_approval_package_outputs,
    write_ohlcv_provider_approved_execution_runbook_outputs,
    write_ohlcv_provider_execution_approval_request_outputs,
    write_ohlcv_provider_safe_execution_harness_outputs,
    write_cache_path_preflight_approval_package_outputs,
    write_cache_purge_inventory_dryrun_contract_outputs,
    write_cache_write_pilot_approval_packet_outputs,
    write_cache_write_pilot_result_review_gate_outputs,
    write_actual_import_readiness_boundary_outputs,
    write_cache_write_operator_signoff_sheet_outputs,
    write_cache_write_readiness_gate_outputs,
    write_cross_provider_validation_result_review_outputs,
    write_cross_provider_validation_runbook_outputs,
    write_tiingo_current_docs_recheck_pack_outputs,
    write_tiingo_live_fetch_result_review_outputs,
    write_tiingo_manual_signoff_ledger_outputs,
    write_us_ohlcv_pilot_approval_bundle_outputs,
    write_us_ohlcv_provider_selection_matrix_outputs,
    write_us_provider_current_evidence_pack_outputs,
)
from invis_alpha_os.data.ohlcv_provider_approval_request import approval_request_scenario_from_cli
from invis_alpha_os.data.ohlcv_provider_runbook import scenario_from_cli
from invis_alpha_os.reports.post_contract_ohlcv_structural_analysis_v32 import (
    build_post_contract_structural_v32,
    sync_post_contract_structural_v32_to_reports_repo,
    write_post_contract_structural_v32_outputs,
)
from invis_alpha_os.reports.manual_data_actual_import_v35 import (
    run_manual_import_v35,
    sync_manual_import_v35_to_reports_repo,
    write_manual_import_v35_outputs,
)
from invis_alpha_os.reports.stooq_manual_csv_ingest import (
    build_stooq_manual_csv_ingest_v34,
    sync_stooq_ingest_v34_to_reports_repo,
    write_stooq_manual_csv_ingest_v34_outputs,
)
from invis_alpha_os.reports.manual_data_acquisition_ux_pack import (
    build_manual_data_acquisition_ux_pack,
    sync_manual_data_acquisition_ux_to_reports_repo,
    write_manual_data_acquisition_ux_outputs,
)
from invis_alpha_os.reports.manual_data_dropzone import (
    build_manual_data_dropzone_status,
    ensure_dropzone_assets,
)
from invis_alpha_os.reports.manual_data_freshness_pipeline import (
    build_manual_data_freshness_pipeline,
    sync_manual_data_freshness_to_reports_repo,
    write_manual_data_freshness_outputs,
)
from invis_alpha_os.reports.manual_data_import_flow import build_manual_data_import_flow
from invis_alpha_os.reports.manual_data_schema_guard import DEFAULT_TARGET_TICKERS_CSV
from invis_alpha_os.reports.manual_data_normalizer import build_manual_data_normalization
from invis_alpha_os.reports.manual_csv_export_request import build_manual_csv_export_request
from invis_alpha_os.reports.manual_csv_import_flow import build_manual_csv_import_flow
from invis_alpha_os.reports.manual_csv_normalizer import build_manual_csv_normalization
from invis_alpha_os.reports.manual_csv_template import build_manual_csv_template
from invis_alpha_os.reports.cache_refresh_postcheck import build_cache_refresh_postcheck
from invis_alpha_os.reports.gmail_delivery import (
    GmailDeliveryError,
    GmailSendBlockedError,
    build_mime_message,
    classify_gmail_failure,
    credentials_configured,
    encode_message_raw,
    resolve_gmail_sender,
    send_gmail_message,
    validate_gmail_send_gates,
    write_email_previews,
)
from invis_alpha_os.reports.symbol_display_names import display_symbol
from invis_alpha_os.reports.us_cache_preview_opt_in import (
    append_us_cache_preview_section,
    build_us_cache_opt_in_preview,
)
from invis_alpha_os.reports.us_signals_opt_in import append_us_signals_dry_run_section
from invis_alpha_os.risk.veto_rules import (
    VetoEngine,
    build_momentum_veto_result,
    format_veto_table_cell,
)
from invis_alpha_os.signals.momentum import (
    analyze_bars_for_code,
    build_momentum_signals,
    load_bars_json_file,
    momentum_row_public_dict,
    synthetic_bars_for_code,
)
from invis_alpha_os.operator.dev_loop import (
    default_profile_path,
    default_task_queue_path,
    dev_loop_should_exit_nonzero,
    run_dev_loop,
)
from invis_alpha_os.operator.operator_autopilot import (
    collect_autopilot_status,
    format_autopilot_status_json,
    format_autopilot_status_markdown,
)
from invis_alpha_os.operator.post_run_integrate import format_integrate_markdown, run_post_run_integrate
from invis_alpha_os.operator.post_run_review import build_post_run_review_markdown
from invis_alpha_os.operator.runner import RunnerStop, default_policy_path, default_task_path, run_operator_task
from invis_alpha_os.operator.pr_loop import run_pr_loop
from invis_alpha_os.utils.date_utils import today_jst_iso

app = typer.Typer(help="Laputa Alpha OS CLI (Phase 0-v1.1)")
snapshot_app = typer.Typer(help="Snapshot commands")
log_app = typer.Typer(help="Log commands")
validate_app = typer.Typer(help="Cache-only validation (observation only)")
debug_app = typer.Typer(help="Debug commands")
operator_runner_app = typer.Typer(help="Policy-gated local operator runner (dry-run default)")

app.add_typer(snapshot_app, name="snapshot")
app.add_typer(log_app, name="log")
app.add_typer(validate_app, name="validate")
app.add_typer(debug_app, name="debug")
app.add_typer(operator_runner_app, name="operator-runner")


def _obs_service() -> ObservationService:
    return ObservationService(
        observation_path=OUTPUTS_DIR / "observation_log" / "observation_log.jsonl",
        outcome_path=OUTPUTS_DIR / "outcome_log" / "outcome_log.jsonl",
    )


def _apply_optional_jquants_env_file(env_file: str | None) -> dict[str, object] | None:
    if not env_file:
        return None
    try:
        result = apply_allowlisted_env_file(Path(env_file), repo_root=ROOT_DIR)
    except EnvFileLoaderError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from exc
    return env_file_load_metadata(result)


def _echo_env_file_meta(command: str, env_file_meta: dict[str, object] | None) -> None:
    if not env_file_meta:
        return
    loaded = env_file_meta.get("keys_loaded_from_file") or []
    skipped = env_file_meta.get("keys_skipped_existing") or []
    typer.echo(
        f"{command}: env_file_used=true keys_loaded_count={len(loaded)} keys_skipped_existing_count={len(skipped)}"
    )


def _jp_watchlist_count(jp_rows: object) -> int:
    if not isinstance(jp_rows, list):
        return 0
    total = 0
    for row in jp_rows:
        if isinstance(row, str) and row.strip():
            total += 1
        elif isinstance(row, dict) and str(row.get("ticker", "")).strip():
            total += 1
    return total


def _jquants_report_settings() -> dict[str, Any]:
    data = load_yaml(CONFIG_DIR / "market_data.yaml")
    md = data.get("market_data")
    if not isinstance(md, dict):
        return {}
    adapters = md.get("adapters")
    if not isinstance(adapters, dict):
        return {}
    jq = adapters.get("jquants")
    if not isinstance(jq, dict):
        return {}
    rep = jq.get("report")
    return dict(rep) if isinstance(rep, dict) else {}


def _daily_report_momentum_sections_flags() -> tuple[bool, bool, bool]:
    """JP cache/mixed gates + optional US cache-only gate (default off)."""

    cfg = load_yaml(CONFIG_DIR / "market_data.yaml")
    dr = cfg.get("daily_report")
    if not isinstance(dr, dict):
        return (True, True, False)

    def _as_bool(raw: object, default: bool) -> bool:
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            stripped = raw.strip().lower()
            if stripped in ("true", "1", "yes", "on"):
                return True
            if stripped in ("false", "0", "no", "off", ""):
                return False
        return default

    cache_on = _as_bool(dr.get("include_momentum_cache_only_section", True), default=True)
    mixed_on = _as_bool(dr.get("include_momentum_mixed_section", True), default=True)
    us_on = _as_bool(dr.get("include_us_momentum_cache_only_section", False), default=False)
    return cache_on, mixed_on, us_on


@app.command("status")
def status() -> None:
    typer.echo("Laputa Alpha OS")
    typer.echo("Current Mode: Observation Only + Shadow Portfolio")
    typer.echo("No Auto Trading")


@app.command("config-check")
def config_check() -> None:
    required = [
        "watchlist.yaml",
        "peer_map.yaml",
        "weights.yaml",
        "veto_rules.yaml",
        "market_risk_indicators.yaml",
        "account_rules.yaml",
        "data_confidence.yaml",
        "market_data.yaml",
        "us_watchlist.yaml",
        "us_market_data.yaml",
    ]
    missing = [name for name in required if not (CONFIG_DIR / name).exists()]
    if missing:
        raise typer.Exit(code=1)
    typer.echo("config-check: OK")


@app.command("us-watchlist-preview")
def us_watchlist_preview_command() -> None:
    """Print normalized US observation-universe symbols (no HTTP)."""

    from invis_alpha_os.config.us_watchlist import load_us_watchlist_tickers

    typer.echo("US watchlist symbols:")
    for s in load_us_watchlist_tickers():
        typer.echo(s)


@app.command("daily")
def daily(
    us_signals_dry_run_manifest: Optional[str] = typer.Option(
        None,
        "--us-signals-dry-run-manifest",
        help="Optional US signals batch manifest JSON; appends dry-run section only when set.",
    ),
    us_cache_preview: bool = typer.Option(
        False,
        "--us-cache-preview",
        help="Append US cache-only preview table (read-only; default off).",
    ),
    us_momentum_section: bool = typer.Option(
        False,
        "--us-momentum-section",
        help="Append US momentum cache-only table with veto column (read-only; default off).",
    ),
    write_observation_log: bool = typer.Option(
        False,
        "--write-observation-log",
        help="Append US signals batch rows to observation_log.jsonl (requires --us-signals-dry-run-manifest).",
    ),
    us_observation_summary: bool = typer.Option(
        False,
        "--us-observation-summary",
        help="Append US observation usefulness summary (cache-only; default off).",
    ),
) -> None:
    today = today_jst_iso()
    out = OUTPUTS_DIR / "reports" / "daily" / f"{today}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    watchlist = load_yaml(CONFIG_DIR / "watchlist.yaml")
    jp_n = _jp_watchlist_count(watchlist.get("jp_watchlist", []))
    jquants = JQuantsStubAdapter()
    if jquants.is_enabled():
        jq_line = "J-Quants stub enabled (Phase 1a; no live API yet)"
    else:
        jq_line = "J-Quants disabled / not configured"

    rep_cfg = _jquants_report_settings()
    jq_watchlist_section = ""
    if rep_cfg.get("include_watchlist_bars_check", True):
        jq_watchlist_section = "\n\n" + render_jquants_watchlist_bars_check_section(rep_cfg)

    inc_cache, inc_mixed, inc_us = _daily_report_momentum_sections_flags()
    if us_momentum_section:
        inc_us = True
    momentum_sections: list[str] = []
    if inc_cache:
        momentum_sections.append(render_momentum_signals_cache_only_section())
    if inc_mixed:
        momentum_sections.append(render_momentum_signals_mixed_section())
    if inc_us:
        momentum_sections.append(render_us_momentum_cache_only_section())

    momentum_blob = "\n\n".join(momentum_sections)
    if jq_watchlist_section and momentum_blob:
        tail = jq_watchlist_section + "\n\n" + momentum_blob
    elif jq_watchlist_section:
        tail = jq_watchlist_section
    elif momentum_blob:
        tail = "\n\n" + momentum_blob
    else:
        tail = ""
    report_body = (
        "\n".join(
            [
                f"# Daily Report ({today})",
                "",
                "Observation only — no auto trading.",
                "",
                "## Japan Signals — Momentum Cache",
                f"- Watchlist count: {jp_n}",
                f"- {jq_line}",
            ]
        )
        + tail
    )
    if us_signals_dry_run_manifest:
        report_body = append_us_signals_dry_run_section(
            report_body,
            us_signals_dry_run_manifest,
            path_base=ROOT_DIR,
        )
        if write_observation_log:
            obs_result = log_us_signals_batch_observations(
                Path(us_signals_dry_run_manifest),
                path_base=ROOT_DIR,
                service=_obs_service(),
            )
            if observation_batch_failed(obs_result):
                typer.echo(json.dumps(obs_result, ensure_ascii=False, indent=2), err=True)
                raise typer.Exit(2)
            typer.echo(
                "observation_log: "
                f"logged={obs_result.get('logged')} "
                f"skipped={obs_result.get('skipped')} "
                f"manifest_status={obs_result.get('manifest_status')}"
            )
    elif write_observation_log:
        typer.echo(
            "daily: --write-observation-log requires --us-signals-dry-run-manifest",
            err=True,
        )
        raise typer.Exit(2)
    if us_cache_preview:
        report_body = append_us_cache_preview_section(report_body)
    if us_observation_summary:
        report_body = report_body.rstrip() + "\n\n" + render_us_observation_summary_markdown(path_base=ROOT_DIR)
    out.write_text(report_body, encoding="utf-8")
    typer.echo(f"daily report created: {out}")


@app.command("weekly-us-observation")
def weekly_us_observation_command(
    manifest_out: Optional[str] = typer.Option(
        None,
        "--manifest-out",
        help="Write batch manifest JSON (default: outputs/signals/weekly_us_manifest.json).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Quality + batch preview only; do not write manifest under outputs/.",
    ),
    write_observation_log: bool = typer.Option(
        False,
        "--write-observation-log",
        help="Append observation_log rows (requires --manifest-out).",
    ),
    with_daily_report: bool = typer.Option(
        False,
        "--with-daily-report",
        help="Also run daily with US opt-in sections (requires --manifest-out).",
    ),
    with_peer_sync: bool = typer.Option(
        False,
        "--with-peer-sync",
        help="Include cache-only peer_sync section from config/peer_map.yaml.",
    ),
    skip_duplicate_iso_week: bool = typer.Option(
        False,
        "--skip-duplicate-iso-week",
        help="When writing observation_log, skip symbols whose ISO week already exists (P3; opt-in).",
    ),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    """P4: US cache-only weekly cycle — manifest, quality, optional observation_log + daily."""

    fmt_norm = fmt.strip().lower()
    if fmt_norm not in {"markdown", "json"}:
        typer.echo("weekly-us-observation: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    if write_observation_log and dry_run:
        typer.echo("weekly-us-observation: --write-observation-log conflicts with --dry-run", err=True)
        raise typer.Exit(2)
    if skip_duplicate_iso_week and not write_observation_log:
        typer.echo(
            "weekly-us-observation: --skip-duplicate-iso-week requires --write-observation-log",
            err=True,
        )
        raise typer.Exit(2)
    if with_daily_report and dry_run:
        typer.echo("weekly-us-observation: --with-daily-report conflicts with --dry-run", err=True)
        raise typer.Exit(2)
    out_path: Path | None = None
    if not dry_run:
        out_path = Path(manifest_out) if manifest_out else OUTPUTS_DIR / "signals" / "weekly_us_manifest.json"
    try:
        result = run_weekly_us_observation_cycle(
            path_base=ROOT_DIR,
            manifest_out=out_path,
            write_observation_log=write_observation_log,
            observation_service=_obs_service() if write_observation_log else None,
            include_peer_sync=with_peer_sync,
            skip_duplicate_iso_week=skip_duplicate_iso_week,
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from exc

    if with_daily_report:
        if not manifest_out and not out_path.is_file():
            typer.echo("weekly-us-observation: --with-daily-report needs writable manifest", err=True)
            raise typer.Exit(2)
        from typer.testing import CliRunner

        runner = CliRunner()
        daily_result = runner.invoke(
            app,
            [
                "daily",
                "--us-signals-dry-run-manifest",
                str(out_path),
                "--us-cache-preview",
                "--us-momentum-section",
                *(["--write-observation-log"] if write_observation_log else []),
            ],
        )
        if daily_result.exit_code != 0:
            typer.echo(daily_result.stdout + daily_result.stderr, err=True)
            raise typer.Exit(daily_result.exit_code)

    payload = {
        "manifest_path": result.manifest_path_written,
        "manifest": result.manifest,
        "batch_previews": result.batch_previews,
        "quality": result.quality,
        "observation_log": result.observation_log,
        "peer_sync": result.peer_sync,
        "observation_write_stats": result.observation_write_stats,
        "peer_sync_write_stats": result.peer_sync_write_stats,
        "duplicate_week_preflight": result.duplicate_week_preflight,
        "p3_path_preflight": result.p3_path_preflight,
        "portfolio_exposure_line": result.portfolio_exposure_line,
        "observation_only": True,
        "live_http": False,
    }
    if fmt_norm == "json":
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(format_weekly_us_observation_markdown(result, path_base=ROOT_DIR))


@app.command("weekly-observation-report-v1")
def weekly_observation_report_v1_command(
    out: Optional[str] = typer.Option(
        None,
        "--out",
        help="Optional path to write markdown (e.g. reports/YYYY-MM-DD/sample_weekly_observation_report_v1.md).",
    ),
    report_date: Optional[str] = typer.Option(
        None,
        "--report-date",
        help="ISO date label for the report header (default: today).",
    ),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    """Weekly Observation Report v1 — single read-only page for human MERGE/STOP judgment."""

    from invis_alpha_os.product.weekly_observation_report_v1 import (
        build_weekly_observation_report_v1,
        format_weekly_observation_report_v1_json,
        format_weekly_observation_report_v1_markdown,
    )

    fmt_norm = fmt.strip().lower()
    if fmt_norm not in {"markdown", "json"}:
        typer.echo("weekly-observation-report-v1: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    report = build_weekly_observation_report_v1(path_base=ROOT_DIR, report_date=report_date)
    if fmt_norm == "json":
        body = format_weekly_observation_report_v1_json(report)
    else:
        body = format_weekly_observation_report_v1_markdown(report, path_base=ROOT_DIR)
    if out:
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(body if body.endswith("\n") else body + "\n", encoding="utf-8")
        typer.echo(f"weekly observation report v1 written: {out_path}")
    typer.echo(body)


@app.command("weekly-candidate-brief")
def weekly_candidate_brief_command(
    out: Optional[str] = typer.Option(
        None,
        "--out",
        help="Optional path to write markdown (e.g. reports/YYYY-MM-DD/weekly_candidate_brief_v0.md).",
    ),
    report_date: Optional[str] = typer.Option(
        None,
        "--report-date",
        help="ISO date label for the report header (default: today JST).",
    ),
    fmt: str = typer.Option(
        "markdown",
        "--format",
        help="Output format: markdown, json, or copy (copy-ready block only).",
    ),
    scan_limit: int = typer.Option(
        0,
        "--scan-limit",
        help="Max ranked rows per market from discovery (0 = all ranked).",
    ),
    jp_universe_file: Optional[str] = typer.Option(
        None,
        "--jp-universe-file",
        help="Optional JP universe YAML (default: local jquants cache symbols).",
    ),
    us_universe_file: Optional[str] = typer.Option(
        None,
        "--us-universe-file",
        help="Optional US universe YAML (default: config/us_watchlist.yaml).",
    ),
) -> None:
    """Weekly Candidate Brief v0.1 — cross-market discovery for human deep-dive candidates."""

    from invis_alpha_os.product.weekly_candidate_brief_v0 import (
        build_weekly_candidate_brief_v0,
        format_weekly_candidate_brief_v0_copy,
        format_weekly_candidate_brief_v0_json,
        format_weekly_candidate_brief_v0_markdown,
    )

    fmt_norm = fmt.strip().lower()
    if fmt_norm not in {"markdown", "json", "copy"}:
        typer.echo("weekly-candidate-brief: --format must be markdown, json, or copy", err=True)
        raise typer.Exit(2)
    jp_path = Path(jp_universe_file) if jp_universe_file else None
    us_path = Path(us_universe_file) if us_universe_file else None
    if jp_path is not None and not jp_path.is_file():
        typer.echo(f"weekly-candidate-brief: jp universe file not found: {jp_path}", err=True)
        raise typer.Exit(2)
    if us_path is not None and not us_path.is_file():
        typer.echo(f"weekly-candidate-brief: us universe file not found: {us_path}", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    try:
        brief = build_weekly_candidate_brief_v0(
            report_date=run_date,
            jp_universe_file=jp_path,
            us_universe_file=us_path,
            scan_limit=scan_limit,
            path_base=ROOT_DIR,
        )
    except ValueError as e:
        typer.echo(f"weekly-candidate-brief: {e}", err=True)
        raise typer.Exit(2) from e
    if fmt_norm == "json":
        body = format_weekly_candidate_brief_v0_json(brief)
    elif fmt_norm == "copy":
        body = format_weekly_candidate_brief_v0_copy(brief)
    else:
        body = format_weekly_candidate_brief_v0_markdown(brief)
    if out:
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(body if body.endswith("\n") else body + "\n", encoding="utf-8")
        status = f"weekly candidate brief written: {out_path}"
        if fmt_norm == "copy":
            typer.echo(status, err=True)
        else:
            typer.echo(status)
    typer.echo(body)


@app.command("weekly-candidate-brief-email")
def weekly_candidate_brief_email_command(
    report_date: Optional[str] = typer.Option(
        None,
        "--report-date",
        help="ISO date label (default: today JST).",
    ),
    report_dir: Optional[str] = typer.Option(
        None,
        "--report-dir",
        help="Report directory (default: reports/YYYY-MM-DD).",
    ),
    copy_file: Optional[str] = typer.Option(
        None,
        "--copy-file",
        help="Copy-only markdown path (default: report_dir/weekly_candidate_brief_copy.md).",
    ),
    full_md: Optional[str] = typer.Option(
        None,
        "--full-md",
        help="Optional full markdown path to attach (preview only).",
    ),
    send_test: bool = typer.Option(
        False,
        "--send-test",
        help="Send Gmail test email only when explicit env gates are satisfied.",
    ),
    gmail_to: Optional[str] = typer.Option(
        None,
        "--gmail-to",
        help="Optional test recipient override (default: GMAIL_TO env).",
    ),
) -> None:
    """Write Weekly Candidate Brief Gmail previews; optional gated test send."""

    run_date = report_date or today_jst_iso()
    resolution = resolve_weekly_report_dir(
        report_date=run_date,
        report_dir=report_dir,
        repo_root=ROOT_DIR,
    )
    base = resolution.path
    if resolution.warning:
        typer.echo(f"weekly-candidate-brief-email: {resolution.warning}", err=True)
    copy_path = Path(copy_file) if copy_file else base / "weekly_candidate_brief_copy.md"
    if not copy_path.is_file():
        typer.echo(f"weekly-candidate-brief-email: copy file not found: {copy_path}", err=True)
        raise typer.Exit(2)

    copy_body = copy_path.read_text(encoding="utf-8")
    draft = build_weekly_candidate_brief_email_draft(report_date=run_date, copy_body=copy_body)

    attachments: list[tuple[str, bytes, str]] | None = None
    full_path = Path(full_md) if full_md else base / "weekly_candidate_brief_v0_1.md"
    if full_path.is_file():
        attachments = [
            (full_path.name, full_path.read_bytes(), "text/markdown"),
        ]

    email_out = base / "email"
    recipient = (gmail_to or os.environ.get("GMAIL_TO", "")).strip()
    dry_run = not send_test
    sender = resolve_gmail_sender(dry_run=dry_run, recipient=recipient)
    to_list = [recipient] if recipient else ["dry-run@local"]
    if dry_run:
        to_list = [recipient or "dry-run@local"]
    message = build_mime_message(
        sender=sender or "dry-run@local",
        to=to_list,
        subject=draft.subject,
        text_body=draft.text_body,
        html_body=draft.html_body,
        attachments=attachments,
    )
    preview_paths = write_email_previews(email_out, message=message)
    raw = encode_message_raw(message)
    (email_out / "email_raw.b64url.txt").write_text(raw, encoding="utf-8")

    typer.echo(f"weekly-candidate-brief-email: subject={draft.subject!r}")
    for key, path in preview_paths.items():
        typer.echo(f"weekly-candidate-brief-email: {key}={path}")
    if full_path.is_file():
        typer.echo(f"weekly-candidate-brief-email: attachment_candidate={full_path}")
    if dry_run:
        typer.echo("weekly-candidate-brief-email: dry-run only (no Gmail API call)")
        raise typer.Exit(0)
    if os.environ.get("INVEST_ALPHA_OS_ALLOW_GMAIL_TEST_SEND", "").strip() != "1":
        typer.echo(
            "weekly-candidate-brief-email: test send blocked "
            "(set INVEST_ALPHA_OS_ALLOW_GMAIL_TEST_SEND=1)",
            err=True,
        )
        raise typer.Exit(2)
    if not recipient:
        typer.echo("weekly-candidate-brief-email: GMAIL_TO is required for --send-test", err=True)
        raise typer.Exit(2)
    if not sender:
        typer.echo(
            "weekly-candidate-brief-email: gmail_failure_reason=gmail_sender_unconfigured "
            "(set GMAIL_REPORT_FROM or GMAIL_SELF_EMAIL)",
            err=True,
        )
        raise typer.Exit(2)
    if "[TEST]" not in draft.subject:
        typer.echo("weekly-candidate-brief-email: subject must include [TEST]", err=True)
        raise typer.Exit(2)
    if not draft.text_body.startswith(("TEST EMAIL", "テストメール")):
        typer.echo("weekly-candidate-brief-email: body must start with TEST EMAIL", err=True)
        raise typer.Exit(2)
    try:
        validate_gmail_send_gates(recipient=recipient)
    except GmailSendBlockedError as e:
        reason = classify_gmail_failure(e)
        typer.echo(f"weekly-candidate-brief-email: gmail_failure_reason={reason}", err=True)
        raise typer.Exit(2) from e
    if not credentials_configured():
        typer.echo("weekly-candidate-brief-email: gmail_failure_reason=gmail_oauth_required", err=True)
        raise typer.Exit(2)
    try:
        result = send_gmail_message(raw, allow_interactive_oauth=False)
    except (GmailSendBlockedError, GmailDeliveryError) as e:
        reason = classify_gmail_failure(e)
        typer.echo(f"weekly-candidate-brief-email: gmail_failure_reason={reason}", err=True)
        raise typer.Exit(2) from e
    except Exception as e:
        reason = classify_gmail_failure(e)
        typer.echo(f"weekly-candidate-brief-email: gmail_failure_reason={reason}", err=True)
        raise typer.Exit(2) from e
    msg_id = result.get("id", "") if isinstance(result, dict) else ""
    masked_to = recipient.split("@")[0][:2] + "***@" + recipient.split("@", 1)[1] if "@" in recipient else "***"
    typer.echo(f"weekly-candidate-brief-email: sent test message id={msg_id!r} to={masked_to}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-schedule-diagnostic")
def weekly_candidate_brief_schedule_diagnostic_command(
    observed_missing_date: str = typer.Option("2026-05-30", "--observed-missing-date"),
    timezone_name: str = typer.Option("Asia/Tokyo", "--timezone"),
    expected_weekday: str = typer.Option("Saturday", "--expected-weekday"),
    expected_hour_jst: int = typer.Option(7, "--expected-hour-jst"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-schedule-diagnostic: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    try:
        payload = build_weekly_report_schedule_diagnostic(
            observed_missing_date=observed_missing_date,
            timezone_name=timezone_name,
            expected_weekday=expected_weekday,
            expected_hour_jst=expected_hour_jst,
            repo_root=ROOT_DIR,
        )
    except ValueError as e:
        typer.echo(f"weekly-candidate-brief-schedule-diagnostic: {e}", err=True)
        raise typer.Exit(2) from e
    markdown_text = format_weekly_report_schedule_diagnostic_markdown(payload)
    run_date = observed_missing_date
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    paths = write_weekly_report_schedule_diagnostic_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=payload,
    )
    if fmt == "json":
        typer.echo(format_weekly_report_schedule_diagnostic_json(payload))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-schedule-diagnostic: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-schedule-diagnostic: "
        "source_only=true workflow_files_modified=false provider_live_access_executed=false live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false env_secret_displayed=false trading_action_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-scheduled-report-observability")
def weekly_candidate_brief_scheduled_report_observability_command(
    report_kind: str = typer.Option("weekly", "--report-kind"),
    as_of_date: str = typer.Option("2026-05-31", "--as-of-date"),
    timezone_name: str = typer.Option("Asia/Tokyo", "--timezone"),
    expected_weekday: str = typer.Option("Saturday", "--expected-weekday"),
    expected_hour_jst: int = typer.Option(7, "--expected-hour-jst"),
    lookback_days: int = typer.Option(10, "--lookback-days"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-scheduled-report-observability: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    try:
        payload = build_scheduled_report_observability(
            report_kind=report_kind,
            as_of_date=as_of_date,
            timezone_name=timezone_name,
            expected_weekday=expected_weekday,
            expected_hour_jst=expected_hour_jst,
            lookback_days=lookback_days,
            repo_root=ROOT_DIR,
        )
    except ValueError as e:
        typer.echo(f"weekly-candidate-brief-scheduled-report-observability: {e}", err=True)
        raise typer.Exit(2) from e
    markdown_text = format_scheduled_report_observability_markdown(payload)
    report_date = payload["last_expected_occurrence"]["expected_date"]
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    paths = write_scheduled_report_observability_outputs(
        out_dir=out_root,
        report_date=report_date,
        markdown_text=markdown_text,
        json_payload=payload,
    )
    if fmt == "json":
        typer.echo(format_scheduled_report_observability_json(payload))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-scheduled-report-observability: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-scheduled-report-observability: "
        "source_only=true sentinel_only=true workflow_files_modified=false gmail_send_executed=false provider_live_access_executed=false live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false raw_ohlcv_persistence_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-recovery-runbook")
def weekly_candidate_brief_recovery_runbook_command(
    missed_report_date: str = typer.Option("2026-05-30", "--missed-report-date"),
    timezone_name: str = typer.Option("Asia/Tokyo", "--timezone"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-recovery-runbook: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    payload = build_weekly_report_recovery_runbook(
        missed_report_date=missed_report_date,
        timezone_name=timezone_name,
    )
    markdown_text = format_weekly_report_recovery_runbook_markdown(payload)
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    paths = write_weekly_report_recovery_runbook_outputs(
        out_dir=out_root,
        report_date=missed_report_date,
        markdown_text=markdown_text,
        json_payload=payload,
    )
    if fmt == "json":
        typer.echo(format_weekly_report_recovery_runbook_json(payload))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-recovery-runbook: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-recovery-runbook: "
        "source_only=true recovery_runbook_only=true backfill_executed=false workflow_files_modified=false gmail_send_executed=false provider_live_access_executed=false live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false raw_ohlcv_persistence_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-workflow-approval-package")
def weekly_candidate_brief_workflow_approval_package_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    target_timezone: str = typer.Option("Asia/Tokyo", "--target-timezone"),
    target_weekday: str = typer.Option("Saturday", "--target-weekday"),
    target_local_hour: int = typer.Option(7, "--target-local-hour"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-workflow-approval-package: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    try:
        payload = build_weekly_report_workflow_approval_package(
            report_date=run_date,
            target_timezone=target_timezone,
            target_weekday=target_weekday,
            target_local_hour=target_local_hour,
            repo_root=ROOT_DIR,
        )
    except ValueError as e:
        typer.echo(f"weekly-candidate-brief-workflow-approval-package: {e}", err=True)
        raise typer.Exit(2) from e
    markdown_text = format_weekly_report_workflow_approval_package_markdown(payload)
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    paths = write_weekly_report_workflow_approval_package_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=payload,
    )
    if fmt == "json":
        typer.echo(format_weekly_report_workflow_approval_package_json(payload))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-workflow-approval-package: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-workflow-approval-package: "
        "source_only=true workflow_patch_package_only=true workflow_files_modified=false provider_live_access_executed=false live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false raw_ohlcv_persistence_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-local-dryrun-backfill-contract")
def weekly_candidate_brief_local_dryrun_backfill_contract_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    missed_report_date: str = typer.Option("2026-05-30", "--missed-report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-local-dryrun-backfill-contract: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    payload = build_weekly_report_local_dryrun_backfill_contract(
        report_date=run_date,
        missed_report_date=missed_report_date,
    )
    markdown_text = format_weekly_report_local_dryrun_backfill_contract_markdown(payload)
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    paths = write_weekly_report_local_dryrun_backfill_contract_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=payload,
    )
    if fmt == "json":
        typer.echo(format_weekly_report_local_dryrun_backfill_contract_json(payload))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-local-dryrun-backfill-contract: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-local-dryrun-backfill-contract: "
        "source_only=true local_dryrun_contract_only=true local_dryrun_executed=false "
        "manual_backfill_executed=false provider_live_access_executed=false live_http_executed=false "
        "cache_write_executed=false actual_refresh_import_executed=false raw_ohlcv_persistence_executed=false "
        "workflow_files_modified=false gmail_send_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-long-run-operator-preflight")
def weekly_candidate_brief_long_run_operator_preflight_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-long-run-operator-preflight: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    payload = build_long_run_operator_preflight_pack(report_date=run_date)
    markdown_text = format_long_run_operator_preflight_pack_markdown(payload)
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    paths = write_long_run_operator_preflight_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=payload,
    )
    if fmt == "json":
        typer.echo(format_long_run_operator_preflight_pack_json(payload))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-long-run-operator-preflight: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-long-run-operator-preflight: "
        "source_only=true sleep_guard_pack_only=true macos_system_settings_changed=false "
        "provider_live_access_executed=false live_http_executed=false cache_write_executed=false "
        "actual_refresh_import_executed=false raw_ohlcv_persistence_executed=false "
        "workflow_files_modified=false dependency_pyproject_changed=false trading_action_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-scheduled-report-assurance-snapshot")
def weekly_candidate_brief_scheduled_report_assurance_snapshot_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    missed_report_date: str = typer.Option("2026-05-30", "--missed-report-date"),
    target_local_hour: int = typer.Option(7, "--target-local-hour"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-scheduled-report-assurance-snapshot: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    payload = build_scheduled_report_assurance_snapshot(
        report_date=run_date,
        missed_report_date=missed_report_date,
        target_local_hour=target_local_hour,
    )
    markdown_text = format_scheduled_report_assurance_snapshot_markdown(payload)
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    paths = write_scheduled_report_assurance_snapshot_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=payload,
    )
    if fmt == "json":
        typer.echo(format_scheduled_report_assurance_snapshot_json(payload))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-scheduled-report-assurance-snapshot: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-scheduled-report-assurance-snapshot: "
        "source_only=true assurance_snapshot_only=true provider_live_access_executed=false "
        "live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false "
        "raw_ohlcv_persistence_executed=false workflow_files_modified=false gmail_send_executed=false "
        "dependency_pyproject_changed=false trading_action_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-workflow-patch-review-gate")
def weekly_candidate_brief_workflow_patch_review_gate_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    target_timezone: str = typer.Option("Asia/Tokyo", "--target-timezone"),
    target_weekday: str = typer.Option("Saturday", "--target-weekday"),
    target_local_hour: int = typer.Option(7, "--target-local-hour"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-workflow-patch-review-gate: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    payload = build_weekly_report_workflow_patch_review_gate(
        report_date=run_date,
        target_timezone=target_timezone,
        target_weekday=target_weekday,
        target_local_hour=target_local_hour,
        repo_root=ROOT_DIR,
    )
    markdown_text = format_weekly_report_workflow_patch_review_gate_markdown(payload)
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    paths = write_weekly_report_workflow_patch_review_gate_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=payload,
    )
    if fmt == "json":
        typer.echo(format_weekly_report_workflow_patch_review_gate_json(payload))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-workflow-patch-review-gate: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-workflow-patch-review-gate: "
        "source_only=true workflow_patch_review_only=true workflow_files_modified=false "
        "provider_live_access_executed=false live_http_executed=false cache_write_executed=false "
        "actual_refresh_import_executed=false raw_ohlcv_persistence_executed=false "
        "dependency_pyproject_changed=false trading_action_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-manual-backfill-command-pack")
def weekly_candidate_brief_manual_backfill_command_pack_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    missed_report_date: str = typer.Option("2026-05-30", "--missed-report-date"),
    target_timezone: str = typer.Option("Asia/Tokyo", "--target-timezone"),
    backfill_out_dir: str = typer.Option("reports", "--backfill-out-dir"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-manual-backfill-command-pack: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    payload = build_weekly_report_manual_backfill_command_pack(
        report_date=run_date,
        missed_report_date=missed_report_date,
        timezone_name=target_timezone,
        out_dir=backfill_out_dir,
    )
    markdown_text = format_weekly_report_manual_backfill_command_pack_markdown(payload)
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    paths = write_weekly_report_manual_backfill_command_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=payload,
    )
    if fmt == "json":
        typer.echo(format_weekly_report_manual_backfill_command_pack_json(payload))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-manual-backfill-command-pack: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-manual-backfill-command-pack: "
        "source_only=true manual_backfill_command_pack_only=true manual_backfill_executed=false "
        "provider_live_access_executed=false live_http_executed=false cache_write_executed=false "
        "actual_refresh_import_executed=false raw_ohlcv_persistence_executed=false workflow_files_modified=false "
        "gmail_send_executed=false trading_action_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-scheduled-report-failure-triage")
def weekly_candidate_brief_scheduled_report_failure_triage_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    expected_cron_utc: str = typer.Option("0 22 * * 5", "--expected-cron-utc"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-scheduled-report-failure-triage: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    payload = build_scheduled_report_failure_triage_matrix(report_date=run_date, expected_cron_utc=expected_cron_utc)
    markdown_text = format_scheduled_report_failure_triage_matrix_markdown(payload)
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    paths = write_scheduled_report_failure_triage_matrix_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=payload,
    )
    if fmt == "json":
        typer.echo(format_scheduled_report_failure_triage_matrix_json(payload))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-scheduled-report-failure-triage: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-scheduled-report-failure-triage: "
        "source_only=true triage_matrix_only=true provider_live_access_executed=false live_http_executed=false "
        "cache_write_executed=false actual_refresh_import_executed=false raw_ohlcv_persistence_executed=false "
        "env_secret_displayed=false workflow_files_modified=false trading_action_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-long-run-progress-snapshot")
def weekly_candidate_brief_long_run_progress_snapshot_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-long-run-progress-snapshot: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    payload = build_long_run_development_progress_snapshot(report_date=run_date)
    markdown_text = format_long_run_development_progress_snapshot_markdown(payload)
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    paths = write_long_run_development_progress_snapshot_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=payload,
    )
    if fmt == "json":
        typer.echo(format_long_run_development_progress_snapshot_json(payload))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-long-run-progress-snapshot: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-long-run-progress-snapshot: "
        "source_only=true progress_snapshot_only=true single_overall_percent_allowed=false "
        "provider_live_access_executed=false live_http_executed=false cache_write_executed=false "
        "actual_refresh_import_executed=false raw_ohlcv_persistence_executed=false "
        "workflow_files_modified=false trading_action_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-workflow-observation-plan")
def weekly_candidate_brief_workflow_observation_plan_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    target_local_hour: int = typer.Option(7, "--target-local-hour"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-workflow-observation-plan: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    payload = build_weekly_workflow_post_merge_observation_plan(
        report_date=run_date,
        target_local_hour=target_local_hour,
        repo_root=ROOT_DIR,
    )
    markdown_text = format_weekly_workflow_post_merge_observation_plan_markdown(payload)
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    paths = write_weekly_workflow_post_merge_observation_plan_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=payload,
    )
    if fmt == "json":
        typer.echo(format_weekly_workflow_post_merge_observation_plan_json(payload))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-workflow-observation-plan: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-workflow-observation-plan: "
        "source_only=true post_merge_observation_plan_only=true manual_workflow_dispatch_executed=false "
        "provider_live_access_executed=false live_http_executed=false cache_write_executed=false "
        "actual_refresh_import_executed=false raw_ohlcv_persistence_executed=false "
        "env_secret_displayed=false workflow_files_modified=false trading_action_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("position-aware-dca-decision-pack")
def position_aware_dca_decision_pack_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    symbols: str = typer.Option(DEFAULT_POSITION_GUARD_SYMBOLS, "--symbols"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("position-aware-dca-decision-pack: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    payload = build_position_aware_dca_decision_pack(report_date=run_date, symbols_csv=symbols)
    markdown_text = format_position_aware_dca_decision_pack_markdown(payload)
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "reports" / "position_aware_dca"
    paths = write_position_aware_dca_decision_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=payload,
    )
    if fmt == "json":
        typer.echo(format_position_aware_dca_decision_pack_json(payload))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"position-aware-dca-decision-pack: {key}={p}", err=True)
    typer.echo(
        "position-aware-dca-decision-pack: "
        "source_only=true redacted_summary_only=true broker_api_access_executed=false "
        "raw_broker_export_parsed=false provider_live_access_executed=false live_http_executed=false "
        "cache_write_executed=false actual_refresh_import_executed=false raw_ohlcv_persistence_executed=false "
        "env_secret_displayed=false workflow_files_modified=false trading_action_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("position-snapshot-template")
def position_snapshot_template_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    symbols: str = typer.Option(DEFAULT_POSITION_GUARD_SYMBOLS, "--symbols"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("position-snapshot-template: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    payload = build_redacted_position_snapshot_template(report_date=run_date, symbols_csv=symbols)
    markdown_text = format_redacted_position_snapshot_template_markdown(payload)
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "reports" / "position_aware_dca"
    paths = write_redacted_position_outputs(
        out_dir=out_root,
        report_date=run_date,
        stem="redacted_position_snapshot_template",
        markdown_text=markdown_text,
        json_payload=payload,
    )
    typer.echo(format_redacted_position_json(payload) if fmt == "json" else markdown_text)
    for key, p in paths.items():
        typer.echo(f"position-snapshot-template: {key}={p}", err=True)
    typer.echo(
        "position-snapshot-template: "
        "source_only=true template_only=true broker_api_access_executed=false raw_broker_export_parsed=false "
        "provider_live_access_executed=false live_http_executed=false cache_write_executed=false "
        "actual_refresh_import_executed=false env_secret_displayed=false trading_action_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("position-snapshot-validate")
def position_snapshot_validate_command(
    snapshot_path: Optional[str] = typer.Option(None, "--snapshot-path"),
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    symbols: str = typer.Option(DEFAULT_POSITION_GUARD_SYMBOLS, "--symbols"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("position-snapshot-validate: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    if snapshot_path:
        snapshot = load_redacted_position_snapshot_json(Path(snapshot_path))
    else:
        snapshot = build_redacted_position_snapshot_template(report_date=run_date, symbols_csv=symbols)[
            "redacted_snapshot_template"
        ]
    payload = validate_redacted_position_snapshot(snapshot)
    markdown_text = format_redacted_position_snapshot_validation_markdown(payload)
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "reports" / "position_aware_dca"
    paths = write_redacted_position_outputs(
        out_dir=out_root,
        report_date=run_date,
        stem="redacted_position_snapshot_validation",
        markdown_text=markdown_text,
        json_payload=payload,
    )
    typer.echo(format_redacted_position_json(payload) if fmt == "json" else markdown_text)
    for key, p in paths.items():
        typer.echo(f"position-snapshot-validate: {key}={p}", err=True)
    typer.echo(
        "position-snapshot-validate: "
        "source_only=true redacted_json_only=true broker_api_access_executed=false raw_broker_export_parsed=false "
        "provider_live_access_executed=false live_http_executed=false cache_write_executed=false "
        "actual_refresh_import_executed=false env_secret_displayed=false trading_action_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("position-aware-dca-strategy-pack")
def position_aware_dca_strategy_pack_command(
    snapshot_path: Optional[str] = typer.Option(None, "--snapshot-path"),
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    symbols: str = typer.Option(DEFAULT_POSITION_GUARD_SYMBOLS, "--symbols"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("position-aware-dca-strategy-pack: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    snapshot = load_redacted_position_snapshot_json(Path(snapshot_path)) if snapshot_path else None
    payload = build_redacted_position_strategy_pack(
        report_date=run_date,
        redacted_snapshot=snapshot,
        symbols_csv=symbols,
    )
    markdown_text = format_redacted_position_strategy_pack_markdown(payload)
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "reports" / "position_aware_dca"
    paths = write_redacted_position_outputs(
        out_dir=out_root,
        report_date=run_date,
        stem="redacted_position_strategy_pack",
        markdown_text=markdown_text,
        json_payload=payload,
    )
    typer.echo(format_redacted_position_json(payload) if fmt == "json" else markdown_text)
    for key, p in paths.items():
        typer.echo(f"position-aware-dca-strategy-pack: {key}={p}", err=True)
    typer.echo(
        "position-aware-dca-strategy-pack: "
        "source_only=true strategy_pack_only=true broker_api_access_executed=false raw_broker_export_parsed=false "
        "provider_live_access_executed=false live_http_executed=false cache_write_executed=false "
        "actual_refresh_import_executed=false env_secret_displayed=false trading_action_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("position-snapshot-human-input-checklist")
def position_snapshot_human_input_checklist_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    symbols: str = typer.Option(DEFAULT_POSITION_GUARD_SYMBOLS, "--symbols"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("position-snapshot-human-input-checklist: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    payload = build_redacted_position_human_input_checklist(report_date=run_date, symbols_csv=symbols)
    markdown_text = format_redacted_position_human_input_checklist_markdown(payload)
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "reports" / "position_aware_dca"
    paths = write_redacted_position_outputs(
        out_dir=out_root,
        report_date=run_date,
        stem="redacted_position_human_input_checklist",
        markdown_text=markdown_text,
        json_payload=payload,
    )
    typer.echo(format_redacted_position_json(payload) if fmt == "json" else markdown_text)
    for key, p in paths.items():
        typer.echo(f"position-snapshot-human-input-checklist: {key}={p}", err=True)
    typer.echo(
        "position-snapshot-human-input-checklist: "
        "source_only=true checklist_only=true broker_api_access_executed=false raw_broker_export_parsed=false "
        "provider_live_access_executed=false live_http_executed=false cache_write_executed=false "
        "actual_refresh_import_executed=false env_secret_displayed=false trading_action_executed=false",
        err=True,
    )
    raise typer.Exit(0)


def _emit_return_to_main_pack(
    *,
    command_name: str,
    payload: dict[str, Any],
    out_dir: Path,
    report_date: str,
    stem: str,
    fmt: str,
    stderr_suffix: str,
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo(f"{command_name}: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    markdown_text = format_return_to_main_pack_markdown(payload)
    paths = write_return_to_main_pack_outputs(
        out_dir=out_dir,
        report_date=report_date,
        stem=stem,
        markdown_text=markdown_text,
        json_payload=payload,
    )
    typer.echo(format_return_to_main_pack_json(payload) if fmt == "json" else markdown_text)
    for key, p in paths.items():
        typer.echo(f"{command_name}: {key}={p}", err=True)
    typer.echo(f"{command_name}: {stderr_suffix}", err=True)
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-scheduled-run-observation-pack")
def weekly_candidate_brief_scheduled_run_observation_pack_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    run_date = report_date or today_jst_iso()
    payload = build_weekly_scheduled_run_observation_pack(report_date=run_date)
    _emit_return_to_main_pack(
        command_name="weekly-candidate-brief-scheduled-run-observation-pack",
        payload=payload,
        out_dir=Path(out_dir) if out_dir else OUTPUTS_DIR / "reports" / "weekly_candidate_brief",
        report_date=run_date,
        stem="weekly_scheduled_run_observation_pack",
        fmt=fmt,
        stderr_suffix=(
            "source_only=true scheduled_run_observation_only=true manual_workflow_dispatch_executed=false "
            "workflow_files_modified=false provider_live_access_executed=false live_http_executed=false "
            "cache_write_executed=false actual_refresh_import_executed=false trading_action_executed=false"
        ),
    )


@app.command("cache-write-pilot-preexecution-readiness-snapshot")
def cache_write_pilot_preexecution_readiness_snapshot_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    candidate_cache_path: str = typer.Option(DEFAULT_CANDIDATE_CACHE_PATH, "--candidate-cache-path"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    run_date = report_date or today_jst_iso()
    payload = build_cache_write_pilot_preexecution_readiness_snapshot(
        report_date=run_date,
        candidate_cache_path=candidate_cache_path,
    )
    _emit_return_to_main_pack(
        command_name="cache-write-pilot-preexecution-readiness-snapshot",
        payload=payload,
        out_dir=Path(out_dir) if out_dir else OUTPUTS_DIR / "reports" / "cache_write_readiness",
        report_date=run_date,
        stem="cache_write_pilot_preexecution_readiness_snapshot",
        fmt=fmt,
        stderr_suffix=(
            "source_only=true preexecution_snapshot_only=true cache_directory_created=false "
            "provider_live_access_executed=false live_http_executed=false cache_write_executed=false "
            "actual_refresh_import_executed=false raw_ohlcv_api_persistence_executed=false "
            "env_secret_displayed=false trading_action_executed=false"
        ),
    )


@app.command("actual-import-quarantine-followthrough-matrix")
def actual_import_quarantine_followthrough_matrix_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    candidate_cache_path: str = typer.Option(DEFAULT_CANDIDATE_CACHE_PATH, "--candidate-cache-path"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    run_date = report_date or today_jst_iso()
    payload = build_actual_import_quarantine_followthrough_matrix(
        report_date=run_date,
        candidate_cache_path=candidate_cache_path,
    )
    _emit_return_to_main_pack(
        command_name="actual-import-quarantine-followthrough-matrix",
        payload=payload,
        out_dir=Path(out_dir) if out_dir else OUTPUTS_DIR / "reports" / "actual_import_readiness",
        report_date=run_date,
        stem="actual_import_quarantine_followthrough_matrix",
        fmt=fmt,
        stderr_suffix=(
            "source_only=true quarantine_matrix_only=true cache_write_executed=false "
            "actual_refresh_import_executed=false manual_actual_import_executed=false "
            "raw_broker_export_parsed=false provider_live_access_executed=false live_http_executed=false "
            "trading_action_executed=false"
        ),
    )


@app.command("portfolio-strategy-observation-report")
def portfolio_strategy_observation_report_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    symbols: str = typer.Option(DEFAULT_POSITION_GUARD_SYMBOLS, "--symbols"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    run_date = report_date or today_jst_iso()
    payload = build_portfolio_strategy_observation_report(report_date=run_date, symbols_csv=symbols)
    _emit_return_to_main_pack(
        command_name="portfolio-strategy-observation-report",
        payload=payload,
        out_dir=Path(out_dir) if out_dir else OUTPUTS_DIR / "reports" / "portfolio_strategy",
        report_date=run_date,
        stem="portfolio_strategy_observation_report",
        fmt=fmt,
        stderr_suffix=(
            "source_only=true portfolio_observation_only=true broker_api_access_executed=false "
            "raw_broker_export_parsed=false provider_live_access_executed=false live_http_executed=false "
            "cache_write_executed=false actual_refresh_import_executed=false trading_action_executed=false"
        ),
    )


@app.command("raw-input-quarantine-review")
def raw_input_quarantine_review_command(
    source_kind: str = typer.Option("fixture", "--source-kind"),
    declared_unit: str = typer.Option("man_yen", "--declared-unit"),
    declared_currency: str = typer.Option("JPY", "--declared-currency"),
    statement_month: str = typer.Option("2026-05", "--statement-month"),
    owner_scope: str = typer.Option("household", "--owner-scope"),
    redaction_status: str = typer.Option("redacted", "--redaction-status"),
    validation_key: list[str] | None = typer.Option(None, "--validation-key"),
    actual_import_requested: bool = typer.Option(False, "--actual-import-requested"),
    cache_write_requested: bool = typer.Option(False, "--cache-write-requested"),
    format: str = typer.Option("markdown", "--format"),
) -> None:
    """Review a declaration-only quarantine manifest; never read raw input."""

    try:
        source = QuarantineSourceKind(source_kind)
    except ValueError:
        typer.echo(f"raw-input-quarantine-review: unsupported source kind: {source_kind}", err=True)
        raise typer.Exit(code=2) from None
    if format not in {"markdown", "json"}:
        typer.echo("raw-input-quarantine-review: --format must be markdown or json", err=True)
        raise typer.Exit(code=2)
    manifest = RawInputQuarantineManifestV110(
        source_kind=source,
        declared_unit=declared_unit,
        declared_currency=declared_currency,
        statement_month=statement_month,
        owner_scope=owner_scope,
        redaction_status=redaction_status,
        actual_import_requested=actual_import_requested,
        cache_write_requested=cache_write_requested,
        validation_keys=tuple(validation_key or ()),
    )
    review = review_raw_input_quarantine_manifest_v110(manifest)
    if format == "json":
        typer.echo(format_raw_input_quarantine_review_json_v110(manifest, review))
    else:
        typer.echo(render_raw_input_quarantine_review_markdown_v110(manifest, review))


@app.command("sample-output-pack")
def sample_output_pack_command(
    format: str = typer.Option("markdown", "--format"),
) -> None:
    """Emit fixture-only quality/quarantine samples to stdout (no cache write or file I/O)."""

    if format != "markdown":
        typer.echo("sample-output-pack: only markdown is supported", err=True)
        raise typer.Exit(code=2)
    typer.echo(render_sample_output_pack_markdown_v112())


@app.command("sample-output-regeneration-contract")
def sample_output_regeneration_contract_command(
    format: str = typer.Option("markdown", "--format"),
) -> None:
    """Emit the source-only sample output regeneration command contract."""

    if format not in {"markdown", "json"}:
        typer.echo("sample-output-regeneration-contract: --format must be markdown or json", err=True)
        raise typer.Exit(code=2)
    contract = build_sample_output_regeneration_contract()
    if format == "json":
        typer.echo(format_sample_output_regeneration_contract_json(contract))
    else:
        typer.echo(render_sample_output_regeneration_contract_markdown(contract))


@app.command("monthly-review-pack-integration")
def monthly_review_pack_integration_command(
    format: str = typer.Option("markdown", "--format"),
) -> None:
    """Check monthly review pack integration using fixture-only contracts."""

    if format not in {"markdown", "json"}:
        typer.echo("monthly-review-pack-integration: --format must be markdown or json", err=True)
        raise typer.Exit(code=2)
    result = build_monthly_review_pack_integration_result()
    if format == "json":
        typer.echo(format_monthly_review_pack_integration_json(result))
    else:
        typer.echo(render_monthly_review_pack_integration_markdown(result))
    if not result.ready:
        raise typer.Exit(code=1)


@app.command("report-ux-language-contract")
def report_ux_language_contract_command(
    format: str = typer.Option("markdown", "--format"),
) -> None:
    """Emit the user-facing report UX language contract."""

    if format not in {"markdown", "json"}:
        typer.echo("report-ux-language-contract: --format must be markdown or json", err=True)
        raise typer.Exit(code=2)
    contract = build_report_ux_language_contract()
    if format == "json":
        typer.echo(format_report_ux_language_contract_json(contract))
    else:
        typer.echo(render_report_ux_language_contract_markdown(contract))


@app.command("operator-dashboard-summary")
def operator_dashboard_summary_command(
    format: str = typer.Option("markdown", "--format"),
) -> None:
    """Emit source-only operator dashboard summary to stdout."""

    if format not in {"markdown", "json"}:
        typer.echo("operator-dashboard-summary: --format must be markdown or json", err=True)
        raise typer.Exit(code=2)
    summary = build_operator_dashboard_summary()
    if format == "json":
        typer.echo(format_operator_dashboard_summary_json(summary))
    else:
        typer.echo(render_operator_dashboard_summary_markdown(summary))


@app.command("v1-readiness-check")
def v1_readiness_check_command(
    repo_root: str = typer.Option(str(ROOT_DIR), "--repo-root"),
    target_use_date: str = typer.Option("2026-06-07", "--target-use-date"),
    format: str = typer.Option("markdown", "--format"),
) -> None:
    """Emit v1.0 operational readiness dashboard for Candidate Discovery OS daily use."""

    if format not in {"markdown", "json"}:
        typer.echo("v1-readiness-check: --format must be markdown or json", err=True)
        raise typer.Exit(code=2)
    result = build_v1_operational_readiness(
        repo_root=Path(repo_root),
        target_use_date=target_use_date,
    )
    if format == "json":
        typer.echo(format_v1_operational_readiness_json(result))
    else:
        typer.echo(render_v1_operational_readiness_markdown(result))
    if not result.v1_usable_tomorrow:
        raise typer.Exit(code=1)


@app.command("progress-dashboard-check")
def progress_dashboard_check_command(
    path: str = typer.Option(str(ROOT_DIR / "docs" / "progress_dashboard.md"), "--path"),
    format: str = typer.Option("markdown", "--format"),
) -> None:
    """Validate progress dashboard table/checklist consistency without side effects."""

    if format not in {"markdown", "json"}:
        typer.echo("progress-dashboard-check: --format must be markdown or json", err=True)
        raise typer.Exit(code=2)
    result = check_progress_dashboard_consistency(Path(path))
    if format == "json":
        typer.echo(format_progress_dashboard_consistency_json(result))
    else:
        typer.echo(render_progress_dashboard_consistency_markdown(result))
    if not result.ok:
        raise typer.Exit(code=1)


@app.command("state-consistency-check")
def state_consistency_check_command(
    path: str = typer.Option(str(ROOT_DIR / "STATE.md"), "--path"),
    expected_main: Optional[str] = typer.Option(None, "--expected-main"),
    strict_latest_main: bool = typer.Option(False, "--strict-latest-main/--warn-latest-main"),
    format: str = typer.Option("markdown", "--format"),
) -> None:
    """Validate STATE.md safety and snapshot markers without modifying STATE.md."""

    if format not in {"markdown", "json"}:
        typer.echo("state-consistency-check: --format must be markdown or json", err=True)
        raise typer.Exit(code=2)
    result = check_state_consistency(
        Path(path),
        expected_main=expected_main,
        strict_latest_main=strict_latest_main,
    )
    if format == "json":
        typer.echo(format_state_consistency_json(result))
    else:
        typer.echo(render_state_consistency_markdown(result))
    if not result.ok:
        raise typer.Exit(code=1)


@app.command("weekly-report-user-summary")
def weekly_report_user_summary_command(
    source: str = typer.Option("sample", "--source", help="sample or composed"),
    report_date: str = typer.Option("2026-06-06", "--report-date"),
    format: str = typer.Option("markdown", "--format"),
) -> None:
    """Emit a user-facing weekly one-page summary from fixture/sample only."""

    if format not in {"markdown", "json"}:
        typer.echo("weekly-report-user-summary: --format must be markdown or json", err=True)
        raise typer.Exit(code=2)
    if source not in {"sample", "composed"}:
        typer.echo("weekly-report-user-summary: --source must be sample or composed", err=True)
        raise typer.Exit(code=2)
    try:
        summary = build_weekly_report_user_summary(source=source, report_date=report_date)
    except ValueError as exc:
        typer.echo(f"weekly-report-user-summary: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    if format == "json":
        typer.echo(format_weekly_report_user_summary_json(summary))
    else:
        typer.echo(render_weekly_report_user_summary_markdown(summary))


@app.command("weekly-artifact-local-verify")
def weekly_artifact_local_verify_command(
    report_date: str = typer.Option(..., "--report-date"),
    report_dir: Optional[str] = typer.Option(None, "--report-dir"),
    status_file: Optional[str] = typer.Option(None, "--status-file"),
    require_json_report: bool = typer.Option(True, "--require-json-report/--json-report-optional"),
    format: str = typer.Option("markdown", "--format"),
) -> None:
    """Verify weekly brief artifacts locally; never dispatch workflows or fetch live data."""

    if format not in {"markdown", "json"}:
        typer.echo("weekly-artifact-local-verify: --format must be markdown or json", err=True)
        raise typer.Exit(code=2)
    resolved_report_dir = Path(report_dir) if report_dir else ROOT_DIR / "reports" / report_date
    resolved_status_file = (
        Path(status_file)
        if status_file
        else ROOT_DIR / "outputs" / "operator" / "weekly_candidate_brief" / report_date / "status.json"
    )
    result = verify_weekly_candidate_brief_local_artifacts(
        report_date=report_date,
        report_dir=resolved_report_dir,
        status_file=resolved_status_file,
        require_json_report=require_json_report,
    )
    if format == "json":
        typer.echo(format_weekly_artifact_local_verification_json(result))
    else:
        typer.echo(render_weekly_artifact_local_verification_markdown(result))
    if not result.ready:
        raise typer.Exit(code=1)


@app.command("portfolio-data-quality-review")
def portfolio_data_quality_review_command(
    format: str = typer.Option("markdown", "--format"),
) -> None:
    """Fixture-only portfolio data quality review to stdout (no raw paths or I/O)."""

    if format not in {"markdown", "json"}:
        typer.echo("portfolio-data-quality-review: --format must be markdown or json", err=True)
        raise typer.Exit(code=2)
    review = build_portfolio_data_quality_review_v109()
    if format == "json":
        typer.echo(format_portfolio_data_quality_review_json_v109(review))
    else:
        typer.echo(render_portfolio_data_quality_review_markdown_v109(review))


@app.command("portfolio-quarantine-cross-review")
def portfolio_quarantine_cross_review_command(
    scenario: str = typer.Option("safe_fixture", "--scenario"),
    format: str = typer.Option("markdown", "--format"),
) -> None:
    """Cross-review safe declaration fixtures without raw input access."""

    if scenario == "safe_fixture":
        manifest = RawInputQuarantineManifestV110(
            source_kind=QuarantineSourceKind.FIXTURE,
            declared_unit="man_yen",
            declared_currency="JPY",
            statement_month="2026-05",
            owner_scope="household",
            redaction_status="redacted",
        )
    elif scenario == "raw_excel_declared":
        manifest = build_declared_raw_excel_manifest_fixture_v111()
    else:
        typer.echo(f"portfolio-quarantine-cross-review: unsupported scenario: {scenario}", err=True)
        raise typer.Exit(code=2)
    if format not in {"markdown", "json"}:
        typer.echo("portfolio-quarantine-cross-review: --format must be markdown or json", err=True)
        raise typer.Exit(code=2)
    portfolio_review = build_portfolio_data_quality_review_v109()
    quarantine_review = review_raw_input_quarantine_manifest_v110(manifest)
    cross_review = build_portfolio_quarantine_cross_review_v111(manifest)
    if format == "json":
        typer.echo(
            format_portfolio_quarantine_cross_review_json_v111(
                portfolio_review,
                quarantine_review,
                cross_review,
            )
        )
    else:
        typer.echo(
            render_portfolio_quarantine_cross_review_markdown_v111(
                portfolio_review,
                quarantine_review,
                cross_review,
            )
        )


@app.command("chatgpt-main-development-handoff-summary")
def chatgpt_main_development_handoff_summary_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    candidate_cache_path: str = typer.Option(DEFAULT_CANDIDATE_CACHE_PATH, "--candidate-cache-path"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    run_date = report_date or today_jst_iso()
    payload = build_chatgpt_main_development_handoff_summary(
        report_date=run_date,
        candidate_cache_path=candidate_cache_path,
    )
    _emit_return_to_main_pack(
        command_name="chatgpt-main-development-handoff-summary",
        payload=payload,
        out_dir=Path(out_dir) if out_dir else OUTPUTS_DIR / "reports" / "chatgpt_handoff",
        report_date=run_date,
        stem="chatgpt_main_development_handoff_summary",
        fmt=fmt,
        stderr_suffix=(
            "source_only=true handoff_summary_only=true provider_live_access_executed=false "
            "live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false "
            "broker_api_access_executed=false raw_broker_export_parsed=false env_secret_displayed=false "
            "workflow_files_modified=false trading_action_executed=false"
        ),
    )


def _emit_monthly_portfolio_pack(
    *,
    command_name: str,
    payload: dict[str, Any],
    out_dir: Path,
    report_month: str,
    stem: str,
    fmt: str,
    stderr_suffix: str,
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo(f"{command_name}: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    markdown_text = format_monthly_portfolio_strategy_markdown(payload)
    paths = write_monthly_portfolio_strategy_outputs(
        out_dir=out_dir,
        report_month=report_month,
        stem=stem,
        markdown_text=markdown_text,
        json_payload=payload,
    )
    typer.echo(format_monthly_portfolio_strategy_json(payload) if fmt == "json" else markdown_text)
    for key, p in paths.items():
        typer.echo(f"{command_name}: {key}={p}", err=True)
    typer.echo(f"{command_name}: {stderr_suffix}", err=True)
    raise typer.Exit(0)


@app.command("monthly-portfolio-snapshot-template")
def monthly_portfolio_snapshot_template_command(
    report_month: str = typer.Option("2026-05", "--report-month"),
    snapshot_date: Optional[str] = typer.Option(None, "--snapshot-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    payload = build_monthly_portfolio_snapshot_template(
        report_month=report_month,
        snapshot_date=snapshot_date,
    )
    _emit_monthly_portfolio_pack(
        command_name="monthly-portfolio-snapshot-template",
        payload=payload,
        out_dir=Path(out_dir) if out_dir else OUTPUTS_DIR / "reports" / "portfolio_strategy",
        report_month=report_month,
        stem="monthly_portfolio_snapshot_template",
        fmt=fmt,
        stderr_suffix=(
            "source_only=true template_only=true manual_redacted_json_only=true "
            "broker_api_access_executed=false raw_broker_export_parsed=false raw_excel_direct_parsed=false "
            "provider_live_access_executed=false live_http_executed=false cache_write_executed=false "
            "actual_refresh_import_executed=false env_secret_displayed=false workflow_files_modified=false "
            "trading_action_executed=false"
        ),
    )


@app.command("monthly-portfolio-snapshot-validate")
def monthly_portfolio_snapshot_validate_command(
    snapshot_path: Optional[str] = typer.Option(None, "--snapshot-path"),
    report_month: str = typer.Option("2026-05", "--report-month"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    snapshot = (
        load_monthly_portfolio_snapshot_json(Path(snapshot_path))
        if snapshot_path
        else build_monthly_portfolio_snapshot_template(report_month=report_month)["monthly_portfolio_snapshot"]
    )
    payload = validate_monthly_portfolio_snapshot(snapshot)
    _emit_monthly_portfolio_pack(
        command_name="monthly-portfolio-snapshot-validate",
        payload=payload,
        out_dir=Path(out_dir) if out_dir else OUTPUTS_DIR / "reports" / "portfolio_strategy",
        report_month=report_month,
        stem="monthly_portfolio_snapshot_validation",
        fmt=fmt,
        stderr_suffix=(
            "source_only=true redacted_json_only=true broker_api_access_executed=false "
            "raw_broker_export_parsed=false raw_excel_direct_parsed=false provider_live_access_executed=false "
            "live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false "
            "env_secret_displayed=false workflow_files_modified=false trading_action_executed=false"
        ),
    )


@app.command("monthly-portfolio-allocation-guardrails")
def monthly_portfolio_allocation_guardrails_command(
    snapshot_path: Optional[str] = typer.Option(None, "--snapshot-path"),
    report_month: str = typer.Option("2026-05", "--report-month"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    snapshot = load_monthly_portfolio_snapshot_json(Path(snapshot_path)) if snapshot_path else None
    payload = build_monthly_portfolio_allocation_guardrails(
        report_month=report_month,
        snapshot=snapshot,
    )
    _emit_monthly_portfolio_pack(
        command_name="monthly-portfolio-allocation-guardrails",
        payload=payload,
        out_dir=Path(out_dir) if out_dir else OUTPUTS_DIR / "reports" / "portfolio_strategy",
        report_month=report_month,
        stem="monthly_portfolio_allocation_guardrails",
        fmt=fmt,
        stderr_suffix=(
            "source_only=true guardrail_report_only=true broker_api_access_executed=false "
            "raw_broker_export_parsed=false raw_excel_direct_parsed=false provider_live_access_executed=false "
            "live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false "
            "env_secret_displayed=false workflow_files_modified=false trading_action_executed=false"
        ),
    )


@app.command("portfolio-cleanup-candidate-matrix")
def portfolio_cleanup_candidate_matrix_command(
    report_month: str = typer.Option("2026-05", "--report-month"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    payload = build_portfolio_cleanup_candidate_matrix(report_month=report_month)
    _emit_monthly_portfolio_pack(
        command_name="portfolio-cleanup-candidate-matrix",
        payload=payload,
        out_dir=Path(out_dir) if out_dir else OUTPUTS_DIR / "reports" / "portfolio_strategy",
        report_month=report_month,
        stem="portfolio_cleanup_candidate_matrix",
        fmt=fmt,
        stderr_suffix=(
            "source_only=true fixture_examples_only=true broker_api_access_executed=false "
            "raw_broker_export_parsed=false raw_excel_direct_parsed=false provider_live_access_executed=false "
            "live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false "
            "env_secret_displayed=false workflow_files_modified=false trading_action_executed=false"
        ),
    )


@app.command("monthly-chatgpt-portfolio-review-pack")
def monthly_chatgpt_portfolio_review_pack_command(
    snapshot_path: Optional[str] = typer.Option(None, "--snapshot-path"),
    report_month: str = typer.Option("2026-05", "--report-month"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    snapshot = load_monthly_portfolio_snapshot_json(Path(snapshot_path)) if snapshot_path else None
    payload = build_monthly_chatgpt_portfolio_review_pack(
        report_month=report_month,
        snapshot=snapshot,
    )
    _emit_monthly_portfolio_pack(
        command_name="monthly-chatgpt-portfolio-review-pack",
        payload=payload,
        out_dir=Path(out_dir) if out_dir else OUTPUTS_DIR / "reports" / "portfolio_strategy",
        report_month=report_month,
        stem="monthly_chatgpt_portfolio_review_pack",
        fmt=fmt,
        stderr_suffix=(
            "source_only=true chatgpt_review_pack_only=true broker_api_access_executed=false "
            "raw_broker_export_parsed=false raw_excel_direct_parsed=false provider_live_access_executed=false "
            "live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false "
            "env_secret_displayed=false workflow_files_modified=false trading_action_executed=false"
        ),
    )


@app.command("weekly-candidate-brief-chatgpt-context")
def weekly_candidate_brief_chatgpt_context_command(
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    report_dir: Optional[str] = typer.Option(None, "--report-dir", help="Report directory (default: reports/YYYY-MM-DD)."),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    fmt: str = typer.Option("both", "--format", help="markdown/json/both"),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
    env_file: Optional[str] = typer.Option(
        None,
        "--env-file",
        help="Local env file path (J-Quants allowlisted keys only; values not printed).",
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    resolution = resolve_weekly_report_dir(
        report_date=run_date,
        report_dir=report_dir,
        repo_root=ROOT_DIR,
    )
    base = resolution.path
    if resolution.warning:
        typer.echo(f"weekly-candidate-brief-chatgpt-context: {resolution.warning}", err=True)
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    fmt_norm = fmt.strip().lower()
    if fmt_norm not in ("markdown", "json", "both"):
        typer.echo("weekly-candidate-brief-chatgpt-context: --format must be markdown/json/both", err=True)
        raise typer.Exit(2)
    env_file_meta = _apply_optional_jquants_env_file(env_file)
    _echo_env_file_meta("weekly-candidate-brief-chatgpt-context", env_file_meta)
    try:
        pack = build_chatgpt_context_pack(report_date=run_date, report_dir=base)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        typer.echo(f"weekly-candidate-brief-chatgpt-context: {e}", err=True)
        raise typer.Exit(2) from e

    md_text = pack.markdown_text if fmt_norm in ("markdown", "both") else "# Context Pack\n\n- markdown出力は無効です。\n"
    js_payload = pack.json_payload if fmt_norm in ("json", "both") else {"report_date": run_date, "disabled": True}
    if isinstance(js_payload, dict):
        js_payload = {
            **js_payload,
            "report_dir_resolution": {
                "path": str(resolution.path),
                "resolution_source": resolution.resolution_source,
                "used_fallback": resolution.used_fallback,
            },
        }
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=md_text,
        json_payload=js_payload,
        write_latest=write_latest,
        write_archive=write_archive,
    )
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-chatgpt-context: {key}={p}")

    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-chatgpt-context: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        try:
            sync_paths = sync_to_reports_repo(
                reports_repo_path=Path(reports_repo_path),
                repo_root=ROOT_DIR,
                report_date=run_date,
                markdown_text=md_text,
                json_payload=js_payload,
            )
        except (ValueError, FileNotFoundError) as e:
            typer.echo(f"weekly-candidate-brief-chatgpt-context: {e}", err=True)
            raise typer.Exit(2) from e
        for key, p in sync_paths.items():
            typer.echo(f"weekly-candidate-brief-chatgpt-context: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-chatgpt-audit")
def weekly_candidate_brief_chatgpt_audit_command(
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    context_json: Optional[str] = typer.Option(
        None,
        "--context-json",
        help="Path to chatgpt_invest_context_pack.json (default: outputs/chatgpt_context/latest).",
    ),
    context_md: Optional[str] = typer.Option(
        None,
        "--context-md",
        help="Path to chatgpt_invest_context_pack.md (optional, used for label/length checks).",
    ),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    write_feedback_template: bool = typer.Option(
        True, "--write-feedback-template/--no-write-feedback-template", help="Write decision feedback template."
    ),
    write_validation_seed: bool = typer.Option(
        True, "--write-validation-seed/--no-write-validation-seed", help="Write forward validation seed."
    ),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    json_path = Path(context_json) if context_json else out_root / "latest" / "chatgpt_invest_context_pack.json"
    md_path = Path(context_md) if context_md else out_root / "latest" / "chatgpt_invest_context_pack.md"
    try:
        context_payload = json.loads(json_path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        typer.echo(f"weekly-candidate-brief-chatgpt-audit: context json not found: {json_path}", err=True)
        raise typer.Exit(2) from e
    except json.JSONDecodeError as e:
        typer.echo(f"weekly-candidate-brief-chatgpt-audit: invalid context json: {e}", err=True)
        raise typer.Exit(2) from e
    if not isinstance(context_payload, dict):
        typer.echo("weekly-candidate-brief-chatgpt-audit: context json must be object", err=True)
        raise typer.Exit(2)

    md_text: str | None = None
    if md_path.is_file():
        md_text = md_path.read_text(encoding="utf-8")

    audit = build_context_pack_quality_audit(
        report_date=run_date,
        context_json_payload=context_payload,
        context_markdown_text=md_text,
    )
    feedback = (
        build_decision_feedback_template(report_date=run_date, context_json_payload=context_payload)
        if write_feedback_template
        else None
    )
    seed = (
        build_forward_validation_seed(report_date=run_date, context_json_payload=context_payload)
        if write_validation_seed
        else None
    )

    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=md_text or "# ChatGPT投資対話用Context Pack\n",
        json_payload=context_payload,
        write_latest=write_latest,
        write_archive=write_archive,
        quality_audit_markdown=audit.markdown_text,
        feedback_template_markdown=feedback.markdown_text if feedback else None,
        decision_seed_markdown=seed.markdown_text if seed else None,
        decision_seed_json_payload=seed.json_payload if seed else None,
    )
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-chatgpt-audit: {key}={p}")

    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-chatgpt-audit: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        if md_text is None:
            md_text = "# ChatGPT投資対話用Context Pack\n"
        try:
            sync_paths = sync_to_reports_repo(
                reports_repo_path=Path(reports_repo_path),
                repo_root=ROOT_DIR,
                report_date=run_date,
                markdown_text=md_text,
                json_payload=context_payload,
                quality_audit_markdown=audit.markdown_text,
                feedback_template_markdown=feedback.markdown_text if feedback else None,
                decision_seed_markdown=seed.markdown_text if seed else None,
                decision_seed_json_payload=seed.json_payload if seed else None,
            )
        except (ValueError, FileNotFoundError) as e:
            typer.echo(f"weekly-candidate-brief-chatgpt-audit: {e}", err=True)
            raise typer.Exit(2) from e
        for key, p in sync_paths.items():
            typer.echo(f"weekly-candidate-brief-chatgpt-audit: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-chatgpt-enrich")
def weekly_candidate_brief_chatgpt_enrich_command(
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    context_json: Optional[str] = typer.Option(
        None, "--context-json", help="Path to chatgpt_invest_context_pack.json (default: outputs/chatgpt_context/latest)."
    ),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
    env_file: Optional[str] = typer.Option(
        None,
        "--env-file",
        help="Local env file path (J-Quants allowlisted keys only; values not printed).",
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    json_path = Path(context_json) if context_json else out_root / "latest" / "chatgpt_invest_context_pack.json"
    md_path = out_root / "latest" / "chatgpt_invest_context_pack.md"
    env_file_meta = _apply_optional_jquants_env_file(env_file)
    _echo_env_file_meta("weekly-candidate-brief-chatgpt-enrich", env_file_meta)
    try:
        context_payload = json.loads(json_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        typer.echo(f"weekly-candidate-brief-chatgpt-enrich: {e}", err=True)
        raise typer.Exit(2) from e
    if not isinstance(context_payload, dict):
        typer.echo("weekly-candidate-brief-chatgpt-enrich: context json must be object", err=True)
        raise typer.Exit(2)

    enrichment = build_context_enrichment(report_date=run_date, context_json_payload=context_payload)
    base_markdown = "# ChatGPT投資対話用Context Pack\n"
    if md_path.is_file():
        loaded_md = md_path.read_text(encoding="utf-8").strip()
        if loaded_md:
            base_markdown = loaded_md + "\n"
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=base_markdown,
        json_payload=context_payload,
        write_latest=write_latest,
        write_archive=write_archive,
        trap_analysis_markdown=enrichment.markdown_text,
        trap_analysis_json_payload=enrichment.json_payload,
    )
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-chatgpt-enrich: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-chatgpt-enrich: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=base_markdown,
            json_payload=context_payload,
            trap_analysis_markdown=enrichment.markdown_text,
            trap_analysis_json_payload=enrichment.json_payload,
        )
        for key, p in sync_paths.items():
            typer.echo(f"weekly-candidate-brief-chatgpt-enrich: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-validation-seed")
def weekly_candidate_brief_validation_seed_command(
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    context_json: Optional[str] = typer.Option(
        None, "--context-json", help="Path to chatgpt_invest_context_pack.json (default: outputs/chatgpt_context/latest)."
    ),
    out_dir: Optional[str] = typer.Option(
        None, "--out-dir", help="Validation output root (default: outputs/chatgpt_context/validation)."
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    context_root = OUTPUTS_DIR / "chatgpt_context"
    json_path = Path(context_json) if context_json else context_root / "latest" / "chatgpt_invest_context_pack.json"
    out_root = Path(out_dir) if out_dir else context_root / "validation"
    try:
        context_payload = json.loads(json_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        typer.echo(f"weekly-candidate-brief-validation-seed: {e}", err=True)
        raise typer.Exit(2) from e
    if not isinstance(context_payload, dict):
        typer.echo("weekly-candidate-brief-validation-seed: context json must be object", err=True)
        raise typer.Exit(2)
    seed = build_validation_seed(report_date=run_date, context_json_payload=context_payload)
    seed_dir = out_root / "seeds" / run_date[:4] / run_date
    seed_dir.mkdir(parents=True, exist_ok=True)
    seed_md = seed_dir / "decision_seed.md"
    seed_json = seed_dir / "decision_seed.json"
    seed_md.write_text(seed.markdown_text, encoding="utf-8")
    seed_json.write_text(json.dumps(seed.json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"weekly-candidate-brief-validation-seed: decision_seed_md={seed_md}")
    typer.echo(f"weekly-candidate-brief-validation-seed: decision_seed_json={seed_json}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-validation-evaluate")
def weekly_candidate_brief_validation_evaluate_command(
    as_of_date: Optional[str] = typer.Option(None, "--as-of-date", help="ISO date for evaluation (default: today JST)."),
    seeds_dir: Optional[str] = typer.Option(
        None, "--seeds-dir", help="Seeds directory (default: outputs/chatgpt_context/validation/seeds)."
    ),
    out_dir: Optional[str] = typer.Option(
        None, "--out-dir", help="Validation output root (default: outputs/chatgpt_context/validation)."
    ),
    write_dashboard: bool = typer.Option(True, "--write-dashboard/--no-write-dashboard", help="Write dashboard outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy validation outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
) -> None:
    eval_date = as_of_date or today_jst_iso()
    context_root = OUTPUTS_DIR / "chatgpt_context" / "validation"
    seeds_root = Path(seeds_dir) if seeds_dir else context_root / "seeds"
    out_root = Path(out_dir) if out_dir else context_root
    paths = evaluate_validation_seeds(as_of_date=eval_date, seeds_dir=seeds_root, out_dir=out_root)
    if not write_dashboard:
        for key in ("dashboard_md", "dashboard_json"):
            _ = paths.pop(key, None)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-validation-evaluate: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-validation-evaluate: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        dashboard_md_text = None
        dashboard_json_payload = None
        if write_dashboard:
            md_path = paths.get("dashboard_md")
            js_path = paths.get("dashboard_json")
            if md_path and md_path.is_file():
                dashboard_md_text = md_path.read_text(encoding="utf-8")
            if js_path and js_path.is_file():
                dashboard_json_payload = json.loads(js_path.read_text(encoding="utf-8"))
        sync_paths = sync_validation_outputs_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            validation_results_dir=out_root,
            dashboard_markdown=dashboard_md_text,
            dashboard_json_payload=dashboard_json_payload,
        )
        for key, p in sync_paths.items():
            typer.echo(f"weekly-candidate-brief-validation-evaluate: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-cache-refresh-readiness")
def weekly_candidate_brief_cache_refresh_readiness_command(
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    context_json: Optional[str] = typer.Option(
        None, "--context-json", help="Path to chatgpt_invest_context_pack.json (default: outputs/chatgpt_context/latest)."
    ),
    trap_json: Optional[str] = typer.Option(
        None, "--trap-json", help="Path to trap_analysis.json (optional)."
    ),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
    env_file: Optional[str] = typer.Option(
        None,
        "--env-file",
        help="Local env file path (J-Quants allowlisted keys only; values not printed).",
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    context_path = Path(context_json) if context_json else out_root / "latest" / "chatgpt_invest_context_pack.json"
    trap_path = Path(trap_json) if trap_json else out_root / "latest" / "trap_analysis.json"
    env_file_meta = _apply_optional_jquants_env_file(env_file)
    _echo_env_file_meta("weekly-candidate-brief-cache-refresh-readiness", env_file_meta)
    context_payload: dict[str, Any] = {}
    trap_payload: dict[str, Any] | None = None
    if context_path.is_file():
        try:
            loaded = json.loads(context_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                context_payload = loaded
        except json.JSONDecodeError:
            context_payload = {}
    if trap_path.is_file():
        try:
            loaded_trap = json.loads(trap_path.read_text(encoding="utf-8"))
            if isinstance(loaded_trap, dict):
                trap_payload = loaded_trap
        except json.JSONDecodeError:
            trap_payload = None
    context_md_path = out_root / "latest" / "chatgpt_invest_context_pack.md"
    context_md_text = (
        context_md_path.read_text(encoding="utf-8")
        if context_md_path.is_file()
        else "# ChatGPT投資対話用Context Pack\n"
    )
    readiness = build_cache_refresh_readiness_report(
        report_date=run_date,
        repo_root=ROOT_DIR,
        context_json_payload=context_payload,
        trap_json_payload=trap_payload,
    )
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload or {"report_date": run_date, "source": "cache_refresh_readiness"},
        write_latest=write_latest,
        write_archive=write_archive,
        cache_refresh_readiness_markdown=readiness.markdown_text,
        cache_refresh_readiness_json_payload=readiness.json_payload,
    )
    for key, p in paths.items():
        if "cache_refresh_readiness" in key:
            typer.echo(f"weekly-candidate-brief-cache-refresh-readiness: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-cache-refresh-readiness: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload or {"report_date": run_date, "source": "cache_refresh_readiness"},
            cache_refresh_readiness_markdown=readiness.markdown_text,
            cache_refresh_readiness_json_payload=readiness.json_payload,
        )
        for key, p in sync_paths.items():
            if "cache_refresh_readiness" in key:
                typer.echo(f"weekly-candidate-brief-cache-refresh-readiness: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-cache-refresh-plan")
def weekly_candidate_brief_cache_refresh_plan_command(
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    readiness_json: Optional[str] = typer.Option(
        None, "--readiness-json", help="Path to cache_refresh_readiness.json (default: outputs/chatgpt_context/latest)."
    ),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
    env_file: Optional[str] = typer.Option(
        None,
        "--env-file",
        help="Local env file path (J-Quants allowlisted keys only; values not printed).",
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    readiness_path = Path(readiness_json) if readiness_json else out_root / "latest" / "cache_refresh_readiness.json"
    env_file_meta = _apply_optional_jquants_env_file(env_file)
    _echo_env_file_meta("weekly-candidate-brief-cache-refresh-plan", env_file_meta)
    readiness_payload: dict[str, Any] = {}
    if readiness_path.is_file():
        try:
            raw = json.loads(readiness_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                readiness_payload = raw
        except json.JSONDecodeError:
            readiness_payload = {}
    plan = build_cache_refresh_execution_plan(report_date=run_date, readiness_json_payload=readiness_payload)
    context_md_path = out_root / "latest" / "chatgpt_invest_context_pack.md"
    context_json_path = out_root / "latest" / "chatgpt_invest_context_pack.json"
    context_md_text = (
        context_md_path.read_text(encoding="utf-8")
        if context_md_path.is_file()
        else "# ChatGPT投資対話用Context Pack\n"
    )
    context_payload: dict[str, Any] = {}
    if context_json_path.is_file():
        try:
            raw = json.loads(context_json_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                context_payload = raw
        except json.JSONDecodeError:
            context_payload = {}
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload or {"report_date": run_date, "source": "cache_refresh_execution_plan"},
        write_latest=write_latest,
        write_archive=write_archive,
        cache_refresh_execution_plan_markdown=plan.markdown_text,
        cache_refresh_execution_plan_json_payload=plan.json_payload,
    )
    for key, p in paths.items():
        if "cache_refresh_execution_plan" in key:
            typer.echo(f"weekly-candidate-brief-cache-refresh-plan: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-cache-refresh-plan: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload or {"report_date": run_date, "source": "cache_refresh_execution_plan"},
            cache_refresh_execution_plan_markdown=plan.markdown_text,
            cache_refresh_execution_plan_json_payload=plan.json_payload,
        )
        for key, p in sync_paths.items():
            if "cache_refresh_execution_plan" in key:
                typer.echo(f"weekly-candidate-brief-cache-refresh-plan: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-cache-refresh-execute")
def weekly_candidate_brief_cache_refresh_execute_command(
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    plan_json: Optional[str] = typer.Option(
        None, "--plan-json", help="Path to cache_refresh_execution_plan.json (default: outputs/chatgpt_context/latest)."
    ),
    provider: str = typer.Option("jquants", "--provider", help="Refresh provider (must be jquants)."),
    targets: str = typer.Option("5802,6645,5801", "--targets", help="Comma-separated JP tickers."),
    scope: str = typer.Option("JP_ONLY", "--scope", help="Execution scope (must be JP_ONLY)."),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    execute_refresh: bool = typer.Option(
        False,
        "--execute-refresh",
        help="Execute one-shot JP refresh when all explicit gates are set.",
    ),
    env_file: Optional[str] = typer.Option(
        None,
        "--env-file",
        help="Local env file path (J-Quants allowlisted keys only; values not printed).",
    ),
    allow_date_clamp: bool = typer.Option(
        False,
        "--allow-date-clamp",
        help="Clamp refresh date range to JQUANTS_DATA_AVAILABLE_* contract bounds.",
    ),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    plan_path = Path(plan_json) if plan_json else out_root / "latest" / "cache_refresh_execution_plan.json"
    plan_payload: dict[str, Any] = {}
    if plan_path.is_file():
        try:
            raw = json.loads(plan_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                plan_payload = raw
        except json.JSONDecodeError:
            plan_payload = {}
    _apply_optional_jquants_env_file(env_file)
    execute_result = build_cache_refresh_execute(
        report_date=run_date,
        plan_json_payload=plan_payload,
        execute_refresh=execute_refresh,
        provider=provider,
        targets_csv=targets,
        scope=scope,
        env=dict(os.environ),
        allow_date_clamp=allow_date_clamp,
    )
    context_md_path = out_root / "latest" / "chatgpt_invest_context_pack.md"
    context_json_path = out_root / "latest" / "chatgpt_invest_context_pack.json"
    context_md_text = (
        context_md_path.read_text(encoding="utf-8")
        if context_md_path.is_file()
        else "# ChatGPT投資対話用Context Pack\n"
    )
    context_payload: dict[str, Any] = {}
    if context_json_path.is_file():
        try:
            raw = json.loads(context_json_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                context_payload = raw
        except json.JSONDecodeError:
            context_payload = {}
    write_kwargs: dict[str, Any] = {
        "out_dir": out_root,
        "report_date": run_date,
        "markdown_text": context_md_text,
        "json_payload": context_payload
        or {"report_date": run_date, "source": "cache_refresh_execute"},
        "write_latest": write_latest,
        "write_archive": write_archive,
    }
    if execute_result.is_result:
        write_kwargs["cache_refresh_execute_result_markdown"] = execute_result.markdown_text
        write_kwargs["cache_refresh_execute_result_json_payload"] = execute_result.json_payload
    else:
        write_kwargs["cache_refresh_execute_dry_run_markdown"] = execute_result.markdown_text
        write_kwargs["cache_refresh_execute_dry_run_json_payload"] = execute_result.json_payload
    paths = write_context_pack_outputs(**write_kwargs)
    for key, p in paths.items():
        if "cache_refresh_execute" in key:
            typer.echo(f"weekly-candidate-brief-cache-refresh-execute: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-cache-refresh-execute: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_kwargs: dict[str, Any] = {
            "reports_repo_path": Path(reports_repo_path),
            "repo_root": ROOT_DIR,
            "report_date": run_date,
            "markdown_text": context_md_text,
            "json_payload": context_payload or {"report_date": run_date, "source": "cache_refresh_execute"},
        }
        if execute_result.is_result:
            sync_kwargs["cache_refresh_execute_result_markdown"] = execute_result.markdown_text
            sync_kwargs["cache_refresh_execute_result_json_payload"] = execute_result.json_payload
        else:
            sync_kwargs["cache_refresh_execute_dry_run_markdown"] = execute_result.markdown_text
            sync_kwargs["cache_refresh_execute_dry_run_json_payload"] = execute_result.json_payload
        sync_paths = sync_to_reports_repo(**sync_kwargs)
        for key, p in sync_paths.items():
            if "cache_refresh_execute" in key:
                typer.echo(f"weekly-candidate-brief-cache-refresh-execute: {key}={p}")
    status = str(execute_result.json_payload.get("status", ""))
    overall = str(execute_result.json_payload.get("overall_status", status))
    if overall.startswith("refused_") or overall in {"gate_refused", "target_mismatch", "auth_missing"}:
        typer.echo(f"weekly-candidate-brief-cache-refresh-execute: {overall}", err=True)
        raise typer.Exit(2)
    if execute_refresh and overall in {"partial_failure", "provider_error"}:
        typer.echo(f"weekly-candidate-brief-cache-refresh-execute: {overall}", err=True)
        raise typer.Exit(1)
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-jp-cache-refresh-dry-run")
def weekly_candidate_brief_jp_cache_refresh_dry_run_command(
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    plan_json: Optional[str] = typer.Option(
        None, "--plan-json", help="Path to cache_refresh_execution_plan.json (default: outputs/chatgpt_context/latest)."
    ),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    plan_path = Path(plan_json) if plan_json else out_root / "latest" / "cache_refresh_execution_plan.json"
    plan_payload: dict[str, Any] = {}
    if plan_path.is_file():
        try:
            raw = json.loads(plan_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                plan_payload = raw
        except json.JSONDecodeError:
            plan_payload = {}
    jp_dry_run = build_jp_cache_refresh_dry_run(report_date=run_date, plan_json_payload=plan_payload)
    context_md_path = out_root / "latest" / "chatgpt_invest_context_pack.md"
    context_json_path = out_root / "latest" / "chatgpt_invest_context_pack.json"
    context_md_text = (
        context_md_path.read_text(encoding="utf-8")
        if context_md_path.is_file()
        else "# ChatGPT投資対話用Context Pack\n"
    )
    context_payload: dict[str, Any] = {}
    if context_json_path.is_file():
        try:
            raw = json.loads(context_json_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                context_payload = raw
        except json.JSONDecodeError:
            context_payload = {}
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload or {"report_date": run_date, "source": "jp_cache_refresh_dry_run"},
        write_latest=write_latest,
        write_archive=write_archive,
        jp_cache_refresh_dry_run_markdown=jp_dry_run.markdown_text,
        jp_cache_refresh_dry_run_json_payload=jp_dry_run.json_payload,
    )
    for key, p in paths.items():
        if "jp_cache_refresh_dry_run" in key:
            typer.echo(f"weekly-candidate-brief-jp-cache-refresh-dry-run: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-jp-cache-refresh-dry-run: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload or {"report_date": run_date, "source": "jp_cache_refresh_dry_run"},
            jp_cache_refresh_dry_run_markdown=jp_dry_run.markdown_text,
            jp_cache_refresh_dry_run_json_payload=jp_dry_run.json_payload,
        )
        for key, p in sync_paths.items():
            if "jp_cache_refresh_dry_run" in key:
                typer.echo(f"weekly-candidate-brief-jp-cache-refresh-dry-run: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-jquants-preflight")
def weekly_candidate_brief_jquants_preflight_command(
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
    env_file: Optional[str] = typer.Option(
        None,
        "--env-file",
        help="Local env file path (J-Quants allowlisted keys only; values not printed).",
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    env_file_meta = _apply_optional_jquants_env_file(env_file)
    preflight = build_jquants_preflight(
        report_date=run_date,
        env=dict(os.environ),
        env_file_meta=env_file_meta,
    )
    context_md_path = out_root / "latest" / "chatgpt_invest_context_pack.md"
    context_json_path = out_root / "latest" / "chatgpt_invest_context_pack.json"
    context_md_text = (
        context_md_path.read_text(encoding="utf-8")
        if context_md_path.is_file()
        else "# ChatGPT投資対話用Context Pack\n"
    )
    context_payload: dict[str, Any] = {}
    if context_json_path.is_file():
        try:
            raw = json.loads(context_json_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                context_payload = raw
        except json.JSONDecodeError:
            context_payload = {}
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload or {"report_date": run_date, "source": "jquants_preflight"},
        write_latest=write_latest,
        write_archive=write_archive,
        jquants_preflight_markdown=preflight.markdown_text,
        jquants_preflight_json_payload=preflight.json_payload,
    )
    for key, p in paths.items():
        if "jquants_preflight" in key:
            typer.echo(f"weekly-candidate-brief-jquants-preflight: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-jquants-preflight: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload or {"report_date": run_date, "source": "jquants_preflight"},
            jquants_preflight_markdown=preflight.markdown_text,
            jquants_preflight_json_payload=preflight.json_payload,
        )
        for key, p in sync_paths.items():
            if "jquants_preflight" in key:
                typer.echo(f"weekly-candidate-brief-jquants-preflight: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-jp-alternative-provider-readiness")
def weekly_candidate_brief_jp_alternative_provider_readiness_command(
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    targets: str = typer.Option(
        "5802,6645,5801,285A,5803",
        "--targets",
        help="Comma-separated JP tickers for contract-limit assessment.",
    ),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
    env_file: Optional[str] = typer.Option(
        None,
        "--env-file",
        help="Local env file path (J-Quants allowlisted keys only; values not printed).",
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    env_file_meta = _apply_optional_jquants_env_file(env_file)
    _echo_env_file_meta("weekly-candidate-brief-jp-alternative-provider-readiness", env_file_meta)
    readiness = build_jp_alternative_provider_readiness(
        report_date=run_date,
        targets_csv=targets,
        repo_root=ROOT_DIR,
        env=dict(os.environ),
    )
    context_md_path = out_root / "latest" / "chatgpt_invest_context_pack.md"
    context_json_path = out_root / "latest" / "chatgpt_invest_context_pack.json"
    context_md_text = (
        context_md_path.read_text(encoding="utf-8")
        if context_md_path.is_file()
        else "# ChatGPT投資対話用Context Pack\n"
    )
    context_payload: dict[str, Any] = {}
    if context_json_path.is_file():
        try:
            raw = json.loads(context_json_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                context_payload = raw
        except json.JSONDecodeError:
            context_payload = {}
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload or {"report_date": run_date, "source": "jp_alternative_provider_readiness"},
        write_latest=write_latest,
        write_archive=write_archive,
        jp_alternative_provider_readiness_markdown=readiness.markdown_text,
        jp_alternative_provider_readiness_json_payload=readiness.json_payload,
    )
    for key, p in paths.items():
        if "jp_alternative_provider_readiness" in key:
            typer.echo(f"weekly-candidate-brief-jp-alternative-provider-readiness: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-jp-alternative-provider-readiness: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload or {"report_date": run_date, "source": "jp_alternative_provider_readiness"},
            jp_alternative_provider_readiness_markdown=readiness.markdown_text,
            jp_alternative_provider_readiness_json_payload=readiness.json_payload,
        )
        for key, p in sync_paths.items():
            if "jp_alternative_provider_readiness" in key:
                typer.echo(f"weekly-candidate-brief-jp-alternative-provider-readiness: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-jp-alternative-provider-execution-plan")
def weekly_candidate_brief_jp_alternative_provider_execution_plan_command(
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    readiness_json: Optional[str] = typer.Option(
        None,
        "--readiness-json",
        help="Path to jp_alternative_provider_readiness.json (default: outputs/chatgpt_context/latest).",
    ),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    readiness_path = (
        Path(readiness_json) if readiness_json else out_root / "latest" / "jp_alternative_provider_readiness.json"
    )
    readiness_payload: dict[str, Any] = {}
    if readiness_path.is_file():
        try:
            raw = json.loads(readiness_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                readiness_payload = raw
        except json.JSONDecodeError:
            readiness_payload = {}
    plan = build_jp_alternative_provider_execution_plan(
        report_date=run_date,
        readiness_json_payload=readiness_payload,
    )
    context_md_path = out_root / "latest" / "chatgpt_invest_context_pack.md"
    context_json_path = out_root / "latest" / "chatgpt_invest_context_pack.json"
    context_md_text = (
        context_md_path.read_text(encoding="utf-8")
        if context_md_path.is_file()
        else "# ChatGPT投資対話用Context Pack\n"
    )
    context_payload: dict[str, Any] = {}
    if context_json_path.is_file():
        try:
            raw_ctx = json.loads(context_json_path.read_text(encoding="utf-8"))
            if isinstance(raw_ctx, dict):
                context_payload = raw_ctx
        except json.JSONDecodeError:
            context_payload = {}
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload or {"report_date": run_date, "source": "jp_alternative_provider_execution_plan"},
        write_latest=write_latest,
        write_archive=write_archive,
        jp_alternative_provider_execution_plan_markdown=plan.markdown_text,
        jp_alternative_provider_execution_plan_json_payload=plan.json_payload,
    )
    for key, p in paths.items():
        if "jp_alternative_provider_execution_plan" in key:
            typer.echo(f"weekly-candidate-brief-jp-alternative-provider-execution-plan: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-jp-alternative-provider-execution-plan: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload or {"report_date": run_date, "source": "jp_alternative_provider_execution_plan"},
            jp_alternative_provider_execution_plan_markdown=plan.markdown_text,
            jp_alternative_provider_execution_plan_json_payload=plan.json_payload,
        )
        for key, p in sync_paths.items():
            if "jp_alternative_provider_execution_plan" in key:
                typer.echo(f"weekly-candidate-brief-jp-alternative-provider-execution-plan: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-manual-csv-validate")
def weekly_candidate_brief_manual_csv_validate_command(
    csv_path: str = typer.Option(..., "--csv-path", help="Path to manual JP bars CSV (must not be git-tracked)."),
    targets: str = typer.Option("5802,6645,5801,285A,5803", "--targets", help="Comma-separated JP tickers."),
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    try:
        resolved_csv = resolve_manual_csv_path(csv_path, repo_root=ROOT_DIR)
    except ManualCsvPathError as exc:
        typer.echo(f"weekly-candidate-brief-manual-csv-validate: {exc}", err=True)
        raise typer.Exit(2) from exc
    validation = validate_manual_csv_file(
        csv_path=resolved_csv,
        targets_csv=targets,
        report_date=run_date,
    )
    context_md_text = "# Manual CSV Validation\n"
    context_payload: dict[str, Any] = {"report_date": run_date, "source": "manual_csv_validation"}
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload,
        write_latest=write_latest,
        write_archive=write_archive,
        manual_csv_validation_markdown=validation.markdown_text,
        manual_csv_validation_json_payload=validation.json_payload,
    )
    for key, p in paths.items():
        if "manual_csv_validation" in key:
            typer.echo(f"weekly-candidate-brief-manual-csv-validate: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-manual-csv-validate: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload,
            manual_csv_validation_markdown=validation.markdown_text,
            manual_csv_validation_json_payload=validation.json_payload,
        )
        for key, p in sync_paths.items():
            if "manual_csv_validation" in key:
                typer.echo(f"weekly-candidate-brief-manual-csv-validate: {key}={p}")
    raise typer.Exit(0 if validation.json_payload.get("validated") else 2)


@app.command("weekly-candidate-brief-manual-csv-import-plan")
def weekly_candidate_brief_manual_csv_import_plan_command(
    csv_path: str = typer.Option(..., "--csv-path", help="Path to manual JP bars CSV (must not be git-tracked)."),
    targets: str = typer.Option("5802,6645,5801,285A,5803", "--targets", help="Comma-separated JP tickers."),
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    try:
        resolved_csv = resolve_manual_csv_path(csv_path, repo_root=ROOT_DIR)
    except ManualCsvPathError as exc:
        typer.echo(f"weekly-candidate-brief-manual-csv-import-plan: {exc}", err=True)
        raise typer.Exit(2) from exc
    plan = build_manual_csv_import_plan(
        csv_path=resolved_csv,
        targets_csv=targets,
        report_date=run_date,
    )
    context_md_text = "# Manual CSV Import Plan\n"
    context_payload: dict[str, Any] = {"report_date": run_date, "source": "manual_csv_import_plan"}
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload,
        write_latest=write_latest,
        write_archive=write_archive,
        manual_csv_import_plan_markdown=plan.markdown_text,
        manual_csv_import_plan_json_payload=plan.json_payload,
    )
    for key, p in paths.items():
        if "manual_csv_import_plan" in key:
            typer.echo(f"weekly-candidate-brief-manual-csv-import-plan: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-manual-csv-import-plan: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload,
            manual_csv_import_plan_markdown=plan.markdown_text,
            manual_csv_import_plan_json_payload=plan.json_payload,
        )
        for key, p in sync_paths.items():
            if "manual_csv_import_plan" in key:
                typer.echo(f"weekly-candidate-brief-manual-csv-import-plan: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-manual-csv-import-execute")
def weekly_candidate_brief_manual_csv_import_execute_command(
    csv_path: str = typer.Option(..., "--csv-path", help="Path to manual JP bars CSV (must not be git-tracked)."),
    targets: str = typer.Option("5802,6645,5801,285A,5803", "--targets", help="Comma-separated JP tickers."),
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    provider: str = typer.Option("manual_csv", "--provider", help="Import provider (must be manual_csv)."),
    scope: str = typer.Option("JP_ONLY", "--scope", help="Execution scope (must be JP_ONLY)."),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    execute_import: bool = typer.Option(
        False,
        "--execute-import",
        help="Execute gated manual CSV cache import when all explicit gates are set.",
    ),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    try:
        resolved_csv = resolve_manual_csv_path(csv_path, repo_root=ROOT_DIR)
    except ManualCsvPathError as exc:
        typer.echo(f"weekly-candidate-brief-manual-csv-import-execute: {exc}", err=True)
        raise typer.Exit(2) from exc
    execute_result = build_manual_csv_import_execute(
        csv_path=resolved_csv,
        targets_csv=targets,
        report_date=run_date,
        provider=provider,
        scope=scope,
        execute_import=execute_import,
        env=dict(os.environ),
    )
    context_md_text = "# Manual CSV Import Execute\n"
    context_payload: dict[str, Any] = {"report_date": run_date, "source": "manual_csv_import_execute"}
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload,
        write_latest=write_latest,
        write_archive=write_archive,
        manual_csv_import_result_markdown=execute_result.markdown_text,
        manual_csv_import_result_json_payload=execute_result.json_payload,
    )
    for key, p in paths.items():
        if "manual_csv_import_result" in key:
            typer.echo(f"weekly-candidate-brief-manual-csv-import-execute: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-manual-csv-import-execute: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload,
            manual_csv_import_result_markdown=execute_result.markdown_text,
            manual_csv_import_result_json_payload=execute_result.json_payload,
        )
        for key, p in sync_paths.items():
            if "manual_csv_import_result" in key:
                typer.echo(f"weekly-candidate-brief-manual-csv-import-execute: {key}={p}")
    overall = str(execute_result.json_payload.get("overall_status", ""))
    if overall in {"gate_refused", "not_importable"} or str(
        execute_result.json_payload.get("status", "")
    ).startswith("refused_"):
        typer.echo(f"weekly-candidate-brief-manual-csv-import-execute: {overall}", err=True)
        raise typer.Exit(2)
    if execute_import and overall not in {"success", "no_op", "planned_dry_run_only"}:
        typer.echo(f"weekly-candidate-brief-manual-csv-import-execute: {overall}", err=True)
        raise typer.Exit(1)
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-manual-data-discover")
def weekly_candidate_brief_manual_data_discover_command(
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    discovery = build_manual_data_discovery(report_date=run_date, repo_root=ROOT_DIR)
    context_md_text = "# Manual Data Discovery Report\n"
    context_payload: dict[str, Any] = {"report_date": run_date, "source": "manual_data_discovery"}
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload,
        write_latest=write_latest,
        write_archive=write_archive,
        manual_data_discovery_markdown=discovery.markdown_text,
        manual_data_discovery_json_payload=discovery.json_payload,
    )
    for key, p in paths.items():
        if "manual_data_discovery" in key:
            typer.echo(f"weekly-candidate-brief-manual-data-discover: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-manual-data-discover: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload,
            manual_data_discovery_markdown=discovery.markdown_text,
            manual_data_discovery_json_payload=discovery.json_payload,
        )
        for key, p in sync_paths.items():
            if "manual_data_discovery" in key:
                typer.echo(f"weekly-candidate-brief-manual-data-discover: {key}={p}")
    raise typer.Exit(0 if discovery.json_payload.get("safe_to_parse") else 1)


@app.command("weekly-candidate-brief-manual-data-freshness-pipeline")
def weekly_candidate_brief_manual_data_freshness_pipeline_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    report_dir: Optional[str] = typer.Option(None, "--report-dir"),
    targets_csv: str = typer.Option(DEFAULT_TARGET_TICKERS_CSV, "--targets-csv"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    resolution = resolve_weekly_report_dir(
        report_date=run_date,
        repo_root=ROOT_DIR,
        report_dir=report_dir,
    )
    if resolution.warning:
        typer.echo(
            f"weekly-candidate-brief-manual-data-freshness-pipeline: {resolution.warning}",
            err=True,
        )
    result = build_manual_data_freshness_pipeline(
        report_date=run_date,
        repo_root=ROOT_DIR,
        report_dir=resolution.path,
        targets_csv=targets_csv,
    )
    paths = write_manual_data_freshness_outputs(
        out_dir=out_root,
        report_date=run_date,
        result=result,
    )
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-manual-data-freshness-pipeline: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-manual-data-freshness-pipeline: --reports-repo-path required",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_manual_data_freshness_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            result=result,
        )
        for key, p in sync_paths.items():
            typer.echo(f"weekly-candidate-brief-manual-data-freshness-pipeline: {key}={p}")
    summary = result.summary
    exit_code = 0 if summary.get("dry_run_status") in {"pass", "not_run"} else 1
    if not summary.get("manual_file_detected"):
        exit_code = 0
    raise typer.Exit(exit_code)


@app.command("weekly-candidate-brief-manual-data-dropzone-helper")
def weekly_candidate_brief_manual_data_dropzone_helper_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
) -> None:
    run_date = report_date or today_jst_iso()
    asset_paths = ensure_dropzone_assets()
    status = build_manual_data_dropzone_status(report_date=run_date)
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    latest = out_root / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    (latest / "manual_data_dropzone_status.md").write_text(status.markdown_text, encoding="utf-8")
    (latest / "manual_data_dropzone_status.json").write_text(
        json.dumps(status.json_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    typer.echo(f"weekly-candidate-brief-manual-data-dropzone-helper: dropzone={asset_paths['readme'].parent}")
    typer.echo(f"weekly-candidate-brief-manual-data-dropzone-helper: next={status.json_payload.get('next_single_action')}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-manual-data-acquisition-ux-pack")
def weekly_candidate_brief_manual_data_acquisition_ux_pack_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    report_dir: Optional[str] = typer.Option(None, "--report-dir"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    resolution = resolve_weekly_report_dir(
        report_date=run_date,
        repo_root=ROOT_DIR,
        report_dir=report_dir,
    )
    if resolution.warning:
        typer.echo(
            f"weekly-candidate-brief-manual-data-acquisition-ux-pack: {resolution.warning}",
            err=True,
        )
    result = build_manual_data_acquisition_ux_pack(
        report_date=run_date,
        repo_root=ROOT_DIR,
        report_dir=resolution.path,
    )
    ux_paths = write_manual_data_acquisition_ux_outputs(
        out_dir=out_root,
        report_date=run_date,
        result=result,
    )
    pipeline_paths = write_manual_data_freshness_outputs(
        out_dir=out_root,
        report_date=run_date,
        result=result.pipeline,
    )
    for key, p in {**ux_paths, **pipeline_paths}.items():
        typer.echo(f"weekly-candidate-brief-manual-data-acquisition-ux-pack: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-manual-data-acquisition-ux-pack: --reports-repo-path required",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_manual_data_acquisition_ux_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            report_date=run_date,
            result=result,
            repo_root=ROOT_DIR,
        )
        for key, p in sync_paths.items():
            typer.echo(f"weekly-candidate-brief-manual-data-acquisition-ux-pack: {key}={p}")
    summary = result.summary
    exit_code = 0 if summary.get("dry_run_status") in {"pass", "not_run"} else 1
    if not summary.get("manual_file_detected"):
        exit_code = 0
    raise typer.Exit(exit_code)


@app.command("weekly-candidate-brief-jp-ohlcv-freshness-source-strategy")
def weekly_candidate_brief_jp_ohlcv_freshness_source_strategy_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    report_dir: Optional[str] = typer.Option(None, "--report-dir"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    targets_csv: str = typer.Option(DEFAULT_TARGET_TICKERS_CSV, "--targets-csv"),
    env_file: Optional[str] = typer.Option(None, "--env-file"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    resolution = resolve_weekly_report_dir(
        report_date=run_date,
        repo_root=ROOT_DIR,
        report_dir=report_dir,
    )
    env_file_meta = _apply_optional_jquants_env_file(env_file)
    _echo_env_file_meta("weekly-candidate-brief-jp-ohlcv-freshness-source-strategy", env_file_meta)
    if resolution.warning:
        typer.echo(
            f"weekly-candidate-brief-jp-ohlcv-freshness-source-strategy: {resolution.warning}",
            err=True,
        )
    result = build_jp_ohlcv_freshness_source_strategy(
        report_date=run_date,
        repo_root=ROOT_DIR,
        report_dir=resolution.path,
        targets_csv=targets_csv,
    )
    paths = write_jp_ohlcv_freshness_source_strategy_outputs(
        out_dir=out_root,
        report_date=run_date,
        result=result,
    )
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-jp-ohlcv-freshness-source-strategy: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-jp-ohlcv-freshness-source-strategy: --reports-repo-path required",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_jp_ohlcv_freshness_source_strategy_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            result=result,
        )
        for key, p in sync_paths.items():
            typer.echo(f"weekly-candidate-brief-jp-ohlcv-freshness-source-strategy: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-jquants-env-preflight-refresh-pack")
def weekly_candidate_brief_jquants_env_preflight_refresh_pack_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    targets_csv: str = typer.Option(DEFAULT_TARGET_TICKERS_CSV, "--targets-csv"),
    env_file: Optional[str] = typer.Option(None, "--env-file"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    env_path = Path(env_file).expanduser() if env_file else None
    result = build_jquants_env_preflight_refresh_pack(
        report_date=run_date,
        repo_root=ROOT_DIR,
        targets_csv=targets_csv,
        env_file=env_path,
    )
    paths = write_jquants_env_preflight_refresh_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        result=result,
    )
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-jquants-env-preflight-refresh-pack: {key}={p}")
    typer.echo(
        "weekly-candidate-brief-jquants-env-preflight-refresh-pack: "
        f"selected_env_redacted={result.summary.get('selected_env_file_redacted')}"
    )
    typer.echo(
        "weekly-candidate-brief-jquants-env-preflight-refresh-pack: "
        f"refresh_recommended={result.summary.get('refresh_recommended')}"
    )
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-jquants-env-preflight-refresh-pack: --reports-repo-path required",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_jquants_env_preflight_refresh_pack_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            report_date=run_date,
            result=result,
        )
        for key, p in sync_paths.items():
            typer.echo(f"weekly-candidate-brief-jquants-env-preflight-refresh-pack: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-investment-readiness-after-refresh")
def weekly_candidate_brief_investment_readiness_after_refresh_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    targets_csv: str = typer.Option(DEFAULT_TARGET_TICKERS_CSV, "--targets-csv"),
    reports_latest_dir: Optional[str] = typer.Option(
        None,
        "--reports-latest-dir",
        help="Path to reports-private latest/ (default: outputs/chatgpt_context/latest).",
    ),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    latest_dir = Path(reports_latest_dir) if reports_latest_dir else out_root / "latest"
    result = build_investment_readiness_v31(
        report_date=run_date,
        reports_latest_dir=latest_dir,
        targets_csv=targets_csv,
    )
    paths = write_investment_readiness_v31_outputs(
        out_dir=out_root,
        report_date=run_date,
        result=result,
    )
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-investment-readiness-after-refresh: {key}={p}")
    typer.echo(
        "weekly-candidate-brief-investment-readiness-after-refresh: "
        f"verdict={result.readiness_json.get('investment_readiness_verdict')}"
    )
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-investment-readiness-after-refresh: --reports-repo-path required",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_investment_readiness_v31_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            report_date=run_date,
            result=result,
        )
        for key, p in sync_paths.items():
            typer.echo(f"weekly-candidate-brief-investment-readiness-after-refresh: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-stooq-manual-csv-ingest-v34")
def weekly_candidate_brief_stooq_manual_csv_ingest_v34_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    targets_csv: str = typer.Option("5802,6645,285A,5803", "--targets-csv"),
    dropzone_dir: Optional[str] = typer.Option(
        None,
        "--dropzone-dir",
        help="Manual data dropzone (default: ~/Downloads/invest-alpha-os-manual-data-dropzone).",
    ),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
) -> None:
    run_date = report_date or today_jst_iso()
    dz = (
        Path(dropzone_dir).expanduser()
        if dropzone_dir
        else Path.home() / "Downloads" / "invest-alpha-os-manual-data-dropzone"
    )
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    result = build_stooq_manual_csv_ingest_v34(
        report_date=run_date,
        repo_root=ROOT_DIR,
        dropzone_dir=dz,
        targets_csv=targets_csv,
    )
    paths = write_stooq_manual_csv_ingest_v34_outputs(
        out_dir=out_root,
        report_date=run_date,
        result=result,
    )
    reg_md, reg_json = build_ohlcv_provider_registry_strategy(report_date=run_date)
    cov_md, cov_json = build_ohlcv_provider_coverage_matrix(report_date=run_date)
    for stem, md, js in (
        ("ohlcv_provider_registry_strategy", reg_md, reg_json),
        ("ohlcv_provider_coverage_matrix", cov_md, cov_json),
    ):
        for root in (out_root / "latest", out_root / "weekly" / "2026" / run_date):
            root.mkdir(parents=True, exist_ok=True)
            (root / f"{stem}.md").write_text(md, encoding="utf-8")
            (root / f"{stem}.json").write_text(
                json.dumps(js, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        paths[f"latest_{stem}_md"] = out_root / "latest" / f"{stem}.md"
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-stooq-manual-csv-ingest-v34: {key}={p}")
    typer.echo(
        "weekly-candidate-brief-stooq-manual-csv-ingest-v34: "
        f"rows_newer_than_cache_total={result.import_plan_json.get('rows_newer_than_cache_total')}"
    )
    typer.echo(
        "weekly-candidate-brief-stooq-manual-csv-ingest-v34: "
        f"approval_status={result.approval_json.get('package_status')}"
    )
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-stooq-manual-csv-ingest-v34: --reports-repo-path required",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_stooq_ingest_v34_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            report_date=run_date,
            result=result,
            registry_md=reg_md,
            registry_json=reg_json,
            coverage_md=cov_md,
            coverage_json=cov_json,
        )
        for key, p in sync_paths.items():
            typer.echo(f"weekly-candidate-brief-stooq-manual-csv-ingest-v34: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-ohlcv-provider-automation-core")
def weekly_candidate_brief_ohlcv_provider_automation_core_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    result = build_ohlcv_provider_automation_core(report_date=run_date)
    paths = write_ohlcv_provider_automation_core_outputs(
        out_dir=out_root,
        report_date=run_date,
        result=result,
    )
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-ohlcv-provider-automation-core: {key}={p}")
    typer.echo(
        "weekly-candidate-brief-ohlcv-provider-automation-core: "
        "dry_run_only=true live_http_executed=false cache_write_executed=false"
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-ohlcv-provider-approval-package")
def weekly_candidate_brief_ohlcv_provider_approval_package_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-ohlcv-provider-approval-package: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_ohlcv_provider_approval_package(report_date=run_date)
    paths = write_ohlcv_provider_approval_package_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-ohlcv-provider-approval-package: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-ohlcv-provider-approval-package: "
        "dry_run_only=true live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-ohlcv-provider-safe-execution-harness")
def weekly_candidate_brief_ohlcv_provider_safe_execution_harness_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-ohlcv-provider-safe-execution-harness: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_ohlcv_provider_safe_execution_harness(report_date=run_date)
    paths = write_ohlcv_provider_safe_execution_harness_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-ohlcv-provider-safe-execution-harness: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-ohlcv-provider-safe-execution-harness: "
        "dry_run_transcript_only=true live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-ohlcv-provider-approved-execution-runbook")
def weekly_candidate_brief_ohlcv_provider_approved_execution_runbook_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
    scenario: str = typer.Option("public_ohlcv", "--scenario", help="public_ohlcv, jquants_refresh, cache_write, actual_import, or manual_import."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-ohlcv-provider-approved-execution-runbook: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    try:
        runbook_scenario = scenario_from_cli(scenario)
    except ValueError as exc:
        typer.echo(f"weekly-candidate-brief-ohlcv-provider-approved-execution-runbook: {exc}", err=True)
        raise typer.Exit(2) from exc
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_ohlcv_provider_approved_execution_runbook(
        report_date=run_date,
        scenario=runbook_scenario,
    )
    paths = write_ohlcv_provider_approved_execution_runbook_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-ohlcv-provider-approved-execution-runbook: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-ohlcv-provider-approved-execution-runbook: "
        "source_only=true commands_executed=false live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-ohlcv-provider-execution-approval-request")
def weekly_candidate_brief_ohlcv_provider_execution_approval_request_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
    scenario: str = typer.Option("public_ohlcv", "--scenario", help="public_ohlcv, jquants_refresh, cache_write, actual_import, or manual_import."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-ohlcv-provider-execution-approval-request: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    try:
        request_scenario = approval_request_scenario_from_cli(scenario)
    except ValueError as exc:
        typer.echo(f"weekly-candidate-brief-ohlcv-provider-execution-approval-request: {exc}", err=True)
        raise typer.Exit(2) from exc
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_ohlcv_provider_execution_approval_request(
        report_date=run_date,
        scenario=request_scenario,
    )
    paths = write_ohlcv_provider_execution_approval_request_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-ohlcv-provider-execution-approval-request: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-ohlcv-provider-execution-approval-request: "
        "source_only=true approval_request_only=true commands_executed=false live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-us-ohlcv-provider-selection-matrix")
def weekly_candidate_brief_us_ohlcv_provider_selection_matrix_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-us-ohlcv-provider-selection-matrix: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_us_ohlcv_provider_selection_matrix_report(report_date=run_date)
    paths = write_us_ohlcv_provider_selection_matrix_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-us-ohlcv-provider-selection-matrix: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-us-ohlcv-provider-selection-matrix: "
        "source_only=true matrix_only=true live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-us-provider-current-evidence-pack")
def weekly_candidate_brief_us_provider_current_evidence_pack_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-us-provider-current-evidence-pack: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_us_provider_current_evidence_pack_report(report_date=run_date)
    paths = write_us_provider_current_evidence_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-us-provider-current-evidence-pack: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-us-provider-current-evidence-pack: "
        "source_only=true current_evidence_only=true live_http_executed=false provider_live_access_executed=false cache_write_executed=false actual_refresh_import_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-us-ohlcv-pilot-approval-bundle")
def weekly_candidate_brief_us_ohlcv_pilot_approval_bundle_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
    provider: str = typer.Option("tiingo", "--provider", help="Modeled provider; default tiingo."),
    scenario: str = typer.Option("public_ohlcv", "--scenario", help="Modeled scenario; public_ohlcv only."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-us-ohlcv-pilot-approval-bundle: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    try:
        markdown_text, json_payload = build_us_ohlcv_pilot_approval_bundle_report(
            report_date=run_date,
            provider=provider,
            scenario=scenario,
        )
    except ValueError as exc:
        typer.echo(f"weekly-candidate-brief-us-ohlcv-pilot-approval-bundle: {exc}", err=True)
        raise typer.Exit(2) from exc
    paths = write_us_ohlcv_pilot_approval_bundle_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-us-ohlcv-pilot-approval-bundle: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-us-ohlcv-pilot-approval-bundle: "
        "source_only=true pilot_approval_bundle_only=true commands_executed=false live_http_executed=false public_ohlcv_source_live_fetch_executed=false provider_live_access_executed=false cache_write_executed=false actual_refresh_import_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-tiingo-current-docs-recheck-pack")
def weekly_candidate_brief_tiingo_current_docs_recheck_pack_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-tiingo-current-docs-recheck-pack: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_tiingo_current_docs_recheck_pack_report(report_date=run_date)
    paths = write_tiingo_current_docs_recheck_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-tiingo-current-docs-recheck-pack: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-tiingo-current-docs-recheck-pack: "
        "source_only=true manual_recheck_pack_only=true live_http_executed=false tiingo_api_called=false provider_live_access_executed=false public_ohlcv_source_live_fetch_executed=false cache_write_executed=false actual_refresh_import_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-tiingo-manual-signoff-ledger")
def weekly_candidate_brief_tiingo_manual_signoff_ledger_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-tiingo-manual-signoff-ledger: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_tiingo_manual_signoff_ledger_report(report_date=run_date)
    paths = write_tiingo_manual_signoff_ledger_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-tiingo-manual-signoff-ledger: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-tiingo-manual-signoff-ledger: "
        "source_only=true manual_signoff_ledger_only=true live_http_executed=false tiingo_api_called=false provider_live_access_executed=false public_ohlcv_source_live_fetch_executed=false cache_write_executed=false actual_refresh_import_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-tiingo-live-fetch-result-review")
def weekly_candidate_brief_tiingo_live_fetch_result_review_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-tiingo-live-fetch-result-review: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_tiingo_live_fetch_result_review_report(report_date=run_date)
    paths = write_tiingo_live_fetch_result_review_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-tiingo-live-fetch-result-review: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-tiingo-live-fetch-result-review: "
        "source_only=true result_review_only=true live_http_executed_by_this_pack=false tiingo_api_called_by_this_pack=false provider_live_access_executed_by_this_pack=false public_ohlcv_source_live_fetch_executed_by_this_pack=false stooq_yahoo_polygon_live_fetch_executed_by_this_pack=false cache_write_executed=false actual_import_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-cross-provider-validation-runbook")
def weekly_candidate_brief_cross_provider_validation_runbook_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-cross-provider-validation-runbook: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_cross_provider_validation_runbook_report(report_date=run_date)
    paths = write_cross_provider_validation_runbook_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-cross-provider-validation-runbook: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-cross-provider-validation-runbook: "
        "source_only=true approval_package_draft_only=true tiingo_api_call_executed=false stooq_live_fetch_executed=false yahoo_yfinance_live_fetch_executed=false polygon_live_fetch_executed=false provider_live_access_executed=false public_ohlcv_source_live_fetch_executed=false cache_write_executed=false actual_refresh_import_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-cross-provider-validation-result-review")
def weekly_candidate_brief_cross_provider_validation_result_review_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo(
            "weekly-candidate-brief-cross-provider-validation-result-review: --format must be markdown or json",
            err=True,
        )
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_cross_provider_validation_result_review_report(report_date=run_date)
    paths = write_cross_provider_validation_result_review_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-cross-provider-validation-result-review: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-cross-provider-validation-result-review: "
        "source_only=true result_review_only=true tiingo_api_call_executed=false stooq_live_fetch_executed=false yahoo_yfinance_live_fetch_executed=false polygon_live_fetch_executed=false provider_live_access_executed=false public_ohlcv_source_live_fetch_executed=false cache_write_executed=false actual_refresh_import_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-cache-write-readiness-gate")
def weekly_candidate_brief_cache_write_readiness_gate_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo("weekly-candidate-brief-cache-write-readiness-gate: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_cache_write_readiness_gate_report(report_date=run_date)
    paths = write_cache_write_readiness_gate_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-cache-write-readiness-gate: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-cache-write-readiness-gate: "
        "source_only=true cache_write_gate_only=true tiingo_api_call_executed=false stooq_live_fetch_executed=false yahoo_yfinance_live_fetch_executed=false polygon_live_fetch_executed=false provider_live_access_executed=false public_ohlcv_source_live_fetch_executed=false cache_write_executed=false actual_refresh_import_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-cache-write-operator-signoff-sheet")
def weekly_candidate_brief_cache_write_operator_signoff_sheet_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo(
            "weekly-candidate-brief-cache-write-operator-signoff-sheet: --format must be markdown or json",
            err=True,
        )
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_cache_write_operator_signoff_sheet_report(report_date=run_date)
    paths = write_cache_write_operator_signoff_sheet_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-cache-write-operator-signoff-sheet: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-cache-write-operator-signoff-sheet: "
        "source_only=true operator_signoff_sheet_only=true tiingo_api_call_executed=false stooq_live_fetch_executed=false yahoo_yfinance_live_fetch_executed=false polygon_live_fetch_executed=false provider_live_access_executed=false public_ohlcv_source_live_fetch_executed=false cache_write_executed=false actual_refresh_import_executed=false raw_ohlcv_persisted=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-cache-path-preflight-approval-package")
def weekly_candidate_brief_cache_path_preflight_approval_package_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    candidate_cache_path: str = typer.Option(DEFAULT_CANDIDATE_CACHE_PATH, "--candidate-cache-path"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo(
            "weekly-candidate-brief-cache-path-preflight-approval-package: --format must be markdown or json",
            err=True,
        )
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_cache_path_preflight_approval_package_report(
        report_date=run_date,
        candidate_cache_path=candidate_cache_path,
    )
    paths = write_cache_path_preflight_approval_package_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-cache-path-preflight-approval-package: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-cache-path-preflight-approval-package: "
        "source_only=true path_preflight_only=true filesystem_probe_performed=false directory_created=false tiingo_api_call_executed=false stooq_live_fetch_executed=false yahoo_yfinance_live_fetch_executed=false polygon_live_fetch_executed=false provider_live_access_executed=false live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false raw_ohlcv_persisted=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-cache-purge-inventory-dryrun-contract")
def weekly_candidate_brief_cache_purge_inventory_dryrun_contract_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    candidate_cache_path: str = typer.Option(DEFAULT_CANDIDATE_CACHE_PATH, "--candidate-cache-path"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo(
            "weekly-candidate-brief-cache-purge-inventory-dryrun-contract: --format must be markdown or json",
            err=True,
        )
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_cache_purge_inventory_dryrun_contract_report(
        report_date=run_date,
        candidate_cache_path=candidate_cache_path,
    )
    paths = write_cache_purge_inventory_dryrun_contract_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-cache-purge-inventory-dryrun-contract: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-cache-purge-inventory-dryrun-contract: "
        "source_only=true purge_inventory_contract_only=true file_deletion_executed=false filesystem_scan_executed=false raw_ohlcv_read=false tiingo_api_call_executed=false provider_live_access_executed=false live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false raw_ohlcv_persisted=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-cache-write-pilot-approval-packet")
def weekly_candidate_brief_cache_write_pilot_approval_packet_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    candidate_cache_path: str = typer.Option(DEFAULT_CANDIDATE_CACHE_PATH, "--candidate-cache-path"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo(
            "weekly-candidate-brief-cache-write-pilot-approval-packet: --format must be markdown or json",
            err=True,
        )
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_cache_write_pilot_approval_packet_report(
        report_date=run_date,
        candidate_cache_path=candidate_cache_path,
    )
    paths = write_cache_write_pilot_approval_packet_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-cache-write-pilot-approval-packet: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-cache-write-pilot-approval-packet: "
        "source_only=true approval_packet_only=true tiingo_api_call_executed=false provider_live_access_executed=false live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false raw_ohlcv_persisted=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-cache-write-pilot-result-review-gate")
def weekly_candidate_brief_cache_write_pilot_result_review_gate_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    candidate_cache_path: str = typer.Option(DEFAULT_CANDIDATE_CACHE_PATH, "--candidate-cache-path"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo(
            "weekly-candidate-brief-cache-write-pilot-result-review-gate: --format must be markdown or json",
            err=True,
        )
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_cache_write_pilot_result_review_gate_report(
        report_date=run_date,
        candidate_cache_path=candidate_cache_path,
    )
    paths = write_cache_write_pilot_result_review_gate_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-cache-write-pilot-result-review-gate: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-cache-write-pilot-result-review-gate: "
        "source_only=true result_review_gate_only=true pilot_has_run=false raw_ohlcv_emitted=false tiingo_api_call_executed=false provider_live_access_executed=false live_http_executed=false cache_write_executed=false actual_refresh_import_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-actual-import-readiness-boundary")
def weekly_candidate_brief_actual_import_readiness_boundary_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    candidate_cache_path: str = typer.Option(DEFAULT_CANDIDATE_CACHE_PATH, "--candidate-cache-path"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    if fmt not in {"markdown", "json"}:
        typer.echo(
            "weekly-candidate-brief-actual-import-readiness-boundary: --format must be markdown or json",
            err=True,
        )
        raise typer.Exit(2)
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    markdown_text, json_payload = build_actual_import_readiness_boundary_report(
        report_date=run_date,
        candidate_cache_path=candidate_cache_path,
    )
    paths = write_actual_import_readiness_boundary_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=markdown_text,
        json_payload=json_payload,
    )
    if fmt == "json":
        typer.echo(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(markdown_text)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-actual-import-readiness-boundary: {key}={p}", err=True)
    typer.echo(
        "weekly-candidate-brief-actual-import-readiness-boundary: "
        "source_only=true actual_import_boundary_only=true cache_write_executed=false actual_refresh_import_executed=false manual_actual_import_executed=false trading_action_executed=false raw_ohlcv_persisted=false tiingo_api_call_executed=false provider_live_access_executed=false live_http_executed=false",
        err=True,
    )
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-manual-import-v35")
def weekly_candidate_brief_manual_import_v35_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    targets: str = typer.Option("5802,6645,285A,5803", "--targets"),
    input_path: Optional[str] = typer.Option(
        None,
        "--input-path",
        help="manual_jp_bars.csv path (default: dropzone).",
    ),
    execute_import: bool = typer.Option(
        False,
        "--execute-import",
        help="Execute gated cache import (requires approval phrase in session).",
    ),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
) -> None:
    run_date = report_date or today_jst_iso()
    dz = Path.home() / "Downloads" / "invest-alpha-os-manual-data-dropzone"
    csv_path = Path(input_path).expanduser() if input_path else dz / "manual_jp_bars.csv"
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    backup_root = OUTPUTS_DIR / "manual_data" / "rollback_snapshots"
    working_dir = out_root / "latest" / "v35_import_work"
    working_dir.mkdir(parents=True, exist_ok=True)
    result = run_manual_import_v35(
        report_date=run_date,
        csv_path=csv_path,
        targets_csv=targets,
        repo_root=ROOT_DIR,
        backup_root=backup_root,
        working_dir=working_dir,
        env=dict(os.environ),
        execute_import=execute_import,
    )
    paths = write_manual_import_v35_outputs(out_dir=out_root, report_date=run_date, result=result)
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-manual-import-v35: {key}={p}")
    typer.echo(
        f"weekly-candidate-brief-manual-import-v35: pre_import_ready={result.pre_import.get('ready_for_import')}"
    )
    typer.echo(
        "weekly-candidate-brief-manual-import-v35: "
        f"actual_import_executed={result.execute_json.get('actual_import_executed')}"
    )
    if sync_github_reports_repo and reports_repo_path:
        sync_paths = sync_manual_import_v35_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            report_date=run_date,
            result=result,
        )
        for key, p in sync_paths.items():
            typer.echo(f"weekly-candidate-brief-manual-import-v35: {key}={p}")
    if execute_import and not result.execute_json.get("actual_import_executed"):
        raise typer.Exit(2)
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-post-contract-ohlcv-structural-v32")
def weekly_candidate_brief_post_contract_ohlcv_structural_v32_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    targets_csv: str = typer.Option("5802,6645,285A,5803", "--targets-csv"),
    reports_latest_dir: Optional[str] = typer.Option(
        None,
        "--reports-latest-dir",
        help="Path to reports-private latest/ (default: outputs/chatgpt_context/latest).",
    ),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    latest_dir = Path(reports_latest_dir) if reports_latest_dir else out_root / "latest"
    result = build_post_contract_structural_v32(
        report_date=run_date,
        repo_root=ROOT_DIR,
        reports_latest_dir=latest_dir,
        targets_csv=targets_csv,
    )
    paths = write_post_contract_structural_v32_outputs(
        out_dir=out_root,
        report_date=run_date,
        result=result,
    )
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-post-contract-ohlcv-structural-v32: {key}={p}")
    typer.echo(
        "weekly-candidate-brief-post-contract-ohlcv-structural-v32: "
        f"discovery_verdict={result.discovery_json.get('discovery_verdict')}"
    )
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-post-contract-ohlcv-structural-v32: --reports-repo-path required",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_post_contract_structural_v32_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            report_date=run_date,
            result=result,
        )
        for key, p in sync_paths.items():
            typer.echo(f"weekly-candidate-brief-post-contract-ohlcv-structural-v32: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-manual-csv-discover")
def weekly_candidate_brief_manual_csv_discover_command(
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    discovery = build_manual_csv_discovery(report_date=run_date, repo_root=ROOT_DIR)
    context_md_text = "# Manual CSV Discovery Report\n"
    context_payload: dict[str, Any] = {"report_date": run_date, "source": "manual_csv_discovery"}
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload,
        write_latest=write_latest,
        write_archive=write_archive,
        manual_csv_discovery_markdown=discovery.markdown_text,
        manual_csv_discovery_json_payload=discovery.json_payload,
    )
    for key, p in paths.items():
        if "manual_csv_discovery" in key:
            typer.echo(f"weekly-candidate-brief-manual-csv-discover: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-manual-csv-discover: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload,
            manual_csv_discovery_markdown=discovery.markdown_text,
            manual_csv_discovery_json_payload=discovery.json_payload,
        )
        for key, p in sync_paths.items():
            if "manual_csv_discovery" in key:
                typer.echo(f"weekly-candidate-brief-manual-csv-discover: {key}={p}")
    raise typer.Exit(0 if discovery.json_payload.get("safe_to_validate") else 1)


@app.command("weekly-candidate-brief-manual-csv-export-request")
def weekly_candidate_brief_manual_csv_export_request_command(
    targets: str = typer.Option("5802,6645,5801,285A,5803", "--targets", help="Comma-separated JP tickers."),
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    request = build_manual_csv_export_request(targets_csv=targets, report_date=run_date)
    context_md_text = "# Manual CSV Export Request Report\n"
    context_payload: dict[str, Any] = {"report_date": run_date, "source": "manual_csv_export_request"}
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload,
        write_latest=write_latest,
        write_archive=write_archive,
        manual_csv_export_request_markdown=request.markdown_text,
        manual_csv_export_request_json_payload=request.json_payload,
    )
    for key, p in paths.items():
        if "manual_csv_export_request" in key:
            typer.echo(f"weekly-candidate-brief-manual-csv-export-request: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-manual-csv-export-request: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload,
            manual_csv_export_request_markdown=request.markdown_text,
            manual_csv_export_request_json_payload=request.json_payload,
        )
        for key, p in sync_paths.items():
            if "manual_csv_export_request" in key:
                typer.echo(f"weekly-candidate-brief-manual-csv-export-request: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-manual-data-export-package")
def weekly_candidate_brief_manual_data_export_package_command(
    targets: str = typer.Option("5802,6645,5801,285A,5803", "--targets", help="Comma-separated JP tickers."),
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    package = build_manual_data_export_package(targets_csv=targets, report_date=run_date)
    context_md_text = "# Manual Data Export Package Report\n"
    context_payload: dict[str, Any] = {"report_date": run_date, "source": "manual_data_export_package"}
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload,
        write_latest=write_latest,
        write_archive=write_archive,
        manual_data_export_package_markdown=package.markdown_text,
        manual_data_export_package_json_payload=package.json_payload,
        manual_jp_bars_template_csv_text=package.template_csv_text,
    )
    for key, p in paths.items():
        if "manual_data_export_package" in key or "manual_jp_bars_template" in key:
            typer.echo(f"weekly-candidate-brief-manual-data-export-package: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-manual-data-export-package: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload,
            manual_data_export_package_markdown=package.markdown_text,
            manual_data_export_package_json_payload=package.json_payload,
            manual_jp_bars_template_csv_text=package.template_csv_text,
        )
        for key, p in sync_paths.items():
            if "manual_data_export_package" in key or "manual_jp_bars_template" in key:
                typer.echo(f"weekly-candidate-brief-manual-data-export-package: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-manual-data-import-flow")
def weekly_candidate_brief_manual_data_import_flow_command(
    input_path: str = typer.Option(..., "--input-path", help="Path to manual JP bars file (csv/tsv/txt/xlsx)."),
    targets: str = typer.Option("5802,6645,5801,285A,5803", "--targets", help="Comma-separated JP tickers."),
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    provider: str = typer.Option("manual_csv", "--provider", help="Import provider (must be manual_csv)."),
    scope: str = typer.Option("JP_ONLY", "--scope", help="Execution scope (must be JP_ONLY)."),
    broker_format: str = typer.Option(
        "auto",
        "--broker-format",
        help="Broker format: generic_ohlcv, moomoo_jp, sbi_jp, rakuten_jp, manual_csv, auto.",
    ),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    execute_import: bool = typer.Option(
        False,
        "--execute-import",
        help="Execute gated manual CSV cache import when all explicit gates are set.",
    ),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    working_dir = out_root / "latest"
    working_dir.mkdir(parents=True, exist_ok=True)
    flow = build_manual_data_import_flow(
        input_path=Path(input_path),
        targets_csv=targets,
        report_date=run_date,
        provider=provider,
        scope=scope,
        broker_format=broker_format,
        execute_import=execute_import,
        env=dict(os.environ),
        repo_root=ROOT_DIR,
        working_dir=working_dir,
    )
    context_md_text = "# Manual Data Import Flow Report\n"
    context_payload: dict[str, Any] = {"report_date": run_date, "source": "manual_data_import_flow"}
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload,
        write_latest=write_latest,
        write_archive=write_archive,
        manual_data_import_flow_markdown=flow.markdown_text,
        manual_data_import_flow_json_payload=flow.json_payload,
    )
    for key, p in paths.items():
        if "manual_data_import_flow" in key:
            typer.echo(f"weekly-candidate-brief-manual-data-import-flow: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-manual-data-import-flow: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload,
            manual_data_import_flow_markdown=flow.markdown_text,
            manual_data_import_flow_json_payload=flow.json_payload,
        )
        for key, p in sync_paths.items():
            if "manual_data_import_flow" in key:
                typer.echo(f"weekly-candidate-brief-manual-data-import-flow: {key}={p}")
    overall = str(flow.json_payload.get("overall_status", ""))
    if overall in {"normalization_failed", "validation_failed", "path_refused", "pii_guard_failed"}:
        raise typer.Exit(2)
    if execute_import and not flow.json_payload.get("actual_import_executed"):
        raise typer.Exit(2)
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-manual-csv-import-flow")
def weekly_candidate_brief_manual_csv_import_flow_command(
    csv_path: str = typer.Option(..., "--csv-path", help="Path to manual JP bars CSV (must not be git-tracked)."),
    targets: str = typer.Option("5802,6645,5801,285A,5803", "--targets", help="Comma-separated JP tickers."),
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    provider: str = typer.Option("manual_csv", "--provider", help="Import provider (must be manual_csv)."),
    scope: str = typer.Option("JP_ONLY", "--scope", help="Execution scope (must be JP_ONLY)."),
    broker_format: str = typer.Option(
        "generic_ohlcv",
        "--broker-format",
        help="Broker CSV format: generic_ohlcv, moomoo_jp, sbi_jp, rakuten_jp, manual_csv, auto.",
    ),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    execute_import: bool = typer.Option(
        False,
        "--execute-import",
        help="Execute gated manual CSV cache import when all explicit gates are set.",
    ),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    working_dir = out_root / "latest"
    working_dir.mkdir(parents=True, exist_ok=True)
    flow = build_manual_csv_import_flow(
        csv_path=Path(csv_path),
        targets_csv=targets,
        report_date=run_date,
        provider=provider,
        scope=scope,
        broker_format=broker_format,
        execute_import=execute_import,
        env=dict(os.environ),
        repo_root=ROOT_DIR,
        working_dir=working_dir,
    )
    context_md_text = "# Manual CSV Import Flow Report\n"
    context_payload: dict[str, Any] = {"report_date": run_date, "source": "manual_csv_import_flow"}
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload,
        write_latest=write_latest,
        write_archive=write_archive,
        manual_csv_import_flow_markdown=flow.markdown_text,
        manual_csv_import_flow_json_payload=flow.json_payload,
    )
    for key, p in paths.items():
        if "manual_csv_import_flow" in key:
            typer.echo(f"weekly-candidate-brief-manual-csv-import-flow: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-manual-csv-import-flow: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload,
            manual_csv_import_flow_markdown=flow.markdown_text,
            manual_csv_import_flow_json_payload=flow.json_payload,
        )
        for key, p in sync_paths.items():
            if "manual_csv_import_flow" in key:
                typer.echo(f"weekly-candidate-brief-manual-csv-import-flow: {key}={p}")
    overall = str(flow.json_payload.get("overall_status", ""))
    if overall in {"pii_guard_failed", "validation_failed", "normalization_failed", "path_refused"}:
        raise typer.Exit(2)
    if execute_import and not flow.json_payload.get("actual_import_executed"):
        raise typer.Exit(2)
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-manual-data-normalize")
def weekly_candidate_brief_manual_data_normalize_command(
    input_path: str = typer.Option(..., "--input-path", help="Path to manual JP bars file (csv/tsv/txt/xlsx)."),
    broker_format: str = typer.Option(
        "generic_ohlcv",
        "--broker-format",
        help="Broker format: generic_ohlcv, moomoo_jp, sbi_jp, rakuten_jp, manual_csv, auto.",
    ),
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    try:
        resolved = resolve_manual_data_path(input_path, repo_root=ROOT_DIR)
    except ManualCsvPathError as exc:
        typer.echo(f"weekly-candidate-brief-manual-data-normalize: {exc}", err=True)
        raise typer.Exit(2) from exc
    norm_out = out_root / "latest" / "manual_data_normalized_working.csv"
    normalization = build_manual_data_normalization(
        input_path=resolved,
        report_date=run_date,
        broker_format=broker_format,
        output_path=norm_out,
    )
    context_md_text = "# Manual Data Normalization Report\n"
    context_payload: dict[str, Any] = {"report_date": run_date, "source": "manual_data_normalization"}
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload,
        write_latest=write_latest,
        write_archive=write_archive,
        manual_data_normalization_markdown=normalization.markdown_text,
        manual_data_normalization_json_payload=normalization.json_payload,
    )
    for key, p in paths.items():
        if "manual_data_normalization" in key:
            typer.echo(f"weekly-candidate-brief-manual-data-normalize: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-manual-data-normalize: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload,
            manual_data_normalization_markdown=normalization.markdown_text,
            manual_data_normalization_json_payload=normalization.json_payload,
        )
        for key, p in sync_paths.items():
            if "manual_data_normalization" in key:
                typer.echo(f"weekly-candidate-brief-manual-data-normalize: {key}={p}")
    if not normalization.json_payload.get("ready_for_validation"):
        raise typer.Exit(2)
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-manual-csv-normalize")
def weekly_candidate_brief_manual_csv_normalize_command(
    csv_path: str = typer.Option(..., "--csv-path", help="Path to manual JP bars CSV (must not be git-tracked)."),
    broker_format: str = typer.Option(
        "generic_ohlcv",
        "--broker-format",
        help="Broker CSV format: generic_ohlcv, moomoo_jp, sbi_jp, rakuten_jp, manual_csv, auto.",
    ),
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    try:
        resolved_csv = resolve_manual_csv_path(csv_path, repo_root=ROOT_DIR)
    except ManualCsvPathError as exc:
        typer.echo(f"weekly-candidate-brief-manual-csv-normalize: {exc}", err=True)
        raise typer.Exit(2) from exc
    norm_out = out_root / "latest" / "manual_csv_normalized_working.csv"
    normalization = build_manual_csv_normalization(
        csv_path=resolved_csv,
        report_date=run_date,
        broker_format=broker_format,
        output_path=norm_out,
    )
    context_md_text = "# Manual CSV Normalization Report\n"
    context_payload: dict[str, Any] = {"report_date": run_date, "source": "manual_csv_normalization"}
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload,
        write_latest=write_latest,
        write_archive=write_archive,
        manual_csv_normalization_markdown=normalization.markdown_text,
        manual_csv_normalization_json_payload=normalization.json_payload,
    )
    for key, p in paths.items():
        if "manual_csv_normalization" in key:
            typer.echo(f"weekly-candidate-brief-manual-csv-normalize: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-manual-csv-normalize: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload,
            manual_csv_normalization_markdown=normalization.markdown_text,
            manual_csv_normalization_json_payload=normalization.json_payload,
        )
        for key, p in sync_paths.items():
            if "manual_csv_normalization" in key:
                typer.echo(f"weekly-candidate-brief-manual-csv-normalize: {key}={p}")
    if not normalization.json_payload.get("ready_for_validation"):
        raise typer.Exit(2)
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-manual-csv-template")
def weekly_candidate_brief_manual_csv_template_command(
    targets: str = typer.Option("5802,6645,5801,285A,5803", "--targets", help="Comma-separated JP tickers."),
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    template = build_manual_csv_template(targets_csv=targets, report_date=run_date)
    context_md_text = "# Manual CSV Template Export\n"
    context_payload: dict[str, Any] = {"report_date": run_date, "source": "manual_csv_template"}
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload,
        write_latest=write_latest,
        write_archive=write_archive,
        manual_csv_template_markdown=template.markdown_text,
        manual_csv_template_csv_text=template.csv_text,
    )
    for key, p in paths.items():
        if "manual_csv_template" in key:
            typer.echo(f"weekly-candidate-brief-manual-csv-template: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-manual-csv-template: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload,
            manual_csv_template_markdown=template.markdown_text,
            manual_csv_template_csv_text=template.csv_text,
        )
        for key, p in sync_paths.items():
            if "manual_csv_template" in key:
                typer.echo(f"weekly-candidate-brief-manual-csv-template: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-cache-refresh-postcheck")
def weekly_candidate_brief_cache_refresh_postcheck_command(
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label (default: today JST)."),
    before_context_json: str = typer.Option(..., "--before-context-json", help="Before context pack JSON path."),
    after_context_json: Optional[str] = typer.Option(
        None, "--after-context-json", help="After context pack JSON path (default latest context pack JSON)."
    ),
    before_readiness_json: str = typer.Option(..., "--before-readiness-json", help="Before readiness JSON path."),
    after_readiness_json: Optional[str] = typer.Option(
        None, "--after-readiness-json", help="After readiness JSON path (default latest readiness JSON)."
    ),
    before_plan_json: Optional[str] = typer.Option(None, "--before-plan-json", help="Before execution plan JSON path."),
    after_plan_json: Optional[str] = typer.Option(
        None, "--after-plan-json", help="After execution plan JSON path (default latest execution plan JSON)."
    ),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/chatgpt_context)."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest", help="Write latest outputs."),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive", help="Write archive outputs."),
    sync_github_reports_repo: bool = typer.Option(
        False, "--sync-github-reports-repo", help="Copy outputs into reports repo clone path."
    ),
    reports_repo_path: Optional[str] = typer.Option(
        None, "--reports-repo-path", help="Path to invest-alpha-os-reports-private local clone."
    ),
    env_file: Optional[str] = typer.Option(
        None,
        "--env-file",
        help="Local env file path (J-Quants allowlisted keys only; values not printed).",
    ),
) -> None:
    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    env_file_meta = _apply_optional_jquants_env_file(env_file)
    _echo_env_file_meta("weekly-candidate-brief-cache-refresh-postcheck", env_file_meta)
    after_context_path = Path(after_context_json) if after_context_json else out_root / "latest" / "chatgpt_invest_context_pack.json"
    after_readiness_path = Path(after_readiness_json) if after_readiness_json else out_root / "latest" / "cache_refresh_readiness.json"
    after_plan_path = Path(after_plan_json) if after_plan_json else out_root / "latest" / "cache_refresh_execution_plan.json"

    def _load_json(path: Path) -> dict[str, Any]:
        if not path.is_file():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return raw if isinstance(raw, dict) else {}

    post = build_cache_refresh_postcheck(
        report_date=run_date,
        before_context_json_payload=_load_json(Path(before_context_json)),
        after_context_json_payload=_load_json(after_context_path),
        before_readiness_json_payload=_load_json(Path(before_readiness_json)),
        after_readiness_json_payload=_load_json(after_readiness_path),
        before_plan_json_payload=_load_json(Path(before_plan_json)) if before_plan_json else {},
        after_plan_json_payload=_load_json(after_plan_path),
    )
    context_md_path = out_root / "latest" / "chatgpt_invest_context_pack.md"
    context_json_path = out_root / "latest" / "chatgpt_invest_context_pack.json"
    context_md_text = (
        context_md_path.read_text(encoding="utf-8")
        if context_md_path.is_file()
        else "# ChatGPT投資対話用Context Pack\n"
    )
    context_payload = _load_json(context_json_path)
    paths = write_context_pack_outputs(
        out_dir=out_root,
        report_date=run_date,
        markdown_text=context_md_text,
        json_payload=context_payload or {"report_date": run_date, "source": "cache_refresh_postcheck"},
        write_latest=write_latest,
        write_archive=write_archive,
        cache_refresh_postcheck_markdown=post.markdown_text,
        cache_refresh_postcheck_json_payload=post.json_payload,
    )
    for key, p in paths.items():
        if "cache_refresh_postcheck" in key:
            typer.echo(f"weekly-candidate-brief-cache-refresh-postcheck: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-cache-refresh-postcheck: --reports-repo-path is required with --sync-github-reports-repo",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            markdown_text=context_md_text,
            json_payload=context_payload or {"report_date": run_date, "source": "cache_refresh_postcheck"},
            cache_refresh_postcheck_markdown=post.markdown_text,
            cache_refresh_postcheck_json_payload=post.json_payload,
        )
        for key, p in sync_paths.items():
            if "cache_refresh_postcheck" in key:
                typer.echo(f"weekly-candidate-brief-cache-refresh-postcheck: {key}={p}")
    raise typer.Exit(0)


@validate_app.command("us-forward-returns")
def validate_us_forward_returns_command(
    observation_log: Optional[str] = typer.Option(
        None,
        "--observation-log",
        help="Path to observation_log.jsonl (default: outputs/observation_log/observation_log.jsonl).",
    ),
    cache_dir: Optional[str] = typer.Option(
        None,
        "--cache-dir",
        help="US daily bars cache directory (default: outputs/market_data/us_daily_bars).",
    ),
    horizons: Optional[str] = typer.Option(
        "5,20,60",
        "--horizons",
        help="Comma-separated session horizons (default: 5,20,60).",
    ),
    reference_date: Optional[str] = typer.Option(
        None,
        "--reference-date",
        help="Optional ISO date; skip observations after this date.",
    ),
    backtest_within_cache: bool = typer.Option(
        False,
        "--backtest-within-cache",
        help="Exploratory: shift event to last in-cache window when future bars missing.",
    ),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    """P5: cache-only forward returns from US observation_log rows (observation only)."""

    fmt_norm = fmt.strip().lower()
    obs_path = (
        Path(observation_log)
        if observation_log
        else OUTPUTS_DIR / "observation_log" / "observation_log.jsonl"
    )
    cache_path = (
        Path(cache_dir) if cache_dir else OUTPUTS_DIR / "market_data" / "us_daily_bars"
    )
    try:
        hz = parse_positive_horizons(horizons or "")
    except ValueError as exc:
        typer.echo(f"validate us-forward-returns: {exc}", err=True)
        raise typer.Exit(2) from exc
    ref: date | None = None
    if reference_date:
        try:
            ref = date.fromisoformat(reference_date.strip()[:10])
        except ValueError as exc:
            typer.echo("validate us-forward-returns: invalid --reference-date", err=True)
            raise typer.Exit(2) from exc
    try:
        report = compute_us_forward_returns(
            observation_path=obs_path,
            cache_dir=cache_path,
            horizons=hz,
            reference_date=ref,
            backtest_within_cache=backtest_within_cache,
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from exc
    if fmt_norm == "json":
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        typer.echo(format_us_forward_return_markdown(report))


@validate_app.command("peer-sync")
def validate_peer_sync_command(
    peer_map: Optional[str] = typer.Option(
        None,
        "--peer-map",
        help="Path to peer_map.yaml (default: config/peer_map.yaml).",
    ),
    window_days: int = typer.Option(
        20,
        "--window-days",
        help="Trailing sessions for spread/correlation (default: 20).",
    ),
    divergence_threshold: float = typer.Option(
        0.05,
        "--divergence-threshold",
        help="Absolute return spread threshold for divergence (default: 0.05).",
    ),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    """Cache-only peer sync check from config/peer_map.yaml (observation only)."""

    fmt_norm = fmt.strip().lower()
    pmap = Path(peer_map) if peer_map else CONFIG_DIR / "peer_map.yaml"
    report = build_peer_sync_cache_only_report(
        path_base=ROOT_DIR,
        peer_map_path=pmap,
        window_days=window_days,
        divergence_threshold=divergence_threshold,
    )
    if fmt_norm == "json":
        typer.echo(format_peer_sync_cache_only_json(report))
    elif fmt_norm == "markdown":
        typer.echo(format_peer_sync_cache_only_markdown(report))
    else:
        typer.echo("validate peer-sync: --format must be markdown or json", err=True)
        raise typer.Exit(2)


@validate_app.command("ops-smoke")
def validate_ops_smoke_command(
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Exit 2 if any check status is fail (warn is ok).",
    ),
) -> None:
    """Read-only consolidated ops smoke (manifest, peer_sync, portfolio, observation health)."""

    fmt_norm = fmt.strip().lower()
    report = build_ops_smoke_report(path_base=ROOT_DIR)
    if fmt_norm == "json":
        typer.echo(format_ops_smoke_json(report))
    elif fmt_norm == "markdown":
        typer.echo(format_ops_smoke_markdown(report))
    else:
        typer.echo("validate ops-smoke: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    if strict and not report.all_ok:
        typer.echo(format_strict_taxonomy_stderr_line(report), err=True)
        raise typer.Exit(2)


@validate_app.command("post-refresh-smoke")
def validate_post_refresh_smoke_command(
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    """Read-only post-P10 refresh smoke aggregate (docs/163)."""

    from invis_alpha_os.product.post_p10_refresh_smoke import (
        build_post_p10_refresh_smoke_summary,
        format_post_p10_refresh_smoke_markdown,
    )

    fmt_norm = fmt.strip().lower()
    report = build_post_p10_refresh_smoke_summary(path_base=ROOT_DIR)
    if fmt_norm == "json":
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    elif fmt_norm == "markdown":
        typer.echo(format_post_p10_refresh_smoke_markdown(report))
    else:
        typer.echo("validate post-refresh-smoke: --format must be markdown or json", err=True)
        raise typer.Exit(2)


@validate_app.command("forward-p3-status")
def validate_forward_p3_status_command(
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    """Read-only US + peer_sync forward progress toward P3 usable (no HTTP)."""

    from invis_alpha_os.product.forward_p3_status import (
        build_forward_p3_status_bundle,
        format_forward_p3_status_markdown,
    )

    fmt_norm = fmt.strip().lower()
    report = build_forward_p3_status_bundle(path_base=ROOT_DIR)
    if fmt_norm == "json":
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    elif fmt_norm == "markdown":
        typer.echo(format_forward_p3_status_markdown(report))
    else:
        typer.echo("validate forward-p3-status: --format must be markdown or json", err=True)
        raise typer.Exit(2)


@validate_app.command("p3-horizon-timeline")
def validate_p3_horizon_timeline_command(
    fmt: str = typer.Option("json", "--format", help="json or markdown."),
    horizon_rows: int = typer.Option(
        100,
        "--horizon-rows",
        help="Max timeline_rows in export (default 100; min 16).",
    ),
) -> None:
    """Read-only JSON export of P3 horizon timeline_rows (cache maturation path)."""

    from invis_alpha_os.product.p3_path_to_usable import (
        build_p3_horizon_timeline_export,
        format_p3_horizon_timeline_export_markdown,
    )

    fmt_norm = fmt.strip().lower()
    if horizon_rows < 1:
        typer.echo("validate p3-horizon-timeline: --horizon-rows must be >= 1", err=True)
        raise typer.Exit(2)
    report = build_p3_horizon_timeline_export(
        path_base=ROOT_DIR,
        horizon_timeline_max_rows=horizon_rows,
    )
    if fmt_norm == "json":
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    elif fmt_norm == "markdown":
        typer.echo(format_p3_horizon_timeline_export_markdown(report))
    else:
        typer.echo("validate p3-horizon-timeline: --format must be json or markdown", err=True)
        raise typer.Exit(2)


@validate_app.command("p3-path-to-usable")
def validate_p3_path_to_usable_command(
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
    horizon_rows: int = typer.Option(
        50,
        "--horizon-rows",
        help="Max horizon timeline_rows in export (default 50; min 16).",
    ),
) -> None:
    """Read-only P3 path A/B summary + horizon timeline (lighter than forward-p3-status)."""

    from invis_alpha_os.product.p3_path_to_usable import (
        build_p3_path_to_usable_bundle,
        format_p3_path_to_usable_bundle_markdown,
    )

    fmt_norm = fmt.strip().lower()
    if horizon_rows < 1:
        typer.echo("validate p3-path-to-usable: --horizon-rows must be >= 1", err=True)
        raise typer.Exit(2)
    report = build_p3_path_to_usable_bundle(
        path_base=ROOT_DIR,
        horizon_timeline_max_rows=horizon_rows,
    )
    if fmt_norm == "json":
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    elif fmt_norm == "markdown":
        typer.echo(format_p3_path_to_usable_bundle_markdown(report))
    else:
        typer.echo("validate p3-path-to-usable: --format must be markdown or json", err=True)
        raise typer.Exit(2)


@validate_app.command("peer-sync-forward-returns")
def validate_peer_sync_forward_returns_command(
    observation_log: Optional[str] = typer.Option(
        None,
        "--observation-log",
        help="Path to observation_log.jsonl (default: outputs/observation_log/observation_log.jsonl).",
    ),
    horizons: Optional[str] = typer.Option(
        "5,20,60",
        "--horizons",
        help="Comma-separated session horizons (default: 5,20,60).",
    ),
    reference_date: Optional[str] = typer.Option(
        None,
        "--reference-date",
        help="Optional ISO date; skip observations after this date.",
    ),
    backtest_within_cache: bool = typer.Option(
        False,
        "--backtest-within-cache",
        help="Exploratory: shift event to last in-cache window when future bars missing.",
    ),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    """Read-only: join peer_sync log rows to anchor forward returns (cache-only)."""

    fmt_norm = fmt.strip().lower()
    obs_path = (
        Path(observation_log)
        if observation_log
        else OUTPUTS_DIR / "observation_log" / "observation_log.jsonl"
    )
    try:
        hz = parse_positive_horizons(horizons or "")
    except ValueError as exc:
        typer.echo(f"validate peer-sync-forward-returns: {exc}", err=True)
        raise typer.Exit(2) from exc
    ref: date | None = None
    if reference_date:
        try:
            ref = date.fromisoformat(reference_date.strip()[:10])
        except ValueError as exc:
            typer.echo("validate peer-sync-forward-returns: invalid --reference-date", err=True)
            raise typer.Exit(2) from exc
    try:
        report = compute_peer_sync_forward_join(
            observation_path=obs_path,
            horizons=hz,
            reference_date=ref,
            backtest_within_cache=backtest_within_cache,
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from exc
    if fmt_norm == "json":
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        typer.echo(format_peer_sync_forward_markdown(report))


@validate_app.command("jp-peer-sync-readiness")
def validate_jp_peer_sync_readiness_command(
    peer_map: Optional[str] = typer.Option(
        None,
        "--peer-map",
        help="Path to peer_map.yaml (default: config/peer_map.yaml).",
    ),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    """Read-only: JP peer_map edges vs J-Quants cache on disk (no HTTP)."""

    fmt_norm = fmt.strip().lower()
    pmap = Path(peer_map) if peer_map else CONFIG_DIR / "peer_map.yaml"
    report = build_jp_peer_sync_readiness_report(
        path_base=ROOT_DIR,
        peer_map_path=pmap,
    )
    if fmt_norm == "json":
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    elif fmt_norm == "markdown":
        typer.echo(format_jp_peer_sync_readiness_markdown(report))
    else:
        typer.echo("validate jp-peer-sync-readiness: --format must be markdown or json", err=True)
        raise typer.Exit(2)


@app.command("us-universe-expansion-plan")
def us_universe_expansion_plan_command(
    config: Optional[str] = typer.Option(
        None,
        "--config",
        help="Expansion YAML (default: config/us_universe_expansion_30.yaml).",
    ),
    tier: Optional[str] = typer.Option(
        None,
        "--tier",
        help="Filter targets by tier (e.g. 1).",
    ),
    missing_only: bool = typer.Option(
        False,
        "--missing-only",
        help="Only list targets without a cache file.",
    ),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    """P6: read-only US 30+ expansion plan vs on-disk cache (no HTTP)."""

    fmt_norm = fmt.strip().lower()
    try:
        report = build_us_universe_expansion_report(
            path_base=ROOT_DIR,
            config_path=Path(config) if config else None,
            tier=tier,
            missing_only=missing_only,
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from exc
    if fmt_norm == "json":
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        typer.echo(format_us_universe_expansion_markdown(report))


@app.command("us-cache-expansion-report")
def us_cache_expansion_report_command(
    limit: int = typer.Option(25, "--limit", min=1, help="Max discovery candidates to list."),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    """P3/US: read-only watchlist vs cache gaps + discovery symbols without cache files."""

    fmt_norm = fmt.strip().lower()
    report = us_cache_expansion_report(path_base=ROOT_DIR, discover_limit=limit)
    if fmt_norm == "json":
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
        return
    lines = [
        "# US cache expansion report (read-only)",
        "",
        f"- watchlist: {report['watchlist_count']}",
        f"- cache files: {report['cache_file_count']}",
        f"- missing on watchlist: {', '.join(report['missing_cache_on_watchlist']) or '(none)'}",
        f"- discovery candidates: {report['discovery_candidates']}",
        "",
        "## Discovery symbols without cache file",
    ]
    for sym in report.get("discovery_without_cache_file") or []:
        lines.append(f"- {sym}")
    lines.append("")
    typer.echo("\n".join(lines))


@app.command("signals")
def signals_command(
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="No live HTTP. synthetic/cache/cache-only use local or deterministic data only.",
    ),
    source: str = typer.Option(
        "synthetic",
        "--source",
        help="synthetic | cache | cache-only — cache prefers local JSON; cache-only ranks cached tickers only.",
    ),
    no_synthetic_fallback: bool = typer.Option(
        False,
        "--no-synthetic-fallback",
        help="With --source cache, skip tickers without cache (same as --source cache-only).",
    ),
    code: Optional[str] = typer.Option(None, "--code", help="Single ticker (requires --bars-file)."),
    bars_file: Optional[str] = typer.Option(
        None,
        "--bars-file",
        help="Path to JSON array of one OHLCV series (open,high,low,close,volume,date).",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        min=1,
        help="Process only the first N JP watchlist tickers (dry-run).",
    ),
    fmt: str = typer.Option(
        "json",
        "--format",
        help="Output format: json (default) | markdown — human-readable table.",
    ),
    us_cache_preview: bool = typer.Option(
        False,
        "--us-cache-preview",
        help="Include US cache-only preview (read-only; default off).",
    ),
) -> None:
    """Observation-only JP momentum-style flags from daily bars (Main E MVP). Not trading advice."""

    src_norm = source.strip().lower().replace("_", "-")
    if src_norm == "cacheonly":
        src_norm = "cache-only"

    if no_synthetic_fallback:
        if src_norm == "cache":
            src_norm = "cache-only"
        elif src_norm != "cache-only":
            typer.echo(
                "signals: --no-synthetic-fallback is only valid with --source cache or cache-only",
                err=True,
            )
            raise typer.Exit(2)

    if src_norm not in ("synthetic", "cache", "cache-only"):
        typer.echo("signals: --source must be synthetic, cache, or cache-only", err=True)
        raise typer.Exit(2)

    if bars_file:
        if not code:
            typer.echo("signals: --bars-file requires --code", err=True)
            raise typer.Exit(2)
        try:
            label = normalize_generic_bars_file_symbol_label(code)
        except ValueError:
            typer.echo("signals: invalid --code for bars-file symbol label", err=True)
            raise typer.Exit(2)
        try:
            bars = load_bars_json_file(Path(bars_file))
        except (OSError, ValueError, json.JSONDecodeError) as e:
            typer.echo(f"signals: failed to load bars file: {e}", err=True)
            raise typer.Exit(2) from e
        one = analyze_bars_for_code(label, bars)
        _file_veto_engine = VetoEngine(rules=load_yaml(CONFIG_DIR / "veto_rules.yaml"))

        ranked_item: list[dict[str, Any]] = []
        if one:
            r = momentum_row_public_dict(one, bars_source="file")
            r["veto_result"] = build_momentum_veto_result(one, _file_veto_engine)
            ranked_item.append(r)
        payload: dict[str, Any] = {
            "mode": "local_bars_file",
            "bars_data_source": "file",
            "observation_only": True,
            "veto_status": "ok",
            "ranked": ranked_item,
        }
        if us_cache_preview:
            payload["us_cache_preview"] = build_us_cache_opt_in_preview()
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        raise typer.Exit(0)

    if src_norm == "synthetic" and not dry_run:
        typer.echo(
            "signals: --no-dry-run is not supported for --source synthetic; "
            "use --source cache (local files) or --bars-file + --code.",
            err=True,
        )
        raise typer.Exit(2)

    tickers = load_jp_watchlist_tickers()
    if limit is not None:
        tickers = tickers[:limit]
    mapping, srcmap, skipped_no_cache = _jp_momentum_bar_mapping(src_norm, tickers)
    ranked = build_momentum_signals(mapping)
    mode = "cache_only_dry_run" if src_norm == "cache-only" else (
        "synthetic_dry_run" if src_norm == "synthetic" else "cache_preferred_dry_run"
    )
    bars_label = "cache" if src_norm == "cache-only" else _bars_data_source_label(srcmap)

    veto_engine = VetoEngine(rules=load_yaml(CONFIG_DIR / "veto_rules.yaml"))

    ranked_rows = []
    for m in ranked:
        row = momentum_row_public_dict(m, bars_source=srcmap.get(m.code, "synthetic"))
        row["veto_result"] = build_momentum_veto_result(m, veto_engine)
        ranked_rows.append(row)

    out: dict[str, Any] = {
        "mode": mode,
        "bars_data_source": bars_label,
        "observation_only": True,
        "veto_status": "ok",
        "ranked": ranked_rows,
    }
    if src_norm == "cache-only":
        out["skipped_no_cache"] = len(skipped_no_cache)
        out["skipped_no_cache_codes"] = skipped_no_cache

    fmt_norm = fmt.strip().lower()
    if us_cache_preview:
        if fmt_norm == "markdown":
            typer.echo(append_us_cache_preview_section(_signals_markdown(out)))
        else:
            out["us_cache_preview"] = build_us_cache_opt_in_preview()
            typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
    elif fmt_norm == "markdown":
        typer.echo(_signals_markdown(out))
    else:
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))


@app.command("daily-email")
def daily_email(
    bundle_dir: str = typer.Option(
        ...,
        "--bundle-dir",
        help="Operator bundle directory (e.g. outputs/operator/daily_usage/YYYY-MM-DD).",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--send",
        help="Dry-run writes local previews only; --send requires CONFIRM_GMAIL_SEND=YES and GMAIL_REPORT_TO.",
    ),
    main_commit: Optional[str] = typer.Option(
        None,
        "--main-commit",
        help="Optional main SHA for email meta (not read from git automatically).",
    ),
) -> None:
    """Build daily observation email from operator bundle; Gmail send is gated."""

    bundle = Path(bundle_dir)
    if not bundle.is_dir():
        typer.echo(f"daily-email: bundle directory not found: {bundle}", err=True)
        raise typer.Exit(2)

    draft = build_daily_email_from_bundle(bundle, main_commit=main_commit)
    recipient = os.environ.get("GMAIL_REPORT_TO", "").strip()
    sender = resolve_gmail_sender(dry_run=dry_run, recipient=recipient)
    email_out = bundle / "email"
    to_list = [recipient] if recipient else ["recipient@example.com"]
    if dry_run:
        to_list = [recipient or "dry-run@local"]

    if not dry_run and not sender:
        typer.echo(
            "daily-email: gmail_failure_reason=gmail_sender_unconfigured "
            "(set GMAIL_REPORT_FROM or GMAIL_SELF_EMAIL)",
            err=True,
        )
        raise typer.Exit(2)

    message = build_mime_message(
        sender=sender or "me",
        to=to_list,
        subject=draft.subject,
        text_body=draft.text_body,
        html_body=draft.html_body,
        attachments=None,
    )
    preview_paths = write_email_previews(email_out, message=message)
    raw = encode_message_raw(message)
    (email_out / "email_raw.b64url.txt").write_text(raw, encoding="utf-8")

    typer.echo(f"daily-email: subject={draft.subject!r}")
    for key, path in preview_paths.items():
        typer.echo(f"daily-email: {key}={path}")

    if dry_run:
        typer.echo("daily-email: dry-run only (no Gmail API call)")
        raise typer.Exit(0)

    if not recipient:
        typer.echo("daily-email: GMAIL_REPORT_TO is required for --send", err=True)
        raise typer.Exit(2)
    allow_interactive_oauth = os.environ.get("GMAIL_ALLOW_INTERACTIVE_OAUTH", "").strip() == "YES"
    try:
        validate_gmail_send_gates(recipient=recipient)
    except GmailSendBlockedError as e:
        reason = classify_gmail_failure(e)
        typer.echo(f"daily-email: gmail_failure_reason={reason}", err=True)
        raise typer.Exit(2) from e
    if not credentials_configured():
        typer.echo("daily-email: gmail_failure_reason=gmail_oauth_required", err=True)
        raise typer.Exit(2)
    try:
        result = send_gmail_message(
            raw,
            allow_interactive_oauth=allow_interactive_oauth,
        )
    except (GmailSendBlockedError, GmailDeliveryError) as e:
        reason = classify_gmail_failure(e)
        typer.echo(f"daily-email: gmail_failure_reason={reason}", err=True)
        raise typer.Exit(2) from e
    except Exception as e:
        reason = classify_gmail_failure(e)
        typer.echo(f"daily-email: gmail_failure_reason={reason}", err=True)
        raise typer.Exit(2) from e
    msg_id = result.get("id", "") if isinstance(result, dict) else ""
    typer.echo(f"daily-email: sent message id={msg_id!r}")
    raise typer.Exit(0)


@app.command("discover-jp")
def discover_jp(
    fmt: str = typer.Option(
        "markdown",
        "--format",
        help="Output format: markdown or json.",
    ),
    limit: int = typer.Option(20, "--limit", help="Max ranked candidates to include."),
    universe_file: Optional[str] = typer.Option(
        None,
        "--universe-file",
        help="YAML universe spec (default: scan local jquants_daily_bars cache).",
    ),
) -> None:
    """JP universe discovery MVP — cache/fixture only; observation-only deep-dive candidates."""

    fmt_norm = fmt.strip().lower()
    if fmt_norm not in ("markdown", "json"):
        typer.echo("discover-jp: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    u_path = Path(universe_file) if universe_file else None
    if u_path is not None and not u_path.is_file():
        typer.echo(f"discover-jp: universe file not found: {u_path}", err=True)
        raise typer.Exit(2)
    try:
        result = scan_jp_universe(universe_file=u_path, limit=limit)
    except ValueError as e:
        typer.echo(f"discover-jp: {e}", err=True)
        raise typer.Exit(2) from e
    if fmt_norm == "json":
        typer.echo(json.dumps(format_jp_discovery_json(result), ensure_ascii=False, indent=2))
    else:
        typer.echo(format_jp_discovery_markdown(result))
    raise typer.Exit(0)


@app.command("discover-us")
def discover_us(
    fmt: str = typer.Option(
        "markdown",
        "--format",
        help="Output format: markdown or json.",
    ),
    limit: int = typer.Option(20, "--limit", help="Max ranked candidates to include."),
    universe_file: Optional[str] = typer.Option(
        None,
        "--universe-file",
        help="YAML universe spec (default: config/us_watchlist.yaml, fallback local us_daily_bars cache).",
    ),
) -> None:
    """US universe discovery MVP — cache-only; observation-only deep-dive candidates."""

    fmt_norm = fmt.strip().lower()
    if fmt_norm not in ("markdown", "json"):
        typer.echo("discover-us: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    u_path = Path(universe_file) if universe_file else None
    if u_path is not None and not u_path.is_file():
        typer.echo(f"discover-us: universe file not found: {u_path}", err=True)
        raise typer.Exit(2)
    try:
        result = scan_us_universe(universe_file=u_path, limit=limit)
    except ValueError as e:
        typer.echo(f"discover-us: {e}", err=True)
        raise typer.Exit(2) from e
    if fmt_norm == "json":
        typer.echo(json.dumps(format_us_discovery_json(result), ensure_ascii=False, indent=2))
    else:
        typer.echo(format_us_discovery_markdown(result))
    raise typer.Exit(0)


@operator_runner_app.command("run")
def operator_runner_run(
    task_file: str = typer.Option(
        str(default_task_path()),
        "--task",
        help="Task YAML path.",
    ),
    policy_file: Optional[str] = typer.Option(
        None,
        "--policy",
        help="Safety policy YAML (default: config/operator_runner_policy.yaml).",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--execute-readonly",
        help="Dry-run plans steps only; execute-readonly runs readonly steps.",
    ),
    execute_gated: bool = typer.Option(
        False,
        "--execute-gated",
        help="Execute gated ingest steps (requires CONFIRM_* gates).",
    ),
    resume_run_dir: Optional[str] = typer.Option(
        None,
        "--resume-run-dir",
        help="Resume from an existing run directory under outputs/operator/runner/.",
    ),
) -> None:
    """Run operator task under safety policy (checkpoint + evidence under outputs/operator/runner/)."""

    task_path = Path(task_file)
    if not task_path.is_file():
        typer.echo(f"operator-runner: task file not found: {task_path}", err=True)
        raise typer.Exit(2)
    policy_path = Path(policy_file) if policy_file else default_policy_path()
    if not policy_path.is_file():
        typer.echo(f"operator-runner: policy file not found: {policy_path}", err=True)
        raise typer.Exit(2)
    if execute_gated:
        mode = "execute_gated"
    elif not dry_run:
        mode = "execute_readonly"
    else:
        mode = "dry_run"
    resume_path = Path(resume_run_dir) if resume_run_dir else None
    if resume_path is not None and not resume_path.is_dir():
        typer.echo(f"operator-runner: resume run dir not found: {resume_path}", err=True)
        raise typer.Exit(2)
    try:
        state = run_operator_task(
            task_path=task_path,
            policy_path=policy_path,
            mode=mode,
            resume_run_dir=resume_path,
        )
    except RunnerStop as e:
        typer.echo(f"operator-runner: stopped: {e.reason}", err=True)
        raise typer.Exit(1) from e
    run_dir = OUTPUTS_DIR / "operator" / "runner" / state.task_id / state.run_id
    if resume_path is not None:
        run_dir = resume_path
    typer.echo(
        f"operator-runner: status={state.status} mode={state.mode} "
        f"steps={len(state.steps)} run_dir={run_dir}"
    )
    raise typer.Exit(0)


@operator_runner_app.command("pr-loop")
def operator_runner_pr_loop(
    branch: str = typer.Option(..., "--branch", help="Head branch for PR."),
    title: str = typer.Option(..., "--title", help="PR title."),
    task_file: Optional[str] = typer.Option(
        None,
        "--task",
        help="Optional operator task YAML to dry-run before PR loop.",
    ),
    pytest_cmd: str = typer.Option(
        "pytest -q tests/test_operator_runner.py tests/test_operator_runner_gated.py tests/test_operator_runner_jquants_wiring.py",
        "--pytest-cmd",
        help="Pytest command (used with --execute-checks).",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--execute-checks",
        help="Dry-run writes PR draft only; execute-checks runs runner/tests/git.",
    ),
    create_pr: bool = typer.Option(
        False,
        "--create-pr",
        help="Create GitHub PR (requires CONFIRM_GITHUB_PR_CREATE=YES and --execute-checks).",
    ),
    check_ci: bool = typer.Option(
        False,
        "--check-ci",
        help="Read-only CI check via gh pr checks; stops on pending/failing/cancelled/unknown.",
    ),
    pr_number: Optional[int] = typer.Option(
        None,
        "--pr-number",
        help="Existing PR number for --check-ci (optional if PR is created in the same run).",
    ),
    wait_ci: bool = typer.Option(
        False,
        "--wait-ci",
        help="Poll gh run list until CI completes, fails, cancels, or times out.",
    ),
    ci_timeout_seconds: int = typer.Option(
        600,
        "--ci-timeout-seconds",
        help="Max seconds to wait when --wait-ci is set.",
    ),
    ci_poll_seconds: int = typer.Option(
        30,
        "--ci-poll-seconds",
        help="Seconds between gh run list polls when --wait-ci is set.",
    ),
) -> None:
    """PR loop foundation: task/evidence/tests/git → PR draft; gated gh pr create; no auto-merge."""

    task_path = Path(task_file) if task_file else None
    if task_path is not None and not task_path.is_file():
        typer.echo(f"operator-runner pr-loop: task file not found: {task_path}", err=True)
        raise typer.Exit(2)
    if create_pr and dry_run:
        typer.echo("operator-runner pr-loop: --create-pr requires --execute-checks", err=True)
        raise typer.Exit(2)
    result = run_pr_loop(
        branch=branch,
        pr_title=title,
        task_path=task_path,
        pytest_cmd=pytest_cmd,
        execute_checks=not dry_run,
        create_pr=create_pr,
        check_ci=check_ci,
        wait_ci=wait_ci,
        ci_timeout_seconds=ci_timeout_seconds,
        ci_poll_seconds=ci_poll_seconds,
        pr_number=pr_number,
    )
    typer.echo(
        f"operator-runner pr-loop: status={result.status} mode={result.pr_create_mode} "
        f"draft={result.pr_body_draft_path}"
    )
    if result.pr_url:
        typer.echo(f"operator-runner pr-loop: pr_url={result.pr_url}")
    if result.ci_wait_status:
        typer.echo(
            f"operator-runner pr-loop: ci_wait_status={result.ci_wait_status} "
            f"polls={result.ci_wait_poll_count}"
        )
    if result.stop_reason:
        typer.echo(f"operator-runner pr-loop: stop_reason={result.stop_reason}", err=True)
        raise typer.Exit(1)
    raise typer.Exit(0)


@operator_runner_app.command("dev-loop")
def operator_runner_dev_loop(
    profile: Optional[str] = typer.Option(
        None,
        "--profile",
        help="Optional run profile name from config/operator_dev_loop_profiles.yaml.",
    ),
    task_queue: str = typer.Option(
        str(default_task_queue_path()),
        "--task-queue",
        help="Task queue YAML path.",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--execute-dev-loop",
        help="Dry-run plans queue only; execute-dev-loop runs queued tasks.",
    ),
    create_pr: bool = typer.Option(
        False,
        "--create-pr",
        help="Create PRs in task runs (requires CONFIRM_GITHUB_PR_CREATE=YES).",
    ),
    max_runtime_minutes: Optional[int] = typer.Option(None, "--max-runtime-minutes"),
    max_tasks: Optional[int] = typer.Option(None, "--max-tasks"),
    max_prs: Optional[int] = typer.Option(None, "--max-prs"),
    stop_on_failure: Optional[bool] = typer.Option(None, "--stop-on-failure/--continue-on-failure"),
    stop_on_dirty_tree: Optional[bool] = typer.Option(None, "--stop-on-dirty-tree/--allow-dirty-tree"),
    wait_ci: Optional[bool] = typer.Option(None, "--wait-ci/--no-wait-ci"),
    ci_timeout_seconds: Optional[int] = typer.Option(None, "--ci-timeout-seconds"),
    ci_poll_seconds: Optional[int] = typer.Option(None, "--ci-poll-seconds"),
    min_runtime_minutes: Optional[int] = typer.Option(
        None,
        "--min-runtime-minutes",
        help="Minimum wall time before successful long-run exit (requires --no-early-success-exit).",
    ),
    no_early_success_exit: bool = typer.Option(
        False,
        "--no-early-success-exit",
        help="After task/PR caps, heartbeat until --min-runtime-minutes instead of stopping.",
    ),
    allow_early_completion: bool = typer.Option(
        False,
        "--allow-early-completion",
        help="When productive queue work is done, exit without heartbeat-only min_runtime wait.",
    ),
    completion_notify: bool = typer.Option(
        False,
        "--completion-notify",
        help="Best-effort macOS sound/notification on run completion (never fails the run).",
    ),
    heartbeat_interval_minutes: int = typer.Option(
        10,
        "--heartbeat-interval-minutes",
        help="Sleep interval during long-run heartbeat/wait phases.",
    ),
    continue_after_pr_limit: Optional[str] = typer.Option(
        None,
        "--continue-after-pr-limit",
        help="wait|heartbeat|next-cycle|stop when max PRs reached (default: stop).",
    ),
    continue_after_task_limit: Optional[str] = typer.Option(
        None,
        "--continue-after-task-limit",
        help="wait|heartbeat|next-cycle|stop when max tasks reached (default: stop).",
    ),
    continue_on_task_failure: bool = typer.Option(
        False,
        "--continue-on-task-failure",
        help="Record noncritical task failures and continue (requires --max-task-failures).",
    ),
    max_task_failures: Optional[int] = typer.Option(
        None,
        "--max-task-failures",
        help="Stop after this many recorded noncritical task failures (default 3 with --continue-on-task-failure).",
    ),
    critical_task_failure_policy: str = typer.Option(
        "stop",
        "--critical-task-failure-policy",
        help="stop|record for critical/safety-class task failures (default: stop immediately).",
    ),
    failure_summary: bool = typer.Option(
        False,
        "--failure-summary",
        help="Print recorded task failure summary at end of run.",
    ),
    max_same_failure_category: Optional[int] = typer.Option(
        None,
        "--max-same-failure-category",
        help="Stop when the same failure category is recorded this many times.",
    ),
    skip_existing_task_artifacts: bool = typer.Option(
        False,
        "--skip-existing-task-artifacts",
        help="Skip tasks when branch/PR artifacts already exist (read-only gh/git checks).",
    ),
) -> None:
    """Overnight autonomous development queue runner (dry-run default; no auto-merge)."""

    queue_path = Path(task_queue)
    if not queue_path.is_file():
        typer.echo(f"operator-runner dev-loop: task queue not found: {queue_path}", err=True)
        raise typer.Exit(2)
    if create_pr and dry_run:
        typer.echo("operator-runner dev-loop: --create-pr requires --execute-dev-loop", err=True)
        raise typer.Exit(2)
    profile_path = default_profile_path()
    if profile and not profile_path.is_file():
        typer.echo(f"operator-runner dev-loop: profile file not found: {profile_path}", err=True)
        raise typer.Exit(2)
    try:
        result = run_dev_loop(
            task_queue_path=queue_path,
            profile_name=profile,
            profile_path=profile_path,
            execute_dev_loop=not dry_run,
            create_pr=create_pr,
            wait_ci=wait_ci,
            ci_timeout_seconds=ci_timeout_seconds,
            ci_poll_seconds=ci_poll_seconds,
            max_runtime_minutes=max_runtime_minutes,
            max_tasks=max_tasks,
            max_prs=max_prs,
            stop_on_failure=stop_on_failure,
            stop_on_dirty_tree=stop_on_dirty_tree,
            min_runtime_minutes=min_runtime_minutes,
            no_early_success_exit=no_early_success_exit,
            allow_early_completion=allow_early_completion,
            completion_notify_enabled=completion_notify,
            heartbeat_interval_minutes=heartbeat_interval_minutes,
            continue_after_pr_limit=continue_after_pr_limit,
            continue_after_task_limit=continue_after_task_limit,
            continue_on_task_failure=continue_on_task_failure,
            max_task_failures=max_task_failures,
            critical_task_failure_policy=critical_task_failure_policy,
            failure_summary=failure_summary,
            max_same_failure_category=max_same_failure_category,
            skip_existing_task_artifacts=skip_existing_task_artifacts,
        )
    except ValueError as e:
        typer.echo(f"operator-runner dev-loop: {e}", err=True)
        raise typer.Exit(2) from e
    typer.echo(
        f"operator-runner dev-loop: status={result.status} mode={result.mode} "
        f"tasks={result.tasks_executed}/{result.tasks_seen} prs={result.prs_created}"
    )
    typer.echo(f"operator-runner dev-loop: evidence={result.evidence_path}")
    if result.stop_reason:
        typer.echo(f"operator-runner dev-loop: stop_reason={result.stop_reason}", err=True)
    if dev_loop_should_exit_nonzero(result):
        raise typer.Exit(1)
    raise typer.Exit(0)


@operator_runner_app.command("post-run-review")
def operator_runner_post_run_review(
    run_id: Optional[str] = typer.Option(
        None,
        "--run-id",
        help="Dev-loop run id (default: latest evidence_summary.json).",
    ),
    fmt: str = typer.Option(
        "markdown",
        "--format",
        help="Output format (markdown only).",
    ),
) -> None:
    """Read-only summary of a completed productive longrun (evidence + optional run.log)."""

    if fmt.strip().lower() != "markdown":
        typer.echo("operator-runner post-run-review: only --format markdown is supported", err=True)
        raise typer.Exit(2)
    try:
        text = build_post_run_review_markdown(run_id)
    except ValueError as e:
        typer.echo(f"operator-runner post-run-review: {e}", err=True)
        raise typer.Exit(2) from e
    typer.echo(text)
    raise typer.Exit(0)


@operator_runner_app.command("post-run-integrate")
def operator_runner_post_run_integrate(
    run_id: Optional[str] = typer.Option(
        None,
        "--run-id",
        help="Dev-loop run id (default: latest evidence_summary.json).",
    ),
    pr_range: Optional[str] = typer.Option(
        None,
        "--pr-range",
        help="PR numbers to audit/integrate (e.g. 185-199). Default: from evidence task_results.",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--execute",
        help="Audit only (default). Use --execute with --integrate for guarded actions.",
    ),
    integrate: bool = typer.Option(
        False,
        "--integrate",
        help="Run guarded integration (requires CONFIRM_PRODUCTIVE_PR_MERGE=YES and --execute).",
    ),
) -> None:
    """Audit and optionally integrate productive longrun PR batches (no auto-merge)."""

    if integrate and dry_run:
        typer.echo(
            "operator-runner post-run-integrate: --integrate requires --execute (not --dry-run)",
            err=True,
        )
        raise typer.Exit(2)
    try:
        result = run_post_run_integrate(
            run_id=run_id,
            pr_range=pr_range,
            dry_run=dry_run,
            integrate=integrate,
        )
    except ValueError as e:
        typer.echo(f"operator-runner post-run-integrate: {e}", err=True)
        raise typer.Exit(2) from e
    typer.echo(format_integrate_markdown(result))
    if result.errors:
        raise typer.Exit(1)
    raise typer.Exit(0)


@operator_runner_app.command("autopilot-status")
def operator_runner_autopilot_status(
    run_id: Optional[str] = typer.Option(
        None,
        "--run-id",
        help="Latest productive dev-loop run id (default: newest evidence).",
    ),
    fmt: str = typer.Option(
        "markdown",
        "--format",
        help="Output format: markdown or json.",
    ),
    no_fetch: bool = typer.Option(
        False,
        "--no-fetch",
        help="Skip git fetch origin main (offline / faster).",
    ),
) -> None:
    """Read-only repo/CI/PR/longrun snapshot for Cursor Agent (no merge, no push)."""

    fmt_norm = fmt.strip().lower()
    if fmt_norm not in {"markdown", "json"}:
        typer.echo("operator-runner autopilot-status: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    result = collect_autopilot_status(run_id=run_id, fetch_main=not no_fetch)
    if fmt_norm == "json":
        typer.echo(format_autopilot_status_json(result))
    else:
        typer.echo(format_autopilot_status_markdown(result))
    raise typer.Exit(0)


@app.command("pack")
def pack(ticker: str = typer.Option(..., "--ticker")) -> None:
    today = today_jst_iso()
    out = OUTPUTS_DIR / "research_packs" / f"{ticker}_{today}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "\n".join(
            [
                f"# Research Pack: {ticker}",
                "",
                "Phase 0 dummy pack.",
                "- Thesis: TODO",
                "- Evidence: TODO",
                "- Risks: TODO",
            ]
        ),
        encoding="utf-8",
    )
    typer.echo(f"research pack created: {out}")


@app.command("risks")
def risks() -> None:
    rules = load_yaml(CONFIG_DIR / "veto_rules.yaml")
    engine = VetoEngine(rules=rules)
    demo = engine.evaluate({"market_heat": 0.95, "valuation_stretch": 0.7})
    typer.echo("risk scan (phase 0 stub):")
    typer.echo(f"triggered veto count: {len(demo)}")


@snapshot_app.command("watchlist")
def snapshot_watchlist() -> None:
    watchlist = load_yaml(CONFIG_DIR / "watchlist.yaml")
    jp_count = _jp_watchlist_count(watchlist.get("jp_watchlist", []))
    us = watchlist.get("us_watchlist", {})
    t1 = len(us.get("tier_1_core", []))
    t2 = len(us.get("tier_2_theme_peers", []))
    t3 = len(us.get("tier_3_optional", []))
    typer.echo(f"JP: {jp_count}, US tier1: {t1}, tier2: {t2}, tier3: {t3}")


@snapshot_app.command("shadow-portfolio")
def snapshot_shadow_portfolio() -> None:
    service = ShadowPortfolioService(OUTPUTS_DIR / "shadow_portfolio" / "positions.jsonl")
    positions = service.list_positions()
    typer.echo(f"shadow positions: {len(positions)}")


@snapshot_app.command("portfolio-observation-summary")
def snapshot_portfolio_observation_summary(
    shadow_path: Optional[str] = typer.Option(
        None,
        "--shadow-path",
        help="Shadow portfolio JSONL (default: outputs/shadow_portfolio/positions.jsonl).",
    ),
    observation_log: Optional[str] = typer.Option(
        None,
        "--observation-log",
        help="Observation log JSONL (default: outputs/observation_log/observation_log.jsonl).",
    ),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    """Read-only linkage between shadow positions and observation_log (observation only)."""

    fmt_norm = fmt.strip().lower()
    shadow = (
        Path(shadow_path)
        if shadow_path
        else OUTPUTS_DIR / "shadow_portfolio" / "positions.jsonl"
    )
    obs = (
        Path(observation_log)
        if observation_log
        else OUTPUTS_DIR / "observation_log" / "observation_log.jsonl"
    )
    summary = build_portfolio_observation_summary(
        path_base=ROOT_DIR,
        shadow_path=shadow,
        observation_path=obs,
    )
    if fmt_norm == "json":
        typer.echo(format_portfolio_observation_summary_json(summary))
    elif fmt_norm == "markdown":
        typer.echo(format_portfolio_observation_summary_markdown(summary))
    else:
        typer.echo(
            "snapshot portfolio-observation-summary: --format must be markdown or json",
            err=True,
        )
        raise typer.Exit(2)


@snapshot_app.command("portfolio-exposure-by-signal-veto")
def snapshot_portfolio_exposure_by_signal_veto(
    shadow_path: Optional[str] = typer.Option(
        None,
        "--shadow-path",
        help="Shadow portfolio JSONL (default: outputs/shadow_portfolio/positions.jsonl).",
    ),
    observation_log: Optional[str] = typer.Option(
        None,
        "--observation-log",
        help="Observation log JSONL (default: outputs/observation_log/observation_log.jsonl).",
    ),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    """Read-only shadow exposure by latest US signal momentum_label and veto bucket."""

    fmt_norm = fmt.strip().lower()
    shadow = (
        Path(shadow_path)
        if shadow_path
        else OUTPUTS_DIR / "shadow_portfolio" / "positions.jsonl"
    )
    obs = (
        Path(observation_log)
        if observation_log
        else OUTPUTS_DIR / "observation_log" / "observation_log.jsonl"
    )
    report = build_portfolio_exposure_by_signal_veto(
        path_base=ROOT_DIR,
        shadow_path=shadow,
        observation_path=obs,
    )
    if fmt_norm == "json":
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    elif fmt_norm == "markdown":
        typer.echo(format_portfolio_exposure_by_signal_veto_markdown(report))
    else:
        typer.echo(
            "snapshot portfolio-exposure-by-signal-veto: --format must be markdown or json",
            err=True,
        )
        raise typer.Exit(2)


@snapshot_app.command("observation-health")
def snapshot_observation_health(
    observation_log: Optional[str] = typer.Option(
        None,
        "--observation-log",
        help="Observation log JSONL (default: outputs/observation_log/observation_log.jsonl).",
    ),
    cache_dir: Optional[str] = typer.Option(
        None,
        "--cache-dir",
        help="US daily bars cache directory (default: outputs/market_data/us_daily_bars).",
    ),
    fmt: str = typer.Option("markdown", "--format", help="markdown or json."),
) -> None:
    """Read-only observation_log health: signals, peer_sync, portfolio, forward sample."""

    fmt_norm = fmt.strip().lower()
    obs = (
        Path(observation_log)
        if observation_log
        else OUTPUTS_DIR / "observation_log" / "observation_log.jsonl"
    )
    cache = (
        Path(cache_dir) if cache_dir else OUTPUTS_DIR / "market_data" / "us_daily_bars"
    )
    report = build_observation_health_report(
        path_base=ROOT_DIR,
        observation_path=obs,
        cache_dir=cache,
    )
    if fmt_norm == "json":
        typer.echo(format_observation_health_json(report))
    elif fmt_norm == "markdown":
        typer.echo(format_observation_health_markdown(report))
    else:
        typer.echo("snapshot observation-health: --format must be markdown or json", err=True)
        raise typer.Exit(2)


@log_app.command("outcome")
def log_outcome(
    symbol: str = typer.Option(..., "--symbol"),
    result: str = typer.Option("unknown", "--result"),
    note: Optional[str] = typer.Option(None, "--note"),
) -> None:
    row = _obs_service().log_outcome(symbol=symbol, result=result, note=note)
    typer.echo(f"outcome logged: {row.id}")


@log_app.command("us-signals-summary")
def log_us_signals_summary() -> None:
    """Summarize US cache signal rows in observation_log.jsonl (read-only)."""

    summary = build_enriched_us_observation_summary(
        OUTPUTS_DIR / "observation_log" / "observation_log.jsonl",
        path_base=ROOT_DIR,
    )
    typer.echo(json.dumps(summary, ensure_ascii=False, indent=2))


@log_app.command("evidence-manifest")
def log_evidence_manifest(
    task_id: str = typer.Option(..., "--task-id"),
    evidence_path: str = typer.Option(..., "--evidence-path"),
    command: str = typer.Option(..., "--command"),
    result: str = typer.Option(..., "--result"),
    summary: str = typer.Option(..., "--summary"),
    report_date: Optional[str] = typer.Option(None, "--report-date"),
) -> None:
    """Write evidence manifest markdown to reports/ (read-only metadata; no secrets)."""

    manifest = build_evidence_manifest(
        task_id=task_id,
        evidence_path=Path(evidence_path),
        command=command,
        result=result,
        summary=summary,
    )
    out = write_evidence_manifest_report(
        manifest,
        path_base=ROOT_DIR,
        report_date=report_date,
    )
    payload = {**manifest, "manifest_report_path": str(out.relative_to(ROOT_DIR))}
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@log_app.command("peer-sync-snapshot")
def log_peer_sync_snapshot(
    peer_map: Optional[str] = typer.Option(
        None,
        "--peer-map",
        help="Path to peer_map.yaml (default: config/peer_map.yaml).",
    ),
    window_days: int = typer.Option(20, "--window-days"),
    divergence_threshold: float = typer.Option(0.05, "--divergence-threshold"),
    skip_missing_cache: bool = typer.Option(
        True,
        "--skip-missing-cache/--include-missing-cache",
        help="Skip pairs with missing_cache status (default: skip).",
    ),
) -> None:
    """Append peer_sync pair rows to observation_log (writes outputs/; explicit opt-in)."""

    pmap = Path(peer_map) if peer_map else CONFIG_DIR / "peer_map.yaml"
    skip: frozenset[str] = frozenset({"missing_cache"}) if skip_missing_cache else frozenset()
    result = log_peer_sync_snapshot_observations(
        path_base=ROOT_DIR,
        service=_obs_service(),
        peer_map_path=pmap,
        window_days=window_days,
        divergence_threshold=divergence_threshold,
        skip_statuses=skip,
    )
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    if peer_sync_log_failed(result):
        raise typer.Exit(2)


@log_app.command("peer-sync-summary")
def log_peer_sync_summary() -> None:
    """Summarize peer_sync rows in observation_log.jsonl (read-only)."""

    summary = summarize_peer_sync_observation_log(
        OUTPUTS_DIR / "observation_log" / "observation_log.jsonl"
    )
    typer.echo(json.dumps(summary, ensure_ascii=False, indent=2))


@log_app.command("us-signals-batch")
def log_us_signals_batch(
    manifest: str = typer.Option(
        ...,
        "--manifest",
        help="US cache signals batch manifest JSON (schema_version 1).",
    ),
) -> None:
    """Append observation_log rows from cache-only US signal previews (no HTTP)."""

    result = log_us_signals_batch_observations(
        Path(manifest),
        path_base=ROOT_DIR,
        service=_obs_service(),
    )
    if observation_batch_failed(result):
        typer.echo(json.dumps(result, ensure_ascii=False, indent=2), err=True)
        raise typer.Exit(2)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@debug_app.command("adapters")
def debug_adapters() -> None:
    adapters = [YFinanceFallbackAdapter(), JQuantsStubAdapter(), EdinetStubAdapter(), SecStubAdapter()]
    for adapter in adapters:
        typer.echo(str(adapter.health()))


@debug_app.command("jquants-status")
def debug_jquants_status() -> None:
    client = JQuantsClient.from_env()
    typer.echo(json.dumps(client.safe_auth_status(), ensure_ascii=False, indent=2))
    typer.echo(
        "(never performs HTTP; see api_version, auth_method, api_key_present, unsupported_api_version, "
        "base_url_present, allow_live_http, configured)"
    )


def _cli_optional_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _fmt_pct_md(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v * 100:+.1f}%"


def _fmt_ratio_md(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:.2f}x"


def _signals_markdown(out: dict[str, Any]) -> str:
    """Render signals JSON payload as a human-readable Markdown table."""
    rows = out.get("ranked", [])
    skipped = out.get("skipped_no_cache", 0)
    mode = out.get("mode", "")
    lines: list[str] = [
        "## Momentum Signals — JP Watchlist",
        "",
        f"*モード: `{mode}` / observation only / Not trading advice.*",
        "",
    ]
    if skipped:
        lines.append(f"**キャッシュなしでスキップ**: {skipped}件")
        lines.append("")
    if not rows:
        lines.append("*(候補なし)*")
        return "\n".join(lines)

    lines.append("| # | Code / Name | Sv2 | Labels | r5 | r20 | r60 | HiDist | VolR | Veto |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for i, row in enumerate(rows, 1):
        labels = ", ".join(row.get("labels", [])) or "—"
        veto_cell = format_veto_table_cell(row.get("veto_result", {}))
        code_cell = display_symbol(str(row.get("code", "")), market="jp")
        lines.append(
            f"| {i} | {code_cell} | {row.get('score_v2', '—')} | {labels} "
            f"| {_fmt_pct_md(row.get('r5'))} | {_fmt_pct_md(row.get('r20'))} "
            f"| {_fmt_pct_md(row.get('r60'))} | {_fmt_pct_md(row.get('high_52w_distance_pct'))} "
            f"| {_fmt_ratio_md(row.get('volume_ratio_25d'))} | {veto_cell} |"
        )
    lines.append("")
    return "\n".join(lines)


def _jp_momentum_bar_mapping(
    source: str, tickers: list[str]
) -> tuple[dict[str, list], dict[str, str], list[str]]:
    """Build code→bars for momentum; ``skipped_no_cache`` lists wire codes with no cache file (cache-only)."""

    mapping: dict[str, list] = {}
    srcmap: dict[str, str] = {}
    skipped_no_cache: list[str] = []
    for raw in tickers:
        w = normalize_jquants_equity_code(str(raw))
        if w is None:
            continue
        if source == "synthetic":
            mapping[w] = synthetic_bars_for_code(w)
            srcmap[w] = "synthetic"
        elif source == "cache":
            got = try_load_cached_daily_bars(w)
            if got is not None:
                mapping[w], srcmap[w] = got
            else:
                mapping[w] = synthetic_bars_for_code(w)
                srcmap[w] = "synthetic"
        elif source == "cache-only":
            got = try_load_cached_daily_bars(w)
            if got is not None:
                mapping[w], srcmap[w] = got
            else:
                skipped_no_cache.append(w)
        else:
            raise ValueError(f"unexpected signals source: {source!r}")
    return mapping, srcmap, skipped_no_cache


def _bars_data_source_label(srcmap: dict[str, str]) -> str:
    u = set(srcmap.values())
    if u == {"cache"}:
        return "cache"
    if u == {"synthetic"}:
        return "synthetic"
    if not u:
        return "synthetic"
    return "mixed"


def _jquants_daily_quotes_cli_snapshot(
    result: dict[str, Any],
    *,
    code: Optional[str],
    from_date: Optional[str],
    to_date: Optional[str],
    date_opt: Optional[str],
) -> dict[str, Any]:
    """Public fields only — no raw body; ``error_body_preview`` is masked/short when present."""

    st = result.get("status")
    snap: dict[str, Any] = {
        "status": st,
        "code": code,
        "date": date_opt,
        "date_from": from_date,
        "date_to": to_date,
    }

    if st == "validation_error":
        r = result.get("reason")
        if isinstance(r, str):
            snap["reason"] = r
        for k in ("data_available_from", "data_available_to"):
            if k in result:
                snap[k] = result[k]
        return snap

    if st == "success":
        snap["row_count"] = result.get("row_count")
        snap["source_key"] = result.get("source_key")
        return snap

    if st == "dry_run":
        ep = result.get("endpoint")
        if ep:
            snap["endpoint"] = ep
        for k in (
            "endpoint_url_without_query",
            "query_params",
            "full_url_without_secrets",
            "api_key_header_name",
            "api_key_header_present",
            "api_key_value_included",
        ):
            if k in result:
                snap[k] = result[k]
        return snap

    if st == "http_error":
        snap["http_status"] = result.get("http_status")
        if snap["http_status"] is None and isinstance(result.get("code"), int):
            snap["http_status"] = result["code"]
        for k in (
            "endpoint_url_without_query",
            "query_params",
            "full_url_without_secrets",
            "api_key_header_present",
            "api_key_header_name",
            "api_key_value_included",
            "raw_response_included",
            "error_body_preview",
        ):
            if k in result:
                snap[k] = result[k]
        return snap

    for k in ("reason", "endpoint_path", "missing"):
        if k in result:
            snap[k] = result[k]

    return snap


def _watchlist_preview_row(code: str, prv: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {"code": code}
    st = prv.get("status")
    row["status"] = st
    if st == "validation_error":
        if isinstance(prv.get("reason"), str):
            row["reason"] = prv["reason"]
        for k in ("data_available_from", "data_available_to"):
            if k in prv:
                row[k] = prv[k]
        row["raw_response_included"] = prv.get("raw_response_included", False)
        return row
    for k in (
        "endpoint_url_without_query",
        "query_params",
        "full_url_without_secrets",
        "api_key_header_name",
        "api_key_header_present",
        "api_key_value_included",
        "reason",
    ):
        if k in prv:
            row[k] = prv[k]
    row["raw_response_included"] = prv.get("raw_response_included", False)
    return row


def _result_row_no_raw(row: dict[str, Any]) -> dict[str, Any]:
    if "raw_response_included" not in row:
        row["raw_response_included"] = False
    return row


def _watchlist_bars_cache_row(
    *,
    code: str,
    status: str,
    row_count: Any = None,
    sanitized_bar_count: Any = None,
    cache_written_to: Any = None,
    reason: Any = None,
    full_url_without_secrets: Any = None,
    http_status: Any = None,
    error_body_preview: Any = None,
) -> dict[str, Any]:
    """Public summary row for ``jquants-watchlist-bars-cache`` (optional safe preview URL in dry-run)."""

    row: dict[str, Any] = {
        "code": code,
        "status": status,
        "row_count": row_count,
        "sanitized_bar_count": sanitized_bar_count,
        "cache_written_to": cache_written_to,
        "reason": reason,
    }
    if full_url_without_secrets is not None:
        row["full_url_without_secrets"] = full_url_without_secrets
    if http_status is not None:
        row["http_status"] = http_status
    if error_body_preview is not None:
        row["error_body_preview"] = error_body_preview
    return _result_row_no_raw(row)


def _reason_from_snap_for_row(status_str: str, snap: dict[str, Any], result: dict[str, Any]) -> str:
    """Non-empty public reason for error rows (never raw API body)."""

    r = snap.get("reason")
    if isinstance(r, str) and r.strip():
        return r
    rx = result.get("reason")
    if isinstance(rx, str) and rx.strip():
        return rx
    if status_str == "http_error":
        hs = snap.get("http_status")
        if hs is None and isinstance(snap.get("code"), int):
            hs = int(snap["code"])
        if isinstance(hs, int):
            return f"http_status_{hs}"
        ebp = snap.get("error_body_preview")
        if isinstance(ebp, str) and ebp.strip():
            return "http_error_masked_preview"
        return "http_error_unknown"
    return status_str


def _watchlist_bars_cache_row_from_snap(code: str, snap: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    st = str(snap.get("status") or result.get("status") or "error")
    reason = _reason_from_snap_for_row(st, snap, result)
    row: dict[str, Any] = {
        "code": code,
        "status": st,
        "row_count": snap.get("row_count"),
        "sanitized_bar_count": None,
        "cache_written_to": None,
        "reason": reason,
    }
    if st == "http_error":
        hs = snap.get("http_status")
        if hs is None and isinstance(result.get("code"), int):
            hs = int(result["code"])
        if isinstance(hs, int):
            row["http_status"] = hs
        # Bulk summary: omit body-derived previews; use http_status + reason only (Main L gate).
        row["raw_response_included"] = False
    else:
        row["raw_response_included"] = bool(snap.get("raw_response_included", False))
    return _result_row_no_raw(row)


def _parse_codes_csv(codes: Optional[str]) -> tuple[list[str], list[str]] | None:
    """Return ``(wire_codes, skipped_raw_tokens)`` or ``None`` if ``codes`` is empty."""

    if codes is None or not str(codes).strip():
        return None
    wire_out: list[str] = []
    skipped: list[str] = []
    for part in str(codes).split(","):
        p = part.strip()
        if not p:
            continue
        w = normalize_jquants_equity_code(p)
        if w is None:
            skipped.append(p)
        else:
            wire_out.append(w)
    return (wire_out, skipped)


def _norm_watchlist_codes_csv_requested(codes_csv: Optional[str]) -> Optional[str]:
    if codes_csv is None or not str(codes_csv).strip():
        return None
    parts = [p.strip() for p in str(codes_csv).split(",") if p.strip()]
    if not parts:
        return None
    return ",".join(parts)


def _resolve_watchlist_bars_cache_tickers(
    *,
    codes_csv: Optional[str],
    limit: Optional[int],
) -> tuple[list[str], list[str]]:
    """Return ``(tickers, skipped_unsupported_from_codes_csv)``."""

    parsed = _parse_codes_csv(codes_csv)
    if parsed is not None:
        wire_list, skipped = parsed
        tickers = wire_list if limit is None else wire_list[:limit]
        return tickers, skipped
    tickers_all = load_jp_watchlist_tickers()
    tickers = tickers_all if limit is None else tickers_all[:limit]
    return tickers, []


def _maybe_save_watchlist_smoke_summary(
    out: dict[str, Any],
    *,
    save_summary: bool,
    preview_request: bool,
    date_opt: Optional[str],
    from_date: Optional[str],
    to_date: Optional[str],
    limit: Optional[int],
) -> dict[str, Any]:
    if not save_summary or preview_request:
        return out
    slug = build_watchlist_filename_date_slug(date_opt, from_date, to_date)
    lim = str(limit) if limit is not None else "all"
    payload = build_watchlist_smoke_summary_document(out)
    main_rel, latest_rel = save_watchlist_smoke_summary_payload(payload, date_slug=slug, limit_display=lim)
    merged = dict(out)
    merged["summary_saved_to"] = main_rel
    merged["latest_summary_saved_to"] = latest_rel
    return merged


@debug_app.command("jquants-watchlist-bars")
def debug_jquants_watchlist_bars(
    date: Optional[str] = typer.Option(
        None,
        "--date",
        help="Single day YYYY-MM-DD or YYYYMMDD (mutually exclusive with --from-date/--to-date).",
    ),
    from_date: Optional[str] = typer.Option(None, "--from-date", help="Range start (requires --to-date for paired use)."),
    to_date: Optional[str] = typer.Option(None, "--to-date", help="Range end (requires --from-date for paired use)."),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        min=1,
        help="Process only the first N tickers from jp_watchlist (order preserved).",
    ),
    live: bool = typer.Option(False, "--live", help="Perform live HTTP when all gates allow it."),
    preview_request: bool = typer.Option(False, "--preview-request", help="Show V2 request preview per ticker; never HTTP."),
    save_summary: bool = typer.Option(
        False,
        "--save-summary",
        help="Write sanitized summary JSON under outputs/jquants_smoke/ (not used with --preview-request).",
    ),
) -> None:
    """Batch daily-bars check for ``jp_watchlist`` (Phase 1a Task 6). Default: dry-run. Task 9.1 smoke JSON splits ``dry_run_count`` vs ``error_count``."""

    client = JQuantsClient.from_env()
    dn = _cli_optional_str(date)
    fn = _cli_optional_str(from_date)
    tn = _cli_optional_str(to_date)

    if (fn is not None) ^ (tn is not None):
        view = _jquants_daily_quotes_cli_snapshot(
            {
                "status": "validation_error",
                "reason": "watchlist_range_requires_both_from_and_to",
                "raw_response_included": False,
            },
            code=None,
            from_date=fn,
            to_date=tn,
            date_opt=dn,
        )
        typer.echo(json.dumps(view, ensure_ascii=False, indent=2))
        raise typer.Exit(1)

    verr = client.validate_daily_quotes_cli_args(None, date=dn, from_date=fn, to_date=tn)
    if verr is not None:
        view = _jquants_daily_quotes_cli_snapshot(verr, code=None, from_date=fn, to_date=tn, date_opt=dn)
        typer.echo(json.dumps(view, ensure_ascii=False, indent=2))
        raise typer.Exit(1)

    try:
        tickers_all = load_jp_watchlist_tickers()
    except (FileNotFoundError, ValueError, OSError) as e:
        typer.echo(json.dumps({"status": "error", "detail": str(e), "raw_response_included": False}, ensure_ascii=False, indent=2))
        raise typer.Exit(1) from e

    tickers = tickers_all if limit is None else tickers_all[:limit]
    base_meta: dict[str, Any] = {
        "date": dn,
        "date_from": fn,
        "date_to": tn,
        "target_count": len(tickers),
        "raw_response_included": False,
    }

    results: list[dict[str, Any]] = []

    if preview_request:
        for code in tickers:
            wire = normalize_jquants_equity_code(code)
            if wire is None:
                results.append(
                    _result_row_no_raw(
                        {"code": (code or "").strip(), "status": "skipped_unsupported_code", "raw_response_included": False}
                    )
                )
                continue
            prv = client.build_v2_daily_bars_request_preview(wire, date=dn, from_date=fn, to_date=tn)
            results.append(_result_row_no_raw(_watchlist_preview_row(wire, prv)))
        out = {"status": "preview", **base_meta, "results": results}
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
        raise typer.Exit(0)

    if not live and not client.is_enabled():
        out = {
            "status": "disabled",
            "reason": "JQUANTS_ENABLED=false",
            **base_meta,
            "results": [],
        }
        out = _maybe_save_watchlist_smoke_summary(
            out,
            save_summary=save_summary,
            preview_request=False,
            date_opt=dn,
            from_date=fn,
            to_date=tn,
            limit=limit,
        )
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
        raise typer.Exit(0)

    for code in tickers:
        wire = normalize_jquants_equity_code(code)
        if wire is None:
            results.append(_result_row_no_raw({"code": (code or "").strip(), "status": "skipped_unsupported_code"}))
            continue
        res = client.get_daily_quotes(wire, date=dn, from_date=fn, to_date=tn, attempt_live=live)
        snap = _jquants_daily_quotes_cli_snapshot(res, code=wire, from_date=fn, to_date=tn, date_opt=dn)
        results.append(_result_row_no_raw(snap))

    if not live:
        out = {"status": "dry_run", **base_meta, "results": results}
        out = _maybe_save_watchlist_smoke_summary(
            out,
            save_summary=save_summary,
            preview_request=False,
            date_opt=dn,
            from_date=fn,
            to_date=tn,
            limit=limit,
        )
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
        raise typer.Exit(0)

    non_skip = [r for r in results if r.get("status") != "skipped_unsupported_code"]
    success_count = sum(1 for r in non_skip if r.get("status") == "success")
    error_count = len(non_skip) - success_count
    out = {
        "status": "completed",
        **base_meta,
        "success_count": success_count,
        "error_count": error_count,
        "results": results,
    }
    out = _maybe_save_watchlist_smoke_summary(
        out,
        save_summary=save_summary,
        preview_request=False,
        date_opt=dn,
        from_date=fn,
        to_date=tn,
        limit=limit,
    )
    typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
    if error_count == 0:
        raise typer.Exit(0)
    raise typer.Exit(1)


@debug_app.command("jquants-daily-quotes")
def debug_jquants_daily_quotes(
    code: Optional[str] = typer.Option(None, "--code", help="Equity code (optional; V2 accepts code-only queries)."),
    from_date: Optional[str] = typer.Option(
        None,
        "--from-date",
        help="Range start (YYYY-MM-DD or YYYYMMDD); sent as query `from` on V2 as YYYYMMDD.",
    ),
    to_date: Optional[str] = typer.Option(
        None,
        "--to-date",
        help="Range end (YYYY-MM-DD or YYYYMMDD); sent as query `to` on V2 as YYYYMMDD.",
    ),
    date: Optional[str] = typer.Option(
        None,
        "--date",
        help="Single day (YYYY-MM-DD or YYYYMMDD); query `date` on V2 as YYYYMMDD. Mutually exclusive with from/to.",
    ),
    live: bool = typer.Option(False, "--live", help="Allow live HTTP (requires JQUANTS_ALLOW_LIVE_HTTP=true)"),
    preview_request: bool = typer.Option(
        False,
        "--preview-request",
        help="Print V2 safe request preview only (never performs HTTP).",
    ),
) -> None:
    client = JQuantsClient.from_env()

    cn = _cli_optional_str(code)
    dn = _cli_optional_str(date)
    fn = _cli_optional_str(from_date)
    tn = _cli_optional_str(to_date)

    verr = client.validate_daily_quotes_cli_args(cn, date=dn, from_date=fn, to_date=tn)
    if verr is not None:
        view = _jquants_daily_quotes_cli_snapshot(verr, code=cn, from_date=fn, to_date=tn, date_opt=dn)
        typer.echo(json.dumps(view, ensure_ascii=False, indent=2))
        raise typer.Exit(1)

    if preview_request:
        prv = client.build_v2_daily_bars_request_preview(cn, date=dn, from_date=fn, to_date=tn)
        typer.echo(json.dumps(prv, ensure_ascii=False, indent=2))
        raise typer.Exit(0)

    if not client.is_enabled():
        view = _jquants_daily_quotes_cli_snapshot(
            {"status": "disabled", "reason": "JQUANTS_ENABLED=false"},
            code=cn,
            from_date=fn,
            to_date=tn,
            date_opt=dn,
        )
        typer.echo(json.dumps(view, ensure_ascii=False, indent=2))
        raise typer.Exit(1 if live else 0)

    result = client.get_daily_quotes(cn, date=dn, from_date=fn, to_date=tn, attempt_live=live)
    view = _jquants_daily_quotes_cli_snapshot(result, code=cn, from_date=fn, to_date=tn, date_opt=dn)
    typer.echo(json.dumps(view, ensure_ascii=False, indent=2))
    if not live:
        raise typer.Exit(0)
    if result.get("status") == "success":
        raise typer.Exit(0)
    raise typer.Exit(1)


@debug_app.command("jquants-daily-bars-cache")
def debug_jquants_daily_bars_cache(
    code: str = typer.Option(..., "--code", help="Equity code (normalized digits/letters)."),
    from_date: str = typer.Option(
        ...,
        "--from-date",
        help="Range start YYYY-MM-DD or YYYYMMDD (pairs with --to-date).",
    ),
    to_date: str = typer.Option(
        ...,
        "--to-date",
        help="Range end YYYY-MM-DD or YYYYMMDD (pairs with --from-date).",
    ),
    live: bool = typer.Option(False, "--live", help="Perform live HTTP when gates allow."),
    write_cache: bool = typer.Option(
        False,
        "--write-cache",
        help="After live success, write sanitized rows to outputs/market_data/jquants_daily_bars/{code}.json.",
    ),
    debug_shape: bool = typer.Option(
        False,
        "--debug-shape",
        help="With --live (+ CONFIRM_LIVE_HTTP=YES), include safe shape_digest on sanitized_empty; never writes cache.",
    ),
) -> None:
    """Dry-run request preview by default. Live + side effects need CONFIRM_LIVE_HTTP=YES."""

    client = JQuantsClient.from_env()
    cn_raw = code.strip()
    w = normalize_jquants_equity_code(cn_raw)
    if w is None:
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "invalid_equity_code",
                    "code": cn_raw,
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise typer.Exit(1)
    cn = w
    fn = from_date.strip()
    tn = to_date.strip()

    if debug_shape and not live:
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "debug_shape_requires_live",
                    "detail": "Use --live with --debug-shape (and CONFIRM_LIVE_HTTP=YES) for HTTP shape diagnostics.",
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            err=True,
        )
        raise typer.Exit(2)

    if write_cache and not live:
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "write_cache_requires_live",
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise typer.Exit(2)

    verr = client.validate_daily_quotes_cli_args(cn, date=None, from_date=fn, to_date=tn)
    if verr is not None:
        view = _jquants_daily_quotes_cli_snapshot(verr, code=cn, from_date=fn, to_date=tn, date_opt=None)
        typer.echo(json.dumps(view, ensure_ascii=False, indent=2))
        raise typer.Exit(1)

    if not live:
        prv = client.build_v2_daily_bars_request_preview(cn, from_date=fn, to_date=tn)
        out = {**prv, "live_http": False, "write_cache": False, "raw_response_included": False}
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
        raise typer.Exit(0 if prv.get("status") == "ok" else 1)

    if live and (write_cache or debug_shape) and os.environ.get("CONFIRM_LIVE_HTTP") != "YES":
        typer.echo(
            json.dumps(
                {
                    "status": "live_blocked",
                    "reason": "confirm_live_http_required",
                    "detail": "Set CONFIRM_LIVE_HTTP=YES for --write-cache and/or --debug-shape live HTTP.",
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            err=True,
        )
        raise typer.Exit(2)

    want_sanitize = write_cache or debug_shape
    result = client.get_daily_quotes(
        cn,
        from_date=fn,
        to_date=tn,
        attempt_live=True,
        return_sanitized_bars=want_sanitize,
        include_shape_digest=debug_shape,
    )
    effective_write = write_cache and not debug_shape

    if want_sanitize and result.get("status") == "sanitized_empty":
        payload: dict[str, Any] = {
            "status": "sanitized_empty",
            "reason": result.get("reason"),
            "code": cn,
            "row_count": result.get("row_count"),
            "source_key": result.get("source_key"),
            "detail": "API returned rows but none mapped to OHLCV; cache not written.",
            "raw_response_included": False,
        }
        sd = result.get("shape_digest")
        if sd is not None:
            payload["shape_digest"] = sd
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2), err=True)
        raise typer.Exit(1)

    if effective_write and result.get("status") == "success":
        bars = result.get("sanitized_bars")
        if not isinstance(bars, list):
            bars = []
        if not bars:
            typer.echo(
                json.dumps(
                    {
                        "status": "success",
                        "code": cn,
                        "row_count": result.get("row_count"),
                        "sanitized_bar_count": 0,
                        "cache_written_to": None,
                        "cache_skipped": "no_sanitized_rows",
                        "raw_response_included": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            raise typer.Exit(0)
        path = save_jquants_daily_bars_cache(
            cn,
            bars,
            source="jquants_v2_equities_bars_daily",
            fetched_at=utc_now_iso(),
            generated_at=None,
        )
        snap = {
            "status": "success",
            "code": cn,
            "row_count": result.get("row_count"),
            "sanitized_bar_count": len(bars),
            "cache_written_to": str(path.relative_to(ROOT_DIR)).replace("\\", "/"),
            "raw_response_included": False,
        }
        typer.echo(json.dumps(snap, ensure_ascii=False, indent=2))
        raise typer.Exit(0)

    view = _jquants_daily_quotes_cli_snapshot(result, code=cn, from_date=fn, to_date=tn, date_opt=None)
    view["write_cache"] = False
    view["debug_shape"] = debug_shape
    typer.echo(json.dumps(view, ensure_ascii=False, indent=2))
    raise typer.Exit(0 if result.get("status") == "success" else 1)


@debug_app.command("us-daily-bars-cache-import")
def debug_us_daily_bars_cache_import(
    symbol: str = typer.Option(..., "--symbol", help="US symbol (normalized for cache filename)."),
    bars_file: Path = typer.Option(..., "--bars-file", help="JSON array of sanitized OHLCV rows."),
    asset_class: Optional[str] = typer.Option(
        None,
        "--asset-class",
        help="Optional persisted label (e.g. us_equity, us_etf).",
    ),
    source: str = typer.Option(
        "local_fixture",
        "--source",
        help="Stored in cache JSON metadata (must not resemble secrets).",
    ),
    write_cache: bool = typer.Option(
        False,
        "--write-cache",
        help="Write outputs/market_data/us_daily_bars/{symbol}.json; default is preview only.",
    ),
) -> None:
    """Import local US OHLCV JSON into on-disk cache (no HTTP)."""

    norm = normalize_us_symbol(symbol.strip())
    if norm is None:
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "invalid_symbol",
                    "symbol_input": symbol,
                    "live_http": False,
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            err=True,
        )
        raise typer.Exit(2)

    p = Path(bars_file)
    if not p.is_file():
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "bars_file_not_found",
                    "path": str(p),
                    "live_http": False,
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            err=True,
        )
        raise typer.Exit(2)

    try:
        bars = load_bars_json_file(p)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "bars_parse_failed",
                    "detail": (
                        "Expected a UTF-8 JSON array of sanitized OHLCV objects "
                        "(date, open, high, low, close, volume)."
                    ),
                    "live_http": False,
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            err=True,
        )
        raise typer.Exit(2)

    rows: list[dict[str, Any]] = [dict(b) for b in bars]
    rel = f"outputs/market_data/us_daily_bars/{norm}.json"

    ac = asset_class.strip() if isinstance(asset_class, str) and asset_class.strip() else None

    if not write_cache:
        typer.echo(
            json.dumps(
                {
                    "status": "dry_run",
                    "symbol": norm,
                    "bar_count": len(rows),
                    "cache_would_write_to": rel,
                    "live_http": False,
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise typer.Exit(0)

    try:
        path = save_us_daily_bars_cache(
            norm,
            rows,
            asset_class=ac,
            source=source.strip(),
            fetched_at=utc_now_iso(),
        )
    except ValueError as e:
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "refused_cache_write",
                    "detail": str(e),
                    "live_http": False,
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            err=True,
        )
        raise typer.Exit(2) from e

    try:
        rel_path = path.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        rel_path = path.relative_to(path.anchor).as_posix() if path.is_absolute() else path.as_posix()
        markers = ("outputs/market_data/us_daily_bars/", "market_data/us_daily_bars/")
        if not any(rel_path.startswith(p) for p in markers):
            rel_path = f"outputs/market_data/us_daily_bars/{norm}.json"

    typer.echo(
        json.dumps(
            {
                "status": "success",
                "symbol": norm,
                "bar_count": len(rows),
                "cache_written_to": rel_path,
                "live_http": False,
                "raw_response_included": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@debug_app.command("us-daily-bars-cache-preview")
def debug_us_daily_bars_cache_preview(
    path: Path = typer.Option(..., "--path", help="US daily bars cache JSON (envelope or fixture)."),
    symbol: Optional[str] = typer.Option(
        None,
        "--symbol",
        help="Optional symbol filter (normalized); mismatch yields invalid preview.",
    ),
    fmt: str = typer.Option(
        "markdown",
        "--format",
        help="markdown | json",
    ),
) -> None:
    """Preview/diagnose a local US daily bars cache JSON file (no HTTP, no cache write)."""

    expect = symbol.strip() if isinstance(symbol, str) and symbol.strip() else None
    preview = build_us_daily_bars_cache_preview(Path(path), expect_symbol=expect)
    fmt_norm = fmt.strip().lower()
    if fmt_norm == "json":
        typer.echo(format_us_daily_bars_cache_preview_json(preview))
    elif fmt_norm == "markdown":
        typer.echo(format_us_daily_bars_cache_preview_markdown(preview))
    else:
        typer.echo("us-daily-bars-cache-preview: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    raise typer.Exit(0 if preview.get("validation_status") == "ok" else 1)


@debug_app.command("us-daily-bars-cache-inventory")
def debug_us_daily_bars_cache_inventory(
    cache_root: Path = typer.Option(
        ...,
        "--cache-root",
        help="Directory of US daily bars cache JSON files ({SYMBOL}.json).",
    ),
    watchlist_path: Optional[Path] = typer.Option(
        None,
        "--watchlist-path",
        help="Optional US watchlist YAML; default is config/us_watchlist.yaml when no --symbol.",
    ),
    symbol: Optional[list[str]] = typer.Option(
        None,
        "--symbol",
        help="Repeatable symbol filter; when set, ignores default watchlist.",
    ),
    fmt: str = typer.Option(
        "markdown",
        "--format",
        help="markdown | json",
    ),
) -> None:
    """Read-only inventory of US daily bars cache files (no HTTP, no cache write)."""

    syms = [s for s in (symbol or []) if str(s).strip()] or None
    inventory = build_us_daily_bars_cache_inventory(
        cache_root,
        symbols=syms,
        watchlist_path=watchlist_path,
    )
    fmt_norm = fmt.strip().lower()
    if fmt_norm == "json":
        typer.echo(format_us_daily_bars_cache_inventory_json(inventory))
    elif fmt_norm == "markdown":
        typer.echo(format_us_daily_bars_cache_inventory_markdown(inventory))
    else:
        typer.echo("us-daily-bars-cache-inventory: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    bad = sum(
        1
        for row in inventory.get("rows") or []
        if row.get("status") in ("missing", "invalid")
    )
    raise typer.Exit(0 if bad == 0 else 1)


@debug_app.command("us-daily-bars-cache-metrics")
def debug_us_daily_bars_cache_metrics(
    path: Path = typer.Option(..., "--path", help="US daily bars cache JSON (envelope or fixture)."),
    symbol: Optional[str] = typer.Option(
        None,
        "--symbol",
        help="Optional symbol filter (normalized); mismatch yields invalid metrics.",
    ),
    fmt: str = typer.Option(
        "markdown",
        "--format",
        help="markdown | json",
    ),
) -> None:
    """Basic metrics diagnostics for a local US daily bars cache JSON (no HTTP, no cache write)."""

    expect = symbol.strip() if isinstance(symbol, str) and symbol.strip() else None
    metrics = build_us_daily_bars_cache_metrics_preview(Path(path), expect_symbol=expect)
    fmt_norm = fmt.strip().lower()
    if fmt_norm == "json":
        typer.echo(format_us_daily_bars_cache_metrics_json(metrics))
    elif fmt_norm == "markdown":
        typer.echo(format_us_daily_bars_cache_metrics_markdown(metrics))
    else:
        typer.echo("us-daily-bars-cache-metrics: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    raise typer.Exit(0 if metrics.get("status") == "ok" else 1)


@debug_app.command("us-cache-signals-preview")
def debug_us_cache_signals_preview(
    path: Path = typer.Option(..., "--path", help="US daily bars cache JSON (envelope or fixture)."),
    symbol: Optional[str] = typer.Option(
        None,
        "--symbol",
        help="Optional symbol filter (normalized); mismatch yields invalid preview.",
    ),
    fmt: str = typer.Option(
        "markdown",
        "--format",
        help="markdown | json",
    ),
    universe_path: Optional[Path] = typer.Option(
        None,
        "--universe-path",
        help="Optional US asset universe JSON; when set, adds universe metadata to output.",
    ),
) -> None:
    """US cache-only signals diagnostics for a local envelope JSON (no HTTP, no cache write)."""

    expect = symbol.strip() if isinstance(symbol, str) and symbol.strip() else None
    preview = build_us_cache_signals_preview(Path(path), expect_symbol=expect)
    if universe_path is not None:
        preview = attach_us_asset_universe_metadata_to_signals_preview(
            preview, Path(universe_path)
        )
    fmt_norm = fmt.strip().lower()
    if fmt_norm == "json":
        typer.echo(format_us_cache_signals_preview_json(preview))
    elif fmt_norm == "markdown":
        typer.echo(format_us_cache_signals_preview_markdown(preview))
    else:
        typer.echo("us-cache-signals-preview: --format must be markdown or json", err=True)
        raise typer.Exit(2)
    raise typer.Exit(0 if preview.get("status") == "ok" else 1)


@debug_app.command("us-provider-preview")
def debug_us_provider_preview(
    symbol: str = typer.Option(..., "--symbol", help="US symbol (normalized for preview/cache path)."),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        help="alpha_vantage_preview | stooq_preview | manual_file (defaults to config/us_market_data.yaml).",
    ),
) -> None:
    """Emit JSON URL/query preview for a planned US provider (Main R2; no HTTP)."""

    payload = build_us_provider_preview_plan(symbol, provider)
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload.get("status") != "preview_ok":
        raise typer.Exit(2)


@debug_app.command("us-provider-live-preview")
def debug_us_provider_live_preview(
    symbol: str = typer.Option(..., "--symbol", help="Single US symbol (Main R3: MSFT smoke path)."),
    provider: str = typer.Option(
        ...,
        "--provider",
        help="stooq_preview only (Main R3).",
    ),
    live: bool = typer.Option(
        False,
        "--live",
        help="Perform one gated HTTP GET (requires CONFIRM_US_LIVE_HTTP=YES). Default: dry_run, no HTTP.",
    ),
) -> None:
    """Stooq-only shape digest preview. No cache write; never emits raw CSV."""

    prov = provider.strip()
    if prov != "stooq_preview":
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "unsupported_provider",
                    "provider_input": prov,
                    "detail": "Main R3 implements stooq_preview only.",
                    "live_http_performed": False,
                    "raw_response_included": False,
                    "cache_write_performed": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        raise typer.Exit(2)

    payload = stooq_live_preview_shape_digest(symbol, live=live)
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    st = payload.get("status")
    if st == "dry_run" or st == "live_preview_ok":
        raise typer.Exit(0)
    if st == "validation_error":
        raise typer.Exit(2)
    raise typer.Exit(1)


@debug_app.command("us-provider-cache-preview")
def debug_us_provider_cache_preview(
    symbol: str = typer.Option(..., "--symbol", help="Single US symbol (Main R4: MSFT smoke path)."),
    provider: str = typer.Option(
        ...,
        "--provider",
        help="stooq_preview only (Main R4).",
    ),
    live: bool = typer.Option(
        False,
        "--live",
        help="Perform one gated Stooq HTTP GET (requires CONFIRM_US_LIVE_HTTP=YES).",
    ),
    write_cache: bool = typer.Option(
        False,
        "--write-cache",
        help="Persist sanitized bars (requires CONFIRM_US_CACHE_WRITE=YES; implies successful parse after live GET).",
    ),
) -> None:
    """Stooq → strict sanitized OHLCV; optional gated cache write. Never emits raw CSV."""

    prov = provider.strip()
    if prov != "stooq_preview":
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "unsupported_provider",
                    "provider_input": prov,
                    "detail": "Main R4 implements stooq_preview only.",
                    "live_http_performed": False,
                    "raw_response_included": False,
                    "cache_write_performed": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        raise typer.Exit(2)

    payload = stooq_live_preview_sanitized_bars(symbol, live=live, write_cache=write_cache)
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    st = payload.get("status")
    if st in ("dry_run", "preview_ok", "success"):
        raise typer.Exit(0)
    if st == "validation_error":
        raise typer.Exit(2)
    raise typer.Exit(1)


@debug_app.command("us-provider-cache-preview-batch")
def debug_us_provider_cache_preview_batch(
    symbols_csv: Optional[str] = typer.Option(
        None,
        "--symbols",
        help="Comma-separated US symbols (merged after --from-watchlist when both set).",
    ),
    from_watchlist: bool = typer.Option(
        False,
        "--from-watchlist",
        help="Include symbols from config/us_watchlist.yaml (normalized; YAML-native dedupe).",
    ),
    provider: str = typer.Option("stooq_preview", "--provider", help="stooq_preview only (Main R5)."),
    live: bool = typer.Option(
        False,
        "--live",
        help="Perform gated Stooq HTTP GET per symbol (requires CONFIRM_US_LIVE_HTTP=YES). Operator-only.",
    ),
    write_cache: bool = typer.Option(
        False,
        "--write-cache",
        help="Batch rejects cache writes Main R5; use debug us-provider-cache-preview.",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        min=1,
        help="Maximum normalized symbols processed after merging inputs (invalid rows unaffected).",
    ),
    markdown: bool = typer.Option(
        False,
        "--markdown",
        help="Emit copy-ready Markdown recap (counts only; JSON canonical for results[]). Main R5.3.",
    ),
) -> None:
    """Multi-symbol Stooq cache preview aggregation (dry-run default; optional gated live loop)."""

    merged: list[str] = []
    if from_watchlist:
        merged.extend(symbols_from_us_watchlist_file())
    if symbols_csv:
        merged.extend([p.strip() for p in str(symbols_csv).split(",") if p.strip()])
    out = run_stooq_cache_preview_batch(
        merged,
        provider=provider,
        live=live,
        write_cache=write_cache,
        limit=limit,
    )
    if markdown:
        typer.echo(render_us_provider_cache_preview_batch_markdown(out), nl=False)
    else:
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
    st_top = str(out.get("status") or "")
    if st_top == "validation_error":
        raise typer.Exit(2)
    raise typer.Exit(0)


@debug_app.command("us-provider-scheduled-ingest-plan")
def debug_us_provider_scheduled_ingest_plan(
    symbols_csv: Optional[str] = typer.Option(
        None,
        "--symbols",
        help="Comma-separated US symbols (merged after --from-watchlist when both set).",
    ),
    from_watchlist: bool = typer.Option(
        False,
        "--from-watchlist",
        help="Include symbols from config/us_watchlist.yaml (normalized; YAML-native dedupe).",
    ),
    provider: str = typer.Option("stooq_preview", "--provider", help="stooq_preview only (Main R6.1 plan)."),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        min=1,
        help="Maximum normalized symbols after merge (invalid rows unaffected).",
    ),
    markdown: bool = typer.Option(
        False,
        "--markdown",
        help="Emit copy-ready Markdown plan (JSON canonical for plan_rows). Main R6.1.",
    ),
) -> None:
    """Dry-run scheduled ingest plan (**no HTTP**, **no cache write**, **no scheduler**)."""

    merged, fw, csv_ok = merged_symbols_for_scheduled_ingest_plan(
        from_watchlist=from_watchlist,
        symbols_csv=symbols_csv,
    )
    out = build_us_provider_scheduled_ingest_plan(
        merged,
        provider=provider,
        from_watchlist_used=fw,
        symbols_csv_provided=csv_ok,
        limit_param=limit,
    )
    if markdown:
        typer.echo(render_us_provider_scheduled_ingest_plan_markdown(out), nl=False)
    else:
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
    st_top = str(out.get("status") or "")
    if st_top == "validation_error":
        raise typer.Exit(2)
    raise typer.Exit(0)


@debug_app.command("us-provider-manual-live-batch-smoke")
def debug_us_provider_manual_live_batch_smoke(
    symbols_csv: Optional[str] = typer.Option(
        None,
        "--symbols",
        help="Comma-separated US symbols (merged after --from-watchlist when both set).",
    ),
    from_watchlist: bool = typer.Option(
        False,
        "--from-watchlist",
        help="Include symbols from config/us_watchlist.yaml (normalized; YAML-native dedupe).",
    ),
    provider: str = typer.Option(
        "stooq_preview",
        "--provider",
        help="stooq_preview only (R6.3 dry-run / R6.4.0 preflight / R6.4.1 bounded live preview).",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        min=1,
        help="Maximum normalized symbols after merge (invalid rows unaffected).",
    ),
    max_http: int = typer.Option(
        0,
        "--max-http",
        min=0,
        help="HTTP cap per run; zero with --live or --execute-live-http is validation_error.",
    ),
    live: bool = typer.Option(
        False,
        "--live",
        help="Required for --preflight and --execute-live-http; alone returns scaffold refusal.",
    ),
    preflight: bool = typer.Option(
        False,
        "--preflight",
        help="Validate gate + cap readiness (R6.4.0); requires --live; no vendor HTTP unless --execute-live-http also set.",
    ),
    execute_live_http: bool = typer.Option(
        False,
        "--execute-live-http",
        help="R6.4.1: bounded live HTTP; requires --live --preflight + CONFIRM_US_LIVE_HTTP=YES + CONFIRM_US_MANUAL_BATCH_SMOKE=YES + --max-http > 0; no cache write.",
    ),
    evaluate_cache_write: bool = typer.Option(
        False,
        "--evaluate-cache-write",
        help="R6.5.1 refusal scaffold only: evaluates cache-write intent and always refuses; no cache write.",
    ),
    execute_cache_write: bool = typer.Option(
        False,
        "--execute-cache-write",
        help="R6.5.7: production cache write; requires --live --preflight --execute-live-http --evaluate-cache-write + all 3 env gates + --max-http > 0.",
    ),
    markdown: bool = typer.Option(
        False,
        "--markdown",
        help="Emit copy-ready Markdown recap (JSON canonical).",
    ),
) -> None:
    """Manual live batch smoke (**R6.5.7**): production cache write + refusal scaffold + bounded live HTTP."""

    merged, fw, csv_ok = merged_symbols_for_scheduled_ingest_plan(
        from_watchlist=from_watchlist,
        symbols_csv=symbols_csv,
    )
    out = build_us_provider_manual_live_batch_smoke_payload(
        merged,
        provider=provider,
        from_watchlist_used=fw,
        symbols_csv_provided=csv_ok,
        limit_param=limit,
        max_http=max_http,
        live_requested=live,
        preflight_requested=preflight,
        execute_live_http_requested=execute_live_http,
        evaluate_cache_write_requested=evaluate_cache_write,
        execute_cache_write_requested=execute_cache_write,
    )
    if markdown:
        typer.echo(render_manual_live_batch_smoke_markdown(out), nl=False)
    else:
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
    st_top = str(out.get("status") or "")
    if st_top == "validation_error":
        raise typer.Exit(2)
    raise typer.Exit(0)


@debug_app.command("jquants-watchlist-bars-cache")
def debug_jquants_watchlist_bars_cache(
    from_date: str = typer.Option(
        ...,
        "--from-date",
        help="Range start YYYY-MM-DD or YYYYMMDD (pairs with --to-date).",
    ),
    to_date: str = typer.Option(
        ...,
        "--to-date",
        help="Range end YYYY-MM-DD or YYYYMMDD (pairs with --from-date).",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        min=1,
        help="Process only the first N JP watchlist tickers (order preserved).",
    ),
    live: bool = typer.Option(
        False,
        "--live",
        help="Bulk live HTTP (requires JQUANTS_ALLOW_LIVE_HTTP=true and CONFIRM_LIVE_HTTP=YES).",
    ),
    write_cache: bool = typer.Option(
        False,
        "--write-cache",
        help="Write sanitized cache per code (requires --live; CONFIRM_LIVE_HTTP=YES is required for any --live).",
    ),
    codes: Optional[str] = typer.Option(
        None,
        "--codes",
        help="Comma-separated wire codes (overrides jp_watchlist). Invalid tokens become skipped rows in results.",
    ),
) -> None:
    """Bulk JP watchlist → V2 daily bars; default dry-run previews only (no HTTP, no cache writes)."""

    fn = from_date.strip()
    tn = to_date.strip()
    client = JQuantsClient.from_env()

    if write_cache and not live:
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "write_cache_requires_live",
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            err=True,
        )
        raise typer.Exit(2)

    if live and os.environ.get("CONFIRM_LIVE_HTTP") != "YES":
        typer.echo(
            json.dumps(
                {
                    "status": "live_blocked",
                    "reason": "confirm_live_http_required",
                    "detail": "Set CONFIRM_LIVE_HTTP=YES for any bulk --live HTTP (read-only or --write-cache).",
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            err=True,
        )
        raise typer.Exit(2)

    verr = client.validate_daily_quotes_cli_args(None, date=None, from_date=fn, to_date=tn)
    if verr is not None:
        view = _jquants_daily_quotes_cli_snapshot(verr, code=None, from_date=fn, to_date=tn, date_opt=None)
        typer.echo(json.dumps(view, ensure_ascii=False, indent=2))
        raise typer.Exit(1)

    try:
        tickers, csv_skipped_tokens = _resolve_watchlist_bars_cache_tickers(codes_csv=codes, limit=limit)
    except (FileNotFoundError, ValueError, OSError) as e:
        typer.echo(
            json.dumps({"status": "error", "reason": "watchlist_load_failed", "detail": str(e), "raw_response_included": False}),
            ensure_ascii=False,
            indent=2,
        )
        raise typer.Exit(1) from e

    if _parse_codes_csv(codes) is not None and not tickers:
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "codes_csv_no_valid_wire_codes",
                    "skipped_unsupported_code_tokens": csv_skipped_tokens,
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        raise typer.Exit(1)

    codes_mode = _parse_codes_csv(codes) is not None
    target_total = len(tickers) + len(csv_skipped_tokens) if codes_mode else len(tickers)

    results: list[dict[str, Any]] = []
    for bad in csv_skipped_tokens:
        results.append(
            _watchlist_bars_cache_row(
                code=bad,
                status="skipped_unsupported_code",
                reason="invalid_jquants_wire_code",
            )
        )
    cache_written_count = 0
    effective_write = bool(write_cache)

    if not live:
        for raw in tickers:
            wire = normalize_jquants_equity_code(str(raw))
            if wire is None:
                results.append(
                    _watchlist_bars_cache_row(
                        code=(str(raw) or "").strip(),
                        status="skipped_unsupported_code",
                        reason="invalid_jquants_wire_code",
                    )
                )
                continue
            prv = client.build_v2_daily_bars_request_preview(wire, date=None, from_date=fn, to_date=tn)
            if prv.get("status") == "ok":
                results.append(
                    _watchlist_bars_cache_row(
                        code=wire,
                        status="preview_ok",
                        full_url_without_secrets=prv.get("full_url_without_secrets"),
                    )
                )
            else:
                rsn = prv.get("reason")
                results.append(
                    _watchlist_bars_cache_row(
                        code=wire,
                        status="preview_error",
                        reason=str(rsn) if isinstance(rsn, str) else "preview_failed",
                    )
                )

        skipped_count = sum(1 for r in results if r.get("status") == "skipped_unsupported_code")
        non_skip = [r for r in results if r.get("status") != "skipped_unsupported_code"]
        success_count = sum(1 for r in non_skip if r.get("status") == "preview_ok")
        error_count = len(non_skip) - success_count
        out: dict[str, Any] = {
            "status": "dry_run",
            "mode": "jquants_watchlist_cache_preview",
            "date_from": fn,
            "date_to": tn,
            "target_count": target_total,
            "success_count": success_count,
            "error_count": error_count,
            "skipped_count": skipped_count,
            "cache_written_count": 0,
            "failed_codes": [str(r.get("code")) for r in non_skip if r.get("status") != "preview_ok"],
            "results": results,
            "live_http_performed": False,
            "raw_response_included": False,
        }
        crq = _norm_watchlist_codes_csv_requested(codes)
        if crq is not None:
            out["codes_requested"] = crq
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
        raise typer.Exit(0 if error_count == 0 else 1)

    for raw in tickers:
        wire = normalize_jquants_equity_code(str(raw))
        if wire is None:
            results.append(
                _watchlist_bars_cache_row(
                    code=(str(raw) or "").strip(),
                    status="skipped_unsupported_code",
                    reason="invalid_jquants_wire_code",
                )
            )
            continue

        result = client.get_daily_quotes(
            wire,
            date=None,
            from_date=fn,
            to_date=tn,
            attempt_live=True,
            return_sanitized_bars=True,
        )
        st = result.get("status")

        if st == "success":
            rc = result.get("row_count")
            sb = result.get("sanitized_bar_count")
            if not isinstance(sb, int):
                sbl = result.get("sanitized_bars")
                sb = len(sbl) if isinstance(sbl, list) else None
            path_rel: str | None = None
            if effective_write:
                bars = result.get("sanitized_bars")
                if isinstance(bars, list) and bars:
                    path = save_jquants_daily_bars_cache(
                        wire,
                        bars,
                        source="jquants_v2_equities_bars_daily",
                        fetched_at=utc_now_iso(),
                        generated_at=None,
                    )
                    try:
                        path_rel = str(path.relative_to(ROOT_DIR)).replace("\\", "/")
                    except ValueError:
                        path_rel = str(path).replace("\\", "/")
                    cache_written_count += 1
                else:
                    st = "cache_not_written"
                    result = dict(result)
                    result["reason"] = "no_sanitized_rows"
            results.append(
                _watchlist_bars_cache_row(
                    code=wire,
                    status=st if isinstance(st, str) else "error",
                    row_count=rc if isinstance(rc, int) else None,
                    sanitized_bar_count=sb,
                    cache_written_to=path_rel,
                    reason=result.get("reason") if st == "cache_not_written" else None,
                )
            )
            continue

        if st == "sanitized_empty":
            results.append(
                _watchlist_bars_cache_row(
                    code=wire,
                    status="sanitized_empty",
                    row_count=result.get("row_count"),
                    sanitized_bar_count=0,
                    cache_written_to=None,
                    reason=result.get("reason") if isinstance(result.get("reason"), str) else "sanitized_empty",
                )
            )
            continue

        snap = _jquants_daily_quotes_cli_snapshot(result, code=wire, from_date=fn, to_date=tn, date_opt=None)
        results.append(_watchlist_bars_cache_row_from_snap(wire, snap, result))

    skipped_count = sum(1 for r in results if r.get("status") == "skipped_unsupported_code")
    non_skip = [r for r in results if r.get("status") != "skipped_unsupported_code"]
    success_count = sum(1 for r in non_skip if r.get("status") == "success")
    error_count = len(non_skip) - success_count
    failed_codes_live = [str(r.get("code")) for r in non_skip if r.get("status") != "success"]
    out_live: dict[str, Any] = {
        "status": "completed",
        "mode": "jquants_watchlist_cache_live",
        "date_from": fn,
        "date_to": tn,
        "target_count": target_total,
        "success_count": success_count,
        "error_count": error_count,
        "skipped_count": skipped_count,
        "cache_written_count": cache_written_count,
        "failed_codes": failed_codes_live,
        "results": results,
        "live_http_performed": True,
        "raw_response_included": False,
    }
    crq_live = _norm_watchlist_codes_csv_requested(codes)
    if crq_live is not None:
        out_live["codes_requested"] = crq_live
    typer.echo(json.dumps(out_live, ensure_ascii=False, indent=2))

    raise typer.Exit(0 if error_count == 0 else 1)


@app.command("source-generated-tracking-plan")
def source_generated_tracking_plan_command(
    source_repo_path: Optional[str] = typer.Option(None, "--source-repo-path"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest"),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
) -> None:
    from invis_alpha_os.security.security_outputs import (
        sync_security_outputs_to_reports_repo,
        write_security_outputs,
    )
    from invis_alpha_os.security.source_generated_tracking_plan import build_source_generated_tracking_plan

    run_date = report_date or today_jst_iso()
    src = Path(source_repo_path) if source_repo_path else ROOT_DIR
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "security"
    result = build_source_generated_tracking_plan(source_repo_path=src)
    paths = write_security_outputs(
        out_dir=out_root,
        report_date=run_date,
        basename="source_generated_tracking_plan",
        markdown_text=result.markdown_text,
        json_payload=result.json_payload,
        write_latest=write_latest,
        write_archive=write_archive,
    )
    for key, p in paths.items():
        typer.echo(f"source-generated-tracking-plan: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo("source-generated-tracking-plan: --reports-repo-path required with sync", err=True)
            raise typer.Exit(2)
        sync_paths = sync_security_outputs_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            basename="source_generated_tracking_plan",
            markdown_text=result.markdown_text,
            json_payload=result.json_payload,
        )
        for key, p in sync_paths.items():
            typer.echo(f"source-generated-tracking-plan: {key}={p}")
    raise typer.Exit(0)


@app.command("leakage-retained-hit-triage")
def leakage_retained_hit_triage_command(
    source_repo_path: Optional[str] = typer.Option(None, "--source-repo-path"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest"),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
) -> None:
    from invis_alpha_os.security.leakage_retained_hit_triage import build_leakage_retained_hit_triage
    from invis_alpha_os.security.security_outputs import (
        sync_security_outputs_to_reports_repo,
        write_security_outputs,
    )

    run_date = report_date or today_jst_iso()
    src = Path(source_repo_path) if source_repo_path else ROOT_DIR
    reports = Path(reports_repo_path) if reports_repo_path else None
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "security"
    result = build_leakage_retained_hit_triage(source_repo_path=src, reports_repo_path=reports)
    paths = write_security_outputs(
        out_dir=out_root,
        report_date=run_date,
        basename="leakage_retained_hit_triage",
        markdown_text=result.markdown_text,
        json_payload=result.json_payload,
        write_latest=write_latest,
        write_archive=write_archive,
    )
    for key, p in paths.items():
        typer.echo(f"leakage-retained-hit-triage: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo("leakage-retained-hit-triage: --reports-repo-path required with sync", err=True)
            raise typer.Exit(2)
        sync_paths = sync_security_outputs_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            basename="leakage_retained_hit_triage",
            markdown_text=result.markdown_text,
            json_payload=result.json_payload,
        )
        for key, p in sync_paths.items():
            typer.echo(f"leakage-retained-hit-triage: {key}={p}")
    raise typer.Exit(0)


@app.command("github-settings-manual-evidence-template")
def github_settings_manual_evidence_template_command(
    repo: str = typer.Option("RUotani/invest-alpha-os", "--repo"),
    source_repo_path: Optional[str] = typer.Option(None, "--source-repo-path"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest"),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
) -> None:
    from invis_alpha_os.security.github_settings_manual_evidence_template import (
        build_github_settings_manual_evidence_template,
    )
    from invis_alpha_os.security.security_outputs import (
        sync_security_outputs_to_reports_repo,
        write_security_outputs,
    )

    run_date = report_date or today_jst_iso()
    root = Path(source_repo_path) if source_repo_path else ROOT_DIR
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "security"
    result = build_github_settings_manual_evidence_template(repo=repo, repo_root=root)
    paths = write_security_outputs(
        out_dir=out_root,
        report_date=run_date,
        basename="github_settings_manual_evidence_template",
        markdown_text=result.markdown_text,
        json_payload=result.json_payload,
        write_latest=write_latest,
        write_archive=write_archive,
    )
    for key, p in paths.items():
        typer.echo(f"github-settings-manual-evidence-template: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo("github-settings-manual-evidence-template: --reports-repo-path required", err=True)
            raise typer.Exit(2)
        sync_paths = sync_security_outputs_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            basename="github_settings_manual_evidence_template",
            markdown_text=result.markdown_text,
            json_payload=result.json_payload,
        )
        for key, p in sync_paths.items():
            typer.echo(f"github-settings-manual-evidence-template: {key}={p}")
    raise typer.Exit(0)


@app.command("security-leakage-audit")
def security_leakage_audit_command(
    source_repo_path: Optional[str] = typer.Option(None, "--source-repo-path", help="Source repo root."),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path", help="Reports-private clone."),
    out_dir: Optional[str] = typer.Option(None, "--out-dir", help="Output root (default: outputs/security)."),
    report_date: Optional[str] = typer.Option(None, "--report-date", help="ISO date label."),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest"),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
) -> None:
    from invis_alpha_os.security.security_leakage_audit import build_security_leakage_audit
    from invis_alpha_os.security.security_outputs import (
        sync_security_outputs_to_reports_repo,
        write_security_outputs,
    )

    run_date = report_date or today_jst_iso()
    src = Path(source_repo_path) if source_repo_path else ROOT_DIR
    reports = Path(reports_repo_path) if reports_repo_path else None
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "security"
    result = build_security_leakage_audit(source_repo_path=src, reports_repo_path=reports)
    paths = write_security_outputs(
        out_dir=out_root,
        report_date=run_date,
        basename="security_leakage_audit",
        markdown_text=result.markdown_text,
        json_payload=result.json_payload,
        write_latest=write_latest,
        write_archive=write_archive,
    )
    for key, p in paths.items():
        typer.echo(f"security-leakage-audit: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo("security-leakage-audit: --reports-repo-path required with sync", err=True)
            raise typer.Exit(2)
        sync_paths = sync_security_outputs_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            basename="security_leakage_audit",
            markdown_text=result.markdown_text,
            json_payload=result.json_payload,
        )
        for key, p in sync_paths.items():
            typer.echo(f"security-leakage-audit: {key}={p}")
    raise typer.Exit(0 if result.json_payload.get("overall_status") == "pass" else 1)


@app.command("github-actions-security-audit")
def github_actions_security_audit_command(
    repo_path: Optional[str] = typer.Option(None, "--repo-path", help="Repo root for workflow scan."),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest"),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
) -> None:
    from invis_alpha_os.security.github_actions_security_audit import build_github_actions_security_audit
    from invis_alpha_os.security.security_outputs import (
        sync_security_outputs_to_reports_repo,
        write_security_outputs,
    )

    run_date = report_date or today_jst_iso()
    repo = Path(repo_path) if repo_path else ROOT_DIR
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "security"
    result = build_github_actions_security_audit(repo_path=repo)
    paths = write_security_outputs(
        out_dir=out_root,
        report_date=run_date,
        basename="github_actions_security_audit",
        markdown_text=result.markdown_text,
        json_payload=result.json_payload,
        write_latest=write_latest,
        write_archive=write_archive,
    )
    for key, p in paths.items():
        typer.echo(f"github-actions-security-audit: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo("github-actions-security-audit: --reports-repo-path required with sync", err=True)
            raise typer.Exit(2)
        sync_paths = sync_security_outputs_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            basename="github_actions_security_audit",
            markdown_text=result.markdown_text,
            json_payload=result.json_payload,
        )
        for key, p in sync_paths.items():
            typer.echo(f"github-actions-security-audit: {key}={p}")
    raise typer.Exit(0)


@app.command("dependency-security-audit")
def dependency_security_audit_command(
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest"),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
) -> None:
    from invis_alpha_os.security.dependency_security_audit import build_dependency_security_audit
    from invis_alpha_os.security.security_outputs import (
        sync_security_outputs_to_reports_repo,
        write_security_outputs,
    )

    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "security"
    result = build_dependency_security_audit()
    paths = write_security_outputs(
        out_dir=out_root,
        report_date=run_date,
        basename="dependency_security_audit",
        markdown_text=result.markdown_text,
        json_payload=result.json_payload,
        write_latest=write_latest,
        write_archive=write_archive,
    )
    for key, p in paths.items():
        typer.echo(f"dependency-security-audit: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo("dependency-security-audit: --reports-repo-path required with sync", err=True)
            raise typer.Exit(2)
        sync_paths = sync_security_outputs_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            basename="dependency_security_audit",
            markdown_text=result.markdown_text,
            json_payload=result.json_payload,
        )
        for key, p in sync_paths.items():
            typer.echo(f"dependency-security-audit: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-manual-data-dry-run-preflight")
def weekly_candidate_brief_manual_data_dry_run_preflight_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    targets: str = typer.Option("5802,6645,5801,285A,5803", "--targets"),
    input_path: Optional[str] = typer.Option(None, "--input-path"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest"),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
) -> None:
    from invis_alpha_os.reports.manual_data_dry_run_preflight import build_manual_data_dry_run_preflight
    from invis_alpha_os.security.security_outputs import (
        sync_security_outputs_to_reports_repo,
        write_security_outputs,
    )

    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    result = build_manual_data_dry_run_preflight(
        report_date=run_date,
        repo_root=ROOT_DIR,
        targets_csv=targets,
        input_path=input_path,
    )
    paths = write_security_outputs(
        out_dir=out_root,
        report_date=run_date,
        basename="manual_data_dry_run_preflight",
        markdown_text=result.markdown_text,
        json_payload=result.json_payload,
        write_latest=write_latest,
        write_archive=write_archive,
    )
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-manual-data-dry-run-preflight: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-manual-data-dry-run-preflight: --reports-repo-path required",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_security_outputs_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            basename="manual_data_dry_run_preflight",
            markdown_text=result.markdown_text,
            json_payload=result.json_payload,
        )
        for key, p in sync_paths.items():
            typer.echo(f"weekly-candidate-brief-manual-data-dry-run-preflight: {key}={p}")
    raise typer.Exit(0)


@app.command("github-settings-evidence-pack")
def github_settings_evidence_pack_command(
    repo: str = typer.Option("RUotani/invest-alpha-os", "--repo"),
    source_repo_path: Optional[str] = typer.Option(None, "--source-repo-path"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest"),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
) -> None:
    from invis_alpha_os.security.github_settings_evidence_pack import build_github_settings_evidence_pack
    from invis_alpha_os.security.security_outputs import (
        sync_security_outputs_to_reports_repo,
        write_security_outputs,
    )

    run_date = report_date or today_jst_iso()
    root = Path(source_repo_path) if source_repo_path else ROOT_DIR
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "security"
    result = build_github_settings_evidence_pack(repo=repo, repo_root=root)
    paths = write_security_outputs(
        out_dir=out_root,
        report_date=run_date,
        basename="github_settings_evidence_pack",
        markdown_text=result.markdown_text,
        json_payload=result.json_payload,
        write_latest=write_latest,
        write_archive=write_archive,
    )
    for key, p in paths.items():
        typer.echo(f"github-settings-evidence-pack: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo("github-settings-evidence-pack: --reports-repo-path required with sync", err=True)
            raise typer.Exit(2)
        sync_paths = sync_security_outputs_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            basename="github_settings_evidence_pack",
            markdown_text=result.markdown_text,
            json_payload=result.json_payload,
        )
        for key, p in sync_paths.items():
            typer.echo(f"github-settings-evidence-pack: {key}={p}")
    raise typer.Exit(0)


@app.command("weekly-candidate-brief-manual-data-dry-run-readiness")
def weekly_candidate_brief_manual_data_dry_run_readiness_command(
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    targets: str = typer.Option("5802,6645,5801,285A,5803", "--targets"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest"),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
) -> None:
    from invis_alpha_os.reports.manual_data_dry_run_readiness import build_manual_data_dry_run_readiness
    from invis_alpha_os.security.security_outputs import (
        sync_security_outputs_to_reports_repo,
        write_security_outputs,
    )

    run_date = report_date or today_jst_iso()
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "chatgpt_context"
    result = build_manual_data_dry_run_readiness(
        report_date=run_date,
        repo_root=ROOT_DIR,
        targets_csv=targets,
    )
    paths = write_security_outputs(
        out_dir=out_root,
        report_date=run_date,
        basename="manual_data_dry_run_readiness",
        markdown_text=result.markdown_text,
        json_payload=result.json_payload,
        write_latest=write_latest,
        write_archive=write_archive,
    )
    for key, p in paths.items():
        typer.echo(f"weekly-candidate-brief-manual-data-dry-run-readiness: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo(
                "weekly-candidate-brief-manual-data-dry-run-readiness: --reports-repo-path required",
                err=True,
            )
            raise typer.Exit(2)
        sync_paths = sync_security_outputs_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            basename="manual_data_dry_run_readiness",
            markdown_text=result.markdown_text,
            json_payload=result.json_payload,
        )
        for key, p in sync_paths.items():
            typer.echo(f"weekly-candidate-brief-manual-data-dry-run-readiness: {key}={p}")
    raise typer.Exit(0)


@app.command("github-repo-settings-checklist")
def github_repo_settings_checklist_command(
    repo: str = typer.Option("RUotani/invest-alpha-os", "--repo"),
    source_repo_path: Optional[str] = typer.Option(None, "--source-repo-path"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest"),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
) -> None:
    from invis_alpha_os.security.github_repo_settings_checklist import build_github_repo_settings_checklist
    from invis_alpha_os.security.security_outputs import (
        sync_security_outputs_to_reports_repo,
        write_security_outputs,
    )

    run_date = report_date or today_jst_iso()
    root = Path(source_repo_path) if source_repo_path else ROOT_DIR
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "security"
    result = build_github_repo_settings_checklist(repo=repo, repo_root=root)
    paths = write_security_outputs(
        out_dir=out_root,
        report_date=run_date,
        basename="github_repo_settings_checklist",
        markdown_text=result.markdown_text,
        json_payload=result.json_payload,
        write_latest=write_latest,
        write_archive=write_archive,
    )
    for key, p in paths.items():
        typer.echo(f"github-repo-settings-checklist: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo("github-repo-settings-checklist: --reports-repo-path required with sync", err=True)
            raise typer.Exit(2)
        sync_paths = sync_security_outputs_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            basename="github_repo_settings_checklist",
            markdown_text=result.markdown_text,
            json_payload=result.json_payload,
        )
        for key, p in sync_paths.items():
            typer.echo(f"github-repo-settings-checklist: {key}={p}")
    raise typer.Exit(0)


@app.command("security-dashboard")
def security_dashboard_command(
    source_repo_path: Optional[str] = typer.Option(None, "--source-repo-path"),
    reports_repo_path: Optional[str] = typer.Option(None, "--reports-repo-path"),
    out_dir: Optional[str] = typer.Option(None, "--out-dir"),
    report_date: Optional[str] = typer.Option(None, "--report-date"),
    export_targets_csv: str = typer.Option("5802,6645,5801,285A,5803", "--export-targets-csv"),
    manual_evidence_json: Optional[str] = typer.Option(
        None,
        "--manual-evidence-json",
        help="Path to filled github_settings_manual_evidence_template.json (default: outputs/security/latest).",
    ),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest"),
    write_archive: bool = typer.Option(True, "--write-archive/--no-write-archive"),
    sync_github_reports_repo: bool = typer.Option(False, "--sync-github-reports-repo"),
) -> None:
    from invis_alpha_os.security.github_settings_manual_evidence_ingest import (
        load_github_settings_manual_evidence,
    )
    from invis_alpha_os.security.security_dashboard import build_security_dashboard
    from invis_alpha_os.security.security_outputs import (
        sync_security_outputs_to_reports_repo,
        write_security_outputs,
    )

    run_date = report_date or today_jst_iso()
    src = Path(source_repo_path) if source_repo_path else ROOT_DIR
    reports = Path(reports_repo_path) if reports_repo_path else None
    out_root = Path(out_dir) if out_dir else OUTPUTS_DIR / "security"
    evidence_path = Path(manual_evidence_json) if manual_evidence_json else None
    manual_evidence = load_github_settings_manual_evidence(repo_root=src, evidence_path=evidence_path)
    result = build_security_dashboard(
        source_repo_path=src,
        reports_repo_path=reports,
        report_date=run_date,
        export_targets_csv=export_targets_csv,
        manual_evidence=manual_evidence,
    )
    paths = write_security_outputs(
        out_dir=out_root,
        report_date=run_date,
        basename="security_dashboard",
        markdown_text=result.markdown_text,
        json_payload=result.json_payload,
        write_latest=write_latest,
        write_archive=write_archive,
    )
    for key, p in paths.items():
        typer.echo(f"security-dashboard: {key}={p}")
    if sync_github_reports_repo:
        if not reports_repo_path:
            typer.echo("security-dashboard: --reports-repo-path required with sync", err=True)
            raise typer.Exit(2)
        sync_paths = sync_security_outputs_to_reports_repo(
            reports_repo_path=Path(reports_repo_path),
            repo_root=ROOT_DIR,
            report_date=run_date,
            basename="security_dashboard",
            markdown_text=result.markdown_text,
            json_payload=result.json_payload,
        )
        for key, p in sync_paths.items():
            typer.echo(f"security-dashboard: {key}={p}")
    raise typer.Exit(0)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
