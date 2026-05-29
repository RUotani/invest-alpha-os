"""Source-only operator runbooks for approved OHLCV provider execution.

The runbook layer prepares human/operator checklists for a future separately
approved task. It never performs live HTTP, cache writes, refreshes, imports,
secret reads, broker login, or raw manual data handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from invis_alpha_os.data.ohlcv_provider_approval import (
    ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
    CACHE_WRITE_APPROVAL_PHRASE,
    ProviderApprovalPackage,
    ProviderExecutionAction,
    ProviderExecutionGate,
    build_default_provider_approval_package,
)
from invis_alpha_os.data.ohlcv_provider_execution import (
    ProviderExecutionHarness,
    ProviderExecutionMode,
    build_provider_safe_execution_harness,
)
from invis_alpha_os.data.ohlcv_provider_registry import (
    JQUANTS_APPROVAL_PHRASE,
    MANUAL_IMPORT_APPROVAL_PHRASE,
    PUBLIC_OHLCV_APPROVAL_PHRASE,
)


NOT_EXECUTED_MARKER = "# NOT EXECUTED - requires explicit approval"


class ProviderApprovedExecutionScenario(str, Enum):
    PUBLIC_OHLCV = "public_ohlcv"
    JQUANTS_REFRESH = "jquants_refresh"
    CACHE_WRITE = "cache_write"
    ACTUAL_IMPORT = "actual_import"
    MANUAL_IMPORT = "manual_import"


@dataclass(frozen=True)
class ProviderExecutionScope:
    scenario: ProviderApprovedExecutionScenario
    provider_action: ProviderExecutionAction
    provider_candidates: tuple[str, ...]
    tickers: tuple[str, ...]
    date_range: str
    requested_operation: str
    remains_unapproved: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario.value,
            "provider_action": self.provider_action.value,
            "provider_candidates": list(self.provider_candidates),
            "tickers": list(self.tickers),
            "date_range": self.date_range,
            "requested_operation": self.requested_operation,
            "remains_unapproved": list(self.remains_unapproved),
        }


@dataclass(frozen=True)
class ProviderApprovalPhraseRequirement:
    scenario: ProviderApprovedExecutionScenario
    phrase: str
    required_gates: tuple[ProviderExecutionGate, ...]
    approval_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario.value,
            "phrase": self.phrase,
            "required_gates": [gate.value for gate in self.required_gates],
            "approval_status": self.approval_status,
        }


@dataclass(frozen=True)
class ProviderOperatorStep:
    order: int
    title: str
    detail: str
    required_before_next: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "order": self.order,
            "title": self.title,
            "detail": self.detail,
            "required_before_next": self.required_before_next,
        }


@dataclass(frozen=True)
class ProviderExecutionCommandPlan:
    commands: tuple[str, ...]
    not_executed_marker: str = NOT_EXECUTED_MARKER

    def to_dict(self) -> dict[str, Any]:
        return {
            "not_executed_marker": self.not_executed_marker,
            "commands": list(self.commands),
        }


@dataclass(frozen=True)
class ProviderOperatorChecklist:
    preconditions: tuple[ProviderOperatorStep, ...]
    preflight: tuple[ProviderOperatorStep, ...]
    artifacts: tuple[str, ...]
    verification: tuple[ProviderOperatorStep, ...]
    rollback: tuple[ProviderOperatorStep, ...]
    stop_conditions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "preconditions": [step.to_dict() for step in self.preconditions],
            "preflight": [step.to_dict() for step in self.preflight],
            "artifacts": list(self.artifacts),
            "verification": [step.to_dict() for step in self.verification],
            "rollback": [step.to_dict() for step in self.rollback],
            "stop_conditions": list(self.stop_conditions),
        }


@dataclass(frozen=True)
class ProviderOperatorDecisionRecord:
    scenario: ProviderApprovedExecutionScenario
    approved_in_this_runbook: bool
    source_only: bool
    audit_flags: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario.value,
            "approved_in_this_runbook": self.approved_in_this_runbook,
            "source_only": self.source_only,
            "audit_flags": dict(self.audit_flags),
        }


@dataclass(frozen=True)
class ProviderApprovedExecutionRunbook:
    report_date: str
    scope: ProviderExecutionScope
    approval_requirement: ProviderApprovalPhraseRequirement
    command_plan: ProviderExecutionCommandPlan
    checklist: ProviderOperatorChecklist
    decision_record: ProviderOperatorDecisionRecord
    approval_package: ProviderApprovalPackage
    safe_execution_harness: ProviderExecutionHarness

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "scope": self.scope.to_dict(),
            "approval_requirement": self.approval_requirement.to_dict(),
            "command_plan": self.command_plan.to_dict(),
            "checklist": self.checklist.to_dict(),
            "decision_record": self.decision_record.to_dict(),
            "approval_package": self.approval_package.to_dict(),
            "safe_execution_harness": self.safe_execution_harness.to_dict(),
        }


def scenario_from_cli(value: str) -> ProviderApprovedExecutionScenario:
    try:
        return ProviderApprovedExecutionScenario(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ProviderApprovedExecutionScenario)
        raise ValueError(f"unknown scenario: {value}; allowed: {allowed}") from exc


def _scenario_action(scenario: ProviderApprovedExecutionScenario) -> ProviderExecutionAction:
    return {
        ProviderApprovedExecutionScenario.PUBLIC_OHLCV: ProviderExecutionAction.PUBLIC_PROVIDER_LIVE_FETCH,
        ProviderApprovedExecutionScenario.JQUANTS_REFRESH: ProviderExecutionAction.JQUANTS_REFRESH,
        ProviderApprovedExecutionScenario.CACHE_WRITE: ProviderExecutionAction.CACHE_WRITE,
        ProviderApprovedExecutionScenario.ACTUAL_IMPORT: ProviderExecutionAction.ACTUAL_IMPORT,
        ProviderApprovedExecutionScenario.MANUAL_IMPORT: ProviderExecutionAction.MANUAL_IMPORT,
    }[scenario]


def _scenario_phrase(scenario: ProviderApprovedExecutionScenario) -> str:
    return {
        ProviderApprovedExecutionScenario.PUBLIC_OHLCV: PUBLIC_OHLCV_APPROVAL_PHRASE,
        ProviderApprovedExecutionScenario.JQUANTS_REFRESH: JQUANTS_APPROVAL_PHRASE,
        ProviderApprovedExecutionScenario.CACHE_WRITE: CACHE_WRITE_APPROVAL_PHRASE,
        ProviderApprovedExecutionScenario.ACTUAL_IMPORT: ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
        ProviderApprovedExecutionScenario.MANUAL_IMPORT: MANUAL_IMPORT_APPROVAL_PHRASE,
    }[scenario]


def _scope_for_scenario(
    *,
    scenario: ProviderApprovedExecutionScenario,
    action: ProviderExecutionAction,
) -> ProviderExecutionScope:
    common_tickers = ("285A", "5802", "5803", "6645", "NVDA", "MSFT")
    if scenario == ProviderApprovedExecutionScenario.PUBLIC_OHLCV:
        return ProviderExecutionScope(
            scenario=scenario,
            provider_action=action,
            provider_candidates=("stooq_live_gated", "alpha_vantage_gated", "tiingo_gated", "polygon_gated"),
            tickers=common_tickers,
            date_range="operator_selected_small_sample",
            requested_operation="future public OHLCV source live fetch preview",
            remains_unapproved=("cache_write", "actual_refresh_import", "manual_import"),
        )
    if scenario == ProviderApprovedExecutionScenario.JQUANTS_REFRESH:
        return ProviderExecutionScope(
            scenario=scenario,
            provider_action=action,
            provider_candidates=("jquants",),
            tickers=("285A", "5802", "5803", "6645", "5801"),
            date_range="within_contract_date_window_only",
            requested_operation="future J-Quants gated refresh",
            remains_unapproved=("cache_write", "actual_import", "manual_import"),
        )
    if scenario == ProviderApprovedExecutionScenario.CACHE_WRITE:
        return ProviderExecutionScope(
            scenario=scenario,
            provider_action=action,
            provider_candidates=("jquants", "stooq_manual", "approved_public_provider_output"),
            tickers=common_tickers,
            date_range="operator_selected_cache_delta_only",
            requested_operation="future approved cache write",
            remains_unapproved=("live_fetch", "actual_import", "manual_import"),
        )
    if scenario == ProviderApprovedExecutionScenario.ACTUAL_IMPORT:
        return ProviderExecutionScope(
            scenario=scenario,
            provider_action=action,
            provider_candidates=("approved_cache_delta",),
            tickers=common_tickers,
            date_range="operator_selected_import_delta_only",
            requested_operation="future actual refresh/import",
            remains_unapproved=("new_live_fetch", "manual_import", "trading_action"),
        )
    return ProviderExecutionScope(
        scenario=scenario,
        provider_action=action,
        provider_candidates=("stooq_manual_dropzone",),
        tickers=("285A", "5802", "5803", "6645", "5801"),
        date_range="operator_selected_manual_file_delta_only",
        requested_operation="future manual actual import",
        remains_unapproved=("broker_login", "raw_manual_data_display", "trading_action"),
    )


def _command_plan(scope: ProviderExecutionScope) -> ProviderExecutionCommandPlan:
    scenario = scope.scenario
    if scenario == ProviderApprovedExecutionScenario.PUBLIC_OHLCV:
        commands = (
            f"{NOT_EXECUTED_MARKER}\n.venv/bin/python -m invis_alpha_os.cli.main <future-approved-public-provider-preview> --scenario public_ohlcv --tickers <approved_tickers>",
        )
    elif scenario == ProviderApprovedExecutionScenario.JQUANTS_REFRESH:
        commands = (
            f"{NOT_EXECUTED_MARKER}\n.venv/bin/python -m invis_alpha_os.cli.main <future-approved-jquants-refresh> --tickers <approved_jp_tickers> --date-range <approved_range>",
        )
    elif scenario == ProviderApprovedExecutionScenario.CACHE_WRITE:
        commands = (
            f"{NOT_EXECUTED_MARKER}\n.venv/bin/python -m invis_alpha_os.cli.main <future-approved-cache-write> --input <approved_sanitized_preview> --tickers <approved_tickers>",
        )
    elif scenario == ProviderApprovedExecutionScenario.ACTUAL_IMPORT:
        commands = (
            f"{NOT_EXECUTED_MARKER}\n.venv/bin/python -m invis_alpha_os.cli.main <future-approved-actual-import> --cache-delta <approved_delta_manifest>",
        )
    else:
        commands = (
            f"{NOT_EXECUTED_MARKER}\n.venv/bin/python -m invis_alpha_os.cli.main <future-approved-manual-import> --input-path <approved_dropzone_file> --tickers <approved_tickers>",
        )
    return ProviderExecutionCommandPlan(commands=commands)


def _steps(prefix: str, items: tuple[str, ...]) -> tuple[ProviderOperatorStep, ...]:
    return tuple(
        ProviderOperatorStep(order=index, title=f"{prefix} {index}", detail=item, required_before_next=True)
        for index, item in enumerate(items, start=1)
    )


def _checklist(scope: ProviderExecutionScope, phrase: str) -> ProviderOperatorChecklist:
    preconditions = _steps(
        "precondition",
        (
            f"Confirm exact approval phrase is present: {phrase}",
            "Confirm scenario, provider candidates, tickers, and date range match the user approval.",
            "Confirm no env/secret values or raw broker/manual data will be printed.",
            "Confirm workflow, dependency, pyproject, and GitHub settings changes are out of scope.",
        ),
    )
    preflight = _steps(
        "preflight",
        (
            "Run source-only runbook generation first and inspect machine-readable summary.",
            "Confirm v39 approval package exists and all unrelated gates remain blocked.",
            "Confirm v41 harness transcript says no live/cache/import operation ran in this preparation step.",
            "Confirm cache/import target paths are enumerated before any future approved state change.",
        ),
    )
    artifacts = (
        "operator_runbook_markdown",
        "operator_runbook_json",
        "redacted_command_transcript",
        "preflight_check_results",
        "post_execution_verification_notes_if_future_execution_is_approved",
    )
    verification = _steps(
        "verification",
        (
            "Confirm expected artifacts exist and contain no secrets or raw provider/manual payloads.",
            "Confirm live/cache/import audit flags are false for source-only runbook generation.",
            "For future approved execution, compare ticker/date deltas against the approved scope only.",
            "Record PASS/FAIL and stop condition status before any next phase.",
        ),
    )
    rollback = _steps(
        "rollback",
        (
            "No rollback is needed for this runbook because no state changes are performed.",
            "For future cache writes, keep a pre-write cache inventory and restore exact touched paths on failure.",
            "For future imports, pair import manifest and postcheck output so exact ticker/date changes can be reversed.",
            "If raw/secret/private data exposure is detected, stop and preserve only redacted incident notes.",
        ),
    )
    stops = (
        "approval_phrase_missing_or_mismatched",
        "scope_exceeds_approved_tickers_or_date_range",
        "command_would_display_secret_or_raw_data",
        "command_would_modify_workflow_dependency_pyproject_or_github_settings",
        "command_would_take_trading_action",
        "reports_private_write_requested_from_codex",
        "unexpected_live_cache_import_execution_during_source_only_runbook",
    )
    return ProviderOperatorChecklist(
        preconditions=preconditions,
        preflight=preflight,
        artifacts=artifacts,
        verification=verification,
        rollback=rollback,
        stop_conditions=stops,
    )


def build_provider_approved_execution_runbook(
    *,
    report_date: str,
    scenario: ProviderApprovedExecutionScenario = ProviderApprovedExecutionScenario.PUBLIC_OHLCV,
) -> ProviderApprovedExecutionRunbook:
    action = _scenario_action(scenario)
    package = build_default_provider_approval_package(report_date=report_date)
    harness = build_provider_safe_execution_harness(
        report_date=report_date,
        mode=ProviderExecutionMode.DRY_RUN_TRANSCRIPT,
        requested_action=action,
    )
    scope = _scope_for_scenario(scenario=scenario, action=action)
    phrase = _scenario_phrase(scenario)
    required_gates = tuple(
        ProviderExecutionGate(gate)
        for gate in harness.to_dict()["result"]["required_gates"]
    )
    approval = ProviderApprovalPhraseRequirement(
        scenario=scenario,
        phrase=phrase,
        required_gates=required_gates,
        approval_status="not_approved_by_this_runbook",
    )
    audit_flags = {
        "live_http_executed": False,
        "public_ohlcv_source_live_fetch_executed": False,
        "jquants_gated_refresh_executed": False,
        "cache_write_executed": False,
        "actual_refresh_import_executed": False,
        "manual_actual_import_executed": False,
        "env_secret_displayed": False,
        "broker_manual_raw_data_handled": False,
        "reports_private_touched": False,
        "trading_action_executed": False,
    }
    decision = ProviderOperatorDecisionRecord(
        scenario=scenario,
        approved_in_this_runbook=False,
        source_only=True,
        audit_flags=audit_flags,
    )
    return ProviderApprovedExecutionRunbook(
        report_date=report_date,
        scope=scope,
        approval_requirement=approval,
        command_plan=_command_plan(scope),
        checklist=_checklist(scope, phrase),
        decision_record=decision,
        approval_package=package,
        safe_execution_harness=harness,
    )
