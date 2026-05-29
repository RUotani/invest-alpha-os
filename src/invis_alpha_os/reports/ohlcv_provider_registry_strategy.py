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
    _ = registry_md, planner_md, approval_md, harness_md, runbook_md
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
