"""Source-only US OHLCV pilot approval bundle.

This module assembles the v46 provider selection matrix, v48 current evidence
pack, and provider approval/runbook layers into a single non-executing first
pilot approval bundle. It never performs live HTTP, provider access, cache
writes, imports, secret inspection, raw data handling, or trading actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invis_alpha_os.data.ohlcv_provider_approval_request import (
    DRAFT_HANDOFF_MARKER,
    build_provider_execution_approval_request,
)
from invis_alpha_os.data.ohlcv_provider_registry import PUBLIC_OHLCV_APPROVAL_PHRASE
from invis_alpha_os.data.ohlcv_provider_runbook import (
    NOT_EXECUTED_MARKER,
    ProviderApprovedExecutionScenario,
)
from invis_alpha_os.data.us_ohlcv_provider_selection import (
    DEFAULT_US_PILOT_UNIVERSE,
    build_us_ohlcv_provider_selection_matrix,
)
from invis_alpha_os.data.us_provider_current_evidence import (
    build_us_provider_current_evidence_pack,
)


DEFAULT_US_OHLCV_PILOT_PROVIDER = "Tiingo"
DEFAULT_US_OHLCV_PILOT_SCENARIO = "public_ohlcv"
DEFAULT_US_OHLCV_PILOT_DATE_RANGE = (
    "2024-01-01 to latest_completed_trading_day_at_future_live_test"
)
US_OHLCV_PILOT_ALLOWED_PROVIDERS = (
    "Tiingo",
    "Polygon.io",
    "Stooq",
    "Alpha Vantage",
    "EODHD",
    "Yahoo Finance / yfinance",
)
US_OHLCV_PILOT_ALLOWED_SCENARIOS = ("public_ohlcv",)
US_OHLCV_PILOT_PRIMARY_APPROVAL_PHRASES = (PUBLIC_OHLCV_APPROVAL_PHRASE,)


@dataclass(frozen=True)
class UsOhlcvPilotCandidate:
    provider: str
    scenario: str
    operation: str
    date_range: str
    universe: tuple[str, ...]
    primary_approval_phrase: str
    approval_phrase_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "scenario": self.scenario,
            "operation": self.operation,
            "date_range": self.date_range,
            "universe": list(self.universe),
            "primary_approval_phrase": self.primary_approval_phrase,
            "approval_phrase_status": self.approval_phrase_status,
        }


@dataclass(frozen=True)
class UsOhlcvPilotEvidenceSummary:
    provider_selection_matrix: dict[str, Any]
    current_evidence_pack: dict[str, Any]
    execution_approval_request: dict[str, Any]
    approved_execution_runbook: dict[str, Any]
    safe_execution_harness: dict[str, Any]
    approval_package: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_selection_matrix": dict(self.provider_selection_matrix),
            "current_evidence_pack": dict(self.current_evidence_pack),
            "execution_approval_request": dict(self.execution_approval_request),
            "approved_execution_runbook": dict(self.approved_execution_runbook),
            "safe_execution_harness": dict(self.safe_execution_harness),
            "approval_package": dict(self.approval_package),
        }


@dataclass(frozen=True)
class UsOhlcvPilotSafetyBoundary:
    source_only: bool
    commands_executed: bool
    live_http_executed: bool
    public_ohlcv_source_live_fetch_executed: bool
    provider_live_access_executed: bool
    jquants_refresh_executed: bool
    cache_write_executed: bool
    actual_refresh_import_executed: bool
    manual_actual_import_executed: bool
    env_secret_displayed: bool
    broker_manual_raw_data_handled: bool
    workflow_dependency_pyproject_changed: bool
    reports_private_touched: bool
    trading_action_executed: bool
    explicitly_not_approved: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_only": self.source_only,
            "commands_executed": self.commands_executed,
            "live_http_executed": self.live_http_executed,
            "public_ohlcv_source_live_fetch_executed": self.public_ohlcv_source_live_fetch_executed,
            "provider_live_access_executed": self.provider_live_access_executed,
            "jquants_refresh_executed": self.jquants_refresh_executed,
            "cache_write_executed": self.cache_write_executed,
            "actual_refresh_import_executed": self.actual_refresh_import_executed,
            "manual_actual_import_executed": self.manual_actual_import_executed,
            "env_secret_displayed": self.env_secret_displayed,
            "broker_manual_raw_data_handled": self.broker_manual_raw_data_handled,
            "workflow_dependency_pyproject_changed": self.workflow_dependency_pyproject_changed,
            "reports_private_touched": self.reports_private_touched,
            "trading_action_executed": self.trading_action_executed,
            "explicitly_not_approved": list(self.explicitly_not_approved),
        }


@dataclass(frozen=True)
class UsOhlcvPilotApprovalBundle:
    report_date: str
    candidate: UsOhlcvPilotCandidate
    evidence_summary: UsOhlcvPilotEvidenceSummary
    safety: UsOhlcvPilotSafetyBoundary
    commands_planned_but_not_executed: tuple[str, ...]
    preflight_checklist: tuple[str, ...]
    redaction_secret_handling_checklist: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    verification_plan: tuple[str, ...]
    rollback_no_write_discipline: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    risk_register: tuple[dict[str, str], ...]
    evidence_gap_closure_checklist: tuple[dict[str, str], ...]
    cursor_handoff_draft: str
    final_readiness_verdict: str
    missing_evidence: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "candidate": self.candidate.to_dict(),
            "evidence_summary": self.evidence_summary.to_dict(),
            "safety": self.safety.to_dict(),
            "commands_planned_but_not_executed": list(self.commands_planned_but_not_executed),
            "preflight_checklist": list(self.preflight_checklist),
            "redaction_secret_handling_checklist": list(self.redaction_secret_handling_checklist),
            "expected_outputs": list(self.expected_outputs),
            "verification_plan": list(self.verification_plan),
            "rollback_no_write_discipline": list(self.rollback_no_write_discipline),
            "stop_conditions": list(self.stop_conditions),
            "risk_register": [dict(item) for item in self.risk_register],
            "evidence_gap_closure_checklist": [
                dict(item) for item in self.evidence_gap_closure_checklist
            ],
            "cursor_handoff_draft": self.cursor_handoff_draft,
            "final_readiness_verdict": self.final_readiness_verdict,
            "missing_evidence": list(self.missing_evidence),
        }


def _provider_from_modeled_input(provider: str) -> str:
    normalized = provider.strip().lower()
    aliases = {
        "tiingo": "Tiingo",
        "polygon": "Polygon.io",
        "polygon.io": "Polygon.io",
        "stooq": "Stooq",
        "alpha_vantage": "Alpha Vantage",
        "alpha vantage": "Alpha Vantage",
        "eodhd": "EODHD",
        "yahoo": "Yahoo Finance / yfinance",
        "yfinance": "Yahoo Finance / yfinance",
        "yahoo finance / yfinance": "Yahoo Finance / yfinance",
    }
    if normalized not in aliases:
        allowed = ", ".join(US_OHLCV_PILOT_ALLOWED_PROVIDERS)
        raise ValueError(f"unknown provider: {provider}; allowed: {allowed}")
    return aliases[normalized]


def _scenario_from_modeled_input(scenario: str) -> str:
    normalized = scenario.strip().lower()
    if normalized not in US_OHLCV_PILOT_ALLOWED_SCENARIOS:
        allowed = ", ".join(US_OHLCV_PILOT_ALLOWED_SCENARIOS)
        raise ValueError(f"unknown scenario: {scenario}; allowed: {allowed}")
    return normalized


def _evidence_summary(*, report_date: str) -> UsOhlcvPilotEvidenceSummary:
    selection = build_us_ohlcv_provider_selection_matrix(report_date=report_date).to_dict()
    current_evidence = build_us_provider_current_evidence_pack(report_date=report_date).to_dict()
    approval_request = build_provider_execution_approval_request(
        report_date=report_date,
        scenario=ProviderApprovedExecutionScenario.PUBLIC_OHLCV,
    ).to_dict()
    request = approval_request["request"]
    source_runbook = request["source_runbook"]
    harness = source_runbook["safe_execution_harness"]["result"]
    package = source_runbook["approval_package"]
    return UsOhlcvPilotEvidenceSummary(
        provider_selection_matrix={
            "exists": True,
            "provider_selected": False,
            "recommended_first_pilot_provider": selection["ranking"]["best_first_pilot_provider"],
            "recommended_production_candidate": selection["ranking"]["best_production_candidate"],
            "recommended_free_fallback": selection["ranking"]["best_free_fallback"],
            "pilot_universe": selection["pilot_design"]["pilot_universe"],
            "pilot_date_range": selection["pilot_design"]["pilot_date_range"],
            "cache_write_approved": selection["pilot_design"]["cache_write_approved"],
            "actual_import_approved": selection["pilot_design"]["actual_import_approved"],
        },
        current_evidence_pack={
            "exists": True,
            "needs_current_recheck": True,
            "evidence_confidence": "seed_only / manual_recheck_required",
            "source_accessed_live": False,
            "evidence_gaps": current_evidence["evidence_gaps"],
            "recommended_first_pilot_recheck": current_evidence["recommended_first_pilot_recheck"],
        },
        execution_approval_request={
            "exists": True,
            "scenario": request["scope"]["scenario"],
            "primary_approval_phrase": request["decision_prompt"]["primary_approval_phrase"],
            "commands_executed": request["risk_summary"]["commands_executed"],
        },
        approved_execution_runbook={
            "exists": True,
            "source_only": source_runbook["decision_record"]["source_only"],
            "commands_marked_not_executed": all(
                command.startswith(NOT_EXECUTED_MARKER)
                for command in source_runbook["command_plan"]["commands"]
            ),
            "operator_checklist_exists": True,
        },
        safe_execution_harness={
            "exists": True,
            "mode": harness["mode"],
            "verdict": harness["transcript"]["verdict"],
            "audit_summary": harness["audit_summary"],
        },
        approval_package={
            "exists": True,
            "dry_run_only": package["execution_plan"]["dry_run_only"],
            "dangerous_gates_default_status": "blocked_until_explicit_approval",
            "requirements": [
                requirement["gate"]
                for requirement in package["requirements"]
            ],
        },
    )


def _cursor_handoff_draft(candidate: UsOhlcvPilotCandidate) -> str:
    return "\n".join(
        [
            DRAFT_HANDOFF_MARKER,
            "",
            "purpose: future Tiingo live-fetch-only US OHLCV pilot",
            f"scenario: {candidate.scenario}",
            f"provider: {candidate.provider}",
            f"required_approval_phrase: {candidate.primary_approval_phrase}",
            f"tickers: {', '.join(candidate.universe)}",
            f"date_range: {candidate.date_range}",
            "",
            "allowed_only_after_human_approval_phrase:",
            "- public OHLCV source live fetch only",
            "",
            "explicitly_prohibited:",
            "- cache write",
            "- actual refresh/import",
            "- manual actual import",
            "- J-Quants refresh",
            "- trading action",
            "- secret display",
            "- broker/manual raw data handling",
            "",
            "planned_commands:",
            (
                f"{NOT_EXECUTED_MARKER}\n"
                ".venv/bin/python -m invis_alpha_os.cli.main "
                "<future-approved-tiingo-live-fetch-only-pilot> "
                "--provider tiingo --scenario public_ohlcv "
                "--tickers AAPL,MSFT,NVDA,AMD,AVGO,TSLA,GOOGL,AMZN,META,JPM,XOM,UNH,SPY,QQQ "
                "--date-from 2024-01-01 --date-to <latest_completed_trading_day>"
            ),
            "",
            "stop if approval phrase, provider, ticker scope, date range, or redaction rules differ.",
        ]
    )


def build_us_ohlcv_pilot_approval_bundle(
    *,
    report_date: str,
    provider: str = DEFAULT_US_OHLCV_PILOT_PROVIDER,
    scenario: str = DEFAULT_US_OHLCV_PILOT_SCENARIO,
) -> UsOhlcvPilotApprovalBundle:
    modeled_provider = _provider_from_modeled_input(provider)
    modeled_scenario = _scenario_from_modeled_input(scenario)
    candidate = UsOhlcvPilotCandidate(
        provider=modeled_provider,
        scenario=modeled_scenario,
        operation="future live fetch only - not executed by this bundle",
        date_range=DEFAULT_US_OHLCV_PILOT_DATE_RANGE,
        universe=DEFAULT_US_PILOT_UNIVERSE,
        primary_approval_phrase=PUBLIC_OHLCV_APPROVAL_PHRASE,
        approval_phrase_status="required_but_not_provided_in_this_source_only_bundle",
    )
    explicitly_not_approved = (
        "cache_write",
        "actual_refresh_import",
        "manual_actual_import",
        "jquants_refresh",
        "broker_manual_raw_data_handling",
        "trading_action",
        "env_secret_display",
        "workflow_dependency_pyproject_change",
        "reports_private_change",
    )
    commands = (
        (
            f"{NOT_EXECUTED_MARKER}\n"
            ".venv/bin/python -m invis_alpha_os.cli.main "
            "<future-approved-tiingo-live-fetch-only-pilot> "
            "--provider tiingo --scenario public_ohlcv "
            "--tickers AAPL,MSFT,NVDA,AMD,AVGO,TSLA,GOOGL,AMZN,META,JPM,XOM,UNH,SPY,QQQ "
            "--date-from 2024-01-01 --date-to <latest_completed_trading_day>"
        ),
    )
    return UsOhlcvPilotApprovalBundle(
        report_date=report_date,
        candidate=candidate,
        evidence_summary=_evidence_summary(report_date=report_date),
        safety=UsOhlcvPilotSafetyBoundary(
            source_only=True,
            commands_executed=False,
            live_http_executed=False,
            public_ohlcv_source_live_fetch_executed=False,
            provider_live_access_executed=False,
            jquants_refresh_executed=False,
            cache_write_executed=False,
            actual_refresh_import_executed=False,
            manual_actual_import_executed=False,
            env_secret_displayed=False,
            broker_manual_raw_data_handled=False,
            workflow_dependency_pyproject_changed=False,
            reports_private_touched=False,
            trading_action_executed=False,
            explicitly_not_approved=explicitly_not_approved,
        ),
        commands_planned_but_not_executed=commands,
        preflight_checklist=(
            "Confirm exact human approval phrase is present in the future execution task.",
            "Confirm provider is Tiingo and scenario is public_ohlcv.",
            "Confirm pilot universe and date range match this bundle.",
            "Confirm future execution is live-fetch-only and excludes cache write/import.",
            "Confirm no workflow, dependency, pyproject, or GitHub settings change is required.",
        ),
        redaction_secret_handling_checklist=(
            "Do not print env values, API keys, tokens, credentials, or account identifiers.",
            "Do not persist raw provider responses in repo artifacts.",
            "Do not display broker or manual raw data.",
            "Only sanitized shape digests and redacted summaries are allowed in the future task.",
        ),
        expected_outputs=(
            "redacted provider fetch log",
            "sanitized OHLCV shape digest",
            "per-symbol success/failure table",
            "adjustment and corporate-action method notes",
            "no cache artifact and no import artifact",
        ),
        verification_plan=(
            "Verify every pilot symbol has an explicit success or provider-reason failure.",
            "Verify no cache files changed.",
            "Verify no import outputs changed.",
            "Verify no secrets or raw provider payloads are printed or committed.",
            "Verify adjusted price method and rate-limit behavior are summarized.",
        ),
        rollback_no_write_discipline=(
            "No rollback should be needed for this source-only bundle because it executes nothing.",
            "Future live-fetch-only task must stop before any cache write or import path is touched.",
            "If any state-changing path changes, stop and treat it as scope violation.",
        ),
        stop_conditions=(
            "Missing or altered approval phrase.",
            "Provider is not Tiingo or scenario is not public_ohlcv.",
            "Any request to write cache or import data.",
            "Any request to display secrets, raw provider responses, broker data, or manual raw data.",
            "Any workflow, dependency, pyproject, GitHub settings, or trading-action requirement.",
        ),
        risk_register=(
            {
                "risk": "current_provider_terms_not_verified",
                "mitigation": "manual current recheck remains required before pilot execution",
                "status": "open",
            },
            {
                "risk": "planned_command_misread_as_execution_instruction",
                "mitigation": "all commands are marked NOT EXECUTED and gated by approval phrase",
                "status": "controlled",
            },
            {
                "risk": "cache_or_import_scope_creep",
                "mitigation": "cache/import are explicitly not approved and have stop conditions",
                "status": "controlled",
            },
        ),
        evidence_gap_closure_checklist=(
            {
                "gap": "pricing_terms",
                "manual_recheck": "Confirm Tiingo current pricing, plan limits, redistribution terms, and trial constraints.",
                "operator_signoff": "pending",
            },
            {
                "gap": "adjusted_price_methodology",
                "manual_recheck": "Confirm adjusted close or adjusted OHLC method, split handling, and dividend treatment.",
                "operator_signoff": "pending",
            },
            {
                "gap": "cache_suitability",
                "manual_recheck": "Confirm whether sanitized derived cache storage is permitted before any cache write approval.",
                "operator_signoff": "pending",
            },
            {
                "gap": "bulk_throughput",
                "manual_recheck": "Confirm rate limits, batch endpoints, retry rules, and pilot-safe request volume.",
                "operator_signoff": "pending",
            },
            {
                "gap": "adr_delisted_coverage",
                "manual_recheck": "Confirm ADR coverage, delisted coverage, and symbol mapping caveats for the pilot universe.",
                "operator_signoff": "pending",
            },
        ),
        cursor_handoff_draft=_cursor_handoff_draft(candidate),
        final_readiness_verdict="ready_for_human_approval_review_not_ready_for_execution",
        missing_evidence=(
            "manual current Tiingo pricing and plan limits",
            "manual current Tiingo terms/cache suitability",
            "manual current Tiingo adjusted price methodology",
            "manual current Tiingo ADR/delisted coverage",
            "manual current Tiingo bulk/rate-limit suitability",
        ),
    )


def validate_single_primary_approval_phrase(bundle: UsOhlcvPilotApprovalBundle) -> bool:
    return (
        bundle.candidate.primary_approval_phrase in US_OHLCV_PILOT_PRIMARY_APPROVAL_PHRASES
        and len(US_OHLCV_PILOT_PRIMARY_APPROVAL_PHRASES) == 1
    )
