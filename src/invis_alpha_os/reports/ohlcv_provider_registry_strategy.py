"""OHLCV provider automation reports (design/dry-run only; no live HTTP)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.data.ohlcv_provider_approval import (
    ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
    CACHE_WRITE_APPROVAL_PHRASE,
    build_default_provider_approval_package,
)
from invis_alpha_os.data.cross_provider_validation_runbook import (
    build_cross_provider_validation_runbook_pack,
)
from invis_alpha_os.data.cross_provider_validation_result_review import (
    build_cross_provider_validation_result_review,
)
from invis_alpha_os.data.cache_write_readiness_gate import (
    build_cache_write_readiness_gate,
)
from invis_alpha_os.data.cache_write_operator_signoff_sheet import (
    build_cache_write_operator_signoff_sheet,
)
from invis_alpha_os.data.cache_path_preflight_approval_package import (
    DEFAULT_CANDIDATE_CACHE_PATH,
    build_cache_path_preflight_approval_package,
)
from invis_alpha_os.data.cache_purge_inventory_dryrun_contract import (
    build_cache_purge_inventory_dryrun_contract,
)
from invis_alpha_os.data.cache_write_pilot_approval_packet import (
    build_cache_write_pilot_approval_packet,
)
from invis_alpha_os.data.cache_write_pilot_result_review_gate import (
    build_cache_write_pilot_result_review_gate,
)
from invis_alpha_os.data.actual_import_readiness_boundary import (
    build_actual_import_readiness_boundary,
)
from invis_alpha_os.data.ohlcv_provider_execution import (
    ProviderExecutionMode,
    build_provider_safe_execution_harness,
)
from invis_alpha_os.data.ohlcv_provider_approval_request import (
    DRAFT_HANDOFF_MARKER,
    build_provider_execution_approval_request,
)
from invis_alpha_os.data.ohlcv_provider_runbook import (
    ProviderApprovedExecutionScenario,
    build_provider_approved_execution_runbook,
)
from invis_alpha_os.data.ohlcv_provider_registry import (
    CANONICAL_OHLCV_COLUMNS,
    JQUANTS_APPROVAL_PHRASE,
    MANUAL_IMPORT_APPROVAL_PHRASE,
    ProviderPriorityPolicy,
    PUBLIC_OHLCV_APPROVAL_PHRASE,
    build_default_ohlcv_provider_registry,
    build_provider_coverage_matrix,
    score_provider_freshness,
)
from invis_alpha_os.data.tiingo_current_docs_recheck import (
    build_tiingo_current_docs_recheck_pack,
)
from invis_alpha_os.data.tiingo_manual_signoff_ledger import (
    build_tiingo_manual_signoff_ledger,
)
from invis_alpha_os.data.tiingo_live_fetch_result_review import (
    build_tiingo_live_fetch_result_review_pack,
)
from invis_alpha_os.data.us_ohlcv_provider_selection import (
    build_us_ohlcv_provider_selection_matrix,
)
from invis_alpha_os.data.us_ohlcv_pilot_approval_bundle import (
    build_us_ohlcv_pilot_approval_bundle,
)
from invis_alpha_os.data.us_provider_current_evidence import (
    build_us_provider_current_evidence_pack,
)

CONTRACT_DATA_TO = "2026-03-06"
JP_SAMPLE_TICKERS = ("285A", "5802", "5803", "6645", "5801")
US_SAMPLE_TICKERS = ("NVDA", "MSFT", "AVGO", "TSLA", "MSTR", "COIN")


@dataclass(frozen=True)
class OhlcvProviderAutomationCoreResult:
    reports: dict[str, tuple[str, dict[str, Any]]]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _payload_base(report_date: str, *, name: str) -> dict[str, Any]:
    return {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "pack_version": "v36",
        "report_name": name,
        "dry_run_only": True,
        "live_http_executed": False,
        "cache_write_executed": False,
        "actual_import_executed": False,
        "secrets_printed": False,
        "broker_manual_raw_data_printed": False,
    }


def _registry() -> Any:
    return build_default_ohlcv_provider_registry()


def build_ohlcv_provider_registry_strategy(*, report_date: str) -> tuple[str, dict[str, Any]]:
    registry = _registry()
    providers = [spec.to_dict() for spec in registry.list()]
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="ohlcv_provider_registry_strategy"),
        "canonical_columns": list(CANONICAL_OHLCV_COLUMNS),
        "contract_data_available_to": CONTRACT_DATA_TO,
        "provider_registry_status": "implemented_dry_run_core",
        "provider_selection_policy": {
            "JP": ["jquants", "stooq_manual", "yahoo_manual", "stooq_live_gated"],
            "US": ["stooq_manual", "yahoo_manual", "stooq_live_gated", "alpha_vantage_gated", "tiingo_gated", "polygon_gated"],
            "ETF": ["stooq_manual", "yahoo_manual", "stooq_live_gated", "alpha_vantage_gated", "tiingo_gated", "polygon_gated"],
        },
        "manual_csv_is_fallback_not_primary": True,
        "providers": providers,
    }
    lines = [
        "# OHLCV Provider Registry Strategy",
        "",
        "## 3行サマリー",
        "- Provider registry core is implemented as dry-run planning only.",
        "- Live providers are represented as gated specs; no HTTP/cache/import is executed.",
        "- Manual CSV remains fallback, not primary automation.",
        "",
        "## Canonical output",
        f"- {', '.join(CANONICAL_OHLCV_COLUMNS)}",
        "",
        "## Providers",
        "| provider | market | role | live_http | approval_required | recommendation |",
        "|---|---|---|---|---|---|",
    ]
    for prov in providers:
        lines.append(
            f"| {prov['provider']} | {','.join(prov['markets'])} | {prov['role']} | "
            f"{str(prov['live_http']).lower()} | {str(prov['approval_required']).lower()} | {prov['recommendation']} |"
        )
    return "\n".join(lines), payload


def build_ohlcv_provider_coverage_matrix(*, report_date: str) -> tuple[str, dict[str, Any]]:
    matrix = build_provider_coverage_matrix(_registry())
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="ohlcv_provider_coverage_matrix"),
        "sample_tickers": {"JP": list(JP_SAMPLE_TICKERS), "US": list(US_SAMPLE_TICKERS)},
        "matrix": matrix.to_dict()["rows"],
    }
    lines = [
        "# OHLCV Provider Coverage Matrix",
        "",
        "## 3行サマリー",
        "- Coverage is evaluated from static provider specs and existing dry-run assumptions.",
        "- No provider fetch, cache write, or raw data read is performed.",
        "- JP sample includes 285A to preserve alphanumeric ticker coverage.",
        "",
        "| provider | market | role | live_http | approval_required | recommendation |",
        "|---|---|---|---|---|---|",
    ]
    for row in payload["matrix"]:
        lines.append(
            f"| {row['provider']} | {row['market']} | {row['role']} | "
            f"{str(row['live_http']).lower()} | {str(row['approval_required']).lower()} | {row['recommendation']} |"
        )
    return "\n".join(lines), payload


def build_ohlcv_provider_freshness_strategy(*, report_date: str) -> tuple[str, dict[str, Any]]:
    scores = [
        score_provider_freshness(
            ticker=t,
            market="JP",
            provider="jquants",
            latest_date=CONTRACT_DATA_TO,
            reference_date=report_date,
        ).to_dict()
        for t in JP_SAMPLE_TICKERS
    ]
    scores.extend(
        score_provider_freshness(
            ticker=t,
            market="US",
            provider="us_daily_bars_cache",
            latest_date=None,
            reference_date=report_date,
        ).to_dict()
        for t in US_SAMPLE_TICKERS
    )
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="ohlcv_provider_freshness_strategy"),
        "freshness_scores": scores,
        "strategy": [
            "Prefer existing sanitized cache first.",
            "Use J-Quants only behind explicit gated refresh approval.",
            "Use manual CSV only as fallback when provider automation is blocked.",
            "Use public live providers only to generate approval packages until explicitly approved.",
        ],
    }
    lines = [
        "# OHLCV Provider Freshness Strategy",
        "",
        "## 3行サマリー",
        "- Freshness strategy is cache/spec based and dry-run only.",
        "- JP contract cap is represented explicitly as a strategy constraint.",
        "- US rows stay unknown unless existing cache/report artifacts provide dates.",
        "",
        "| ticker | market | provider | latest_date | status | stale_days |",
        "|---|---|---|---|---|---:|",
    ]
    for row in scores:
        lines.append(
            f"| {row['ticker']} | {row['market']} | {row['provider']} | {row['latest_date']} | "
            f"{row['freshness_status']} | {row['stale_days']} |"
        )
    return "\n".join(lines), payload


def build_ohlcv_provider_selection_planner(*, report_date: str) -> tuple[str, dict[str, Any]]:
    policy = ProviderPriorityPolicy(_registry())
    cases = [
        ("JP primary cache gap", "JP", "285A", False, False, True),
        ("JP gated refresh approved later", "JP", "5802", True, False, True),
        ("US live disabled", "US", "NVDA", False, False, True),
        ("US public approval package", "US", "MSFT", True, False, True),
    ]
    selections = [
        {
            "use_case": name,
            **policy.select(
                market=market,
                ticker=ticker,
                required_date_from=CONTRACT_DATA_TO,
                required_date_to=report_date,
                freshness_required=freshness,
                allow_live_http=allow_live,
                allow_cache_write=allow_cache,
            ).to_dict(),
        }
        for name, market, ticker, allow_live, allow_cache, freshness in cases
    ]
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="ohlcv_provider_selection_planner"),
        "inputs_default": {
            "freshness_required": True,
            "allow_live_http": False,
            "allow_cache_write": False,
        },
        "selections": selections,
    }
    lines = [
        "# OHLCV Provider Selection Planner",
        "",
        "## 3行サマリー",
        "- Planner returns provider choices and approval phrases without executing providers.",
        "- `allow_live_http=false` blocks live providers and selects manual fallback when available.",
        "- Cache write remains disabled in all v36 examples.",
        "",
        "| use_case | selected_provider | fallback | approval_required | reason |",
        "|---|---|---|---|---|",
    ]
    for row in selections:
        lines.append(
            f"| {row['use_case']} | {row['selected_provider']} | {row['fallback_provider']} | "
            f"{str(row['requires_approval']).lower()} | {row['reason']} |"
        )
    return "\n".join(lines), payload


def build_stooq_manual_fallback_generalization(*, report_date: str) -> tuple[str, dict[str, Any]]:
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="stooq_manual_fallback_generalization"),
        "scope": [
            "multi_file_csv_ingestion",
            "filename_ticker_inference",
            "header_normalization",
            "prohibited_column_safety",
            "provider_provenance_metadata",
            "duplicate_handling",
            "per_provider_adjustment_note",
        ],
        "status": "generalized_from_v34_v35_dropzone_flow",
        "prohibited_columns": ["secret", "token", "credential", "account", "broker_account"],
        "provider_metadata": {
            "provider": "stooq_manual",
            "adjustment": "provider_csv_as_supplied",
            "source_timestamp": "manual_file_mtime_or_import_time",
        },
        "duplicate_policy": "ticker_date_duplicate_rows_are_rejected_or_deduped_before_cache_write_approval",
    }
    lines = [
        "# Stooq Manual Fallback Generalization",
        "",
        "## 3行サマリー",
        "- Stooq manual CSV is formalized as fallback, not primary automation.",
        "- Filename ticker inference supports alphanumeric JP codes such as 285A.",
        "- Raw manual/broker data is not printed by this report.",
        "",
        "| item | status |",
        "|---|---|",
    ]
    for item in payload["scope"]:
        lines.append(f"| {item} | covered_by_design |")
    return "\n".join(lines), payload


def build_provider_context_pack_block(*, report_date: str) -> dict[str, Any]:
    registry_md, registry_json = build_ohlcv_provider_registry_strategy(report_date=report_date)
    planner_md, planner_json = build_ohlcv_provider_selection_planner(report_date=report_date)
    approval_md, approval_json = build_ohlcv_provider_approval_package(report_date=report_date)
    harness_md, harness_json = build_ohlcv_provider_safe_execution_harness(report_date=report_date)
    runbook_md, runbook_json = build_ohlcv_provider_approved_execution_runbook(report_date=report_date)
    request_md, request_json = build_ohlcv_provider_execution_approval_request(report_date=report_date)
    us_matrix_md, us_matrix_json = build_us_ohlcv_provider_selection_matrix_report(report_date=report_date)
    current_evidence_md, current_evidence_json = build_us_provider_current_evidence_pack_report(report_date=report_date)
    pilot_bundle_md, pilot_bundle_json = build_us_ohlcv_pilot_approval_bundle_report(report_date=report_date)
    tiingo_recheck_md, tiingo_recheck_json = build_tiingo_current_docs_recheck_pack_report(report_date=report_date)
    tiingo_ledger_md, tiingo_ledger_json = build_tiingo_manual_signoff_ledger_report(report_date=report_date)
    tiingo_result_md, tiingo_result_json = build_tiingo_live_fetch_result_review_report(report_date=report_date)
    cross_provider_md, cross_provider_json = build_cross_provider_validation_runbook_report(report_date=report_date)
    result_review_md, result_review_json = build_cross_provider_validation_result_review_report(report_date=report_date)
    cache_gate_md, cache_gate_json = build_cache_write_readiness_gate_report(report_date=report_date)
    operator_sheet_md, operator_sheet_json = build_cache_write_operator_signoff_sheet_report(report_date=report_date)
    path_preflight_md, path_preflight_json = build_cache_path_preflight_approval_package_report(
        report_date=report_date,
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    )
    purge_contract_md, purge_contract_json = build_cache_purge_inventory_dryrun_contract_report(
        report_date=report_date,
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    )
    pilot_packet_md, pilot_packet_json = build_cache_write_pilot_approval_packet_report(
        report_date=report_date,
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    )
    result_review_gate_md, result_review_gate_json = build_cache_write_pilot_result_review_gate_report(
        report_date=report_date,
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    )
    actual_import_boundary_md, actual_import_boundary_json = build_actual_import_readiness_boundary_report(
        report_date=report_date,
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    )
    _ = (
        registry_md,
        planner_md,
        approval_md,
        harness_md,
        runbook_md,
        request_md,
        us_matrix_md,
        current_evidence_md,
        pilot_bundle_md,
        tiingo_recheck_md,
        tiingo_ledger_md,
        tiingo_result_md,
        cross_provider_md,
        result_review_md,
        cache_gate_md,
        operator_sheet_md,
        path_preflight_md,
        purge_contract_md,
        pilot_packet_md,
        result_review_gate_md,
        actual_import_boundary_md,
    )
    return {
        "provider_registry_status": registry_json["provider_registry_status"],
        "provider_selection_policy": registry_json["provider_selection_policy"],
        "latest_ohlcv_provider_by_ticker": {
            **{ticker: "jquants_or_stooq_manual_fallback" for ticker in JP_SAMPLE_TICKERS},
            **{ticker: "us_daily_bars_cache_or_stooq_manual_fallback" for ticker in US_SAMPLE_TICKERS},
        },
        "fallback_required_tickers": list(JP_SAMPLE_TICKERS),
        "approval_gate_status": {
            "allow_live_http": False,
            "allow_cache_write": False,
            "planner_examples_require_approval": [
                row
                for row in planner_json["selections"]
                if row.get("requires_approval")
            ],
        },
        "provider_approval_package_status": {
            "available": True,
            "dry_run_only": approval_json["dry_run_only"],
            "gates_covered": [
                req["gate"]
                for req in approval_json["package"]["requirements"]
            ],
        },
        "provider_safe_execution_harness_status": {
            "available": True,
            "mode": harness_json["harness"]["result"]["mode"],
            "dry_run_transcript_only": True,
            "current_verdict": harness_json["harness"]["result"]["transcript"]["verdict"],
            "hard_gates_unapproved": [
                gate
                for gate in harness_json["harness"]["result"]["required_gates"]
                if gate not in harness_json["harness"]["result"]["approved_action"]["approved_gates"]
            ],
            "next_required_user_approval_phrase": PUBLIC_OHLCV_APPROVAL_PHRASE,
        },
        "provider_approved_execution_runbook_status": {
            "available": True,
            "source_only": runbook_json["runbook"]["decision_record"]["source_only"],
            "current_phase": "no_live_no_cache_no_import",
            "scenario": runbook_json["runbook"]["scope"]["scenario"],
            "operator_runbook_exists": True,
            "approval_package_exists": True,
            "safe_execution_harness_exists": True,
            "next_required_approval_phrase_by_scenario": {
                item["scenario"]: item["required_approval_phrase"]
                for item in runbook_json["supported_scenarios"]
            },
        },
        "provider_execution_approval_request_status": {
            "available": True,
            "source_only": request_json["approval_request"]["request"]["risk_summary"]["source_only"],
            "current_phase": "no_live_no_cache_no_import",
            "scenario": request_json["approval_request"]["request"]["scope"]["scenario"],
            "approval_package_exists": True,
            "safe_execution_harness_exists": True,
            "operator_runbook_exists": True,
            "execution_approval_request_exists": True,
            "next_human_approval_phrase_by_scenario": {
                item["scenario"]: item["primary_approval_phrase"]
                for item in request_json["supported_scenarios"]
            },
        },
        "us_ohlcv_provider_selection_status": {
            "provider_selected": False,
            "selection_matrix_exists": True,
            "recommended_first_pilot_provider": us_matrix_json["selection_matrix"]["ranking"]["best_first_pilot_provider"],
            "recommended_production_candidate": us_matrix_json["selection_matrix"]["ranking"]["best_production_candidate"],
            "recommended_free_fallback": us_matrix_json["selection_matrix"]["ranking"]["best_free_fallback"],
            "pilot_universe": us_matrix_json["selection_matrix"]["pilot_design"]["pilot_universe"],
            "pilot_date_range": us_matrix_json["selection_matrix"]["pilot_design"]["pilot_date_range"],
            "hard_gates_for_live_test": us_matrix_json["selection_matrix"]["safety"]["hard_gates_required_for_live_test"],
            "cache_write_approved": us_matrix_json["selection_matrix"]["pilot_design"]["cache_write_approved"],
            "actual_import_approved": us_matrix_json["selection_matrix"]["pilot_design"]["actual_import_approved"],
        },
        "us_provider_current_evidence_status": {
            "current_evidence_pack_exists": True,
            "source_only": current_evidence_json["current_evidence_pack"]["safety"]["source_only"],
            "source_accessed_live": False,
            "evidence_confidence": "seed_only / manual_recheck_required",
            "providers": [
                row["provider"]
                for row in current_evidence_json["current_evidence_pack"]["providers"]
            ],
            "evidence_gaps": current_evidence_json["current_evidence_pack"]["evidence_gaps"],
            "needs_current_recheck": True,
            "recommended_first_pilot_recheck": current_evidence_json["current_evidence_pack"][
                "recommended_first_pilot_recheck"
            ],
            "explicitly_not_approved": current_evidence_json["current_evidence_pack"]["safety"][
                "explicitly_not_approved"
            ],
        },
        "us_ohlcv_pilot_approval_bundle_status": {
            "pilot_approval_bundle_exists": True,
            "source_only": pilot_bundle_json["pilot_approval_bundle"]["safety"]["source_only"],
            "commands_executed": pilot_bundle_json["pilot_approval_bundle"]["safety"]["commands_executed"],
            "recommended_first_pilot_provider": pilot_bundle_json["pilot_approval_bundle"]["candidate"]["provider"],
            "scenario": pilot_bundle_json["pilot_approval_bundle"]["candidate"]["scenario"],
            "approval_phrase_required": pilot_bundle_json["pilot_approval_bundle"]["candidate"][
                "primary_approval_phrase"
            ],
            "cache_write_approved": False,
            "actual_import_approved": False,
            "next_step_requires_explicit_human_approval": True,
            "readiness_verdict": pilot_bundle_json["pilot_approval_bundle"]["final_readiness_verdict"],
        },
        "tiingo_current_docs_recheck_status": {
            "recheck_pack_exists": True,
            "source_only": tiingo_recheck_json["tiingo_current_docs_recheck_pack"]["safety"]["source_only"],
            "manual_recheck_required_before_live_fetch": True,
            "pricing_terms_cache_adjustment_rate_limit_signoff_required": True,
            "pilot_approved": False,
            "cache_write_approved": False,
            "actual_import_approved": False,
            "next_action": "manual_recheck_or_explicit_approval_after_recheck",
            "readiness_verdict": tiingo_recheck_json["tiingo_current_docs_recheck_pack"][
                "readiness_verdict"
            ],
        },
        "tiingo_manual_signoff_ledger_status": {
            "manual_signoff_ledger_exists": True,
            "all_items_default_unreviewed": True,
            "source_only": tiingo_ledger_json["tiingo_manual_signoff_ledger"]["safety"]["source_only"],
            "live_fetch_approved": False,
            "cache_write_approved": False,
            "actual_import_approved": False,
            "primary_blocker": tiingo_ledger_json["tiingo_manual_signoff_ledger"]["evidence_summary"][
                "primary_blocker"
            ],
            "next_action": tiingo_ledger_json["tiingo_manual_signoff_ledger"]["next_human_action"],
            "final_verdict": tiingo_ledger_json["tiingo_manual_signoff_ledger"]["final_verdict"],
        },
        "tiingo_live_fetch_result_review_status": {
            "result_review_pack_exists": True,
            "source_only": tiingo_result_json["tiingo_live_fetch_result_review"]["pilot_result"]["safety"][
                "source_only"
            ],
            "v63b_result_status": tiingo_result_json["tiingo_live_fetch_result_review"]["pilot_result"][
                "result_status"
            ],
            "symbols_total": tiingo_result_json["tiingo_live_fetch_result_review"]["pilot_result"]["symbols_total"],
            "symbols_success": tiingo_result_json["tiingo_live_fetch_result_review"]["pilot_result"][
                "symbols_success"
            ],
            "symbols_failed": tiingo_result_json["tiingo_live_fetch_result_review"]["pilot_result"]["symbols_failed"],
            "base_fields_all_present": tiingo_result_json["tiingo_live_fetch_result_review"]["pilot_result"][
                "field_summary"
            ]["base_fields_all_present"],
            "adjusted_fields_all_present": tiingo_result_json["tiingo_live_fetch_result_review"]["pilot_result"][
                "field_summary"
            ]["adjusted_fields_all_present"],
            "raw_data_persisted": tiingo_result_json["tiingo_live_fetch_result_review"]["pilot_result"]["safety"][
                "raw_data_persisted"
            ],
            "cache_write_approved": tiingo_result_json["tiingo_live_fetch_result_review"][
                "cache_write_readiness_assessment"
            ]["cache_write_approved"],
            "actual_import_approved": tiingo_result_json["tiingo_live_fetch_result_review"][
                "cache_write_readiness_assessment"
            ]["actual_import_approved"],
            "next_recommended_task": tiingo_result_json["tiingo_live_fetch_result_review"]["next_step"][
                "recommended_task"
            ],
            "cache_write_readiness": tiingo_result_json["tiingo_live_fetch_result_review"]["verdict"][
                "cache_write_readiness"
            ],
        },
        "cross_provider_validation_runbook_status": {
            "runbook_pack_exists": True,
            "source_only": cross_provider_json["cross_provider_validation_runbook"]["safety_controls"]["source_only"],
            "package_status": cross_provider_json["cross_provider_validation_runbook"]["approval_package"][
                "package_status"
            ],
            "operation": cross_provider_json["cross_provider_validation_runbook"]["approval_package"]["operation"],
            "providers": cross_provider_json["cross_provider_validation_runbook"]["approval_package"]["providers"],
            "optional_providers": cross_provider_json["cross_provider_validation_runbook"]["approval_package"][
                "optional_providers"
            ],
            "universe_count": len(cross_provider_json["cross_provider_validation_runbook"]["universe"]["symbols"]),
            "approval_phrase_issued": cross_provider_json["cross_provider_validation_runbook"]["approval_package"][
                "approval_phrase_issued"
            ],
            "separate_explicit_approval_required": cross_provider_json["cross_provider_validation_runbook"][
                "approval_package"
            ]["separate_explicit_approval_required"],
            "raw_data_persistence_allowed": cross_provider_json["cross_provider_validation_runbook"][
                "approval_package"
            ]["raw_data_persistence_allowed"],
            "cache_write_approved": cross_provider_json["cross_provider_validation_runbook"]["approval_package"][
                "cache_write_approved"
            ],
            "actual_import_approved": cross_provider_json["cross_provider_validation_runbook"]["approval_package"][
                "actual_import_approved"
            ],
            "readiness_verdict": cross_provider_json["cross_provider_validation_runbook"]["readiness_verdict"][
                "cross_provider_validation_execution_readiness"
            ],
            "cache_write_readiness": cross_provider_json["cross_provider_validation_runbook"]["readiness_verdict"][
                "cache_write_readiness"
            ],
            "cursor_handoff_status": cross_provider_json["cross_provider_validation_runbook"]["cursor_handoff"][
                "handoff_status"
            ],
        },
        "cross_provider_validation_result_review_status": {
            "result_review_pack_exists": True,
            "source_only": True,
            "v65_verdict": result_review_json["cross_provider_validation_result_review"]["result_summary"][
                "verdict"
            ],
            "required_providers_available": result_review_json["cross_provider_validation_result_review"][
                "result_summary"
            ]["required_providers_available"],
            "required_provider_symbols_success": result_review_json["cross_provider_validation_result_review"][
                "result_summary"
            ]["required_provider_symbols_success"],
            "tiingo_yahoo_adjusted_close_consistency": result_review_json[
                "cross_provider_validation_result_review"
            ]["result_summary"]["tiingo_yahoo_adjusted_close_consistency"],
            "stooq_adjusted_comparison_suitability": result_review_json[
                "cross_provider_validation_result_review"
            ]["result_summary"]["stooq_adjusted_comparison_suitability"],
            "stooq_base_close_comparison_suitability": result_review_json[
                "cross_provider_validation_result_review"
            ]["result_summary"]["stooq_base_close_comparison_suitability"],
            "nvda_avgo_warning_interpretation": "likely_stooq_series_definition_mismatch_not_tiingo_failure_by_default",
            "tiingo_provider_viability": result_review_json["cross_provider_validation_result_review"][
                "cache_write_readiness"
            ]["live_fetch_provider_viability"],
            "tiingo_adjusted_series_confidence": result_review_json["cross_provider_validation_result_review"][
                "cache_write_readiness"
            ]["tiingo_adjusted_series_confidence"],
            "cache_write_readiness": result_review_json["cross_provider_validation_result_review"][
                "cache_write_readiness"
            ]["cache_write_readiness"],
            "actual_import_readiness": result_review_json["cross_provider_validation_result_review"][
                "cache_write_readiness"
            ]["actual_import_readiness"],
            "next_recommended_task": result_review_json["cross_provider_validation_result_review"]["next_step"][
                "recommended_next_step"
            ],
        },
        "cache_write_readiness_gate_status": {
            "gate_exists": True,
            "source_only": cache_gate_json["cache_write_readiness_gate"]["safety_flags"]["source_only"],
            "gate_status": cache_gate_json["cache_write_readiness_gate"]["gate_status"],
            "signoff16_status": cache_gate_json["cache_write_readiness_gate"]["readiness_verdict"][
                "signoff16_status"
            ],
            "cache_write_approved": cache_gate_json["cache_write_readiness_gate"]["readiness_verdict"][
                "cache_write_approved"
            ],
            "actual_import_approved": cache_gate_json["cache_write_readiness_gate"]["readiness_verdict"][
                "actual_import_approved"
            ],
            "trading_action_approved": cache_gate_json["cache_write_readiness_gate"]["readiness_verdict"][
                "trading_action_approved"
            ],
            "approval_phrase_issued": cache_gate_json["cache_write_readiness_gate"]["readiness_verdict"][
                "approval_phrase_issued"
            ],
            "cache_write_readiness": cache_gate_json["cache_write_readiness_gate"]["readiness_verdict"][
                "cache_write_readiness"
            ],
            "actual_import_readiness": cache_gate_json["cache_write_readiness_gate"]["readiness_verdict"][
                "actual_import_readiness"
            ],
            "cache_location": cache_gate_json["cache_write_readiness_gate"]["storage_policy"]["cache_location"],
            "raw_data_git_allowed": cache_gate_json["cache_write_readiness_gate"]["storage_policy"][
                "raw_data_git_allowed"
            ],
            "raw_data_reports_private_allowed": cache_gate_json["cache_write_readiness_gate"]["storage_policy"][
                "raw_data_reports_private_allowed"
            ],
            "redacted_summary_reports_private_allowed": cache_gate_json["cache_write_readiness_gate"][
                "storage_policy"
            ]["redacted_summary_reports_private_allowed"],
            "future_cache_write_pilot_status": cache_gate_json["cache_write_readiness_gate"][
                "future_cache_write_pilot"
            ]["package_status"],
            "future_cache_write_pilot_subset": cache_gate_json["cache_write_readiness_gate"][
                "future_cache_write_pilot"
            ]["recommended_first_subset"],
            "next_cursor_handoff_status": cache_gate_json["cache_write_readiness_gate"]["next_cursor_handoff"][
                "handoff_status"
            ],
        },
        "cache_write_operator_signoff_sheet_status": {
            "sheet_exists": True,
            "source_only": operator_sheet_json["cache_write_operator_signoff_sheet"]["safety_flags"]["source_only"],
            "operator_signoff_status": operator_sheet_json["cache_write_operator_signoff_sheet"][
                "readiness_verdict"
            ]["operator_signoff_status"],
            "overall_readiness": operator_sheet_json["cache_write_operator_signoff_sheet"]["readiness_verdict"][
                "overall_readiness"
            ],
            "cache_write_approval_status": operator_sheet_json["cache_write_operator_signoff_sheet"][
                "readiness_verdict"
            ]["cache_write_approval_status"],
            "cache_write_execution_status": operator_sheet_json["cache_write_operator_signoff_sheet"][
                "readiness_verdict"
            ]["cache_write_execution_status"],
            "actual_import_approval_status": operator_sheet_json["cache_write_operator_signoff_sheet"][
                "readiness_verdict"
            ]["actual_import_approval_status"],
            "actual_import_execution_status": operator_sheet_json["cache_write_operator_signoff_sheet"][
                "readiness_verdict"
            ]["actual_import_execution_status"],
            "cache_path_proposed": operator_sheet_json["cache_write_operator_signoff_sheet"][
                "cache_location_checklist"
            ]["cache_path_proposed"],
            "cache_path_unset_blocks_readiness": operator_sheet_json["cache_write_operator_signoff_sheet"][
                "cache_location_checklist"
            ]["cache_path_unset_blocks_readiness"],
            "approval_phrase_issued": operator_sheet_json["cache_write_operator_signoff_sheet"][
                "approval_phrase_boundary"
            ]["cache_write_approval_phrase_issued"],
            "next_task": operator_sheet_json["cache_write_operator_signoff_sheet"]["next_cursor_handoff_draft"][
                "next_task"
            ],
        },
        "cache_path_preflight_approval_package_status": {
            "package_exists": True,
            "source_only": path_preflight_json["cache_path_preflight_approval_package"]["safety_flags"][
                "source_only"
            ],
            "package_status": path_preflight_json["cache_path_preflight_approval_package"]["package_status"],
            "preflight_verdict": path_preflight_json["cache_path_preflight_approval_package"][
                "readiness_verdict"
            ]["preflight_verdict"],
            "all_structural_checks_pass": path_preflight_json["cache_path_preflight_approval_package"][
                "readiness_verdict"
            ]["all_structural_checks_pass"],
            "candidate_cache_path": path_preflight_json["cache_path_preflight_approval_package"][
                "cache_path_preflight"
            ]["candidate_cache_path"],
            "path_expansion_performed": path_preflight_json["cache_path_preflight_approval_package"][
                "cache_path_preflight"
            ]["path_expansion_performed"],
            "filesystem_probe_performed": path_preflight_json["cache_path_preflight_approval_package"][
                "cache_path_preflight"
            ]["filesystem_probe_performed"],
            "directory_created": path_preflight_json["cache_path_preflight_approval_package"][
                "cache_path_preflight"
            ]["directory_created"],
            "cache_write_approval_status": path_preflight_json["cache_path_preflight_approval_package"][
                "readiness_verdict"
            ]["cache_write_approval_status"],
            "actual_import_approval_status": path_preflight_json["cache_path_preflight_approval_package"][
                "readiness_verdict"
            ]["actual_import_approval_status"],
            "approval_phrase_issued": path_preflight_json["cache_path_preflight_approval_package"][
                "readiness_verdict"
            ]["approval_phrase_issued"],
            "next_task": path_preflight_json["cache_path_preflight_approval_package"]["context_summary"][
                "next_task"
            ],
        },
        "cache_purge_inventory_dryrun_contract_status": {
            "contract_exists": True,
            "source_only": purge_contract_json["cache_purge_inventory_dryrun_contract"]["safety_flags"][
                "source_only"
            ],
            "contract_status": purge_contract_json["cache_purge_inventory_dryrun_contract"]["contract_status"],
            "contract_verdict": purge_contract_json["cache_purge_inventory_dryrun_contract"]["readiness_verdict"][
                "contract_verdict"
            ],
            "candidate_cache_path": purge_contract_json["cache_purge_inventory_dryrun_contract"][
                "candidate_cache_path"
            ],
            "redacted_manifest_schema_status": purge_contract_json["cache_purge_inventory_dryrun_contract"][
                "readiness_verdict"
            ]["redacted_manifest_schema_status"],
            "purge_execution_status": purge_contract_json["cache_purge_inventory_dryrun_contract"][
                "readiness_verdict"
            ]["purge_execution_status"],
            "cache_write_approval_status": purge_contract_json["cache_purge_inventory_dryrun_contract"][
                "readiness_verdict"
            ]["cache_write_approval_status"],
            "actual_import_approval_status": purge_contract_json["cache_purge_inventory_dryrun_contract"][
                "readiness_verdict"
            ]["actual_import_approval_status"],
            "file_deletion_executed": purge_contract_json["cache_purge_inventory_dryrun_contract"]["safety_flags"][
                "file_deletion_executed"
            ],
            "raw_ohlcv_read": purge_contract_json["cache_purge_inventory_dryrun_contract"]["safety_flags"][
                "raw_ohlcv_read"
            ],
            "next_task": purge_contract_json["cache_purge_inventory_dryrun_contract"]["context_summary"][
                "next_task"
            ],
        },
        "cache_write_pilot_approval_packet_status": {
            "packet_exists": True,
            "source_only": pilot_packet_json["cache_write_pilot_approval_packet"]["safety_flags"]["source_only"],
            "packet_status": pilot_packet_json["cache_write_pilot_approval_packet"]["packet_status"],
            "packet_verdict": pilot_packet_json["cache_write_pilot_approval_packet"]["readiness_verdict"][
                "packet_verdict"
            ],
            "provider": pilot_packet_json["cache_write_pilot_approval_packet"]["future_pilot_identity"][
                "provider"
            ],
            "first_subset": pilot_packet_json["cache_write_pilot_approval_packet"]["future_pilot_identity"][
                "first_subset"
            ],
            "candidate_cache_path": pilot_packet_json["cache_write_pilot_approval_packet"][
                "future_pilot_identity"
            ]["candidate_cache_path"],
            "cache_write_approval_status": pilot_packet_json["cache_write_pilot_approval_packet"][
                "readiness_verdict"
            ]["cache_write_approval_status"],
            "actual_import_approval_status": pilot_packet_json["cache_write_pilot_approval_packet"][
                "readiness_verdict"
            ]["actual_import_approval_status"],
            "approval_phrase_issued": pilot_packet_json["cache_write_pilot_approval_packet"][
                "readiness_verdict"
            ]["approval_phrase_issued"],
            "raw_ohlcv_persisted": pilot_packet_json["cache_write_pilot_approval_packet"]["safety_flags"][
                "raw_ohlcv_persisted"
            ],
            "next_task": pilot_packet_json["cache_write_pilot_approval_packet"]["context_summary"]["next_task"],
        },
        "cache_write_pilot_result_review_gate_status": {
            "gate_exists": True,
            "source_only": result_review_gate_json["cache_write_pilot_result_review_gate"]["safety_flags"][
                "source_only"
            ],
            "review_status": result_review_gate_json["cache_write_pilot_result_review_gate"]["review_status"],
            "current_verdict": result_review_gate_json["cache_write_pilot_result_review_gate"][
                "readiness_verdict"
            ]["result_review_verdict"],
            "pilot_has_run": result_review_gate_json["cache_write_pilot_result_review_gate"][
                "readiness_verdict"
            ]["pilot_has_run"],
            "actual_import_readiness": result_review_gate_json["cache_write_pilot_result_review_gate"][
                "readiness_verdict"
            ]["actual_import_readiness"],
            "trading_readiness": result_review_gate_json["cache_write_pilot_result_review_gate"][
                "readiness_verdict"
            ]["trading_readiness"],
            "raw_ohlcv_emitted": result_review_gate_json["cache_write_pilot_result_review_gate"]["safety_flags"][
                "raw_ohlcv_emitted"
            ],
            "next_task": result_review_gate_json["cache_write_pilot_result_review_gate"]["context_summary"][
                "next_task"
            ],
        },
        "actual_import_readiness_boundary_status": {
            "boundary_exists": True,
            "source_only": actual_import_boundary_json["actual_import_readiness_boundary"]["safety_flags"][
                "source_only"
            ],
            "boundary_status": actual_import_boundary_json["actual_import_readiness_boundary"]["boundary_status"],
            "actual_import_readiness": actual_import_boundary_json["actual_import_readiness_boundary"][
                "readiness_verdict"
            ]["actual_import_readiness"],
            "cache_write_pilot_readiness": actual_import_boundary_json["actual_import_readiness_boundary"][
                "readiness_verdict"
            ]["cache_write_pilot_readiness"],
            "cache_write_pilot_result_review_readiness": actual_import_boundary_json[
                "actual_import_readiness_boundary"
            ]["readiness_verdict"]["cache_write_pilot_result_review_readiness"],
            "cache_write_approval_does_not_imply_actual_import": actual_import_boundary_json[
                "actual_import_readiness_boundary"
            ]["approval_phrase_boundary"]["cache_write_approval_does_not_imply_actual_import"],
            "result_review_pass_not_sufficient_for_actual_import": actual_import_boundary_json[
                "actual_import_readiness_boundary"
            ]["approval_phrase_boundary"]["result_review_pass_not_sufficient_for_actual_import"],
            "actual_import_approval_phrase_issued": actual_import_boundary_json[
                "actual_import_readiness_boundary"
            ]["approval_phrase_boundary"]["actual_import_approval_phrase_issued"],
            "actual_import_execution_allowed_now": actual_import_boundary_json["actual_import_readiness_boundary"][
                "readiness_verdict"
            ]["actual_import_execution_allowed_now"],
            "trading_readiness": actual_import_boundary_json["actual_import_readiness_boundary"][
                "readiness_verdict"
            ]["trading_readiness"],
            "next_task": actual_import_boundary_json["actual_import_readiness_boundary"]["context_summary"][
                "next_task"
            ],
        },
        "manual_csv_is_fallback_not_primary": True,
    }


def build_ohlcv_provider_automation_core(*, report_date: str) -> OhlcvProviderAutomationCoreResult:
    reports = {
        "ohlcv_provider_registry_strategy": build_ohlcv_provider_registry_strategy(report_date=report_date),
        "ohlcv_provider_coverage_matrix": build_ohlcv_provider_coverage_matrix(report_date=report_date),
        "ohlcv_provider_freshness_strategy": build_ohlcv_provider_freshness_strategy(report_date=report_date),
        "ohlcv_provider_selection_planner": build_ohlcv_provider_selection_planner(report_date=report_date),
        "stooq_manual_fallback_generalization": build_stooq_manual_fallback_generalization(report_date=report_date),
    }
    context_block = build_provider_context_pack_block(report_date=report_date)
    context_md = "\n".join(
        [
            "# ChatGPT Context Pack Provider Block",
            "",
            "## 3行サマリー",
            "- Provider registry status can be embedded into the context pack.",
            "- Manual CSV is marked fallback, not primary.",
            "- Approval gates remain false until Cursor/human approval.",
            "",
            f"- provider_registry_status: {context_block['provider_registry_status']}",
            f"- manual_csv_is_fallback_not_primary: {str(context_block['manual_csv_is_fallback_not_primary']).lower()}",
        ]
    )
    reports["chatgpt_invest_context_pack"] = (
        context_md,
        {**_payload_base(report_date, name="chatgpt_invest_context_pack_provider_block"), **context_block},
    )
    cache_md = "\n".join(
        [
            "# Cache Refresh Readiness",
            "",
            "## 3行サマリー",
            "- v36 creates a readiness summary only.",
            "- No live HTTP/cache write/actual import is executed.",
            "- Cursor should generate real local reports after approval gates are set.",
        ]
    )
    reports["cache_refresh_readiness"] = (
        cache_md,
        {
            **_payload_base(report_date, name="cache_refresh_readiness_provider_gate_summary"),
            "readiness": "approval_package_required_before_live_or_cache_write",
        },
    )
    return OhlcvProviderAutomationCoreResult(reports=reports)


def build_ohlcv_provider_approval_package(*, report_date: str) -> tuple[str, dict[str, Any]]:
    package = build_default_provider_approval_package(report_date=report_date)
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="ohlcv_provider_approval_package"),
        "pack_version": "v39",
        "package": package.to_dict(),
    }
    requirements = payload["package"]["requirements"]
    plan = payload["package"]["execution_plan"]
    lines = [
        "# OHLCV Provider Approval Package",
        "",
        "## Executive Summary",
        "",
        "- This package is source-only and preview-only.",
        "- All dangerous provider execution actions remain blocked until explicit approval.",
        "- No live HTTP, cache write, actual refresh/import, manual import, secret display, or raw data handling is executed.",
        "",
        "## Current Freshness / Coverage Context",
        "",
        f"- report_date: {report_date}",
        "- JP sample: 285A, 5802, 5803, 6645, 5801",
        "- US sample: NVDA, MSFT, AVGO, TSLA, MSTR, COIN",
        "- Registry state: v36 provider registry core is available on source main.",
        "",
        "## Proposed Provider Execution Plan",
        "",
        "| order | title | preview_only | required_gates | stop_conditions |",
        "|---:|---|---|---|---|",
    ]
    for step in plan["steps"]:
        lines.append(
            f"| {step['order']} | {step['title']} | {str(step['preview_only']).lower()} | "
            f"{', '.join(step['required_gates']) or '(none)'} | {', '.join(step['stop_conditions'])} |"
        )
    lines.extend(
        [
            "",
            "## Actions Requiring Explicit Approval",
            "",
            "| gate | action | default_status | approval_required | approval_phrase |",
            "|---|---|---|---|---|",
        ]
    )
    for req in requirements:
        lines.append(
            f"| {req['gate']} | {req['action']} | {req['default_status']} | "
            f"{str(req['explicit_user_approval_required']).lower()} | {req['approval_phrase'] or '(separate approval required)'} |"
        )
    lines.extend(
        [
            "",
            "## Safety Gates",
            "",
            "| gate | safe_by_default_behavior | expected_artifacts |",
            "|---|---|---|",
        ]
    )
    for req in requirements:
        lines.append(
            f"| {req['gate']} | {req['safe_by_default_behavior']} | {', '.join(req['expected_artifacts'])} |"
        )
    lines.extend(
        [
            "",
            "## Expected Outputs",
            "",
            "- `latest/ohlcv_provider_approval_package.md`",
            "- `latest/ohlcv_provider_approval_package.json`",
            "- `weekly/2026/{report_date}/ohlcv_provider_approval_package.md`",
            "- `weekly/2026/{report_date}/ohlcv_provider_approval_package.json`",
            "",
            "## Verification Plan",
            "",
        ]
    )
    for check in plan["verification"]["checks"]:
        lines.append(f"- {check}")
    lines.extend(["", "## Rollback Plan", ""])
    for note in plan["rollback_plan"]["notes"]:
        lines.append(f"- {note}")
    lines.extend(["", "## Stop Conditions", ""])
    for condition in payload["package"]["stop_conditions"]:
        lines.append(f"- {condition}")
    lines.extend(
        [
            "",
            "## Approval Phrases",
            "",
            f"- {PUBLIC_OHLCV_APPROVAL_PHRASE}",
            f"- {JQUANTS_APPROVAL_PHRASE}",
            f"- {CACHE_WRITE_APPROVAL_PHRASE}",
            f"- {ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE}",
            f"- {MANUAL_IMPORT_APPROVAL_PHRASE}",
            "",
            "## Non-Goals",
            "",
        ]
    )
    for non_goal in payload["package"]["non_goals"]:
        lines.append(f"- {non_goal}")
    lines.extend(
        [
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "dry_run_only": payload["dry_run_only"],
                    "gates": [req["gate"] for req in requirements],
                    "safety_summary": payload["package"]["safety_summary"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_ohlcv_provider_safe_execution_harness(*, report_date: str) -> tuple[str, dict[str, Any]]:
    harness = build_provider_safe_execution_harness(
        report_date=report_date,
        mode=ProviderExecutionMode.DRY_RUN_TRANSCRIPT,
    )
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="ohlcv_provider_safe_execution_harness"),
        "pack_version": "v41",
        "harness": harness.to_dict(),
    }
    result = payload["harness"]["result"]
    events = result["transcript"]["events"]
    lines = [
        "# OHLCV Provider Safe Execution Harness",
        "",
        "## Executive Summary",
        "",
        "- This harness is source-only and transcript-only.",
        "- It consumes the v39 approval package model and validates gates without executing providers.",
        "- No live HTTP, cache write, actual refresh/import, manual import, secret display, or raw data handling is executed.",
        "",
        "## Approval Package Input Summary",
        "",
        f"- report_date: {report_date}",
        f"- requirements: {len(payload['harness']['approval_package']['requirements'])}",
        f"- safety_summary.live_http_executed: {payload['harness']['approval_package']['safety_summary']['live_http_executed']}",
        "",
        "## Requested Execution Scenario",
        "",
        f"- mode: {result['mode']}",
        f"- requested_action: {result['requested_action']}",
        f"- required_gates: {', '.join(result['required_gates']) or '(none)'}",
        "",
        "## Gate Evaluation",
        "",
        "| gate | approved |",
        "|---|---|",
    ]
    approved = set(result["approved_action"]["approved_gates"])
    for gate in result["required_gates"]:
        lines.append(f"| {gate} | {str(gate in approved).lower()} |")
    if not result["required_gates"]:
        lines.append("| (none) | true |")
    lines.extend(
        [
            "",
            "## Preflight Result",
            "",
            "| check | passed | status | notes |",
            "|---|---|---|---|",
        ]
    )
    for check in result["preflight"]:
        lines.append(
            f"| {check['name']} | {str(check['passed']).lower()} | {check['status']} | {', '.join(check['notes'])} |"
        )
    lines.extend(
        [
            "",
            "## Dry-Run Transcript",
            "",
        ]
    )
    for event in events:
        lines.extend([f"### {event['section']}", event["message"], ""])
    lines.extend(["## Expected Artifacts", ""])
    for item in result["artifact_plan"]["expected_outputs"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Verification Checklist", ""])
    for item in result["verification_checklist"]["items"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Rollback Checklist", ""])
    for item in result["rollback_checklist"]["items"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Stop Conditions", ""])
    for item in result["stop_conditions"]:
        lines.append(f"- {item['label']}: {item['description']}")
    lines.extend(
        [
            "",
            "## Safety Verdict",
            "",
            f"- {result['transcript']['verdict']}",
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "mode": result["mode"],
                    "requested_action": result["requested_action"],
                    "required_gates": result["required_gates"],
                    "verdict": result["transcript"]["verdict"],
                    "audit_summary": result["audit_summary"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_ohlcv_provider_approved_execution_runbook(
    *,
    report_date: str,
    scenario: ProviderApprovedExecutionScenario = ProviderApprovedExecutionScenario.PUBLIC_OHLCV,
) -> tuple[str, dict[str, Any]]:
    runbook = build_provider_approved_execution_runbook(report_date=report_date, scenario=scenario)
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="ohlcv_provider_approved_execution_runbook"),
        "pack_version": "v43",
        "supported_scenarios": [
            {
                "scenario": item.value,
                "required_approval_phrase": build_provider_approved_execution_runbook(
                    report_date=report_date,
                    scenario=item,
                ).approval_requirement.phrase,
            }
            for item in ProviderApprovedExecutionScenario
        ],
        "runbook": runbook.to_dict(),
    }
    rb = payload["runbook"]
    scope = rb["scope"]
    approval = rb["approval_requirement"]
    checklist = rb["checklist"]
    command_plan = rb["command_plan"]
    decision = rb["decision_record"]
    lines = [
        "# OHLCV Provider Approved Execution Runbook",
        "",
        "## Executive Summary",
        "",
        "- This operator runbook is source-only.",
        "- It bridges the v39 approval package and v41 safe execution harness to a future separately approved operation.",
        "- Commands below are plans only and are not executed by this report.",
        "",
        "## Execution Scope",
        "",
        f"- scenario: {scope['scenario']}",
        f"- requested_operation: {scope['requested_operation']}",
        f"- provider_action: {scope['provider_action']}",
        f"- provider_candidates: {', '.join(scope['provider_candidates'])}",
        f"- tickers: {', '.join(scope['tickers'])}",
        f"- date_range: {scope['date_range']}",
        "",
        "## Required Approval Phrase",
        "",
        f"- {approval['phrase']}",
        f"- approval_status: {approval['approval_status']}",
        f"- required_gates: {', '.join(approval['required_gates']) or '(none)'}",
        "",
        "## Explicitly Not Approved",
        "",
    ]
    for item in scope["remains_unapproved"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Operator Preconditions", ""])
    for step in checklist["preconditions"]:
        lines.append(f"- {step['title']}: {step['detail']}")
    lines.extend(["", "## Commands To Run Later", ""])
    for command in command_plan["commands"]:
        lines.append(f"```bash\n{command}\n```")
    lines.extend(["", "## Expected Artifacts", ""])
    for artifact in checklist["artifacts"]:
        lines.append(f"- {artifact}")
    lines.extend(["", "## Preflight Checklist", ""])
    for step in checklist["preflight"]:
        lines.append(f"- {step['title']}: {step['detail']}")
    lines.extend(["", "## Verification Checklist", ""])
    for step in checklist["verification"]:
        lines.append(f"- {step['title']}: {step['detail']}")
    lines.extend(["", "## Rollback Runbook", ""])
    for step in checklist["rollback"]:
        lines.append(f"- {step['title']}: {step['detail']}")
    lines.extend(["", "## Stop Conditions", ""])
    for condition in checklist["stop_conditions"]:
        lines.append(f"- {condition}")
    lines.extend(
        [
            "",
            "## Audit Notes",
            "",
            f"- source_only: {str(decision['source_only']).lower()}",
            f"- approved_in_this_runbook: {str(decision['approved_in_this_runbook']).lower()}",
        ]
    )
    for key, value in decision["audit_flags"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(
        [
            "",
            "## Handoff To Cursor",
            "",
            "- Use this runbook only after a separate explicit approval task exists.",
            "- Confirm scenario, approval phrase, ticker scope, and date range before running any future command.",
            "- Stop if any command would reveal secrets, raw provider/manual data, or touch reports-private from Codex.",
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "scenario": scope["scenario"],
                    "required_approval_phrase": approval["phrase"],
                    "source_only": decision["source_only"],
                    "commands_marked_not_executed": all(
                        command.startswith(command_plan["not_executed_marker"]) or command_plan["not_executed_marker"] in command
                        for command in command_plan["commands"]
                    ),
                    "audit_flags": decision["audit_flags"],
                    "stop_conditions": checklist["stop_conditions"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_ohlcv_provider_execution_approval_request(
    *,
    report_date: str,
    scenario: ProviderApprovedExecutionScenario = ProviderApprovedExecutionScenario.PUBLIC_OHLCV,
) -> tuple[str, dict[str, Any]]:
    bundle = build_provider_execution_approval_request(report_date=report_date, scenario=scenario)
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="ohlcv_provider_execution_approval_request"),
        "pack_version": "v44",
        "supported_scenarios": [
            {
                "scenario": item.value,
                "primary_approval_phrase": build_provider_execution_approval_request(
                    report_date=report_date,
                    scenario=item,
                ).request.decision_prompt.primary_approval_phrase,
            }
            for item in ProviderApprovedExecutionScenario
        ],
        "approval_request": bundle.to_dict(),
    }
    request = payload["approval_request"]["request"]
    scope = request["scope"]
    decision = request["decision_prompt"]
    checklist = request["checklist"]
    evidence = request["evidence"]
    risk = request["risk_summary"]
    lines = [
        "# OHLCV Provider Execution Approval Request",
        "",
        "## Executive Summary",
        "",
        "- This approval request is source-only and human-reviewable.",
        "- It combines v39 approval package, v41 safe execution harness, and v43 operator runbook evidence.",
        "- No live HTTP, cache write, actual refresh/import, manual import, secret display, or raw data handling is executed.",
        "",
        "## Requested Scenario",
        "",
        f"- scenario: {scope['scenario']}",
        f"- requested_operation: {scope['requested_operation']}",
        "",
        "## Why This Is Needed",
        "",
        "- Future provider execution must be separated from source-only planning.",
        "- The human needs one explicit yes/no approval phrase before Cursor/local execution can proceed.",
        "- This packet records scope, evidence, planned commands, rollback, verification, and stop conditions.",
        "",
        "## Scope",
        "",
        f"- provider_candidates: {', '.join(scope['provider_candidates'])}",
        f"- tickers: {', '.join(scope['tickers'])}",
        f"- date_range: {scope['date_range']}",
        "",
        "## Required Human Approval Phrase",
        "",
        f"- {decision['primary_approval_phrase']}",
        f"- final_decision_required: {decision['final_decision_required']}",
        "",
        "## Explicitly Not Approved",
        "",
    ]
    for item in scope["explicitly_not_approved"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Evidence From Approval Package",
            "",
            f"- exists: {str(evidence['approval_package']['exists']).lower()}",
            f"- dry_run_only: {str(evidence['approval_package']['dry_run_only']).lower()}",
            f"- dangerous_gates_default_status: {evidence['approval_package']['dangerous_gates_default_status']}",
            "",
            "## Evidence From Safe Execution Harness",
            "",
            f"- exists: {str(evidence['safe_execution_harness']['exists']).lower()}",
            f"- mode: {evidence['safe_execution_harness']['mode']}",
            f"- verdict: {evidence['safe_execution_harness']['verdict']}",
            "",
            "## Evidence From Operator Runbook",
            "",
            f"- exists: {str(evidence['operator_runbook']['exists']).lower()}",
            f"- source_only: {str(evidence['operator_runbook']['source_only']).lower()}",
            f"- commands_marked_not_executed: {str(evidence['operator_runbook']['commands_marked_not_executed']).lower()}",
            "",
            "## Commands Planned But Not Executed",
            "",
        ]
    )
    for command in request["commands_planned_but_not_executed"]:
        lines.append(f"```bash\n{command}\n```")
    lines.extend(["", "## Required Preconditions", ""])
    for item in checklist["preconditions"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Required Redaction Checks", ""])
    for item in checklist["redaction_checks"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Expected Artifacts", ""])
    for item in checklist["expected_artifacts"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Rollback Plan", ""])
    for item in checklist["rollback_plan"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Verification Plan", ""])
    for item in checklist["verification_plan"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Stop Conditions", ""])
    for item in checklist["stop_conditions"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Final Human Decision",
            "",
            f"- approve_phrase: {decision['primary_approval_phrase']}",
            "- reject_or_modify: provide revised scenario, ticker scope, date range, or rollback requirement.",
            "",
            "## Cursor Execution Handoff Draft",
            "",
            "```text",
            request["cursor_execution_handoff_draft"],
            "```",
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "scenario": scope["scenario"],
                    "primary_approval_phrase": decision["primary_approval_phrase"],
                    "source_only": risk["source_only"],
                    "commands_executed": risk["commands_executed"],
                    "commands_marked_not_executed": all(
                        command.startswith("# NOT EXECUTED")
                        for command in request["commands_planned_but_not_executed"]
                    ),
                    "handoff_marker_present": DRAFT_HANDOFF_MARKER in request["cursor_execution_handoff_draft"],
                    "explicitly_not_approved": scope["explicitly_not_approved"],
                    "audit_flags": risk["audit_flags"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_us_ohlcv_provider_selection_matrix_report(*, report_date: str) -> tuple[str, dict[str, Any]]:
    matrix = build_us_ohlcv_provider_selection_matrix(report_date=report_date)
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="us_ohlcv_provider_selection_matrix"),
        "pack_version": "v46",
        "selection_matrix": matrix.to_dict(),
    }
    data = payload["selection_matrix"]
    ranking = data["ranking"]
    pilot = data["pilot_design"]
    safety = data["safety"]
    lines = [
        "# US OHLCV Provider Selection Matrix",
        "",
        "## Executive Summary",
        "",
        "- US OHLCV provider is not yet selected.",
        "- This matrix is source-only and does not validate provider data live.",
        "- First pilot recommendation is based on planning criteria only; live testing requires explicit approval.",
        "",
        "## Why This Matters For Stock Recommendations",
        "",
        "- Broad US stock recommendations require reliable price, historical OHLCV, adjusted prices, volume, corporate actions, and broad universe coverage.",
        "- Without provider validation, screening output can be stale, unadjusted, incomplete, or legally unsuitable for cache storage.",
        "",
        "## Provider Candidates",
        "",
    ]
    for provider in data["providers"]:
        lines.append(f"- {provider['provider']} ({provider['cost_tier']})")
    lines.extend(["", "## Evaluation Criteria", ""])
    for dimension in data["evaluation_dimensions"]:
        lines.append(f"- {dimension}")
    lines.extend(
        [
            "",
            "## Provider Matrix",
            "",
            "| provider | cost_tier | pilot | production | fallback | rate_limit_risk | cache_terms_review |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for provider in data["providers"]:
        lines.append(
            f"| {provider['provider']} | {provider['cost_tier']} | {provider['fit_for_pilot']} | "
            f"{provider['fit_for_production']} | {provider['fit_for_fallback']} | {provider['rate_limit_risk']} | "
            f"{str(provider['terms_cache_suitability_review_needed']).lower()} |"
        )
    lines.extend(["", "## Free / Low-Cost Options", ""])
    for provider in data["providers"]:
        if provider["cost_tier"] in {"free", "free_limited", "paid_low"}:
            lines.append(f"- {provider['provider']}: {provider['notes']}")
    lines.extend(["", "## Paid / Production Candidates", ""])
    for provider in data["providers"]:
        if provider["cost_tier"] in {"paid_low", "paid_mid", "paid_high"}:
            lines.append(f"- {provider['provider']}: {provider['fit_for_production']}")
    lines.extend(
        [
            "",
            "## Recommended First Pilot",
            "",
            f"- {ranking['best_first_pilot_provider']}",
            f"- production_candidate: {ranking['best_production_candidate']}",
            f"- low_cost_candidate: {ranking['best_low_cost_candidate']}",
            f"- free_fallback: {ranking['best_free_fallback']}",
            "",
            "## Pilot Universe",
            "",
            f"- {', '.join(pilot['pilot_universe'])}",
            "",
            "## Pilot Date Range",
            "",
            f"- {pilot['pilot_date_range']}",
            "",
            "## Success Criteria",
            "",
        ]
    )
    for item in pilot["success_criteria"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Failure Criteria", ""])
    for item in pilot["failure_criteria"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Data Quality Checks", ""])
    for group in ("data_quality_checks", "adjustment_checks", "volume_checks", "symbol_mapping_checks", "rate_limit_checks"):
        lines.append(f"### {group}")
        for item in pilot[group]:
            lines.append(f"- {item}")
        lines.append("")
    lines.extend(["## Hard Gates Required For Live Testing", ""])
    for gate in safety["hard_gates_required_for_live_test"]:
        lines.append(f"- {gate}")
    lines.extend(["", "## Explicitly Not Approved", ""])
    for item in safety["explicitly_not_approved"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Missing Evidence", ""])
    for item in data["missing_evidence"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Recommended Next Approval Request",
            "",
            f"- Generate v44 approval request for scenario `public_ohlcv` with provider candidates: {', '.join(pilot['provider_candidates_to_test'])}.",
            "- Do not include cache write or actual import approval in the first pilot request.",
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "provider_selected": False,
                    "providers": [provider["provider"] for provider in data["providers"]],
                    "recommended_first_pilot_provider": ranking["best_first_pilot_provider"],
                    "recommended_production_candidate": ranking["best_production_candidate"],
                    "recommended_free_fallback": ranking["best_free_fallback"],
                    "pilot_universe": pilot["pilot_universe"],
                    "pilot_date_range": pilot["pilot_date_range"],
                    "hard_gates_required_for_live_test": safety["hard_gates_required_for_live_test"],
                    "cache_write_approved": pilot["cache_write_approved"],
                    "actual_import_approved": pilot["actual_import_approved"],
                    "source_only": safety["source_only"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_us_provider_current_evidence_pack_report(*, report_date: str) -> tuple[str, dict[str, Any]]:
    pack = build_us_provider_current_evidence_pack(report_date=report_date)
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="us_provider_current_evidence_pack"),
        "pack_version": "v48",
        "current_evidence_pack": pack.to_dict(),
    }
    data = payload["current_evidence_pack"]
    safety = data["safety"]
    providers = data["providers"]
    lines = [
        "# US OHLCV Provider Current Evidence Pack",
        "",
        "## Executive Summary",
        "",
        "- This pack converts v46 missing evidence into source-only review evidence.",
        "- All provider evidence is seed-only and requires manual current recheck before any live testing.",
        "- Tiingo remains the first pilot candidate; Polygon.io remains the production candidate; Stooq remains fallback only.",
        "",
        "## Evidence Date",
        "",
        f"- report_date: {data['report_date']}",
        f"- evidence_date: {data['evidence_date']}",
        "- source_accessed_live: false",
        "- evidence_confidence: seed_only / manual_recheck_required",
        "",
        "## Why This Evidence Pack Exists",
        "",
        "- v46 intentionally left current pricing/terms, cache suitability, adjusted price method, ADR/delisted coverage, and bulk throughput unverified.",
        "- Live HTTP and provider live access are not approved in this task, so current evidence is represented as recheck requirements, not as verified live facts.",
        "- This prevents a source-only selection matrix from being mistaken for production provider approval.",
        "",
        "## Current v46 Recommendation",
        "",
    ]
    for key, value in data["current_v46_recommendation"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Provider Evidence Table",
            "",
            "| provider | role | needs_current_recheck | evidence_confidence | source_accessed_live | pilot_readiness |",
            "|---|---|---|---|---|---|",
        ]
    )
    for provider in providers:
        lines.append(
            f"| {provider['provider']} | {provider['recommended_role']} | "
            f"{str(provider['needs_current_recheck']).lower()} | {provider['evidence_confidence']} | "
            f"{str(provider['source_accessed_live']).lower()} | {provider['pilot_readiness']} |"
        )
    section_map = (
        ("Pricing / Plan Evidence", "current_pricing_terms"),
        ("Historical OHLCV Evidence", "notes"),
        ("Adjusted Price / Corporate Action Evidence", "adjusted_price_method"),
        ("Coverage / Universe Evidence", "adr_delisted_coverage"),
        ("Bulk / Rate Limit Evidence", "bulk_throughput"),
        ("Terms / Cache Suitability Evidence", "cache_suitability"),
    )
    for heading, key in section_map:
        lines.extend(["", f"## {heading}", ""])
        for provider in providers:
            lines.append(f"- {provider['provider']}: {provider[key]}")
    lines.extend(["", "## Evidence Gaps", ""])
    for gap in data["evidence_gaps"]:
        lines.append(f"- {gap}: needs_current_recheck=true; source_accessed_live=false")
    lines.extend(
        [
            "",
            "## Pilot Readiness Verdict",
            "",
            "- not_approved_for_live_testing",
            "- Tiingo is the first manual recheck target, not an approved live provider.",
            "- Polygon.io remains the production-style candidate, not an approved production source.",
            "- Stooq remains fallback evidence only, not primary production.",
            "",
            "## Recommended First Pilot Recheck",
            "",
        ]
    )
    for item in data["recommended_first_pilot_recheck"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Hard Gates Required For Live Testing", ""])
    for gate in safety["hard_gates_required_for_live_testing"]:
        lines.append(f"- {gate}")
    lines.extend(["", "## Explicitly Not Approved", ""])
    for item in safety["explicitly_not_approved"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Next Approval Request Draft", ""])
    for item in data["next_approval_request_draft"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "provider_selected": False,
                    "providers": [provider["provider"] for provider in providers],
                    "needs_current_recheck": True,
                    "evidence_confidence": "seed_only / manual_recheck_required",
                    "source_accessed_live": False,
                    "recommended_first_pilot_candidate": data["current_v46_recommendation"]["first_pilot_candidate"],
                    "production_candidate": data["current_v46_recommendation"]["production_candidate"],
                    "free_fallback": data["current_v46_recommendation"]["free_fallback"],
                    "hard_gates_required_for_live_testing": safety["hard_gates_required_for_live_testing"],
                    "explicitly_not_approved": safety["explicitly_not_approved"],
                    "source_only": safety["source_only"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_us_ohlcv_pilot_approval_bundle_report(
    *,
    report_date: str,
    provider: str = "tiingo",
    scenario: str = "public_ohlcv",
) -> tuple[str, dict[str, Any]]:
    bundle = build_us_ohlcv_pilot_approval_bundle(
        report_date=report_date,
        provider=provider,
        scenario=scenario,
    )
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="us_ohlcv_pilot_approval_bundle"),
        "pack_version": "v49",
        "pilot_approval_bundle": bundle.to_dict(),
    }
    data = payload["pilot_approval_bundle"]
    candidate = data["candidate"]
    evidence = data["evidence_summary"]
    safety = data["safety"]
    lines = [
        "# US OHLCV Pilot Approval Bundle",
        "",
        "## Executive Summary",
        "",
        "- This is a source-only approval bundle for a future US OHLCV first pilot.",
        "- Tiingo is the default first pilot candidate, but no live fetch is executed here.",
        "- Cache write, actual import, manual import, J-Quants refresh, and trading action remain explicitly not approved.",
        "",
        "## First Pilot Candidate",
        "",
        f"- provider: {candidate['provider']}",
        f"- scenario: {candidate['scenario']}",
        f"- operation: {candidate['operation']}",
        f"- approval_phrase_status: {candidate['approval_phrase_status']}",
        "",
        "## Why Tiingo Is The First Pilot Candidate",
        "",
        "- v46 ranks Tiingo as the first pilot candidate because it balances paid-provider quality, implementation effort, and low-cost pilot fit.",
        "- v48 keeps Tiingo as first pilot candidate while requiring manual current recheck before execution.",
        "- Polygon.io remains the production-style candidate; Stooq remains fallback only.",
        "",
        "## Evidence From Provider Selection Matrix",
        "",
    ]
    for key, value in evidence["provider_selection_matrix"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Evidence From Current Evidence Pack", ""])
    for key, value in evidence["current_evidence_pack"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Pilot Universe",
            "",
            f"- {', '.join(candidate['universe'])}",
            "",
            "## Pilot Date Range",
            "",
            f"- {candidate['date_range']}",
            "",
            "## Required Human Approval Phrase",
            "",
            f"- {candidate['primary_approval_phrase']}",
            "",
            "## Explicitly Not Approved",
            "",
        ]
    )
    for item in safety["explicitly_not_approved"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Commands Planned But Not Executed", ""])
    for command in data["commands_planned_but_not_executed"]:
        lines.extend(["```bash", command, "```"])
    lines.extend(["", "## Preflight Checklist", ""])
    for item in data["preflight_checklist"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Redaction / Secret Handling Checklist", ""])
    for item in data["redaction_secret_handling_checklist"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Expected Outputs", ""])
    for item in data["expected_outputs"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Verification Plan", ""])
    for item in data["verification_plan"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Rollback / No-Write Discipline", ""])
    for item in data["rollback_no_write_discipline"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Stop Conditions", ""])
    for item in data["stop_conditions"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Risk Register", ""])
    lines.extend(["| risk | mitigation | status |", "|---|---|---|"])
    for item in data["risk_register"]:
        lines.append(f"| {item['risk']} | {item['mitigation']} | {item['status']} |")
    lines.extend(["", "## Evidence Gap Closure Checklist", ""])
    lines.extend(["| gap | manual_recheck | operator_signoff |", "|---|---|---|"])
    for item in data["evidence_gap_closure_checklist"]:
        lines.append(f"| {item['gap']} | {item['manual_recheck']} | {item['operator_signoff']} |")
    lines.extend(
        [
            "",
            "## Cursor Handoff Draft",
            "",
            "DRAFT ONLY - DO NOT RUN UNTIL HUMAN APPROVAL PHRASE IS PROVIDED",
            "",
            "```text",
            data["cursor_handoff_draft"],
            "```",
            "",
            "## Final Readiness Verdict",
            "",
            f"- {data['final_readiness_verdict']}",
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "provider": candidate["provider"],
                    "scenario": candidate["scenario"],
                    "pilot_universe": candidate["universe"],
                    "pilot_date_range": candidate["date_range"],
                    "primary_approval_phrase": candidate["primary_approval_phrase"],
                    "primary_approval_phrase_count": 1,
                    "source_only": safety["source_only"],
                    "commands_executed": safety["commands_executed"],
                    "cache_write_approved": False,
                    "actual_import_approved": False,
                    "manual_actual_import_approved": False,
                    "readiness_verdict": data["final_readiness_verdict"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_tiingo_current_docs_recheck_pack_report(*, report_date: str) -> tuple[str, dict[str, Any]]:
    pack = build_tiingo_current_docs_recheck_pack(report_date=report_date)
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="tiingo_current_docs_recheck_pack"),
        "pack_version": "v52",
        "tiingo_current_docs_recheck_pack": pack.to_dict(),
    }
    data = payload["tiingo_current_docs_recheck_pack"]
    safety = data["safety"]
    checklist = data["checklist_items"]

    def lines_for_categories(categories: tuple[str, ...]) -> list[str]:
        rows: list[str] = []
        for item in checklist:
            if item["category"] in categories:
                rows.append(
                    f"- {item['category']}: {item['operator_question']} "
                    f"(signoff: {item['required_signoff']})"
                )
        return rows

    lines = [
        "# Tiingo Current Docs Manual Recheck Pack",
        "",
        "## Executive Summary",
        "",
        "- This pack is source-only and prepares manual Tiingo docs recheck before any live fetch.",
        "- All evidence items require manual recheck; no Tiingo API call or provider live access is performed.",
        "- The default verdict remains manual_recheck_required_before_live_fetch.",
        "",
        "## Why This Pack Exists",
        "",
        "- v49 made Tiingo the first live-fetch-only pilot candidate, but current docs evidence remains unverified.",
        "- Pricing, terms, redistribution, limits, adjustment method, coverage, and cache suitability can change.",
        "- This pack creates operator signoff fields without approving or executing the pilot.",
        "",
        "## Current Pilot Candidate",
        "",
        f"- provider: {data['provider']}",
        f"- scenario: {data['scenario']}",
        f"- pilot_date_range: {data['pilot_date_range']}",
        f"- pilot_universe: {', '.join(data['pilot_universe'])}",
        "",
        "## Official Source References",
        "",
        "| label | reference | needs_manual_recheck | seed_summary |",
        "|---|---|---|---|",
    ]
    for ref in data["official_references"]:
        lines.append(
            f"| {ref['label']} | {ref['url_or_reference']} | "
            f"{str(ref['needs_manual_recheck']).lower()} | {ref['seed_summary']} |"
        )
    section_categories = (
        ("Pricing / Plan Recheck", ("pricing_plan",)),
        (
            "API Limits / Throughput Recheck",
            ("api_limits_unique_symbol_limits_request_limits",),
        ),
        (
            "Terms / Redistribution / Attribution Recheck",
            ("terms_of_use", "redistribution_attribution"),
        ),
        ("Cache Suitability Recheck", ("local_cache_internal_storage_suitability",)),
        ("EOD Coverage Recheck", ("eod_endpoint_coverage",)),
        (
            "Adjusted Price Method Recheck",
            ("adjusted_close_adjusted_ohlc_availability",),
        ),
        (
            "Split / Dividend / Corporate Action Recheck",
            ("split_handling", "dividend_handling"),
        ),
        (
            "ETF / ADR / Mutual Fund / Delisted Coverage Recheck",
            ("etf_coverage", "adr_coverage", "mutual_fund_coverage", "delisted_coverage"),
        ),
        ("Python Implementation Notes", ("python_implementation_approach",)),
        ("Pilot Universe Compatibility", ("pilot_universe_compatibility",)),
    )
    for heading, categories in section_categories:
        lines.extend(["", f"## {heading}", ""])
        lines.extend(lines_for_categories(categories))
        if heading == "Python Implementation Notes":
            for note in data["python_implementation_notes"]:
                lines.append(f"- implementation_note: {note}")
        if heading == "Pilot Universe Compatibility":
            for note in data["pilot_universe_compatibility_notes"]:
                lines.append(f"- compatibility_note: {note}")
    lines.extend(["", "## Manual Sign-off Checklist", ""])
    for item in data["manual_signoff_checklist"]:
        lines.append(f"- [ ] {item}")
    lines.extend(["", "## Blocking Questions Before Live Fetch", ""])
    for item in data["blocking_questions_before_live_fetch"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Explicitly Not Approved", ""])
    for item in safety["explicitly_not_approved"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Next Approval Decision", ""])
    for item in data["next_approval_decision"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "provider": data["provider"],
                    "scenario": data["scenario"],
                    "readiness_verdict": data["readiness_verdict"],
                    "needs_manual_recheck": True,
                    "source_accessed_live": False,
                    "api_called": False,
                    "cache_written": False,
                    "pilot_approved": False,
                    "cache_write_approved": False,
                    "actual_import_approved": False,
                    "checklist_categories": [item["category"] for item in checklist],
                    "manual_signoff_checklist": data["manual_signoff_checklist"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_tiingo_manual_signoff_ledger_report(*, report_date: str) -> tuple[str, dict[str, Any]]:
    ledger = build_tiingo_manual_signoff_ledger(report_date=report_date)
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="tiingo_manual_signoff_ledger"),
        "pack_version": "v54",
        "tiingo_manual_signoff_ledger": ledger.to_dict(),
    }
    data = payload["tiingo_manual_signoff_ledger"]
    summary = data["evidence_summary"]
    safety = data["safety"]

    def section_lines(sections: tuple[str, ...]) -> list[str]:
        rows: list[str] = []
        for item in data["signoff_items"]:
            if item["section"] in sections:
                rows.append(
                    f"| {item['item_id']} | {item['question']} | {item['operator_signoff_status']} | "
                    f"{str(item['blocking_if_unanswered']).lower()} | {item['operator_answer_placeholder']} |"
                )
        return rows

    lines = [
        "# Tiingo Manual Signoff Review Sheet",
        "",
        "## Executive Summary",
        "",
        "- This ledger is source-only and creates human-fillable signoff fields before any Tiingo live-fetch-only pilot.",
        "- All signoff items default to unreviewed and block live fetch until reviewed.",
        "- Live fetch, cache write, actual import, and trading action remain not approved.",
        "",
        "## Current Pilot Candidate",
        "",
        f"- provider: {data['provider']}",
        f"- scenario: {data['scenario']}",
        f"- pilot_date_range: {data['pilot_date_range']}",
        f"- pilot_universe: {', '.join(data['pilot_universe'])}",
        "",
        "## Current Approval Status",
        "",
        f"- live_fetch_approved: {str(summary['live_fetch_approved']).lower()}",
        f"- cache_write_approved: {str(summary['cache_write_approved']).lower()}",
        f"- actual_import_approved: {str(summary['actual_import_approved']).lower()}",
        f"- primary_blocker: {summary['primary_blocker']}",
        "",
        "## How To Use This Review Sheet",
        "",
        "- Fill `operator_answer_placeholder` with the current manual evidence summary.",
        "- Change status only after human review; default source output remains unreviewed.",
        "- Do not treat this ledger as approval to run Tiingo or write cache/import artifacts.",
        "",
        "## Signoff Status Summary",
        "",
        f"- total_items: {summary['total_items']}",
        f"- unreviewed_items: {summary['unreviewed_items']}",
        f"- default_status: {summary['default_status']}",
        "",
        "## Blocking Items Before Live Fetch",
        "",
        f"- blocking_live_fetch_items: {summary['blocking_live_fetch_items']}",
        f"- blocking_cache_write_items: {summary['blocking_cache_write_items']}",
        f"- blocking_actual_import_items: {summary['blocking_actual_import_items']}",
    ]
    section_groups = (
        ("Pricing / Plan Signoff", ("pricing_plan", "subscription_entitlement")),
        ("Terms / Redistribution / Attribution Signoff", ("terms_of_use", "redistribution_attribution")),
        ("API Limits / Throughput Signoff", ("api_limits_request_limits", "unique_symbol_universe_limits")),
        ("EOD Historical OHLCV Signoff", ("eod_historical_ohlcv_endpoint",)),
        ("Adjusted Price Method Signoff", ("adjusted_price_methodology",)),
        (
            "Split / Dividend / Corporate Action Signoff",
            ("split_handling", "dividend_handling", "corporate_actions"),
        ),
        (
            "Coverage Signoff",
            ("etf_coverage", "adr_coverage", "mutual_fund_coverage", "delisted_coverage"),
        ),
        ("Cache Suitability Signoff", ("cache_suitability_local_storage",)),
        ("Pilot Scope Signoff", ("pilot_universe_compatibility", "pilot_date_range_compatibility")),
        (
            "Secret / Redaction / No-Write Discipline",
            ("secret_handling", "redaction_handling", "no_write_discipline", "rollback_cleanup_expectations"),
        ),
        ("Verification Criteria", ("verification_criteria", "python_implementation_path")),
    )
    for heading, sections in section_groups:
        lines.extend(["", f"## {heading}", ""])
        lines.extend(["| item_id | question | status | blocking | operator_answer |", "|---|---|---|---|---|"])
        lines.extend(section_lines(sections))
    lines.extend(["", "## Operator Signoff Fields", ""])
    lines.extend(
        [
            "| item_id | section | required_evidence | blocks_live_fetch | blocks_cache_write | blocks_actual_import |",
            "|---|---|---|---|---|---|",
        ]
    )
    for item in data["signoff_items"]:
        lines.append(
            f"| {item['item_id']} | {item['section']} | {item['required_evidence']} | "
            f"{str(item['blocks_live_fetch']).lower()} | {str(item['blocks_cache_write']).lower()} | "
            f"{str(item['blocks_actual_import']).lower()} |"
        )
    lines.extend(["", "## Explicitly Not Approved", ""])
    for item in data["explicitly_not_approved"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Final Readiness Verdict",
            "",
            f"- {data['final_verdict']}",
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "provider": data["provider"],
                    "scenario": data["scenario"],
                    "total_items": summary["total_items"],
                    "default_status": summary["default_status"],
                    "live_fetch_approved": summary["live_fetch_approved"],
                    "cache_write_approved": summary["cache_write_approved"],
                    "actual_import_approved": summary["actual_import_approved"],
                    "primary_blocker": summary["primary_blocker"],
                    "source_only": safety["source_only"],
                    "tiingo_api_called": safety["tiingo_api_called"],
                    "cache_write_executed": safety["cache_write_executed"],
                    "actual_refresh_import_executed": safety["actual_refresh_import_executed"],
                    "final_verdict": data["final_verdict"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_tiingo_live_fetch_result_review_report(*, report_date: str) -> tuple[str, dict[str, Any]]:
    pack = build_tiingo_live_fetch_result_review_pack(report_date=report_date)
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="tiingo_live_fetch_result_review"),
        "pack_version": "v64",
        "tiingo_live_fetch_result_review": pack.to_dict(),
    }
    data = payload["tiingo_live_fetch_result_review"]
    pilot = data["pilot_result"]
    field_summary = pilot["field_summary"]
    safety = pilot["safety"]
    verdict = data["verdict"]
    validation_plan = data["data_quality_validation_plan"]
    readiness = data["cache_write_readiness_assessment"]
    next_step = data["next_step"]

    lines = [
        "# Tiingo Live Fetch Result Review & Data Quality Validation Pack",
        "",
        "## Executive Summary",
        "",
        "- v63B Tiingo live-fetch-only pilot is recorded as passed from the redacted result summary.",
        "- The pilot proves fetch viability and field presence, not price accuracy or adjustment correctness.",
        "- Cache write and actual import remain not ready and not approved.",
        "- Next recommended task is a separate no-write cross-provider data-quality validation pilot.",
        "",
        "## v63B Pilot Result",
        "",
        f"- v63B_result_status: {pilot['result_status']}",
        f"- provider: {pilot['provider']}",
        f"- scenario: {pilot['scenario']}",
        f"- operation: {pilot['operation']}",
        f"- date_range: {pilot['date_range']}",
        f"- symbols_total: {pilot['symbols_total']}",
        f"- symbols_success: {pilot['symbols_success']}",
        f"- symbols_failed: {pilot['symbols_failed']}",
        f"- row_count_per_symbol: {pilot['row_count_per_symbol']}",
        f"- provider_request_count: {pilot['provider_request_count']}",
        f"- provider_total_seconds_approx: {pilot['provider_total_seconds_approx']}",
        f"- provider_avg_ms_per_request_approx: {pilot['provider_avg_ms_per_request_approx']}",
        "",
        "## What The Pilot Proved",
        "",
    ]
    lines.extend(f"- {item}" for item in verdict["what_was_proven"])
    lines.extend(["", "## What The Pilot Did Not Prove", ""])
    lines.extend(f"- {item}" for item in verdict["what_was_not_proven"])
    lines.extend(
        [
            "",
            "## Symbol-Level Summary",
            "",
            "| symbol | status | row_count | base_fields | adjusted_fields | raw_data_persisted |",
            "|---|---|---:|---|---|---|",
        ]
    )
    for row in pilot["symbol_summaries"]:
        lines.append(
            f"| {row['symbol']} | {row['status']} | {row['row_count']} | "
            f"{str(row['base_fields_present']).lower()} | {str(row['adjusted_fields_present']).lower()} | "
            f"{str(row['raw_data_persisted']).lower()} |"
        )
    lines.extend(
        [
            "",
            "## Field Availability Summary",
            "",
            f"- base_fields_all_present: {str(field_summary['base_fields_all_present']).lower()}",
            f"- base_fields: {', '.join(field_summary['base_fields'])}",
            f"- raw_price_accuracy_proven: {str(field_summary['raw_price_accuracy_proven']).lower()}",
            "",
            "## Adjusted Field Presence Summary",
            "",
            f"- adjusted_fields_all_present: {str(field_summary['adjusted_fields_all_present']).lower()}",
            f"- adjusted_fields: {', '.join(field_summary['adjusted_fields'])}",
            "- adjusted field presence is not the same as adjusted calculation correctness.",
            f"- adjusted_calculation_correctness_proven: {str(field_summary['adjusted_calculation_correctness_proven']).lower()}",
            "",
            "## No-Write / No-Import Verification",
            "",
            f"- raw_data_persisted: {str(safety['raw_data_persisted']).lower()}",
            f"- reports_private_raw_data_written: {str(safety['reports_private_raw_data_written']).lower()}",
            f"- cache_write_executed: {str(safety['cache_write_executed']).lower()}",
            f"- actual_import_executed: {str(safety['actual_import_executed']).lower()}",
            f"- manual_actual_import_executed: {str(safety['manual_actual_import_executed']).lower()}",
            f"- env_secret_displayed: {str(safety['env_secret_displayed']).lower()}",
            f"- trading_action_executed: {str(safety['trading_action_executed']).lower()}",
            f"- tiingo_api_called_by_this_pack: {str(safety['tiingo_api_called_by_this_pack']).lower()}",
            f"- stooq_yahoo_polygon_live_fetch_executed_by_this_pack: {str(safety['stooq_yahoo_polygon_live_fetch_executed_by_this_pack']).lower()}",
            "",
            "## Data Quality Validation Plan",
            "",
            f"- package_status: {validation_plan['package_status']}",
            f"- operation: {validation_plan['operation']}",
            f"- providers: {', '.join(validation_plan['providers'])}",
            f"- universe: {', '.join(validation_plan['universe'])}",
            f"- date_range: {validation_plan['date_range']}",
            f"- required_approval_phrase: {validation_plan['required_approval_phrase']}",
            f"- next_recommended_execution: {validation_plan['next_recommended_execution']}",
            f"- raw_data_persistence_allowed: {str(validation_plan['raw_data_persistence_allowed']).lower()}",
            f"- cache_write_approved: {str(validation_plan['cache_write_approved']).lower()}",
            f"- actual_import_approved: {str(validation_plan['actual_import_approved']).lower()}",
            "",
            "## Cross-Provider Validation Matrix",
            "",
            "| check_id | category | providers | universe_slice | tolerance_policy |",
            "|---|---|---|---|---|",
        ]
    )
    for check in validation_plan["checks"]:
        lines.append(
            f"| {check['check_id']} | {check['category']} | {', '.join(check['providers'])} | "
            f"{', '.join(check['universe_slice'])} | {check['tolerance_policy']} |"
        )
    lines.extend(
        [
            "",
            "## Cache-Write Readiness Assessment",
            "",
            f"- cache_write_readiness: {readiness['cache_write_readiness']}",
            f"- cache_write_approved: {str(readiness['cache_write_approved']).lower()}",
            f"- next_approval_package_needed: {readiness['next_approval_package_needed']}",
            "",
            "| prerequisite_id | status | blocks_cache_write | description |",
            "|---|---|---|---|",
        ]
    )
    for item in readiness["prerequisites"]:
        lines.append(
            f"| {item['prerequisite_id']} | {item['status']} | "
            f"{str(item['blocks_cache_write']).lower()} | {item['description']} |"
        )
    lines.extend(
        [
            "",
            "## Actual Import Readiness Assessment",
            "",
            f"- actual_import_readiness: {readiness['actual_import_readiness']}",
            f"- actual_import_approved: {str(readiness['actual_import_approved']).lower()}",
            "- actual import remains downstream of cache-write readiness and explicit approval.",
            "",
            "## Risk Register",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in data["risk_register"])
    lines.extend(
        [
            "",
            "## Recommended Next Task",
            "",
            f"- recommended_task: {next_step['recommended_task']}",
            f"- approval_phrase_required: {next_step['approval_phrase_required']}",
            "- run only as a future no-write validation task after explicit approval.",
            "",
            "## Explicitly Not Approved",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in next_step["explicitly_not_approved"])
    lines.extend(
        [
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "v63B_result_status": pilot["result_status"],
                    "symbols_total": pilot["symbols_total"],
                    "symbols_success": pilot["symbols_success"],
                    "symbols_failed": pilot["symbols_failed"],
                    "base_fields_all_present": field_summary["base_fields_all_present"],
                    "adjusted_fields_all_present": field_summary["adjusted_fields_all_present"],
                    "row_count_per_symbol": pilot["row_count_per_symbol"],
                    "raw_data_persisted": safety["raw_data_persisted"],
                    "cache_write_executed": safety["cache_write_executed"],
                    "actual_import_executed": safety["actual_import_executed"],
                    "trading_action_executed": safety["trading_action_executed"],
                    "cache_write_readiness": readiness["cache_write_readiness"],
                    "actual_import_readiness": readiness["actual_import_readiness"],
                    "next_recommended_execution": validation_plan["next_recommended_execution"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_cross_provider_validation_runbook_report(*, report_date: str) -> tuple[str, dict[str, Any]]:
    pack = build_cross_provider_validation_runbook_pack(report_date=report_date)
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="cross_provider_validation_runbook"),
        "pack_version": "v64B",
        "cross_provider_validation_runbook": pack.to_dict(),
    }
    data = payload["cross_provider_validation_runbook"]
    scope = data["provider_scope"]
    universe = data["universe"]
    tolerance = data["tolerance_policy"]
    schema = data["redacted_output_schema"]
    safety = data["safety_controls"]
    approval = data["approval_package"]
    runbook = data["runbook"]
    verdict = data["readiness_verdict"]
    handoff = data["cursor_handoff"]
    lines = [
        "# Cross-Provider Data Quality Validation Approval & Runbook Pack",
        "",
        "## Executive Summary",
        "",
        "- This pack prepares the next no-write cross-provider data-quality validation task.",
        "- It is a source-only approval/runbook draft and does not access Tiingo, Stooq, Yahoo/yfinance, or Polygon.",
        "- The approval phrase is documented for a future task but is not issued by this pack.",
        "- Cache write and actual import remain not ready and not approved.",
        "",
        "## Why This Pack Exists",
        "",
        "- v63B/v64 proved Tiingo live-fetch viability for the 14-symbol pilot universe.",
        "- Price accuracy, adjusted calculation correctness, and cross-provider consistency remain unproven.",
        "- A no-write validation runbook is required before any cache/database readiness decision.",
        "",
        "## Current State After v63B/v64",
        "",
    ]
    for key, value in data["current_state"].items():
        if isinstance(value, list):
            lines.append(f"- {key}: {', '.join(value)}")
        else:
            lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Provider Scope",
            "",
            f"- required_providers: {', '.join(scope['required_providers'])}",
            f"- optional_providers: {', '.join(scope['optional_providers'])}",
            f"- provider_live_access_executed_by_this_pack: {str(scope['provider_live_access_executed_by_this_pack']).lower()}",
            "",
            "| provider | role |",
            "|---|---|",
        ]
    )
    for provider, role in scope["provider_roles"].items():
        lines.append(f"| {provider} | {role} |")
    lines.extend(
        [
            "",
            "## Universe",
            "",
            f"- symbols_count: {len(universe['symbols'])}",
            f"- symbols: {', '.join(universe['symbols'])}",
            "",
            "| sample_group | symbols |",
            "|---|---|",
        ]
    )
    for group, symbols in universe["sample_groups"].items():
        lines.append(f"| {group} | {', '.join(symbols)} |")
    lines.extend(
        [
            "",
            "## Future Date Range",
            "",
            f"- {universe['date_range']}",
            "",
            "## Validation Checks",
            "",
            "| check_id | category | compute_now | blocks_cache_import | description |",
            "|---|---|---|---|---|",
        ]
    )
    for check in data["validation_checks"]:
        lines.append(
            f"| {check['check_id']} | {check['category']} | {str(check['compute_now']).lower()} | "
            f"{str(check['blocks_cache_import_on_major_disagreement']).lower()} | {check['description']} |"
        )
    lines.extend(
        [
            "",
            "## Tolerance Policy",
            "",
            f"- row_count_tolerance_days: {tolerance['row_count_tolerance_days']}",
            f"- date_range_tolerance_days: {tolerance['date_range_tolerance_days']}",
            f"- close_relative_tolerance: {tolerance['close_relative_tolerance_pct']}%",
            f"- adjusted_close_relative_tolerance: {tolerance['adjusted_close_relative_tolerance_pct']}%",
            f"- volume_relative_tolerance: {tolerance['volume_relative_tolerance_pct']}%",
            f"- split_sensitive_requires_manual_review: {str(tolerance['split_sensitive_requires_manual_review']).lower()}",
            f"- missing_day_requires_investigation: {str(tolerance['missing_day_requires_investigation']).lower()}",
            f"- provider_disagreement_requires_no_cache_import: {str(tolerance['provider_disagreement_requires_no_cache_import']).lower()}",
            f"- policy_note: {tolerance['policy_note']}",
            "",
            "## Redacted Output Schema",
            "",
            "- allowed_fields:",
        ]
    )
    lines.extend(f"  - {item}" for item in schema["allowed_fields"])
    lines.append("- forbidden_fields:")
    lines.extend(f"  - {item}" for item in schema["forbidden_fields"])
    lines.extend(
        [
            f"- reports_private_raw_data_forbidden: {str(schema['reports_private_raw_data_forbidden']).lower()}",
            f"- raw_ohlcv_rows_allowed: {str(schema['raw_ohlcv_rows_allowed']).lower()}",
            f"- raw_provider_responses_allowed: {str(schema['raw_provider_responses_allowed']).lower()}",
            "",
            "## No-Write / No-Import Safety Controls",
            "",
        ]
    )
    for key, value in safety.items():
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(["", "## Stop Conditions", ""])
    for condition in data["stop_conditions"]:
        lines.append(f"- {condition['label']}: {condition['description']}")
    lines.extend(
        [
            "",
            "## Approval Package Draft",
            "",
            f"- package_status: {approval['package_status']}",
            f"- operation: {approval['operation']}",
            f"- providers: {', '.join(approval['providers'])}",
            f"- optional_providers: {', '.join(approval['optional_providers'])}",
            f"- universe_count: {len(approval['universe'])}",
            f"- date_range: {approval['date_range']}",
            f"- future_approval_phrase: {approval['future_approval_phrase']}",
            f"- approval_phrase_issued: {str(approval['approval_phrase_issued']).lower()}",
            f"- separate_explicit_approval_required: {str(approval['separate_explicit_approval_required']).lower()}",
            f"- raw_data_persistence_allowed: {str(approval['raw_data_persistence_allowed']).lower()}",
            f"- cache_write_approved: {str(approval['cache_write_approved']).lower()}",
            f"- actual_import_approved: {str(approval['actual_import_approved']).lower()}",
            f"- manual_import_approved: {str(approval['manual_import_approved']).lower()}",
            f"- trading_action_approved: {str(approval['trading_action_approved']).lower()}",
            "",
            "## Operator Runbook",
            "",
            "### Preconditions",
        ]
    )
    lines.extend(f"- {item}" for item in runbook["preconditions"])
    lines.extend(["", "### Operator Steps"])
    lines.extend(f"- {item}" for item in runbook["operator_steps"])
    lines.extend(["", "### Verification Steps"])
    lines.extend(f"- {item}" for item in runbook["verification_steps"])
    lines.extend(["", "### Cleanup Verification"])
    lines.extend(f"- {item}" for item in runbook["cleanup_verification"])
    lines.extend(
        [
            "",
            "## Readiness Verdict",
            "",
            f"- cross_provider_validation_execution_readiness: {verdict['cross_provider_validation_execution_readiness']}",
            f"- cache_write_readiness: {verdict['cache_write_readiness']}",
            f"- actual_import_readiness: {verdict['actual_import_readiness']}",
        ]
    )
    lines.extend(f"- rationale: {item}" for item in verdict["rationale"])
    lines.extend(["", "## Explicitly Not Approved", ""])
    for item in (
        "provider_live_access",
        "public_ohlcv_source_live_fetch_by_this_pack",
        "tiingo_api_call",
        "stooq_live_fetch",
        "yahoo_yfinance_live_fetch",
        "polygon_live_fetch",
        "cache_write",
        "actual_refresh_import",
        "manual_actual_import",
        "env_secret_display",
        "broker_manual_raw_data",
        "reports_private_change",
        "trading_action",
    ):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Next Cursor Handoff",
            "",
            f"- handoff_status: {handoff['handoff_status']}",
            f"- required_approval_phrase: {handoff['required_approval_phrase']}",
            f"- execution_scope: {handoff['execution_scope']}",
            "- no_write_rules:",
        ]
    )
    lines.extend(f"  - {item}" for item in handoff["no_write_rules"])
    lines.append("- output_rules:")
    lines.extend(f"  - {item}" for item in handoff["output_rules"])
    lines.extend(
        [
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "package_status": approval["package_status"],
                    "operation": approval["operation"],
                    "providers": approval["providers"],
                    "optional_providers": approval["optional_providers"],
                    "universe_count": len(approval["universe"]),
                    "approval_phrase_issued": approval["approval_phrase_issued"],
                    "raw_data_persistence_allowed": approval["raw_data_persistence_allowed"],
                    "cache_write_approved": approval["cache_write_approved"],
                    "actual_import_approved": approval["actual_import_approved"],
                    "readiness_verdict": verdict["cross_provider_validation_execution_readiness"],
                    "cache_write_readiness": verdict["cache_write_readiness"],
                    "actual_import_readiness": verdict["actual_import_readiness"],
                    "source_only": safety["source_only"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_cross_provider_validation_result_review_report(*, report_date: str) -> tuple[str, dict[str, Any]]:
    review = build_cross_provider_validation_result_review(report_date=report_date)
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="cross_provider_validation_result_review"),
        "pack_version": "v66",
        "cross_provider_validation_result_review": review.to_dict(),
    }
    data = payload["cross_provider_validation_result_review"]
    summary = data["result_summary"]
    stooq_policy = data["stooq_adjustment_policy"]
    readiness = data["cache_write_readiness"]
    next_step = data["next_step"]
    lines = [
        "# Cross-Provider Validation Result Review & Adjustment Policy Pack",
        "",
        "## Executive Summary",
        "",
        "- v65 completed as no-write cross-provider validation and returned warn_manual_review_required.",
        "- Required providers all succeeded for 14/14 symbols with consistent row counts.",
        "- Tiingo/Yahoo adjusted close agreement passed and is the stronger adjusted-series signal.",
        "- Stooq lacks adjusted close and must not be used as an adjusted-series oracle.",
        "- Cache write and actual import remain not ready and not approved.",
        "",
        "## v65 Result Summary",
        "",
        f"- v65_verdict: {summary['verdict']}",
        f"- operation: {summary['operation']}",
        f"- providers_executed: {', '.join(summary['providers_executed'])}",
        f"- polygon_status: {summary['polygon_status']}",
        f"- universe_count: {len(summary['universe'])}",
        f"- date_range: {summary['date_range']}",
        f"- required_providers_available: {str(summary['required_providers_available']).lower()}",
        f"- required_provider_symbols_success: {summary['required_provider_symbols_success']}",
        f"- row_count_per_symbol: {summary['row_count_per_symbol']}",
        f"- row_count_consistent: {str(summary['row_count_consistent']).lower()}",
        f"- date_range_consistent: {str(summary['date_range_consistent']).lower()}",
        f"- tolerance_breaches_total: {summary['tolerance_breaches_total']}",
        f"- close_breaches: {summary['close_breaches']}",
        f"- volume_breaches: {summary['volume_breaches']}",
        "",
        "## Warning Interpretation",
        "",
        "- NVDA/AVGO large close/volume deviations should not be treated as Tiingo failure by default.",
        "- The likely cause is Stooq non-adjusted/base series compared against adjusted or differently adjusted series.",
        "- Stooq should not be used as adjusted-close oracle unless explicit adjusted series becomes available.",
        "- Tiingo vs Yahoo adjusted close agreement is the stronger validation signal for adjusted series.",
        "",
        "## Provider-Pair Comparison Policy",
        "",
        "| pair | role | series_type | suitability | status_after_v65 | policy |",
        "|---|---|---|---|---|---|",
    ]
    for row in data["provider_pair_policy"]:
        lines.append(
            f"| {row['pair']} | {row['role']} | {row['series_type']} | {row['suitability']} | "
            f"{row['status_after_v65']} | {row['policy']} |"
        )
    lines.extend(
        [
            "",
            "## Stooq Adjustment Policy",
            "",
            f"- has_adjusted_close: {str(stooq_policy['has_adjusted_close']).lower()}",
            f"- adjusted_series_oracle: {str(stooq_policy['adjusted_series_oracle']).lower()}",
            f"- base_close_role: {stooq_policy['base_close_role']}",
            f"- coverage_role: {stooq_policy['coverage_role']}",
            f"- fallback_role: {stooq_policy['fallback_role']}",
            f"- split_sensitive_warning_interpretation: {stooq_policy['split_sensitive_warning_interpretation']}",
            "- disable_adjusted_comparison_unless_adjusted_series_available: "
            f"{str(stooq_policy['disable_adjusted_comparison_unless_adjusted_series_available']).lower()}",
            "",
            "## Tolerance Policy Refinement",
            "",
            "| tolerance_id | name | providers | tolerance | policy |",
            "|---|---|---|---|---|",
        ]
    )
    for row in data["tolerance_policy_refinement"]:
        lines.append(
            f"| {row['tolerance_id']} | {row['name']} | {', '.join(row['providers'])} | "
            f"{row['tolerance']} | {row['policy']} |"
        )
    lines.extend(
        [
            "",
            "## Tiingo/Yahoo Agreement Assessment",
            "",
            f"- tiingo_yahoo_adjusted_close_consistency: {summary['tiingo_yahoo_adjusted_close_consistency']}",
            "- adjusted_close_tiingo_yahoo_max_deviation_approx_pct: "
            f"{summary['adjusted_close_tiingo_yahoo_max_deviation_approx_pct']}",
            f"- tiingo_adjusted_series_confidence: {readiness['tiingo_adjusted_series_confidence']}",
            "",
            "## Impact on Tiingo Provider Viability",
            "",
            f"- live_fetch_provider_viability: {readiness['live_fetch_provider_viability']}",
            f"- cross_provider_validation_result: {readiness['cross_provider_validation_result']}",
            "- Tiingo remains viable as first private/local cache candidate after policy refinement.",
            "",
            "## Cache-Write Readiness Assessment",
            "",
            f"- cache_write_readiness: {readiness['cache_write_readiness']}",
            f"- cache_write_approved: {str(readiness['cache_write_approved']).lower()}",
            "",
            "| prerequisite_id | status | blocks_cache_write | description |",
            "|---|---|---|---|",
        ]
    )
    for row in readiness["prerequisites"]:
        lines.append(
            f"| {row['prerequisite_id']} | {row['status']} | "
            f"{str(row['blocks_cache_write']).lower()} | {row['description']} |"
        )
    lines.extend(
        [
            "",
            "## Actual Import Readiness Assessment",
            "",
            f"- actual_import_readiness: {readiness['actual_import_readiness']}",
            f"- actual_import_approved: {str(readiness['actual_import_approved']).lower()}",
            "- Actual import remains downstream of cache-write readiness and separate approval.",
            "",
            "## Risk Register",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in data["risk_register"])
    lines.extend(
        [
            "",
            "## Recommended Next Step",
            "",
            f"- recommended_next_step: {next_step['recommended_next_step']}",
            f"- rationale: {next_step['rationale']}",
            f"- approval_phrase_issued: {str(next_step['approval_phrase_issued']).lower()}",
            "",
            "## Explicitly Not Approved",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in next_step["explicitly_not_approved"])
    lines.extend(
        [
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "v65_verdict": summary["verdict"],
                    "required_providers_available": summary["required_providers_available"],
                    "required_provider_symbols_success": summary["required_provider_symbols_success"],
                    "tiingo_yahoo_adjusted_close_consistency": summary[
                        "tiingo_yahoo_adjusted_close_consistency"
                    ],
                    "stooq_adjusted_comparison_suitability": summary[
                        "stooq_adjusted_comparison_suitability"
                    ],
                    "stooq_base_close_comparison_suitability": summary[
                        "stooq_base_close_comparison_suitability"
                    ],
                    "polygon_status": summary["polygon_status"],
                    "raw_data_persisted": summary["raw_data_persisted"],
                    "cache_write_executed": summary["cache_write_executed"],
                    "actual_import_executed": summary["actual_import_executed"],
                    "trading_action_executed": summary["trading_action_executed"],
                    "cache_write_readiness": readiness["cache_write_readiness"],
                    "actual_import_readiness": readiness["actual_import_readiness"],
                    "next_recommended_task": next_step["recommended_next_step"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_cache_write_readiness_gate_report(*, report_date: str) -> tuple[str, dict[str, Any]]:
    gate = build_cache_write_readiness_gate(report_date=report_date)
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="cache_write_readiness_gate"),
        "pack_version": "v67",
        "cache_write_readiness_gate": gate.to_dict(),
    }
    data = payload["cache_write_readiness_gate"]
    storage = data["storage_policy"]
    retention = data["retention_policy"]
    purge = data["purge_rollback_policy"]
    acknowledgement = data["terms_cache_acknowledgement"]
    cache_boundary = data["cache_write_approval_boundary"]
    import_boundary = data["actual_import_boundary"]
    pilot = data["future_cache_write_pilot"]
    verdict = data["readiness_verdict"]
    lines = [
        "# Cache-Write Readiness Gate Draft",
        "",
        "## Executive Summary",
        "",
        "- This pack is source-only and prepares cache-write readiness requirements without writing cache.",
        "- SIGNOFF-16 remains unresolved and required before any Tiingo private/local cache-write pilot.",
        "- Raw OHLCV remains forbidden in Git, reports-private, ChatGPT/Cursor paste, public outputs, and artifacts.",
        "- Cache write, actual import, and trading action remain not approved.",
        "",
        "## Current State After v63B/v65/v66",
        "",
    ]
    for key, value in data["current_state"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## SIGNOFF-16 Requirements",
            "",
            "| requirement_id | status | required | description |",
            "|---|---|---|---|",
        ]
    )
    for row in data["signoff16_requirements"]:
        lines.append(
            f"| {row['requirement_id']} | {row['status']} | "
            f"{str(row['required_before_cache_write']).lower()} | {row['description']} |"
        )
    lines.extend(
        [
            "",
            "## Private/Local Cache Storage Policy",
            "",
            f"- policy_status: {storage['policy_status']}",
            f"- cache_location: {storage['cache_location']}",
            f"- raw_data_git_allowed: {str(storage['raw_data_git_allowed']).lower()}",
            f"- raw_data_reports_private_allowed: {str(storage['raw_data_reports_private_allowed']).lower()}",
            "- redacted_summary_reports_private_allowed: "
            f"{str(storage['redacted_summary_reports_private_allowed']).lower()}",
            "",
            "| location_id | allowed_after_future_approval | description | required_controls |",
            "|---|---|---|---|",
        ]
    )
    for row in storage["allowed_candidates"]:
        lines.append(
            f"| {row['location_id']} | {str(row['allowed_only_after_future_approval']).lower()} | "
            f"{row['description']} | {', '.join(row['required_controls'])} |"
        )
    lines.extend(
        [
            "",
            "## Forbidden Raw Data Locations",
            "",
            "| location_id | description | reason |",
            "|---|---|---|",
        ]
    )
    for row in storage["forbidden_locations"]:
        lines.append(f"| {row['location_id']} | {row['description']} | {row['reason']} |")
    lines.extend(
        [
            "",
            "## Retention Policy Draft",
            "",
            f"- retention_period_initial_pilot: {retention['retention_period_initial_pilot']}",
            f"- retention_owner_required: {str(retention['retention_owner_required']).lower()}",
            f"- raw_file_inventory_required: {str(retention['raw_file_inventory_required']).lower()}",
            f"- redacted_summary_required: {str(retention['redacted_summary_required']).lower()}",
            f"- no_orphan_raw_files_required: {str(retention['no_orphan_raw_files_required']).lower()}",
            "",
            "## Purge / Rollback Policy Draft",
            "",
            f"- cache_purge_command_required: {str(purge['cache_purge_command_required']).lower()}",
            f"- rollback_checklist_required: {str(purge['rollback_checklist_required']).lower()}",
            f"- purge_dry_run_required: {str(purge['purge_dry_run_required']).lower()}",
            f"- post_purge_verification_required: {str(purge['post_purge_verification_required']).lower()}",
        ]
    )
    lines.extend(f"- future_checklist: {item}" for item in purge["future_checklist"])
    lines.extend(
        [
            "",
            "## Terms / Cache Acknowledgement",
            "",
            f"- acknowledgement_status: {acknowledgement['acknowledgement_status']}",
            f"- operator_signoff_required: {str(acknowledgement['operator_signoff_required']).lower()}",
        ]
    )
    lines.extend(f"- required_statement: {item}" for item in acknowledgement["required_statements"])
    lines.extend(
        [
            "",
            "## Cache-Write Approval Boundary",
            "",
            f"- future_cache_write_approval_phrase: {cache_boundary['future_cache_write_approval_phrase']}",
            f"- cache_write_approved: {str(cache_boundary['cache_write_approved']).lower()}",
            f"- approval_phrase_issued: {str(cache_boundary['approval_phrase_issued']).lower()}",
            "- separate_explicit_approval_required: "
            f"{str(cache_boundary['separate_explicit_approval_required']).lower()}",
            f"- trading_action_approved: {str(cache_boundary['trading_action_approved']).lower()}",
            "",
            "## Actual Import Boundary",
            "",
            f"- future_actual_import_approval_phrase: {import_boundary['future_actual_import_approval_phrase']}",
            f"- actual_import_approved: {str(import_boundary['actual_import_approved']).lower()}",
            f"- approval_phrase_issued: {str(import_boundary['approval_phrase_issued']).lower()}",
            f"- remains_separate_from_cache_write: {str(import_boundary['remains_separate_from_cache_write']).lower()}",
            "",
            "## Future Cache-Write Pilot Draft",
            "",
            f"- package_status: {pilot['package_status']}",
            f"- operation: {pilot['operation']}",
            f"- provider: {pilot['provider']}",
            f"- universe_count: {len(pilot['universe'])}",
            f"- recommended_first_subset: {', '.join(pilot['recommended_first_subset'])}",
            f"- first_subset_reason: {pilot['first_subset_reason']}",
            f"- date_range: {pilot['date_range']}",
            f"- cache_location: {pilot['cache_location']}",
            f"- raw_data_git_allowed: {str(pilot['raw_data_git_allowed']).lower()}",
            f"- raw_data_reports_private_allowed: {str(pilot['raw_data_reports_private_allowed']).lower()}",
            "- redacted_summary_reports_private_allowed: "
            f"{str(pilot['redacted_summary_reports_private_allowed']).lower()}",
            f"- approval_phrase_issued: {str(pilot['approval_phrase_issued']).lower()}",
            "- separate_explicit_approval_required: "
            f"{str(pilot['separate_explicit_approval_required']).lower()}",
            "",
            "## Readiness Verdict",
            "",
            f"- signoff16_status: {verdict['signoff16_status']}",
            f"- cache_write_readiness: {verdict['cache_write_readiness']}",
            f"- actual_import_readiness: {verdict['actual_import_readiness']}",
            f"- cache_write_approved: {str(verdict['cache_write_approved']).lower()}",
            f"- actual_import_approved: {str(verdict['actual_import_approved']).lower()}",
            f"- trading_action_approved: {str(verdict['trading_action_approved']).lower()}",
            f"- approval_phrase_issued: {str(verdict['approval_phrase_issued']).lower()}",
            "",
            "## Explicitly Not Approved",
            "",
        ]
    )
    for item in (
        "tiingo_api_call",
        "stooq_live_fetch",
        "yahoo_yfinance_live_fetch",
        "polygon_live_fetch",
        "provider_live_access",
        "public_ohlcv_source_live_fetch",
        "cache_write",
        "actual_refresh_import",
        "manual_actual_import",
        "env_secret_display",
        "broker_manual_raw_data",
        "workflow_dependency_pyproject_change",
        "reports_private_change",
        "trading_action",
    ):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "gate_status": data["gate_status"],
                    "signoff16_status": verdict["signoff16_status"],
                    "cache_write_approved": verdict["cache_write_approved"],
                    "actual_import_approved": verdict["actual_import_approved"],
                    "trading_action_approved": verdict["trading_action_approved"],
                    "approval_phrase_issued": verdict["approval_phrase_issued"],
                    "cache_location": storage["cache_location"],
                    "raw_data_git_allowed": storage["raw_data_git_allowed"],
                    "raw_data_reports_private_allowed": storage["raw_data_reports_private_allowed"],
                    "retention_period_initial_pilot": retention["retention_period_initial_pilot"],
                    "cache_purge_command_required": purge["cache_purge_command_required"],
                    "future_cache_write_pilot_status": pilot["package_status"],
                    "future_cache_write_pilot_subset": pilot["recommended_first_subset"],
                    "source_only": data["safety_flags"]["source_only"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_cache_write_operator_signoff_sheet_report(*, report_date: str) -> tuple[str, dict[str, Any]]:
    sheet = build_cache_write_operator_signoff_sheet(report_date=report_date)
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="cache_write_operator_signoff_sheet"),
        "pack_version": "v68",
        "cache_write_operator_signoff_sheet": sheet.to_dict(),
    }
    data = payload["cache_write_operator_signoff_sheet"]
    review = data["operator_review"]
    operation = data["proposed_future_operation"]
    location = data["cache_location_checklist"]
    phrase = data["approval_phrase_boundary"]
    boundary = data["execution_boundary"]
    verdict = data["readiness_verdict"]
    lines = [
        "# v68 Cache-Write Operator Signoff Sheet",
        "",
        "## Verdict",
        "",
        f"- operator_signoff_status: {verdict['operator_signoff_status']}",
        f"- cache_write_approval_status: {verdict['cache_write_approval_status']}",
        f"- cache_write_execution_status: {verdict['cache_write_execution_status']}",
        f"- actual_import_approval_status: {verdict['actual_import_approval_status']}",
        f"- actual_import_execution_status: {verdict['actual_import_execution_status']}",
        f"- overall_readiness: {verdict['overall_readiness']}",
        "",
        "## Operator Review Fields",
        "",
    ]
    for key, value in review.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Proposed Future Operation",
            "",
            f"- operation_name: {operation['operation_name']}",
            f"- provider: {operation['provider']}",
            f"- symbols: {', '.join(operation['symbols'])}",
            f"- date_range: {operation['date_range']}",
            f"- data_type: {operation['data_type']}",
            f"- raw_data_expected: {str(operation['raw_data_expected']).lower()}",
            f"- adjusted_fields_expected: {str(operation['adjusted_fields_expected']).lower()}",
            f"- cache_write_scope: {operation['cache_write_scope']}",
            f"- actual_import_scope: {operation['actual_import_scope']}",
            f"- trading_scope: {operation['trading_scope']}",
            "",
            "## Cache Location Checklist",
            "",
        ]
    )
    for key, value in location.items():
        lines.append(f"- {key}: {str(value).lower() if isinstance(value, bool) else value}")
    lines.extend(
        [
            "",
            "## Forbidden Raw Data Locations",
            "",
            "| item_id | current_status | blocks_cache_write | label |",
            "|---|---|---|---|",
        ]
    )
    for row in data["forbidden_raw_data_locations"]:
        lines.append(
            f"| {row['item_id']} | {row['current_status']} | "
            f"{str(row['blocks_cache_write_if_unconfirmed']).lower()} | {row['label']} |"
        )
    for section_title, section_key in (
        ("Retention / Inventory Checklist", "retention_inventory_checklist"),
        ("Purge / Rollback Checklist", "purge_rollback_checklist"),
        ("Data Quality Preconditions", "data_quality_preconditions"),
    ):
        lines.extend(
            [
                "",
                f"## {section_title}",
                "",
                "| item_id | current_status | required_answer | label |",
                "|---|---|---|---|",
            ]
        )
        for row in data[section_key]:
            lines.append(f"| {row['item_id']} | {row['current_status']} | {row['required_answer']} | {row['label']} |")
    lines.extend(
        [
            "",
            "## Approval Phrase Boundary",
            "",
            f"- cache_write_approval_phrase_required: {str(phrase['cache_write_approval_phrase_required']).lower()}",
            f"- cache_write_approval_phrase: {phrase['cache_write_approval_phrase']}",
            f"- cache_write_approval_phrase_issued: {str(phrase['cache_write_approval_phrase_issued']).lower()}",
            f"- actual_import_approval_phrase_required: {str(phrase['actual_import_approval_phrase_required']).lower()}",
            f"- actual_import_approval_phrase: {phrase['actual_import_approval_phrase']}",
            f"- actual_import_approval_phrase_issued: {str(phrase['actual_import_approval_phrase_issued']).lower()}",
            "- placeholder_phrase_is_not_runtime_approval: "
            f"{str(phrase['placeholder_phrase_is_not_runtime_approval']).lower()}",
            "",
            "## Execution Boundary",
            "",
        ]
    )
    for key, value in boundary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## What Is Still Not Approved",
            "",
            "- provider live access",
            "- public OHLCV source live fetch",
            "- Tiingo API call",
            "- cache write",
            "- actual refresh/import",
            "- manual actual import",
            "- raw OHLCV persistence",
            "- raw API response persistence",
            "- reports-private raw data write",
            "- env/secret display",
            "- broker/manual raw data handling",
            "- trading action",
            "",
            "## Next Human Actions",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in data["next_human_actions"])
    handoff = data["next_cursor_handoff_draft"]
    lines.extend(
        [
            "",
            "## Next Cursor Handoff Draft",
            "",
            f"- handoff_status: {handoff['handoff_status']}",
            f"- next_task: {handoff['next_task']}",
        ]
    )
    lines.extend(f"- must_not_execute: {item}" for item in handoff["must_not_execute"])
    lines.extend(f"- required_before_future_execution: {item}" for item in handoff["required_before_future_execution"])
    lines.extend(
        [
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "operator_signoff_status": verdict["operator_signoff_status"],
                    "cache_write_approval_status": verdict["cache_write_approval_status"],
                    "cache_write_execution_status": verdict["cache_write_execution_status"],
                    "actual_import_approval_status": verdict["actual_import_approval_status"],
                    "actual_import_execution_status": verdict["actual_import_execution_status"],
                    "overall_readiness": verdict["overall_readiness"],
                    "cache_path_proposed": location["cache_path_proposed"],
                    "cache_path_unset_blocks_readiness": location["cache_path_unset_blocks_readiness"],
                    "cache_write_approval_phrase_issued": phrase["cache_write_approval_phrase_issued"],
                    "actual_import_approval_phrase_issued": phrase["actual_import_approval_phrase_issued"],
                    "source_only": data["safety_flags"]["source_only"],
                    "cache_write_executed": data["safety_flags"]["cache_write_executed"],
                    "actual_refresh_import_executed": data["safety_flags"]["actual_refresh_import_executed"],
                    "raw_ohlcv_persisted": data["safety_flags"]["raw_ohlcv_persisted"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_cache_path_preflight_approval_package_report(
    *,
    report_date: str,
    candidate_cache_path: str,
) -> tuple[str, dict[str, Any]]:
    package = build_cache_path_preflight_approval_package(
        report_date=report_date,
        candidate_cache_path=candidate_cache_path,
    )
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="cache_path_preflight_approval_package"),
        "pack_version": "v69",
        "cache_path_preflight_approval_package": package.to_dict(),
    }
    data = payload["cache_path_preflight_approval_package"]
    preflight = data["cache_path_preflight"]
    pilot = data["pilot_approval_package"]
    verdict = data["readiness_verdict"]
    lines = [
        "# v69 Cache Path Preflight / Cache-Write Pilot Approval Package",
        "",
        "## Verdict",
        "",
        f"- preflight_verdict: {verdict['preflight_verdict']}",
        f"- all_structural_checks_pass: {str(verdict['all_structural_checks_pass']).lower()}",
        f"- cache_write_approval_status: {verdict['cache_write_approval_status']}",
        f"- cache_write_execution_status: {verdict['cache_write_execution_status']}",
        f"- actual_import_approval_status: {verdict['actual_import_approval_status']}",
        f"- actual_import_execution_status: {verdict['actual_import_execution_status']}",
        f"- provider_live_access_status: {verdict['provider_live_access_status']}",
        f"- raw_ohlcv_persistence_status: {verdict['raw_ohlcv_persistence_status']}",
        "",
        "## Candidate Cache Path",
        "",
        f"- candidate_cache_path: {preflight['candidate_cache_path']}",
        f"- path_input_source: {preflight['path_input_source']}",
        f"- path_expansion_performed: {str(preflight['path_expansion_performed']).lower()}",
        f"- filesystem_probe_performed: {str(preflight['filesystem_probe_performed']).lower()}",
        f"- directory_created: {str(preflight['directory_created']).lower()}",
        "",
        "## Structural Preflight Checks",
        "",
        "| check_id | status | blocks_future_cache_write | description | evidence |",
        "|---|---|---|---|---|",
    ]
    for row in preflight["structural_checks"]:
        lines.append(
            f"| {row['check_id']} | {row['status']} | "
            f"{str(row['blocks_future_cache_write_if_failed']).lower()} | {row['description']} | {row['evidence']} |"
        )
    lines.extend(
        [
            "",
            "## Path Classification",
            "",
        ]
    )
    for key, value in preflight["path_classification"].items():
        lines.append(f"- {key}: {str(value).lower() if isinstance(value, bool) else value}")
    lines.extend(
        [
            "",
            "## Future Pilot Approval Package",
            "",
            f"- package_status: {pilot['package_status']}",
            f"- operation_name: {pilot['operation_name']}",
            f"- provider: {pilot['provider']}",
            f"- symbols: {', '.join(pilot['symbols'])}",
            f"- candidate_cache_path: {pilot['candidate_cache_path']}",
            f"- cache_write_scope: {pilot['cache_write_scope']}",
            f"- actual_import_scope: {pilot['actual_import_scope']}",
            f"- trading_scope: {pilot['trading_scope']}",
            "",
            "## Raw Data Handling Boundary",
            "",
        ]
    )
    for key, value in pilot["raw_data_handling"].items():
        lines.append(f"- {key}: {str(value).lower() if isinstance(value, bool) else value}")
    lines.extend(
        [
            "",
            "## Required Operator Confirmations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in pilot["required_operator_confirmations"])
    phrase = pilot["approval_phrase_boundary"]
    lines.extend(
        [
            "",
            "## Approval Phrase Boundary",
            "",
            f"- cache_write_approval_phrase_required: {str(phrase['cache_write_approval_phrase_required']).lower()}",
            f"- cache_write_approval_phrase: {phrase['cache_write_approval_phrase']}",
            f"- cache_write_approval_phrase_issued: {str(phrase['cache_write_approval_phrase_issued']).lower()}",
            f"- actual_import_approval_phrase_required: {str(phrase['actual_import_approval_phrase_required']).lower()}",
            f"- actual_import_approval_phrase: {phrase['actual_import_approval_phrase']}",
            f"- actual_import_approval_phrase_issued: {str(phrase['actual_import_approval_phrase_issued']).lower()}",
            "- placeholder_phrase_is_not_runtime_approval: "
            f"{str(phrase['placeholder_phrase_is_not_runtime_approval']).lower()}",
            "",
            "## Stop Conditions",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in pilot["stop_conditions"])
    lines.extend(
        [
            "",
            "## What Is Still Not Approved",
            "",
            "- provider live access",
            "- live HTTP",
            "- Tiingo API call",
            "- Stooq / Yahoo / Polygon live fetch",
            "- cache write",
            "- actual refresh/import",
            "- manual actual import",
            "- raw OHLCV persistence",
            "- raw API response persistence",
            "- reports-private raw data write",
            "- Git-tracked raw data write",
            "- env/secret display",
            "- broker/manual raw data handling",
            "- trading action",
            "",
            "## Next Source-Only Handoff",
            "",
            f"- handoff_status: {data['next_cursor_handoff']['handoff_status']}",
            f"- recommended_next_source_only_task: {data['next_cursor_handoff']['recommended_next_source_only_task']}",
            f"- future_execution_task: {data['next_cursor_handoff']['future_execution_task']}",
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "preflight_verdict": verdict["preflight_verdict"],
                    "candidate_cache_path": preflight["candidate_cache_path"],
                    "all_structural_checks_pass": verdict["all_structural_checks_pass"],
                    "path_expansion_performed": preflight["path_expansion_performed"],
                    "filesystem_probe_performed": preflight["filesystem_probe_performed"],
                    "directory_created": preflight["directory_created"],
                    "cache_write_approval_status": verdict["cache_write_approval_status"],
                    "actual_import_approval_status": verdict["actual_import_approval_status"],
                    "approval_phrase_issued": verdict["approval_phrase_issued"],
                    "source_only": data["safety_flags"]["source_only"],
                    "cache_write_executed": data["safety_flags"]["cache_write_executed"],
                    "raw_ohlcv_persisted": data["safety_flags"]["raw_ohlcv_persisted"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_cache_purge_inventory_dryrun_contract_report(
    *,
    report_date: str,
    candidate_cache_path: str,
) -> tuple[str, dict[str, Any]]:
    contract = build_cache_purge_inventory_dryrun_contract(
        report_date=report_date,
        candidate_cache_path=candidate_cache_path,
    )
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="cache_purge_inventory_dryrun_contract"),
        "pack_version": "v69B",
        "cache_purge_inventory_dryrun_contract": contract.to_dict(),
    }
    data = payload["cache_purge_inventory_dryrun_contract"]
    verdict = data["readiness_verdict"]
    semantics = data["dryrun_semantics"]
    lines = [
        "# v69B Cache Purge / Inventory Dry-Run Contract & Redacted Manifest Schema",
        "",
        "## Verdict",
        "",
        f"- contract_verdict: {verdict['contract_verdict']}",
        f"- v69_preflight_verdict: {verdict['v69_preflight_verdict']}",
        f"- cache_write_approval_status: {verdict['cache_write_approval_status']}",
        f"- cache_write_execution_status: {verdict['cache_write_execution_status']}",
        f"- actual_import_approval_status: {verdict['actual_import_approval_status']}",
        f"- actual_import_execution_status: {verdict['actual_import_execution_status']}",
        f"- purge_execution_status: {verdict['purge_execution_status']}",
        f"- destructive_purge_approval_status: {verdict['destructive_purge_approval_status']}",
        f"- redacted_manifest_schema_status: {verdict['redacted_manifest_schema_status']}",
        "",
        "## Candidate Cache Path",
        "",
        f"- candidate_cache_path: {data['candidate_cache_path']}",
        f"- contract_status: {data['contract_status']}",
        "",
        "## Dry-Run Semantics",
        "",
    ]
    for key, value in semantics.items():
        lines.append(f"- {key}: {str(value).lower() if isinstance(value, bool) else value}")
    lines.extend(
        [
            "",
            "## Allowed Redacted Manifest Fields",
            "",
            "| field_name | field_type | allowed | reason |",
            "|---|---|---|---|",
        ]
    )
    for row in data["redacted_manifest_allowed_fields"]:
        lines.append(f"| {row['field_name']} | {row['field_type']} | {str(row['allowed']).lower()} | {row['reason']} |")
    lines.extend(
        [
            "",
            "## Forbidden Manifest Fields",
            "",
            "| field_name | field_type | allowed | reason |",
            "|---|---|---|---|",
        ]
    )
    for row in data["redacted_manifest_forbidden_fields"]:
        lines.append(f"| {row['field_name']} | {row['field_type']} | {str(row['allowed']).lower()} | {row['reason']} |")
    lines.extend(
        [
            "",
            "## Cache File Classification Contract",
            "",
            "| classification_id | label | selection_mode | raw_read_allowed | delete_allowed |",
            "|---|---|---|---|---|",
        ]
    )
    for row in data["cache_file_classification"]:
        lines.append(
            f"| {row['classification_id']} | {row['label']} | {row['selection_mode']} | "
            f"{str(row['raw_read_allowed']).lower()} | {str(row['delete_allowed']).lower()} |"
        )
    for title, key in (
        ("Purge Target Selection Semantics", "purge_target_selection_semantics"),
        ("Orphan Raw File Check Semantics", "orphan_raw_file_check_semantics"),
        ("Post-Purge Verification Checklist", "post_purge_verification_checklist"),
        ("Rollback Checklist", "rollback_checklist"),
    ):
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                "| step_id | execution_mode | destructive_action_allowed | raw_ohlcv_read_allowed | description |",
                "|---|---|---|---|---|",
            ]
        )
        for row in data[key]:
            lines.append(
                f"| {row['step_id']} | {row['execution_mode']} | "
                f"{str(row['destructive_action_allowed']).lower()} | "
                f"{str(row['raw_ohlcv_read_allowed']).lower()} | {row['description']} |"
            )
    lines.extend(
        [
            "",
            "## What Is Still Not Approved",
            "",
            "- provider live access",
            "- live HTTP",
            "- Tiingo API call",
            "- Stooq / Yahoo / Polygon live fetch",
            "- cache write",
            "- actual refresh/import",
            "- manual actual import",
            "- raw OHLCV read or persistence",
            "- raw API response persistence",
            "- reports-private raw data write",
            "- Git-tracked raw data write",
            "- destructive purge / file deletion",
            "- env/secret display",
            "- broker/manual raw data handling",
            "- trading action",
            "",
            "## Next Source-Only Handoff",
            "",
            f"- handoff_status: {data['next_cursor_handoff']['handoff_status']}",
            f"- recommended_next_task: {data['next_cursor_handoff']['recommended_next_task']}",
            "- do_not_start_without_future_approval_phrase: "
            f"{str(data['next_cursor_handoff']['do_not_start_without_future_approval_phrase']).lower()}",
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "contract_verdict": verdict["contract_verdict"],
                    "candidate_cache_path": data["candidate_cache_path"],
                    "redacted_manifest_schema_status": verdict["redacted_manifest_schema_status"],
                    "purge_execution_status": verdict["purge_execution_status"],
                    "cache_write_approval_status": verdict["cache_write_approval_status"],
                    "actual_import_approval_status": verdict["actual_import_approval_status"],
                    "no_file_deletion_executed": semantics["no_file_deletion_executed"],
                    "no_raw_ohlcv_read": semantics["no_raw_ohlcv_read"],
                    "source_only": data["safety_flags"]["source_only"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_cache_write_pilot_approval_packet_report(
    *,
    report_date: str,
    candidate_cache_path: str,
) -> tuple[str, dict[str, Any]]:
    packet = build_cache_write_pilot_approval_packet(
        report_date=report_date,
        candidate_cache_path=candidate_cache_path,
    )
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="cache_write_pilot_approval_packet"),
        "pack_version": "v70",
        "cache_write_pilot_approval_packet": packet.to_dict(),
    }
    data = payload["cache_write_pilot_approval_packet"]
    identity = data["future_pilot_identity"]
    verdict = data["readiness_verdict"]
    phrase = data["approval_phrase_boundary"]
    lines = [
        "# v70 Cache-Write Pilot Execution Runbook / Operator Approval Packet",
        "",
        "## Verdict",
        "",
        f"- packet_verdict: {verdict['packet_verdict']}",
        f"- cache_write_approval_status: {verdict['cache_write_approval_status']}",
        f"- cache_write_execution_status: {verdict['cache_write_execution_status']}",
        f"- actual_import_approval_status: {verdict['actual_import_approval_status']}",
        f"- actual_import_execution_status: {verdict['actual_import_execution_status']}",
        f"- trading_action_status: {verdict['trading_action_status']}",
        f"- raw_ohlcv_persistence_status: {verdict['raw_ohlcv_persistence_status']}",
        f"- provider_live_access_status: {verdict['provider_live_access_status']}",
        "",
        "## Future Pilot Identity",
        "",
        f"- provider: {identity['provider']}",
        f"- operation: {identity['operation']}",
        f"- first_subset: {', '.join(identity['first_subset'])}",
        f"- candidate_cache_path: {identity['candidate_cache_path']}",
        f"- data_type: {identity['data_type']}",
        f"- storage: {identity['storage']}",
        f"- v69_preflight_verdict: {identity['v69_preflight_verdict']}",
        f"- v69b_contract_verdict: {identity['v69b_contract_verdict']}",
        "",
        "## Required Preconditions",
        "",
        "| item_id | current_status | blocks_execution | description |",
        "|---|---|---|---|",
    ]
    for row in data["required_preconditions"]:
        lines.append(
            f"| {row['item_id']} | {row['current_status']} | "
            f"{str(row['blocks_execution_if_unmet']).lower()} | {row['description']} |"
        )
    for title, key in (
        ("Required Operator Fields", "required_operator_fields"),
        ("Forbidden Operations", "forbidden_operations"),
        ("Execution Runbook", "execution_runbook"),
    ):
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                "| item_id | current_status | required | description |",
                "|---|---|---|---|",
            ]
        )
        for row in data[key]:
            lines.append(
                f"| {row['item_id']} | {row['current_status']} | {str(row['required']).lower()} | "
                f"{row['description']} |"
            )
    constraints = data["output_constraints"]
    lines.extend(
        [
            "",
            "## Output Constraints",
            "",
            f"- allowed_outputs: {', '.join(constraints['allowed_outputs'])}",
            f"- forbidden_outputs: {', '.join(constraints['forbidden_outputs'])}",
            f"- reports_private_raw_data_allowed: {str(constraints['reports_private_raw_data_allowed']).lower()}",
            f"- git_tracked_raw_data_allowed: {str(constraints['git_tracked_raw_data_allowed']).lower()}",
            f"- chatgpt_cursor_raw_paste_allowed: {str(constraints['chatgpt_cursor_raw_paste_allowed']).lower()}",
            "",
            "## Approval Phrase Boundary",
            "",
            f"- this_package_approves_cache_write: {str(phrase['this_package_approves_cache_write']).lower()}",
            f"- cache_write_approval_phrase_required: {str(phrase['cache_write_approval_phrase_required']).lower()}",
            f"- cache_write_approval_phrase: {phrase['cache_write_approval_phrase']}",
            f"- cache_write_approval_phrase_issued: {str(phrase['cache_write_approval_phrase_issued']).lower()}",
            f"- future_phrase_scope: {phrase['future_phrase_scope']}",
            f"- actual_import_approval_phrase_required: {str(phrase['actual_import_approval_phrase_required']).lower()}",
            f"- actual_import_approval_phrase: {phrase['actual_import_approval_phrase']}",
            f"- actual_import_approval_phrase_issued: {str(phrase['actual_import_approval_phrase_issued']).lower()}",
            "- cache_write_does_not_approve_actual_import: "
            f"{str(phrase['cache_write_does_not_approve_actual_import']).lower()}",
            f"- cache_write_does_not_approve_trading: {str(phrase['cache_write_does_not_approve_trading']).lower()}",
            "- cache_write_does_not_approve_raw_data_in_git_reports_private_or_chat: "
            f"{str(phrase['cache_write_does_not_approve_raw_data_in_git_reports_private_or_chat']).lower()}",
            "",
            "## What Is Still Not Approved",
            "",
            "- provider live access",
            "- live HTTP",
            "- Tiingo API call",
            "- cache write",
            "- actual refresh/import",
            "- manual actual import",
            "- raw OHLCV persistence",
            "- raw API response persistence",
            "- reports-private raw data write",
            "- Git-tracked raw data write",
            "- env/secret display",
            "- broker/manual raw data handling",
            "- trading action",
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "packet_verdict": verdict["packet_verdict"],
                    "provider": identity["provider"],
                    "first_subset": identity["first_subset"],
                    "candidate_cache_path": identity["candidate_cache_path"],
                    "cache_write_approval_status": verdict["cache_write_approval_status"],
                    "actual_import_approval_status": verdict["actual_import_approval_status"],
                    "approval_phrase_issued": verdict["approval_phrase_issued"],
                    "source_only": data["safety_flags"]["source_only"],
                    "cache_write_executed": data["safety_flags"]["cache_write_executed"],
                    "raw_ohlcv_persisted": data["safety_flags"]["raw_ohlcv_persisted"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_cache_write_pilot_result_review_gate_report(
    *,
    report_date: str,
    candidate_cache_path: str,
) -> tuple[str, dict[str, Any]]:
    gate = build_cache_write_pilot_result_review_gate(
        report_date=report_date,
        candidate_cache_path=candidate_cache_path,
    )
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="cache_write_pilot_result_review_gate"),
        "pack_version": "v70B",
        "cache_write_pilot_result_review_gate": gate.to_dict(),
    }
    data = payload["cache_write_pilot_result_review_gate"]
    verdict = data["readiness_verdict"]
    lines = [
        "# v70B Cache-Write Pilot Result Review Gate / Data Quality Acceptance Pack",
        "",
        "## Verdict",
        "",
        f"- result_review_verdict: {verdict['result_review_verdict']}",
        f"- pilot_has_run: {str(verdict['pilot_has_run']).lower()}",
        f"- cache_write_pilot_review_ready: {str(verdict['cache_write_pilot_review_ready']).lower()}",
        f"- actual_import_readiness: {verdict['actual_import_readiness']}",
        f"- trading_readiness: {verdict['trading_readiness']}",
        f"- raw_ohlcv_fields_emitted: {str(verdict['raw_ohlcv_fields_emitted']).lower()}",
        "",
        "## Future Pilot Scope",
        "",
    ]
    for key, value in data["future_pilot_scope"].items():
        lines.append(f"- {key}: {', '.join(value) if isinstance(value, list) else value}")
    lines.extend(
        [
            "",
            "## Acceptance Criteria",
            "",
            "| criterion_id | current_status | raw_values_allowed | allowed_output | description |",
            "|---|---|---|---|---|",
        ]
    )
    for row in data["acceptance_criteria"]:
        lines.append(
            f"| {row['criterion_id']} | {row['current_status']} | "
            f"{str(row['raw_values_allowed']).lower()} | {row['allowed_output']} | {row['description']} |"
        )
    lines.extend(
        [
            "",
            "## Allowed Result Fields",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in data["allowed_result_fields"])
    lines.extend(
        [
            "",
            "## Forbidden Result Fields",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in data["forbidden_result_fields"])
    policy = data["verdict_policy"]
    lines.extend(
        [
            "",
            "## Verdict Policy",
            "",
            f"- allowed_verdicts: {', '.join(policy['allowed_verdicts'])}",
            f"- current_verdict: {policy['current_verdict']}",
            f"- pass_requires_no_raw_leakage: {str(policy['pass_requires_no_raw_leakage']).lower()}",
            f"- pass_requires_cache_path_policy_pass: {str(policy['pass_requires_cache_path_policy_pass']).lower()}",
            f"- pass_requires_redacted_manifest: {str(policy['pass_requires_redacted_manifest']).lower()}",
            f"- pass_requires_purge_contract: {str(policy['pass_requires_purge_contract']).lower()}",
            f"- pass_does_not_approve_actual_import: {str(policy['pass_does_not_approve_actual_import']).lower()}",
            f"- pass_does_not_approve_trading: {str(policy['pass_does_not_approve_trading']).lower()}",
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "result_review_verdict": verdict["result_review_verdict"],
                    "pilot_has_run": verdict["pilot_has_run"],
                    "actual_import_readiness": verdict["actual_import_readiness"],
                    "trading_readiness": verdict["trading_readiness"],
                    "raw_ohlcv_fields_emitted": verdict["raw_ohlcv_fields_emitted"],
                    "source_only": data["safety_flags"]["source_only"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def build_actual_import_readiness_boundary_report(
    *,
    report_date: str,
    candidate_cache_path: str,
) -> tuple[str, dict[str, Any]]:
    boundary = build_actual_import_readiness_boundary(
        report_date=report_date,
        candidate_cache_path=candidate_cache_path,
    )
    payload: dict[str, Any] = {
        **_payload_base(report_date, name="actual_import_readiness_boundary"),
        "pack_version": "v70C",
        "actual_import_readiness_boundary": boundary.to_dict(),
    }
    data = payload["actual_import_readiness_boundary"]
    verdict = data["readiness_verdict"]
    phrase = data["approval_phrase_boundary"]
    lines = [
        "# v70C Actual Import Separation / Quarantine Boundary / Readiness Matrix",
        "",
        "## Verdict",
        "",
        f"- cache_write_pilot_readiness: {verdict['cache_write_pilot_readiness']}",
        f"- cache_write_pilot_result_review_readiness: {verdict['cache_write_pilot_result_review_readiness']}",
        f"- actual_import_readiness: {verdict['actual_import_readiness']}",
        f"- manual_actual_import_readiness: {verdict['manual_actual_import_readiness']}",
        f"- trading_readiness: {verdict['trading_readiness']}",
        f"- cache_write_execution_allowed_now: {str(verdict['cache_write_execution_allowed_now']).lower()}",
        f"- actual_import_execution_allowed_now: {str(verdict['actual_import_execution_allowed_now']).lower()}",
        f"- trading_action_allowed_now: {str(verdict['trading_action_allowed_now']).lower()}",
        "",
        "## Cache Pilot Scope",
        "",
    ]
    for key, value in data["cache_pilot_scope"].items():
        lines.append(f"- {key}: {', '.join(value) if isinstance(value, list) else value}")
    lines.extend(
        [
            "",
            "## Quarantine Boundary",
            "",
        ]
    )
    for key, value in data["quarantine_boundary"].items():
        lines.append(f"- {key}: {str(value).lower() if isinstance(value, bool) else value}")
    lines.extend(
        [
            "",
            "## Readiness Matrix",
            "",
            "| area | current_status | approval_phrase_issued | execution_allowed_now | notes |",
            "|---|---|---|---|---|",
        ]
    )
    for row in data["readiness_matrix"]:
        lines.append(
            f"| {row['area']} | {row['current_status']} | "
            f"{str(row['approval_phrase_issued']).lower()} | {str(row['execution_allowed_now']).lower()} | "
            f"{row['notes']} |"
        )
    lines.extend(
        [
            "",
            "## Actual Import Prerequisites",
            "",
            "| area | current_status | execution_allowed_now | notes |",
            "|---|---|---|---|",
        ]
    )
    for row in data["actual_import_prerequisites"]:
        lines.append(
            f"| {row['area']} | {row['current_status']} | "
            f"{str(row['execution_allowed_now']).lower()} | {row['notes']} |"
        )
    lines.extend(
        [
            "",
            "## Approval Phrase Boundary",
            "",
            f"- cache_write_approval_phrase: {phrase['cache_write_approval_phrase']}",
            f"- cache_write_approval_phrase_issued: {str(phrase['cache_write_approval_phrase_issued']).lower()}",
            "- cache_write_approval_does_not_imply_actual_import: "
            f"{str(phrase['cache_write_approval_does_not_imply_actual_import']).lower()}",
            "- result_review_pass_required_for_actual_import_discussion: "
            f"{str(phrase['result_review_pass_required_for_actual_import_discussion']).lower()}",
            "- result_review_pass_not_sufficient_for_actual_import: "
            f"{str(phrase['result_review_pass_not_sufficient_for_actual_import']).lower()}",
            f"- actual_import_approval_phrase: {phrase['actual_import_approval_phrase']}",
            f"- actual_import_approval_phrase_issued: {str(phrase['actual_import_approval_phrase_issued']).lower()}",
            "- actual_import_approval_phrase_required_separately: "
            f"{str(phrase['actual_import_approval_phrase_required_separately']).lower()}",
            f"- trading_action_approval_in_scope: {str(phrase['trading_action_approval_in_scope']).lower()}",
            "",
            "## What Is Still Not Approved",
            "",
            "- provider live access",
            "- live HTTP",
            "- Tiingo API call",
            "- cache write",
            "- actual refresh/import",
            "- manual actual import",
            "- raw OHLCV persistence",
            "- raw API response persistence",
            "- reports-private raw data write",
            "- Git-tracked raw data write",
            "- env/secret display",
            "- broker/manual raw data handling",
            "- trading action",
            "",
            "## Machine-Readable Summary",
            "",
            "```json",
            json.dumps(
                {
                    "actual_import_readiness": verdict["actual_import_readiness"],
                    "cache_write_approval_does_not_imply_actual_import": phrase[
                        "cache_write_approval_does_not_imply_actual_import"
                    ],
                    "result_review_pass_not_sufficient_for_actual_import": phrase[
                        "result_review_pass_not_sufficient_for_actual_import"
                    ],
                    "actual_import_execution_allowed_now": verdict["actual_import_execution_allowed_now"],
                    "trading_action_allowed_now": verdict["trading_action_allowed_now"],
                    "source_only": data["safety_flags"]["source_only"],
                    "cache_write_executed": data["safety_flags"]["cache_write_executed"],
                    "actual_refresh_import_executed": data["safety_flags"]["actual_refresh_import_executed"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines), payload


def write_us_ohlcv_provider_selection_matrix_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "us_ohlcv_provider_selection_matrix.md"
        json_path = root / "us_ohlcv_provider_selection_matrix.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_us_ohlcv_provider_selection_matrix_md"] = md_path
        paths[f"{label}_us_ohlcv_provider_selection_matrix_json"] = json_path
    return paths


def write_tiingo_current_docs_recheck_pack_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "tiingo_current_docs_recheck_pack.md"
        json_path = root / "tiingo_current_docs_recheck_pack.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_tiingo_current_docs_recheck_pack_md"] = md_path
        paths[f"{label}_tiingo_current_docs_recheck_pack_json"] = json_path
    return paths


def write_tiingo_manual_signoff_ledger_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "tiingo_manual_signoff_ledger.md"
        json_path = root / "tiingo_manual_signoff_ledger.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_tiingo_manual_signoff_ledger_md"] = md_path
        paths[f"{label}_tiingo_manual_signoff_ledger_json"] = json_path
    return paths


def write_tiingo_live_fetch_result_review_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "tiingo_live_fetch_result_review.md"
        json_path = root / "tiingo_live_fetch_result_review.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_tiingo_live_fetch_result_review_md"] = md_path
        paths[f"{label}_tiingo_live_fetch_result_review_json"] = json_path
    return paths


def write_cross_provider_validation_runbook_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "cross_provider_validation_runbook.md"
        json_path = root / "cross_provider_validation_runbook.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_cross_provider_validation_runbook_md"] = md_path
        paths[f"{label}_cross_provider_validation_runbook_json"] = json_path
    return paths


def write_cross_provider_validation_result_review_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "cross_provider_validation_result_review.md"
        json_path = root / "cross_provider_validation_result_review.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_cross_provider_validation_result_review_md"] = md_path
        paths[f"{label}_cross_provider_validation_result_review_json"] = json_path
    return paths


def write_cache_write_readiness_gate_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "cache_write_readiness_gate.md"
        json_path = root / "cache_write_readiness_gate.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_cache_write_readiness_gate_md"] = md_path
        paths[f"{label}_cache_write_readiness_gate_json"] = json_path
    return paths


def write_cache_write_operator_signoff_sheet_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "cache_write_operator_signoff_sheet.md"
        json_path = root / "cache_write_operator_signoff_sheet.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_cache_write_operator_signoff_sheet_md"] = md_path
        paths[f"{label}_cache_write_operator_signoff_sheet_json"] = json_path
    return paths


def write_cache_path_preflight_approval_package_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "cache_path_preflight_approval_package.md"
        json_path = root / "cache_path_preflight_approval_package.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_cache_path_preflight_approval_package_md"] = md_path
        paths[f"{label}_cache_path_preflight_approval_package_json"] = json_path
    return paths


def write_cache_purge_inventory_dryrun_contract_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "cache_purge_inventory_dryrun_contract.md"
        json_path = root / "cache_purge_inventory_dryrun_contract.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_cache_purge_inventory_dryrun_contract_md"] = md_path
        paths[f"{label}_cache_purge_inventory_dryrun_contract_json"] = json_path
    return paths


def write_cache_write_pilot_approval_packet_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "cache_write_pilot_approval_packet.md"
        json_path = root / "cache_write_pilot_approval_packet.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_cache_write_pilot_approval_packet_md"] = md_path
        paths[f"{label}_cache_write_pilot_approval_packet_json"] = json_path
    return paths


def write_cache_write_pilot_result_review_gate_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "cache_write_pilot_result_review_gate.md"
        json_path = root / "cache_write_pilot_result_review_gate.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_cache_write_pilot_result_review_gate_md"] = md_path
        paths[f"{label}_cache_write_pilot_result_review_gate_json"] = json_path
    return paths


def write_actual_import_readiness_boundary_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "actual_import_readiness_boundary.md"
        json_path = root / "actual_import_readiness_boundary.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_actual_import_readiness_boundary_md"] = md_path
        paths[f"{label}_actual_import_readiness_boundary_json"] = json_path
    return paths


def write_us_ohlcv_pilot_approval_bundle_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "us_ohlcv_pilot_approval_bundle.md"
        json_path = root / "us_ohlcv_pilot_approval_bundle.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_us_ohlcv_pilot_approval_bundle_md"] = md_path
        paths[f"{label}_us_ohlcv_pilot_approval_bundle_json"] = json_path
    return paths


def write_us_provider_current_evidence_pack_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "us_provider_current_evidence_pack.md"
        json_path = root / "us_provider_current_evidence_pack.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_us_provider_current_evidence_pack_md"] = md_path
        paths[f"{label}_us_provider_current_evidence_pack_json"] = json_path
    return paths


def write_ohlcv_provider_execution_approval_request_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "ohlcv_provider_execution_approval_request.md"
        json_path = root / "ohlcv_provider_execution_approval_request.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_ohlcv_provider_execution_approval_request_md"] = md_path
        paths[f"{label}_ohlcv_provider_execution_approval_request_json"] = json_path
    return paths


def write_ohlcv_provider_approved_execution_runbook_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "ohlcv_provider_approved_execution_runbook.md"
        json_path = root / "ohlcv_provider_approved_execution_runbook.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_ohlcv_provider_approved_execution_runbook_md"] = md_path
        paths[f"{label}_ohlcv_provider_approved_execution_runbook_json"] = json_path
    return paths


def write_ohlcv_provider_safe_execution_harness_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "ohlcv_provider_safe_execution_harness.md"
        json_path = root / "ohlcv_provider_safe_execution_harness.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_ohlcv_provider_safe_execution_harness_md"] = md_path
        paths[f"{label}_ohlcv_provider_safe_execution_harness_json"] = json_path
    return paths


def write_ohlcv_provider_approval_package_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "ohlcv_provider_approval_package.md"
        json_path = root / "ohlcv_provider_approval_package.json"
        md_path.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_ohlcv_provider_approval_package_md"] = md_path
        paths[f"{label}_ohlcv_provider_approval_package_json"] = json_path
    return paths


def write_ohlcv_provider_automation_core_outputs(
    *,
    out_dir: Path,
    report_date: str,
    result: OhlcvProviderAutomationCoreResult,
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for stem, (markdown, payload) in result.reports.items():
        for label, root in (("latest", latest), ("weekly", weekly)):
            md_path = root / f"{stem}.md"
            json_path = root / f"{stem}.json"
            md_path.write_text(markdown.rstrip() + "\n", encoding="utf-8")
            json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths[f"{label}_{stem}_md"] = md_path
            paths[f"{label}_{stem}_json"] = json_path
    return paths
