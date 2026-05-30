"""Source-only SIGNOFF-16 operator signoff sheet.

This module turns the v67 cache-write gate into a human-fillable checklist. It
does not call providers, write cache, import data, persist raw OHLCV, print
secrets, touch reports-private, or perform trading actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invis_alpha_os.data.cache_write_readiness_gate import (
    FUTURE_CACHE_WRITE_OPERATION,
    build_cache_write_readiness_gate,
)
from invis_alpha_os.data.ohlcv_provider_approval import (
    ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
    CACHE_WRITE_APPROVAL_PHRASE,
)


V68_OPERATOR_SIGNOFF_STATUS = "human_review_required"
V68_OVERALL_READINESS = "not_ready_pending_SIGNOFF_16_operator_completion"
V68_BASELINE_MAIN_COMMIT = "bd887f315da499c4d6444c8bda7834b2c35971df"


@dataclass(frozen=True)
class OperatorReviewMetadata:
    signoff_id: str
    report_date: str
    operator_name_or_handle: str
    review_timestamp: str
    review_scope: str
    milestone_version: str
    source_main_commit: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "signoff_id": self.signoff_id,
            "report_date": self.report_date,
            "operator_name_or_handle": self.operator_name_or_handle,
            "review_timestamp": self.review_timestamp,
            "review_scope": self.review_scope,
            "milestone_version": self.milestone_version,
            "source_main_commit": self.source_main_commit,
        }


@dataclass(frozen=True)
class ProposedFutureOperation:
    operation_name: str
    provider: str
    symbols: tuple[str, ...]
    date_range: str
    data_type: str
    raw_data_expected: bool
    adjusted_fields_expected: bool
    cache_write_scope: str
    actual_import_scope: str
    trading_scope: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_name": self.operation_name,
            "provider": self.provider,
            "symbols": list(self.symbols),
            "date_range": self.date_range,
            "data_type": self.data_type,
            "raw_data_expected": self.raw_data_expected,
            "adjusted_fields_expected": self.adjusted_fields_expected,
            "cache_write_scope": self.cache_write_scope,
            "actual_import_scope": self.actual_import_scope,
            "trading_scope": self.trading_scope,
        }


@dataclass(frozen=True)
class CacheLocationChecklist:
    cache_path_proposed: str
    cache_path_is_git_ignored: str
    cache_path_is_outside_source_git: str
    cache_path_is_outside_reports_private: str
    cache_path_is_local_or_private: str
    cache_path_owner: str
    cache_path_unset_blocks_readiness: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "cache_path_proposed": self.cache_path_proposed,
            "cache_path_is_git_ignored": self.cache_path_is_git_ignored,
            "cache_path_is_outside_source_git": self.cache_path_is_outside_source_git,
            "cache_path_is_outside_reports_private": self.cache_path_is_outside_reports_private,
            "cache_path_is_local_or_private": self.cache_path_is_local_or_private,
            "cache_path_owner": self.cache_path_owner,
            "cache_path_unset_blocks_readiness": self.cache_path_unset_blocks_readiness,
        }


@dataclass(frozen=True)
class OperatorChecklistItem:
    item_id: str
    label: str
    required_answer: str
    current_status: str
    blocks_cache_write_if_unconfirmed: bool
    blocks_actual_import_if_unconfirmed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "label": self.label,
            "required_answer": self.required_answer,
            "current_status": self.current_status,
            "blocks_cache_write_if_unconfirmed": self.blocks_cache_write_if_unconfirmed,
            "blocks_actual_import_if_unconfirmed": self.blocks_actual_import_if_unconfirmed,
        }


@dataclass(frozen=True)
class ApprovalPhraseBoundary:
    cache_write_approval_phrase_required: bool
    cache_write_approval_phrase: str
    cache_write_approval_phrase_issued: bool
    actual_import_approval_phrase_required: bool
    actual_import_approval_phrase: str
    actual_import_approval_phrase_issued: bool
    placeholder_phrase_is_not_runtime_approval: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "cache_write_approval_phrase_required": self.cache_write_approval_phrase_required,
            "cache_write_approval_phrase": self.cache_write_approval_phrase,
            "cache_write_approval_phrase_issued": self.cache_write_approval_phrase_issued,
            "actual_import_approval_phrase_required": self.actual_import_approval_phrase_required,
            "actual_import_approval_phrase": self.actual_import_approval_phrase,
            "actual_import_approval_phrase_issued": self.actual_import_approval_phrase_issued,
            "placeholder_phrase_is_not_runtime_approval": self.placeholder_phrase_is_not_runtime_approval,
        }


@dataclass(frozen=True)
class CacheWriteOperatorSignoffSheet:
    report_date: str
    sheet_status: str
    readiness_phase: dict[str, bool]
    operator_review: OperatorReviewMetadata
    proposed_future_operation: ProposedFutureOperation
    cache_location_checklist: CacheLocationChecklist
    forbidden_raw_data_locations: tuple[OperatorChecklistItem, ...]
    retention_inventory_checklist: tuple[OperatorChecklistItem, ...]
    purge_rollback_checklist: tuple[OperatorChecklistItem, ...]
    data_quality_preconditions: tuple[OperatorChecklistItem, ...]
    approval_phrase_boundary: ApprovalPhraseBoundary
    execution_boundary: dict[str, Any]
    readiness_verdict: dict[str, Any]
    next_human_actions: tuple[str, ...]
    next_cursor_handoff_draft: dict[str, Any]
    safety_flags: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "sheet_status": self.sheet_status,
            "readiness_phase": dict(self.readiness_phase),
            "operator_review": self.operator_review.to_dict(),
            "proposed_future_operation": self.proposed_future_operation.to_dict(),
            "cache_location_checklist": self.cache_location_checklist.to_dict(),
            "forbidden_raw_data_locations": [item.to_dict() for item in self.forbidden_raw_data_locations],
            "retention_inventory_checklist": [item.to_dict() for item in self.retention_inventory_checklist],
            "purge_rollback_checklist": [item.to_dict() for item in self.purge_rollback_checklist],
            "data_quality_preconditions": [item.to_dict() for item in self.data_quality_preconditions],
            "approval_phrase_boundary": self.approval_phrase_boundary.to_dict(),
            "execution_boundary": dict(self.execution_boundary),
            "readiness_verdict": dict(self.readiness_verdict),
            "next_human_actions": list(self.next_human_actions),
            "next_cursor_handoff_draft": dict(self.next_cursor_handoff_draft),
            "safety_flags": dict(self.safety_flags),
        }


def _unreviewed_item(
    item_id: str,
    label: str,
    *,
    answer: str = "operator_must_confirm",
    blocks_actual_import: bool = True,
) -> OperatorChecklistItem:
    return OperatorChecklistItem(
        item_id=item_id,
        label=label,
        required_answer=answer,
        current_status="unreviewed",
        blocks_cache_write_if_unconfirmed=True,
        blocks_actual_import_if_unconfirmed=blocks_actual_import,
    )


def _forbidden_locations() -> tuple[OperatorChecklistItem, ...]:
    return (
        _unreviewed_item("FORBIDDEN-01", "source Git: forbidden for raw OHLCV"),
        _unreviewed_item("FORBIDDEN-02", "reports-private: forbidden for raw OHLCV"),
        _unreviewed_item("FORBIDDEN-03", "GitHub artifacts: forbidden for raw OHLCV"),
        _unreviewed_item("FORBIDDEN-04", "ChatGPT pasted content: forbidden for raw OHLCV"),
        _unreviewed_item("FORBIDDEN-05", "Cursor pasted content: forbidden for raw OHLCV"),
        _unreviewed_item("FORBIDDEN-06", "public outputs: forbidden for raw OHLCV"),
        _unreviewed_item("FORBIDDEN-07", "broker/manual raw mix: forbidden"),
    )


def _retention_inventory_items() -> tuple[OperatorChecklistItem, ...]:
    return (
        _unreviewed_item("RETENTION-01", "retention_policy is explicit"),
        _unreviewed_item("RETENTION-02", "retention_days_or_operator_defined is recorded"),
        _unreviewed_item("RETENTION-03", "raw_inventory_required is accepted"),
        _unreviewed_item("RETENTION-04", "redacted_metadata_index_allowed only without raw values"),
        _unreviewed_item("RETENTION-05", "orphan_raw_files_forbidden is accepted"),
        _unreviewed_item("RETENTION-06", "owner_required is recorded"),
    )


def _purge_rollback_items() -> tuple[OperatorChecklistItem, ...]:
    return (
        _unreviewed_item("PURGE-01", "purge_command_or_manual_steps_required"),
        _unreviewed_item("PURGE-02", "purge_dry_run_required"),
        _unreviewed_item("PURGE-03", "rollback_checklist_required"),
        _unreviewed_item("PURGE-04", "post_purge_verification_required"),
        _unreviewed_item("PURGE-05", "failure_stop_condition is explicit"),
    )


def _data_quality_preconditions() -> tuple[OperatorChecklistItem, ...]:
    return (
        _unreviewed_item("DQ-01", "provider_terms_reviewed"),
        _unreviewed_item("DQ-02", "provider_rate_limit_reviewed"),
        _unreviewed_item("DQ-03", "raw_adjusted_field_policy_reviewed"),
        _unreviewed_item("DQ-04", "cross_provider_validation_reviewed"),
        _unreviewed_item("DQ-05", "Stooq_adjustment_policy_reviewed"),
        _unreviewed_item("DQ-06", "data_quality_validation_required_before_actual_import"),
    )


def build_cache_write_operator_signoff_sheet(*, report_date: str) -> CacheWriteOperatorSignoffSheet:
    gate = build_cache_write_readiness_gate(report_date=report_date).to_dict()
    return CacheWriteOperatorSignoffSheet(
        report_date=report_date,
        sheet_status=V68_OPERATOR_SIGNOFF_STATUS,
        readiness_phase={
            "draft_only": True,
            "human_review_required": True,
            "ready_for_human_signoff": True,
            "approved_by_human_phrase_present": False,
            "execution_still_not_performed": True,
        },
        operator_review=OperatorReviewMetadata(
            signoff_id=f"SIGNOFF-16-{report_date}",
            report_date=report_date,
            operator_name_or_handle="TBD_BY_HUMAN",
            review_timestamp="TBD_BY_HUMAN",
            review_scope="Tiingo private/local cache-write pilot approval boundary only",
            milestone_version="v68",
            source_main_commit=V68_BASELINE_MAIN_COMMIT,
        ),
        proposed_future_operation=ProposedFutureOperation(
            operation_name=FUTURE_CACHE_WRITE_OPERATION,
            provider="Tiingo",
            symbols=("SPY", "QQQ", "AAPL", "NVDA"),
            date_range="future approved pilot range only",
            data_type="daily OHLCV with base and adjusted fields where provider supplies them",
            raw_data_expected=True,
            adjusted_fields_expected=True,
            cache_write_scope="private/local cache only, future milestone only",
            actual_import_scope="not approved",
            trading_scope="not approved",
        ),
        cache_location_checklist=CacheLocationChecklist(
            cache_path_proposed="UNSET",
            cache_path_is_git_ignored="unverified",
            cache_path_is_outside_source_git="unverified",
            cache_path_is_outside_reports_private="unverified",
            cache_path_is_local_or_private="unverified",
            cache_path_owner="TBD_BY_HUMAN",
            cache_path_unset_blocks_readiness=True,
        ),
        forbidden_raw_data_locations=_forbidden_locations(),
        retention_inventory_checklist=_retention_inventory_items(),
        purge_rollback_checklist=_purge_rollback_items(),
        data_quality_preconditions=_data_quality_preconditions(),
        approval_phrase_boundary=ApprovalPhraseBoundary(
            cache_write_approval_phrase_required=True,
            cache_write_approval_phrase=CACHE_WRITE_APPROVAL_PHRASE,
            cache_write_approval_phrase_issued=False,
            actual_import_approval_phrase_required=True,
            actual_import_approval_phrase=ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
            actual_import_approval_phrase_issued=False,
            placeholder_phrase_is_not_runtime_approval=True,
        ),
        execution_boundary={
            "cache_write_approval_status": "not_approved",
            "cache_write_execution_status": "not_executed",
            "actual_import_approval_status": "not_approved",
            "actual_import_execution_status": "not_executed",
            "trading_action_status": "not_approved_not_executed",
            "raw_ohlcv_persistence_status": "not_approved_not_executed",
            "provider_live_access_status": "not_approved_not_executed",
        },
        readiness_verdict={
            "operator_signoff_status": V68_OPERATOR_SIGNOFF_STATUS,
            "cache_write_approval_status": "not_approved",
            "cache_write_execution_status": "not_executed",
            "actual_import_approval_status": "not_approved",
            "actual_import_execution_status": "not_executed",
            "overall_readiness": V68_OVERALL_READINESS,
            "v67_gate_status": gate["gate_status"],
            "v67_signoff16_status": gate["readiness_verdict"]["signoff16_status"],
            "cache_path_unset_blocks_readiness": True,
        },
        next_human_actions=(
            "Select and record a private/local cache path without exposing raw data.",
            "Verify the cache path is Git-ignored, private/local, and outside reports-private.",
            "Review Tiingo terms/cache suitability and confirm no redistribution.",
            "Record retention owner, inventory rule, purge dry-run, rollback, and post-purge verification.",
            "Issue cache-write approval phrase only in a separate future execution milestone if all gates pass.",
        ),
        next_cursor_handoff_draft={
            "handoff_status": "draft_only_do_not_execute",
            "next_task": "private_local_cache_path_selection_and_cache_write_pilot_approval_package",
            "must_not_execute": (
                "provider live access",
                "cache write",
                "actual refresh/import",
                "raw OHLCV persistence",
                "trading action",
            ),
            "required_before_future_execution": (
                "SIGNOFF-16 completed by human",
                "cache path approved and verified",
                "retention and purge/rollback accepted",
                "cache-write approval phrase issued in future runtime context",
            ),
        },
        safety_flags={
            "source_only": True,
            "live_http_executed": False,
            "tiingo_api_call_executed": False,
            "stooq_live_fetch_executed": False,
            "yahoo_yfinance_live_fetch_executed": False,
            "polygon_live_fetch_executed": False,
            "provider_live_access_executed": False,
            "public_ohlcv_source_live_fetch_executed": False,
            "cache_write_executed": False,
            "actual_refresh_import_executed": False,
            "manual_actual_import_executed": False,
            "env_secret_displayed": False,
            "broker_manual_raw_data_handled": False,
            "workflow_dependency_pyproject_changed": False,
            "reports_private_touched": False,
            "trading_action_executed": False,
            "raw_ohlcv_persisted": False,
            "raw_api_response_persisted": False,
        },
    )
