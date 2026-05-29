"""Source-only safe execution harness for OHLCV provider operations.

The harness consumes the v39 approval model and emits dry-run transcripts,
preflight findings, rollback checklists, and verification checklists. It does
not execute providers, write caches, import data, read secrets, or inspect raw
broker/manual files.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from invis_alpha_os.data.ohlcv_provider_approval import (
    ProviderApprovalPackage,
    ProviderApprovalRequirement,
    ProviderExecutionAction,
    ProviderExecutionGate,
    build_default_provider_approval_package,
)


class ProviderExecutionMode(str, Enum):
    PREVIEW_ONLY = "PREVIEW_ONLY"
    DRY_RUN_TRANSCRIPT = "DRY_RUN_TRANSCRIPT"
    PREFLIGHT_ONLY = "PREFLIGHT_ONLY"
    APPROVED_EXECUTION_STUB = "APPROVED_EXECUTION_STUB"


class ProviderExecutionVerdict(str, Enum):
    PREVIEW_ONLY_SAFE = "preview_only_safe"
    BLOCKED_MISSING_APPROVAL = "blocked_missing_approval"
    BLOCKED_HARD_GATE = "blocked_hard_gate"
    READY_FOR_EXPLICIT_USER_APPROVAL = "ready_for_explicit_user_approval"


@dataclass(frozen=True)
class ProviderApprovedAction:
    action: ProviderExecutionAction
    approved_gates: tuple[ProviderExecutionGate, ...]
    approval_phrases: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "approved_gates": [gate.value for gate in self.approved_gates],
            "approval_phrases": list(self.approval_phrases),
        }


@dataclass(frozen=True)
class ProviderExecutionPreflight:
    name: str
    passed: bool
    status: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "status": self.status,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class ProviderCacheWritePreflight:
    would_write_cache: bool
    status: str
    risk: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "would_write_cache": self.would_write_cache,
            "status": self.status,
            "risk": self.risk,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class ProviderActualImportPreflight:
    would_import: bool
    status: str
    risk: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "would_import": self.would_import,
            "status": self.status,
            "risk": self.risk,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class ProviderExecutionArtifactPlan:
    expected_outputs: tuple[str, ...]
    forbidden_outputs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "expected_outputs": list(self.expected_outputs),
            "forbidden_outputs": list(self.forbidden_outputs),
        }


@dataclass(frozen=True)
class ProviderRollbackChecklist:
    items: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"items": list(self.items)}


@dataclass(frozen=True)
class ProviderVerificationChecklist:
    items: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"items": list(self.items)}


@dataclass(frozen=True)
class ProviderExecutionStopCondition:
    label: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "description": self.description}


@dataclass(frozen=True)
class ProviderExecutionTranscriptEvent:
    section: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"section": self.section, "message": self.message}


@dataclass(frozen=True)
class ProviderExecutionTranscript:
    requested_action: str
    events: tuple[ProviderExecutionTranscriptEvent, ...]
    verdict: ProviderExecutionVerdict

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_action": self.requested_action,
            "events": [event.to_dict() for event in self.events],
            "verdict": self.verdict.value,
        }


@dataclass(frozen=True)
class ProviderExecutionAuditSummary:
    live_http_executed: bool
    cache_write_executed: bool
    actual_refresh_import_executed: bool
    env_secret_displayed: bool
    raw_data_handled: bool
    trading_action_executed: bool
    reports_private_touched: bool

    def to_dict(self) -> dict[str, bool]:
        return {
            "live_http_executed": self.live_http_executed,
            "cache_write_executed": self.cache_write_executed,
            "actual_refresh_import_executed": self.actual_refresh_import_executed,
            "env_secret_displayed": self.env_secret_displayed,
            "raw_data_handled": self.raw_data_handled,
            "trading_action_executed": self.trading_action_executed,
            "reports_private_touched": self.reports_private_touched,
        }


@dataclass(frozen=True)
class ProviderExecutionDryRunResult:
    mode: ProviderExecutionMode
    requested_action: ProviderExecutionAction
    required_gates: tuple[ProviderExecutionGate, ...]
    approved_action: ProviderApprovedAction
    preflight: tuple[ProviderExecutionPreflight, ...]
    cache_write_preflight: ProviderCacheWritePreflight
    actual_import_preflight: ProviderActualImportPreflight
    artifact_plan: ProviderExecutionArtifactPlan
    rollback_checklist: ProviderRollbackChecklist
    verification_checklist: ProviderVerificationChecklist
    stop_conditions: tuple[ProviderExecutionStopCondition, ...]
    transcript: ProviderExecutionTranscript
    audit_summary: ProviderExecutionAuditSummary

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "requested_action": self.requested_action.value,
            "required_gates": [gate.value for gate in self.required_gates],
            "approved_action": self.approved_action.to_dict(),
            "preflight": [item.to_dict() for item in self.preflight],
            "cache_write_preflight": self.cache_write_preflight.to_dict(),
            "actual_import_preflight": self.actual_import_preflight.to_dict(),
            "artifact_plan": self.artifact_plan.to_dict(),
            "rollback_checklist": self.rollback_checklist.to_dict(),
            "verification_checklist": self.verification_checklist.to_dict(),
            "stop_conditions": [item.to_dict() for item in self.stop_conditions],
            "transcript": self.transcript.to_dict(),
            "audit_summary": self.audit_summary.to_dict(),
        }


@dataclass(frozen=True)
class ProviderExecutionHarness:
    report_date: str
    approval_package: ProviderApprovalPackage
    result: ProviderExecutionDryRunResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "approval_package": self.approval_package.to_dict(),
            "result": self.result.to_dict(),
        }


def _requirements_for_action(
    requirements: tuple[ProviderApprovalRequirement, ...],
    action: ProviderExecutionAction,
) -> tuple[ProviderApprovalRequirement, ...]:
    if action == ProviderExecutionAction.PREVIEW_APPROVAL_PACKAGE:
        return ()
    if action == ProviderExecutionAction.PUBLIC_PROVIDER_LIVE_FETCH:
        wanted = {
            ProviderExecutionGate.LIVE_HTTP,
            ProviderExecutionGate.PUBLIC_OHLCV_SOURCE_LIVE_FETCH,
        }
    elif action == ProviderExecutionAction.JQUANTS_REFRESH:
        wanted = {
            ProviderExecutionGate.LIVE_HTTP,
            ProviderExecutionGate.JQUANTS_GATED_REFRESH,
        }
    elif action == ProviderExecutionAction.CACHE_WRITE:
        wanted = {ProviderExecutionGate.CACHE_WRITE}
    elif action == ProviderExecutionAction.ACTUAL_REFRESH:
        wanted = {
            ProviderExecutionGate.LIVE_HTTP,
            ProviderExecutionGate.CACHE_WRITE,
            ProviderExecutionGate.ACTUAL_REFRESH,
        }
    elif action == ProviderExecutionAction.ACTUAL_IMPORT:
        wanted = {
            ProviderExecutionGate.CACHE_WRITE,
            ProviderExecutionGate.ACTUAL_IMPORT,
        }
    elif action == ProviderExecutionAction.MANUAL_IMPORT:
        wanted = {
            ProviderExecutionGate.MANUAL_ACTUAL_IMPORT,
            ProviderExecutionGate.BROKER_OR_MANUAL_RAW_DATA_HANDLING,
        }
    else:
        wanted = set()
    return tuple(req for req in requirements if req.gate in wanted)


def _approved_action(
    *,
    requirements: tuple[ProviderApprovalRequirement, ...],
    action: ProviderExecutionAction,
    approved_phrases: tuple[str, ...],
) -> ProviderApprovedAction:
    phrase_set = {phrase.strip() for phrase in approved_phrases if phrase.strip()}
    approved_gates: list[ProviderExecutionGate] = []
    for req in _requirements_for_action(requirements, action):
        if req.approval_phrase and req.approval_phrase in phrase_set:
            approved_gates.append(req.gate)
    return ProviderApprovedAction(
        action=action,
        approved_gates=tuple(approved_gates),
        approval_phrases=tuple(sorted(phrase_set)),
    )


def _verdict(
    *,
    mode: ProviderExecutionMode,
    action: ProviderExecutionAction,
    required_gates: tuple[ProviderExecutionGate, ...],
    approved: ProviderApprovedAction,
) -> ProviderExecutionVerdict:
    if action == ProviderExecutionAction.PREVIEW_APPROVAL_PACKAGE:
        return ProviderExecutionVerdict.PREVIEW_ONLY_SAFE
    hard_gates = {
        ProviderExecutionGate.ENV_OR_SECRET_REQUIRED,
        ProviderExecutionGate.WORKFLOW_DEPENDENCY_OR_PYPROJECT_CHANGE,
        ProviderExecutionGate.TRADING_ACTION,
    }
    if any(gate in hard_gates for gate in required_gates):
        return ProviderExecutionVerdict.BLOCKED_HARD_GATE
    missing = [gate for gate in required_gates if gate not in set(approved.approved_gates)]
    if missing:
        return ProviderExecutionVerdict.BLOCKED_MISSING_APPROVAL
    if mode == ProviderExecutionMode.APPROVED_EXECUTION_STUB:
        return ProviderExecutionVerdict.READY_FOR_EXPLICIT_USER_APPROVAL
    return ProviderExecutionVerdict.PREVIEW_ONLY_SAFE


def _preflights(
    *,
    required_gates: tuple[ProviderExecutionGate, ...],
    approved: ProviderApprovedAction,
    verdict: ProviderExecutionVerdict,
) -> tuple[ProviderExecutionPreflight, ...]:
    approved_set = set(approved.approved_gates)
    return (
        ProviderExecutionPreflight(
            name="provider_capability_readiness",
            passed=True,
            status="registry_specs_available",
            notes=("Uses v36/v39 source models only.", "No provider endpoint is contacted."),
        ),
        ProviderExecutionPreflight(
            name="approval_phrase_presence",
            passed=all(gate in approved_set for gate in required_gates),
            status=verdict.value,
            notes=tuple(
                f"{gate.value}: {'approved' if gate in approved_set else 'missing'}"
                for gate in required_gates
            )
            or ("no gated action requested",),
        ),
        ProviderExecutionPreflight(
            name="expected_output_paths",
            passed=True,
            status="report_paths_only",
            notes=("latest/ohlcv_provider_safe_execution_harness.md", "latest/ohlcv_provider_safe_execution_harness.json"),
        ),
        ProviderExecutionPreflight(
            name="stop_conditions",
            passed=verdict != ProviderExecutionVerdict.BLOCKED_HARD_GATE,
            status=verdict.value,
            notes=("Hard gates remain non-executable in source-only harness.",),
        ),
    )


def build_provider_safe_execution_harness(
    *,
    report_date: str,
    mode: ProviderExecutionMode = ProviderExecutionMode.DRY_RUN_TRANSCRIPT,
    requested_action: ProviderExecutionAction = ProviderExecutionAction.ACTUAL_REFRESH,
    approved_phrases: tuple[str, ...] = (),
) -> ProviderExecutionHarness:
    package = build_default_provider_approval_package(report_date=report_date)
    requirements = package.requirements
    action_requirements = _requirements_for_action(requirements, requested_action)
    required_gates = tuple(req.gate for req in action_requirements)
    approved = _approved_action(
        requirements=requirements,
        action=requested_action,
        approved_phrases=approved_phrases,
    )
    verdict = _verdict(
        mode=mode,
        action=requested_action,
        required_gates=required_gates,
        approved=approved,
    )
    preflights = _preflights(required_gates=required_gates, approved=approved, verdict=verdict)
    cache_preflight = ProviderCacheWritePreflight(
        would_write_cache=False,
        status="transcript_only",
        risk="high_if_future_enabled",
        notes=(
            "Cache write is never performed by v41.",
            "Future cache write requires explicit cache write approval and a separate execution task.",
        ),
    )
    import_preflight = ProviderActualImportPreflight(
        would_import=False,
        status="transcript_only",
        risk="high_if_future_enabled",
        notes=(
            "Actual import is never performed by v41.",
            "Future import requires explicit actual import approval and separate postcheck verification.",
        ),
    )
    artifact_plan = ProviderExecutionArtifactPlan(
        expected_outputs=(
            "latest/ohlcv_provider_safe_execution_harness.md",
            "latest/ohlcv_provider_safe_execution_harness.json",
            "weekly/2026/{report_date}/ohlcv_provider_safe_execution_harness.md",
            "weekly/2026/{report_date}/ohlcv_provider_safe_execution_harness.json",
        ),
        forbidden_outputs=(
            "cache files",
            "raw provider responses",
            "broker/manual raw files",
            "env or secret values",
            "reports-private writes from Codex",
        ),
    )
    rollback = ProviderRollbackChecklist(
        items=(
            "No rollback is needed for v41 because no state-changing operation is executed.",
            "Before future cache writes, capture cache inventory and target path list.",
            "After future writes/imports, verify exact ticker/date deltas and keep a revert note.",
            "Stop rather than rollback if raw or secret data would be exposed.",
        )
    )
    verification = ProviderVerificationChecklist(
        items=(
            "Confirm transcript verdict before any future execution.",
            "Confirm all required gates have explicit approval phrases.",
            "Confirm CLI exposes no live/cache/import execution options.",
            "Confirm generated artifacts are Markdown/JSON previews only.",
            "Confirm focused tests pass without network or cache writes.",
        )
    )
    stops = (
        ProviderExecutionStopCondition("missing_approval", "Required gate approval phrase is absent."),
        ProviderExecutionStopCondition("hard_gate", "Workflow/dependency/pyproject/trading/secret/raw-data boundary would be crossed."),
        ProviderExecutionStopCondition("stateful_execution", "Any live HTTP, cache write, refresh, or import would be executed."),
        ProviderExecutionStopCondition("private_output", "reports-private or raw/manual/broker artifacts would be touched by Codex."),
    )
    events = (
        ProviderExecutionTranscriptEvent("Requested Action", requested_action.value),
        ProviderExecutionTranscriptEvent("Required Gates", ", ".join(g.value for g in required_gates) or "(none)"),
        ProviderExecutionTranscriptEvent("Approval Status", ", ".join(g.value for g in approved.approved_gates) or "none approved"),
        ProviderExecutionTranscriptEvent("Preconditions", "Source models available; no provider/network/cache/import access attempted."),
        ProviderExecutionTranscriptEvent("Would Execute", "No execution in v41; transcript-only harness."),
        ProviderExecutionTranscriptEvent("Would Write", "Only preview Markdown/JSON report paths if caller asks writer to persist them."),
        ProviderExecutionTranscriptEvent("Would Verify", "; ".join(verification.items)),
        ProviderExecutionTranscriptEvent("Rollback Checklist", "; ".join(rollback.items)),
        ProviderExecutionTranscriptEvent("Stop Conditions", "; ".join(item.description for item in stops)),
        ProviderExecutionTranscriptEvent("Final Safety Verdict", verdict.value),
    )
    transcript = ProviderExecutionTranscript(
        requested_action=requested_action.value,
        events=events,
        verdict=verdict,
    )
    audit = ProviderExecutionAuditSummary(
        live_http_executed=False,
        cache_write_executed=False,
        actual_refresh_import_executed=False,
        env_secret_displayed=False,
        raw_data_handled=False,
        trading_action_executed=False,
        reports_private_touched=False,
    )
    result = ProviderExecutionDryRunResult(
        mode=mode,
        requested_action=requested_action,
        required_gates=required_gates,
        approved_action=approved,
        preflight=preflights,
        cache_write_preflight=cache_preflight,
        actual_import_preflight=import_preflight,
        artifact_plan=artifact_plan,
        rollback_checklist=rollback,
        verification_checklist=verification,
        stop_conditions=stops,
        transcript=transcript,
        audit_summary=audit,
    )
    return ProviderExecutionHarness(report_date=report_date, approval_package=package, result=result)
