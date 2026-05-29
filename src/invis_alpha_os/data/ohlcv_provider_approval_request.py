"""Source-only execution approval request templates for OHLCV provider operations.

This module builds the final human-facing pre-approval packet from the v39
approval package, v41 safe execution harness, and v43 operator runbook. It does
not execute live HTTP, cache writes, refreshes, imports, broker login, secret
reads, or raw manual data handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invis_alpha_os.data.ohlcv_provider_runbook import (
    NOT_EXECUTED_MARKER,
    ProviderApprovedExecutionRunbook,
    ProviderApprovedExecutionScenario,
    build_provider_approved_execution_runbook,
    scenario_from_cli,
)

DRAFT_HANDOFF_MARKER = "DRAFT ONLY - DO NOT RUN UNTIL HUMAN APPROVAL PHRASE IS PROVIDED"


@dataclass(frozen=True)
class ProviderExecutionApprovalScope:
    scenario: ProviderApprovedExecutionScenario
    provider_candidates: tuple[str, ...]
    tickers: tuple[str, ...]
    date_range: str
    requested_operation: str
    explicitly_not_approved: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario.value,
            "provider_candidates": list(self.provider_candidates),
            "tickers": list(self.tickers),
            "date_range": self.date_range,
            "requested_operation": self.requested_operation,
            "explicitly_not_approved": list(self.explicitly_not_approved),
        }


@dataclass(frozen=True)
class ProviderExecutionApprovalDecisionPrompt:
    primary_approval_phrase: str
    final_decision_required: str
    acceptance_criteria: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_approval_phrase": self.primary_approval_phrase,
            "final_decision_required": self.final_decision_required,
            "acceptance_criteria": list(self.acceptance_criteria),
        }


@dataclass(frozen=True)
class ProviderExecutionApprovalChecklist:
    preconditions: tuple[str, ...]
    redaction_checks: tuple[str, ...]
    expected_artifacts: tuple[str, ...]
    rollback_plan: tuple[str, ...]
    verification_plan: tuple[str, ...]
    stop_conditions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "preconditions": list(self.preconditions),
            "redaction_checks": list(self.redaction_checks),
            "expected_artifacts": list(self.expected_artifacts),
            "rollback_plan": list(self.rollback_plan),
            "verification_plan": list(self.verification_plan),
            "stop_conditions": list(self.stop_conditions),
        }


@dataclass(frozen=True)
class ProviderExecutionApprovalEvidence:
    approval_package: dict[str, Any]
    safe_execution_harness: dict[str, Any]
    operator_runbook: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_package": dict(self.approval_package),
            "safe_execution_harness": dict(self.safe_execution_harness),
            "operator_runbook": dict(self.operator_runbook),
        }


@dataclass(frozen=True)
class ProviderExecutionApprovalRiskSummary:
    source_only: bool
    commands_executed: bool
    audit_flags: dict[str, bool]
    residual_risks: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_only": self.source_only,
            "commands_executed": self.commands_executed,
            "audit_flags": dict(self.audit_flags),
            "residual_risks": list(self.residual_risks),
        }


@dataclass(frozen=True)
class ProviderExecutionApprovalRequest:
    report_date: str
    scope: ProviderExecutionApprovalScope
    decision_prompt: ProviderExecutionApprovalDecisionPrompt
    checklist: ProviderExecutionApprovalChecklist
    evidence: ProviderExecutionApprovalEvidence
    risk_summary: ProviderExecutionApprovalRiskSummary
    commands_planned_but_not_executed: tuple[str, ...]
    cursor_execution_handoff_draft: str
    source_runbook: ProviderApprovedExecutionRunbook

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "scope": self.scope.to_dict(),
            "decision_prompt": self.decision_prompt.to_dict(),
            "checklist": self.checklist.to_dict(),
            "evidence": self.evidence.to_dict(),
            "risk_summary": self.risk_summary.to_dict(),
            "commands_planned_but_not_executed": list(self.commands_planned_but_not_executed),
            "cursor_execution_handoff_draft": self.cursor_execution_handoff_draft,
            "source_runbook": self.source_runbook.to_dict(),
        }


@dataclass(frozen=True)
class ProviderExecutionApprovalRequestBundle:
    report_date: str
    request: ProviderExecutionApprovalRequest
    supported_scenarios: tuple[ProviderApprovedExecutionScenario, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "request": self.request.to_dict(),
            "supported_scenarios": [scenario.value for scenario in self.supported_scenarios],
        }


def approval_request_scenario_from_cli(value: str) -> ProviderApprovedExecutionScenario:
    return scenario_from_cli(value)


def _request_scope(runbook: ProviderApprovedExecutionRunbook) -> ProviderExecutionApprovalScope:
    scope = runbook.scope
    return ProviderExecutionApprovalScope(
        scenario=scope.scenario,
        provider_candidates=scope.provider_candidates,
        tickers=scope.tickers,
        date_range=scope.date_range,
        requested_operation=scope.requested_operation,
        explicitly_not_approved=scope.remains_unapproved,
    )


def _evidence(runbook: ProviderApprovedExecutionRunbook) -> ProviderExecutionApprovalEvidence:
    runbook_dict = runbook.to_dict()
    package = runbook_dict["approval_package"]
    harness = runbook_dict["safe_execution_harness"]["result"]
    operator = {
        "scenario": runbook_dict["scope"]["scenario"],
        "source_only": runbook_dict["decision_record"]["source_only"],
        "commands_marked_not_executed": all(
            command.startswith(NOT_EXECUTED_MARKER)
            for command in runbook_dict["command_plan"]["commands"]
        ),
        "stop_conditions": runbook_dict["checklist"]["stop_conditions"],
    }
    return ProviderExecutionApprovalEvidence(
        approval_package={
            "exists": True,
            "dry_run_only": package["execution_plan"]["dry_run_only"],
            "dangerous_gates_default_status": "blocked_until_explicit_approval",
            "non_goals": package["non_goals"],
        },
        safe_execution_harness={
            "exists": True,
            "mode": harness["mode"],
            "verdict": harness["transcript"]["verdict"],
            "audit_summary": harness["audit_summary"],
        },
        operator_runbook={
            "exists": True,
            **operator,
        },
    )


def _checklist(runbook: ProviderApprovedExecutionRunbook) -> ProviderExecutionApprovalChecklist:
    rb = runbook.to_dict()
    checklist = rb["checklist"]
    return ProviderExecutionApprovalChecklist(
        preconditions=tuple(step["detail"] for step in checklist["preconditions"]),
        redaction_checks=(
            "Do not display env, token, credential, API key, account, broker, or raw manual data values.",
            "Do not persist raw provider responses or manual raw file contents in repo artifacts.",
            "Do not touch reports-private from Codex.",
            "Only redacted Markdown/JSON planning artifacts may be generated by this source-only request.",
        ),
        expected_artifacts=tuple(checklist["artifacts"]),
        rollback_plan=tuple(step["detail"] for step in checklist["rollback"]),
        verification_plan=tuple(step["detail"] for step in checklist["verification"]),
        stop_conditions=tuple(checklist["stop_conditions"]),
    )


def _decision_prompt(runbook: ProviderApprovedExecutionRunbook) -> ProviderExecutionApprovalDecisionPrompt:
    phrase = runbook.approval_requirement.phrase
    return ProviderExecutionApprovalDecisionPrompt(
        primary_approval_phrase=phrase,
        final_decision_required=f"Approve exactly this phrase to continue in a separate execution task: {phrase}",
        acceptance_criteria=(
            "Scenario matches the requested provider operation.",
            "Ticker and date range scope are acceptable.",
            "Explicitly not approved actions remain excluded.",
            "Rollback and verification plans are acceptable.",
        ),
    )


def _risk_summary(runbook: ProviderApprovedExecutionRunbook) -> ProviderExecutionApprovalRiskSummary:
    audit_flags = dict(runbook.decision_record.audit_flags)
    return ProviderExecutionApprovalRiskSummary(
        source_only=True,
        commands_executed=False,
        audit_flags=audit_flags,
        residual_risks=(
            "A future operator may misread planned commands as runnable without the approval phrase.",
            "Approval scope may be too broad unless ticker/date range is repeated in the execution task.",
            "Cache/import rollback is manual unless exact touched paths and deltas are captured.",
        ),
    )


def _handoff_draft(runbook: ProviderApprovedExecutionRunbook) -> str:
    scope = runbook.scope
    phrase = runbook.approval_requirement.phrase
    commands = "\n\n".join(runbook.command_plan.commands)
    return "\n".join(
        [
            DRAFT_HANDOFF_MARKER,
            "",
            f"scenario: {scope.scenario.value}",
            f"required_approval_phrase: {phrase}",
            f"tickers: {', '.join(scope.tickers)}",
            f"date_range: {scope.date_range}",
            "",
            "planned_commands:",
            commands,
            "",
            "stop if approval phrase, ticker scope, date range, redaction checks, or rollback plan do not match.",
        ]
    )


def build_provider_execution_approval_request(
    *,
    report_date: str,
    scenario: ProviderApprovedExecutionScenario = ProviderApprovedExecutionScenario.PUBLIC_OHLCV,
) -> ProviderExecutionApprovalRequestBundle:
    runbook = build_provider_approved_execution_runbook(report_date=report_date, scenario=scenario)
    request = ProviderExecutionApprovalRequest(
        report_date=report_date,
        scope=_request_scope(runbook),
        decision_prompt=_decision_prompt(runbook),
        checklist=_checklist(runbook),
        evidence=_evidence(runbook),
        risk_summary=_risk_summary(runbook),
        commands_planned_but_not_executed=runbook.command_plan.commands,
        cursor_execution_handoff_draft=_handoff_draft(runbook),
        source_runbook=runbook,
    )
    return ProviderExecutionApprovalRequestBundle(
        report_date=report_date,
        request=request,
        supported_scenarios=tuple(ProviderApprovedExecutionScenario),
    )
