"""Provider approval package model for future OHLCV execution.

This module is intentionally planning-only. It never performs live HTTP,
cache writes, refreshes, imports, secret reads, or broker/manual raw data
handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from invis_alpha_os.data.ohlcv_provider_registry import (
    JQUANTS_APPROVAL_PHRASE,
    MANUAL_IMPORT_APPROVAL_PHRASE,
    PUBLIC_OHLCV_APPROVAL_PHRASE,
)

CACHE_WRITE_APPROVAL_PHRASE = "cache writeを実行してよい"
ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE = "actual refresh/importを実行してよい"


class ProviderExecutionGate(str, Enum):
    LIVE_HTTP = "LIVE_HTTP"
    PUBLIC_OHLCV_SOURCE_LIVE_FETCH = "PUBLIC_OHLCV_SOURCE_LIVE_FETCH"
    JQUANTS_GATED_REFRESH = "JQUANTS_GATED_REFRESH"
    CACHE_WRITE = "CACHE_WRITE"
    ACTUAL_REFRESH = "ACTUAL_REFRESH"
    ACTUAL_IMPORT = "ACTUAL_IMPORT"
    MANUAL_ACTUAL_IMPORT = "MANUAL_ACTUAL_IMPORT"
    BROKER_OR_MANUAL_RAW_DATA_HANDLING = "BROKER_OR_MANUAL_RAW_DATA_HANDLING"
    ENV_OR_SECRET_REQUIRED = "ENV_OR_SECRET_REQUIRED"
    WORKFLOW_DEPENDENCY_OR_PYPROJECT_CHANGE = "WORKFLOW_DEPENDENCY_OR_PYPROJECT_CHANGE"
    TRADING_ACTION = "TRADING_ACTION"


class ProviderExecutionAction(str, Enum):
    PREVIEW_APPROVAL_PACKAGE = "PREVIEW_APPROVAL_PACKAGE"
    PUBLIC_PROVIDER_LIVE_FETCH = "PUBLIC_PROVIDER_LIVE_FETCH"
    JQUANTS_REFRESH = "JQUANTS_REFRESH"
    CACHE_WRITE = "CACHE_WRITE"
    ACTUAL_REFRESH = "ACTUAL_REFRESH"
    ACTUAL_IMPORT = "ACTUAL_IMPORT"
    MANUAL_IMPORT = "MANUAL_IMPORT"


class ProviderExecutionRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked_until_explicit_approval"


@dataclass(frozen=True)
class ProviderApprovalRequirement:
    gate: ProviderExecutionGate
    action: ProviderExecutionAction
    default_status: str
    explicit_user_approval_required: bool
    safe_by_default_behavior: str
    approval_phrase: str | None
    expected_artifacts: tuple[str, ...]
    rollback_notes: str
    verification_notes: str
    risk: ProviderExecutionRisk

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate.value,
            "action": self.action.value,
            "default_status": self.default_status,
            "explicit_user_approval_required": self.explicit_user_approval_required,
            "safe_by_default_behavior": self.safe_by_default_behavior,
            "approval_phrase": self.approval_phrase,
            "expected_artifacts": list(self.expected_artifacts),
            "rollback_notes": self.rollback_notes,
            "verification_notes": self.verification_notes,
            "risk": self.risk.value,
        }


@dataclass(frozen=True)
class ProviderExecutionIntent:
    name: str
    market: str
    tickers: tuple[str, ...]
    provider_candidates: tuple[str, ...]
    required_gates: tuple[ProviderExecutionGate, ...]
    non_goals: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "market": self.market,
            "tickers": list(self.tickers),
            "provider_candidates": list(self.provider_candidates),
            "required_gates": [g.value for g in self.required_gates],
            "non_goals": list(self.non_goals),
        }


@dataclass(frozen=True)
class ProviderExecutionPlanStep:
    order: int
    title: str
    action: ProviderExecutionAction
    required_gates: tuple[ProviderExecutionGate, ...]
    preview_only: bool
    expected_outputs: tuple[str, ...]
    stop_conditions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "order": self.order,
            "title": self.title,
            "action": self.action.value,
            "required_gates": [g.value for g in self.required_gates],
            "preview_only": self.preview_only,
            "expected_outputs": list(self.expected_outputs),
            "stop_conditions": list(self.stop_conditions),
        }


@dataclass(frozen=True)
class ProviderExecutionRollbackPlan:
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"notes": list(self.notes)}


@dataclass(frozen=True)
class ProviderExecutionVerification:
    checks: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"checks": list(self.checks)}


@dataclass(frozen=True)
class ProviderExecutionPlan:
    intent: ProviderExecutionIntent
    steps: tuple[ProviderExecutionPlanStep, ...]
    rollback_plan: ProviderExecutionRollbackPlan
    verification: ProviderExecutionVerification
    dry_run_only: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.to_dict(),
            "steps": [step.to_dict() for step in self.steps],
            "rollback_plan": self.rollback_plan.to_dict(),
            "verification": self.verification.to_dict(),
            "dry_run_only": self.dry_run_only,
        }


@dataclass(frozen=True)
class ProviderApprovalDecision:
    approved: bool
    approval_phrase: str | None
    decided_by: str
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "approval_phrase": self.approval_phrase,
            "decided_by": self.decided_by,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ProviderApprovalPackage:
    report_date: str
    requirements: tuple[ProviderApprovalRequirement, ...]
    execution_plan: ProviderExecutionPlan
    decisions: tuple[ProviderApprovalDecision, ...]
    stop_conditions: tuple[str, ...]
    non_goals: tuple[str, ...]
    safety_summary: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "requirements": [req.to_dict() for req in self.requirements],
            "execution_plan": self.execution_plan.to_dict(),
            "decisions": [decision.to_dict() for decision in self.decisions],
            "stop_conditions": list(self.stop_conditions),
            "non_goals": list(self.non_goals),
            "safety_summary": dict(self.safety_summary),
        }


def _requirement(
    *,
    gate: ProviderExecutionGate,
    action: ProviderExecutionAction,
    approval_phrase: str | None,
    expected_artifacts: tuple[str, ...],
    risk: ProviderExecutionRisk,
) -> ProviderApprovalRequirement:
    return ProviderApprovalRequirement(
        gate=gate,
        action=action,
        default_status="blocked_until_explicit_approval",
        explicit_user_approval_required=True,
        safe_by_default_behavior="preview_only_no_execution",
        approval_phrase=approval_phrase,
        expected_artifacts=expected_artifacts,
        rollback_notes="No rollback should be needed before approval because no state-changing operation is executed.",
        verification_notes="Verify command output and generated package only; do not infer execution success.",
        risk=risk,
    )


def default_provider_approval_requirements() -> tuple[ProviderApprovalRequirement, ...]:
    return (
        _requirement(
            gate=ProviderExecutionGate.LIVE_HTTP,
            action=ProviderExecutionAction.PUBLIC_PROVIDER_LIVE_FETCH,
            approval_phrase=PUBLIC_OHLCV_APPROVAL_PHRASE,
            expected_artifacts=("provider_response_shape_digest", "no_raw_response_persisted"),
            risk=ProviderExecutionRisk.HIGH,
        ),
        _requirement(
            gate=ProviderExecutionGate.PUBLIC_OHLCV_SOURCE_LIVE_FETCH,
            action=ProviderExecutionAction.PUBLIC_PROVIDER_LIVE_FETCH,
            approval_phrase=PUBLIC_OHLCV_APPROVAL_PHRASE,
            expected_artifacts=("provider_fetch_log_redacted", "sanitized_ohlcv_preview"),
            risk=ProviderExecutionRisk.HIGH,
        ),
        _requirement(
            gate=ProviderExecutionGate.JQUANTS_GATED_REFRESH,
            action=ProviderExecutionAction.JQUANTS_REFRESH,
            approval_phrase=JQUANTS_APPROVAL_PHRASE,
            expected_artifacts=("jquants_refresh_preflight", "contract_cap_status"),
            risk=ProviderExecutionRisk.HIGH,
        ),
        _requirement(
            gate=ProviderExecutionGate.CACHE_WRITE,
            action=ProviderExecutionAction.CACHE_WRITE,
            approval_phrase=CACHE_WRITE_APPROVAL_PHRASE,
            expected_artifacts=("cache_write_plan", "post_write_cache_preview"),
            risk=ProviderExecutionRisk.HIGH,
        ),
        _requirement(
            gate=ProviderExecutionGate.ACTUAL_REFRESH,
            action=ProviderExecutionAction.ACTUAL_REFRESH,
            approval_phrase=ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
            expected_artifacts=("refresh_execution_log", "post_refresh_readiness"),
            risk=ProviderExecutionRisk.HIGH,
        ),
        _requirement(
            gate=ProviderExecutionGate.ACTUAL_IMPORT,
            action=ProviderExecutionAction.ACTUAL_IMPORT,
            approval_phrase=ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
            expected_artifacts=("import_plan", "post_import_readiness"),
            risk=ProviderExecutionRisk.HIGH,
        ),
        _requirement(
            gate=ProviderExecutionGate.MANUAL_ACTUAL_IMPORT,
            action=ProviderExecutionAction.MANUAL_IMPORT,
            approval_phrase=MANUAL_IMPORT_APPROVAL_PHRASE,
            expected_artifacts=("manual_import_plan", "post_manual_import_readiness"),
            risk=ProviderExecutionRisk.HIGH,
        ),
        _requirement(
            gate=ProviderExecutionGate.BROKER_OR_MANUAL_RAW_DATA_HANDLING,
            action=ProviderExecutionAction.MANUAL_IMPORT,
            approval_phrase=None,
            expected_artifacts=("redacted_schema_summary",),
            risk=ProviderExecutionRisk.HIGH,
        ),
        _requirement(
            gate=ProviderExecutionGate.ENV_OR_SECRET_REQUIRED,
            action=ProviderExecutionAction.PREVIEW_APPROVAL_PACKAGE,
            approval_phrase=None,
            expected_artifacts=("secret_requirement_status_without_values",),
            risk=ProviderExecutionRisk.HIGH,
        ),
        _requirement(
            gate=ProviderExecutionGate.WORKFLOW_DEPENDENCY_OR_PYPROJECT_CHANGE,
            action=ProviderExecutionAction.PREVIEW_APPROVAL_PACKAGE,
            approval_phrase=None,
            expected_artifacts=("separate_change_request",),
            risk=ProviderExecutionRisk.HIGH,
        ),
        _requirement(
            gate=ProviderExecutionGate.TRADING_ACTION,
            action=ProviderExecutionAction.PREVIEW_APPROVAL_PACKAGE,
            approval_phrase=None,
            expected_artifacts=("none_trading_is_out_of_scope",),
            risk=ProviderExecutionRisk.BLOCKED,
        ),
    )


def build_default_provider_execution_plan(*, report_date: str) -> ProviderExecutionPlan:
    intent = ProviderExecutionIntent(
        name="future_gated_ohlcv_provider_execution",
        market="JP/US/ETF",
        tickers=("285A", "5802", "5803", "6645", "5801", "NVDA", "MSFT", "AVGO", "TSLA", "MSTR", "COIN"),
        provider_candidates=("jquants", "stooq_manual", "stooq_live_gated", "alpha_vantage_gated", "tiingo_gated", "polygon_gated", "eodhd_gated"),
        required_gates=tuple(req.gate for req in default_provider_approval_requirements()),
        non_goals=(
            "no_live_http_in_v39",
            "no_cache_write_in_v39",
            "no_actual_refresh_or_import_in_v39",
            "no_env_secret_value_display",
            "no_broker_or_manual_raw_data_handling",
        ),
    )
    _ = report_date
    steps = (
        ProviderExecutionPlanStep(
            order=1,
            title="Generate approval package preview",
            action=ProviderExecutionAction.PREVIEW_APPROVAL_PACKAGE,
            required_gates=(),
            preview_only=True,
            expected_outputs=("ohlcv_provider_approval_package.md", "ohlcv_provider_approval_package.json"),
            stop_conditions=("unexpected_stateful_option_present", "raw_or_secret_data_detected"),
        ),
        ProviderExecutionPlanStep(
            order=2,
            title="Human review of explicit gates",
            action=ProviderExecutionAction.PREVIEW_APPROVAL_PACKAGE,
            required_gates=tuple(req.gate for req in default_provider_approval_requirements()),
            preview_only=True,
            expected_outputs=("approval_phrase_selection", "scope_boundaries"),
            stop_conditions=("approval_phrase_missing", "scope_includes_forbidden_non_goal"),
        ),
        ProviderExecutionPlanStep(
            order=3,
            title="Future gated execution in separate task",
            action=ProviderExecutionAction.ACTUAL_REFRESH,
            required_gates=(
                ProviderExecutionGate.LIVE_HTTP,
                ProviderExecutionGate.CACHE_WRITE,
                ProviderExecutionGate.ACTUAL_REFRESH,
            ),
            preview_only=True,
            expected_outputs=("separate_execution_instruction",),
            stop_conditions=("any_gate_unapproved", "ci_or_source_change_required"),
        ),
    )
    rollback = ProviderExecutionRollbackPlan(
        notes=(
            "Before explicit approval, no rollback is required because v39 does not mutate cache or provider state.",
            "For future cache writes, snapshot target cache metadata before writing and restore from the pre-write copy if verification fails.",
            "For future imports, keep import plan and postcheck artifacts paired so the exact changed ticker/date range can be reverted manually.",
        )
    )
    verification = ProviderExecutionVerification(
        checks=(
            "Approval package generated with dry_run_only=true.",
            "All dangerous gates remain blocked_until_explicit_approval.",
            "CLI exposes no live/cache/import execution option.",
            "Focused tests pass without network or cache writes.",
            "Generated package contains rollback plan, verification plan, stop conditions, and approval phrases.",
        )
    )
    return ProviderExecutionPlan(
        intent=intent,
        steps=steps,
        rollback_plan=rollback,
        verification=verification,
        dry_run_only=True,
    )


def build_default_provider_approval_package(*, report_date: str) -> ProviderApprovalPackage:
    requirements = default_provider_approval_requirements()
    plan = build_default_provider_execution_plan(report_date=report_date)
    decisions = tuple(
        ProviderApprovalDecision(
            approved=False,
            approval_phrase=req.approval_phrase,
            decided_by="not_approved_in_v39",
            notes="This package records the approval boundary only; execution requires a separate explicit approval.",
        )
        for req in requirements
    )
    return ProviderApprovalPackage(
        report_date=report_date,
        requirements=requirements,
        execution_plan=plan,
        decisions=decisions,
        stop_conditions=(
            "Any live HTTP or provider fetch would be required.",
            "Any cache write or actual import would be required.",
            "Any env/secret value would need to be displayed.",
            "Any broker/manual raw file content would need to be printed or committed.",
            "Any workflow, dependency, pyproject, GitHub setting, or trading action is requested.",
        ),
        non_goals=plan.intent.non_goals,
        safety_summary={
            "live_http_executed": False,
            "public_ohlcv_source_live_fetch_executed": False,
            "jquants_gated_refresh_executed": False,
            "cache_write_executed": False,
            "actual_refresh_import_executed": False,
            "manual_actual_import_executed": False,
            "env_secret_displayed": False,
            "broker_manual_raw_data_handled": False,
            "workflow_dependency_pyproject_changed": False,
            "reports_private_touched": False,
            "trading_action_executed": False,
        },
    )
