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
