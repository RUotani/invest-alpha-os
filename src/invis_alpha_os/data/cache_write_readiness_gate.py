"""Source-only cache-write readiness gate draft.

This module prepares SIGNOFF-16 requirements, private/local cache storage
policy, retention and purge/rollback policy, approval boundaries, and a future
cache-write pilot draft. It never calls providers, writes cache, imports data,
persists raw OHLCV, displays secrets, touches reports-private, or performs
trading actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invis_alpha_os.data.cross_provider_validation_result_review import (
    STOOQ_ADJUSTED_SUITABILITY,
    V65_RECLASSIFIED_VERDICT,
    TIINGO_ADJUSTED_SERIES_CONFIDENCE,
)
from invis_alpha_os.data.ohlcv_provider_approval import (
    ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
    CACHE_WRITE_APPROVAL_PHRASE,
)
from invis_alpha_os.data.tiingo_live_fetch_result_review import (
    TIINGO_ACTUAL_IMPORT_READINESS_VERDICT,
    TIINGO_CACHE_WRITE_READINESS_VERDICT,
    TIINGO_V63B_PILOT_UNIVERSE,
    TIINGO_V63B_RESULT_VERDICT,
)


CACHE_WRITE_GATE_STATUS = "draft_only_not_approved"
SIGNOFF_16_STATUS = "unresolved_required_before_cache_write"
FUTURE_CACHE_WRITE_OPERATION = "tiingo_private_local_cache_write_pilot"


@dataclass(frozen=True)
class CacheWriteSignoff16Requirement:
    requirement_id: str
    description: str
    status: str
    required_before_cache_write: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "description": self.description,
            "status": self.status,
            "required_before_cache_write": self.required_before_cache_write,
        }


@dataclass(frozen=True)
class RawDataAllowedLocationCandidate:
    location_id: str
    description: str
    allowed_only_after_future_approval: bool
    required_controls: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "location_id": self.location_id,
            "description": self.description,
            "allowed_only_after_future_approval": self.allowed_only_after_future_approval,
            "required_controls": list(self.required_controls),
        }


@dataclass(frozen=True)
class RawDataForbiddenLocation:
    location_id: str
    description: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "location_id": self.location_id,
            "description": self.description,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PrivateLocalCacheStoragePolicy:
    policy_status: str
    allowed_candidates: tuple[RawDataAllowedLocationCandidate, ...]
    forbidden_locations: tuple[RawDataForbiddenLocation, ...]
    cache_location: str
    raw_data_git_allowed: bool
    raw_data_reports_private_allowed: bool
    redacted_summary_reports_private_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_status": self.policy_status,
            "allowed_candidates": [item.to_dict() for item in self.allowed_candidates],
            "forbidden_locations": [item.to_dict() for item in self.forbidden_locations],
            "cache_location": self.cache_location,
            "raw_data_git_allowed": self.raw_data_git_allowed,
            "raw_data_reports_private_allowed": self.raw_data_reports_private_allowed,
            "redacted_summary_reports_private_allowed": self.redacted_summary_reports_private_allowed,
        }


@dataclass(frozen=True)
class CacheRetentionPolicyDraft:
    retention_period_initial_pilot: str
    retention_owner_required: bool
    raw_file_inventory_required: bool
    redacted_summary_required: bool
    no_orphan_raw_files_required: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "retention_period_initial_pilot": self.retention_period_initial_pilot,
            "retention_owner_required": self.retention_owner_required,
            "raw_file_inventory_required": self.raw_file_inventory_required,
            "redacted_summary_required": self.redacted_summary_required,
            "no_orphan_raw_files_required": self.no_orphan_raw_files_required,
        }


@dataclass(frozen=True)
class CachePurgeRollbackPolicyDraft:
    cache_purge_command_required: bool
    rollback_checklist_required: bool
    purge_dry_run_required: bool
    post_purge_verification_required: bool
    future_checklist: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cache_purge_command_required": self.cache_purge_command_required,
            "rollback_checklist_required": self.rollback_checklist_required,
            "purge_dry_run_required": self.purge_dry_run_required,
            "post_purge_verification_required": self.post_purge_verification_required,
            "future_checklist": list(self.future_checklist),
        }


@dataclass(frozen=True)
class TermsCacheAcknowledgement:
    acknowledgement_status: str
    required_statements: tuple[str, ...]
    operator_signoff_required: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "acknowledgement_status": self.acknowledgement_status,
            "required_statements": list(self.required_statements),
            "operator_signoff_required": self.operator_signoff_required,
        }


@dataclass(frozen=True)
class CacheWriteApprovalBoundary:
    future_cache_write_approval_phrase: str
    cache_write_approved: bool
    approval_phrase_issued: bool
    separate_explicit_approval_required: bool
    trading_action_approved: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "future_cache_write_approval_phrase": self.future_cache_write_approval_phrase,
            "cache_write_approved": self.cache_write_approved,
            "approval_phrase_issued": self.approval_phrase_issued,
            "separate_explicit_approval_required": self.separate_explicit_approval_required,
            "trading_action_approved": self.trading_action_approved,
        }


@dataclass(frozen=True)
class ActualImportBoundary:
    future_actual_import_approval_phrase: str
    actual_import_approved: bool
    approval_phrase_issued: bool
    remains_separate_from_cache_write: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "future_actual_import_approval_phrase": self.future_actual_import_approval_phrase,
            "actual_import_approved": self.actual_import_approved,
            "approval_phrase_issued": self.approval_phrase_issued,
            "remains_separate_from_cache_write": self.remains_separate_from_cache_write,
        }


@dataclass(frozen=True)
class CacheWritePilotApprovalPrerequisite:
    prerequisite_id: str
    description: str
    status: str
    blocks_pilot: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "prerequisite_id": self.prerequisite_id,
            "description": self.description,
            "status": self.status,
            "blocks_pilot": self.blocks_pilot,
        }


@dataclass(frozen=True)
class FutureCacheWritePilotDraft:
    package_status: str
    operation: str
    provider: str
    universe: tuple[str, ...]
    recommended_first_subset: tuple[str, ...]
    first_subset_reason: str
    date_range: str
    cache_location: str
    raw_data_git_allowed: bool
    raw_data_reports_private_allowed: bool
    redacted_summary_reports_private_allowed: bool
    approval_phrase_issued: bool
    separate_explicit_approval_required: bool
    prerequisites: tuple[CacheWritePilotApprovalPrerequisite, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_status": self.package_status,
            "operation": self.operation,
            "provider": self.provider,
            "universe": list(self.universe),
            "recommended_first_subset": list(self.recommended_first_subset),
            "first_subset_reason": self.first_subset_reason,
            "date_range": self.date_range,
            "cache_location": self.cache_location,
            "raw_data_git_allowed": self.raw_data_git_allowed,
            "raw_data_reports_private_allowed": self.raw_data_reports_private_allowed,
            "redacted_summary_reports_private_allowed": self.redacted_summary_reports_private_allowed,
            "approval_phrase_issued": self.approval_phrase_issued,
            "separate_explicit_approval_required": self.separate_explicit_approval_required,
            "prerequisites": [item.to_dict() for item in self.prerequisites],
        }


@dataclass(frozen=True)
class CacheWriteNextCursorHandoff:
    handoff_status: str
    next_task: str
    required_before_execution: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    final_report_fields: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "handoff_status": self.handoff_status,
            "next_task": self.next_task,
            "required_before_execution": list(self.required_before_execution),
            "stop_conditions": list(self.stop_conditions),
            "final_report_fields": list(self.final_report_fields),
        }


@dataclass(frozen=True)
class CacheWriteReadinessGate:
    report_date: str
    gate_status: str
    current_state: dict[str, Any]
    signoff16_requirements: tuple[CacheWriteSignoff16Requirement, ...]
    storage_policy: PrivateLocalCacheStoragePolicy
    retention_policy: CacheRetentionPolicyDraft
    purge_rollback_policy: CachePurgeRollbackPolicyDraft
    terms_cache_acknowledgement: TermsCacheAcknowledgement
    cache_write_approval_boundary: CacheWriteApprovalBoundary
    actual_import_boundary: ActualImportBoundary
    future_cache_write_pilot: FutureCacheWritePilotDraft
    readiness_verdict: dict[str, Any]
    next_cursor_handoff: CacheWriteNextCursorHandoff
    safety_flags: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "gate_status": self.gate_status,
            "current_state": dict(self.current_state),
            "signoff16_requirements": [item.to_dict() for item in self.signoff16_requirements],
            "storage_policy": self.storage_policy.to_dict(),
            "retention_policy": self.retention_policy.to_dict(),
            "purge_rollback_policy": self.purge_rollback_policy.to_dict(),
            "terms_cache_acknowledgement": self.terms_cache_acknowledgement.to_dict(),
            "cache_write_approval_boundary": self.cache_write_approval_boundary.to_dict(),
            "actual_import_boundary": self.actual_import_boundary.to_dict(),
            "future_cache_write_pilot": self.future_cache_write_pilot.to_dict(),
            "readiness_verdict": dict(self.readiness_verdict),
            "next_cursor_handoff": self.next_cursor_handoff.to_dict(),
            "safety_flags": dict(self.safety_flags),
        }


def _signoff16_requirements() -> tuple[CacheWriteSignoff16Requirement, ...]:
    rows = (
        ("SIGNOFF-16-01", "Tiingo terms/cache suitability acknowledgement"),
        ("SIGNOFF-16-02", "private/internal use only"),
        ("SIGNOFF-16-03", "no redistribution"),
        ("SIGNOFF-16-04", "raw data must not be committed to Git"),
        ("SIGNOFF-16-05", "raw data must not be committed to reports-private"),
        ("SIGNOFF-16-06", "raw data must not be pasted to ChatGPT/Cursor"),
        ("SIGNOFF-16-07", "raw data must not be published"),
        ("SIGNOFF-16-08", "raw data may only be written to approved private/local cache path after approval"),
        ("SIGNOFF-16-09", "cache path must be Git-ignored and outside reports-private"),
        ("SIGNOFF-16-10", "retention policy must be explicit"),
        ("SIGNOFF-16-11", "purge/rollback procedure must be tested"),
        ("SIGNOFF-16-12", "redacted summary only may be synced to reports-private"),
        ("SIGNOFF-16-13", "cache write approval phrase must be separately issued"),
        ("SIGNOFF-16-14", "actual import remains separate"),
    )
    return tuple(
        CacheWriteSignoff16Requirement(
            requirement_id=req_id,
            description=description,
            status=SIGNOFF_16_STATUS,
            required_before_cache_write=True,
        )
        for req_id, description in rows
    )


def _storage_policy() -> PrivateLocalCacheStoragePolicy:
    return PrivateLocalCacheStoragePolicy(
        policy_status="draft_only_not_approved",
        allowed_candidates=(
            RawDataAllowedLocationCandidate(
                "gitignored_source_repo_cache",
                "private local cache directory under source repo only if Git-ignored and never committed",
                True,
                ("gitignore_verified", "outside_reports_private", "operator_approved_path"),
            ),
            RawDataAllowedLocationCandidate(
                "external_private_data_directory",
                "external private data directory outside source repo and reports-private",
                True,
                ("operator_approved_path", "raw_inventory", "purge_plan"),
            ),
            RawDataAllowedLocationCandidate(
                "encrypted_local_user_machine",
                "encrypted/local user machine storage if feasible",
                True,
                ("local_only", "operator_access_control", "purge_plan"),
            ),
            RawDataAllowedLocationCandidate(
                "redacted_metadata_index",
                "metadata index without raw values may be allowed in reports-private only if redacted",
                True,
                ("no_raw_values", "redacted_summary_only", "separate_sync_approval"),
            ),
        ),
        forbidden_locations=(
            RawDataForbiddenLocation("reports_private_raw_ohlcv", "reports-private raw OHLCV", "raw provider data"),
            RawDataForbiddenLocation("source_git_raw_ohlcv", "source Git raw OHLCV", "committed raw data risk"),
            RawDataForbiddenLocation("github_artifacts_raw_ohlcv", "GitHub artifacts containing raw OHLCV", "artifact retention risk"),
            RawDataForbiddenLocation("chatgpt_pasted_raw_data", "ChatGPT pasted raw data", "third-party disclosure risk"),
            RawDataForbiddenLocation("public_outputs", "public outputs", "redistribution risk"),
            RawDataForbiddenLocation("broker_manual_raw_mix", "broker/manual raw data mixing", "data boundary confusion"),
        ),
        cache_location="to be explicitly configured",
        raw_data_git_allowed=False,
        raw_data_reports_private_allowed=False,
        redacted_summary_reports_private_allowed=True,
    )


def _future_pilot_prerequisites() -> tuple[CacheWritePilotApprovalPrerequisite, ...]:
    return (
        CacheWritePilotApprovalPrerequisite("SIGNOFF-16", "terms/cache suitability signoff", "unresolved", True),
        CacheWritePilotApprovalPrerequisite("CACHE-LOCATION", "approved private/local cache path", "not_configured", True),
        CacheWritePilotApprovalPrerequisite("GITIGNORE-CHECK", "cache path ignored and outside reports-private", "not_verified", True),
        CacheWritePilotApprovalPrerequisite("RETENTION", "short-lived/operator-defined retention", "draft_only", True),
        CacheWritePilotApprovalPrerequisite("PURGE-ROLLBACK", "tested purge/rollback procedure", "not_tested", True),
        CacheWritePilotApprovalPrerequisite("CACHE-APPROVAL", "cache write approval phrase", "not_issued", True),
    )


def build_cache_write_readiness_gate(*, report_date: str) -> CacheWriteReadinessGate:
    storage = _storage_policy()
    return CacheWriteReadinessGate(
        report_date=report_date,
        gate_status=CACHE_WRITE_GATE_STATUS,
        current_state={
            "v66_completed": True,
            "tiingo_provider_viability": TIINGO_V63B_RESULT_VERDICT,
            "v65_reclassified_verdict": V65_RECLASSIFIED_VERDICT,
            "stooq_adjusted_comparison_suitability": STOOQ_ADJUSTED_SUITABILITY,
            "tiingo_adjusted_series_confidence": TIINGO_ADJUSTED_SERIES_CONFIDENCE,
            "cache_write_readiness": TIINGO_CACHE_WRITE_READINESS_VERDICT,
            "actual_import_readiness": TIINGO_ACTUAL_IMPORT_READINESS_VERDICT,
        },
        signoff16_requirements=_signoff16_requirements(),
        storage_policy=storage,
        retention_policy=CacheRetentionPolicyDraft(
            retention_period_initial_pilot="short_lived_or_operator_defined",
            retention_owner_required=True,
            raw_file_inventory_required=True,
            redacted_summary_required=True,
            no_orphan_raw_files_required=True,
        ),
        purge_rollback_policy=CachePurgeRollbackPolicyDraft(
            cache_purge_command_required=True,
            rollback_checklist_required=True,
            purge_dry_run_required=True,
            post_purge_verification_required=True,
            future_checklist=(
                "inventory every raw cache file before write",
                "verify cache path is Git-ignored and outside reports-private",
                "run future purge command in dry-run mode before any destructive cleanup",
                "verify no orphan raw files remain after purge",
                "record redacted summary only",
            ),
        ),
        terms_cache_acknowledgement=TermsCacheAcknowledgement(
            acknowledgement_status="unresolved_required_before_cache_write",
            required_statements=(
                "Tiingo cache/storage terms reviewed for private/internal use",
                "no redistribution of raw provider data",
                "raw data will not be committed, pasted, published, or synced to reports-private",
                "operator accepts retention and purge obligations",
            ),
            operator_signoff_required=True,
        ),
        cache_write_approval_boundary=CacheWriteApprovalBoundary(
            future_cache_write_approval_phrase=CACHE_WRITE_APPROVAL_PHRASE,
            cache_write_approved=False,
            approval_phrase_issued=False,
            separate_explicit_approval_required=True,
            trading_action_approved=False,
        ),
        actual_import_boundary=ActualImportBoundary(
            future_actual_import_approval_phrase=ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
            actual_import_approved=False,
            approval_phrase_issued=False,
            remains_separate_from_cache_write=True,
        ),
        future_cache_write_pilot=FutureCacheWritePilotDraft(
            package_status="draft_only_not_approved",
            operation=FUTURE_CACHE_WRITE_OPERATION,
            provider="Tiingo",
            universe=TIINGO_V63B_PILOT_UNIVERSE,
            recommended_first_subset=("SPY", "QQQ", "AAPL", "NVDA"),
            first_subset_reason="ETF + mega-cap + split-sensitive/high-beta sample",
            date_range="2024-01-01 to latest completed trading day at future execution",
            cache_location=storage.cache_location,
            raw_data_git_allowed=False,
            raw_data_reports_private_allowed=False,
            redacted_summary_reports_private_allowed=True,
            approval_phrase_issued=False,
            separate_explicit_approval_required=True,
            prerequisites=_future_pilot_prerequisites(),
        ),
        readiness_verdict={
            "signoff16_status": SIGNOFF_16_STATUS,
            "cache_write_readiness": TIINGO_CACHE_WRITE_READINESS_VERDICT,
            "actual_import_readiness": TIINGO_ACTUAL_IMPORT_READINESS_VERDICT,
            "cache_write_approved": False,
            "actual_import_approved": False,
            "trading_action_approved": False,
            "approval_phrase_issued": False,
        },
        next_cursor_handoff=CacheWriteNextCursorHandoff(
            handoff_status="draft_only_do_not_execute_without_cache_write_approval_phrase",
            next_task="cache_write_pilot_approval_package_after_signoff16",
            required_before_execution=(
                "SIGNOFF-16 completed",
                "private/local cache path explicitly configured",
                "cache path Git-ignore verified and outside reports-private",
                "retention and purge/rollback policy accepted",
                "cache write approval phrase issued in a separate task",
            ),
            stop_conditions=(
                "cache path is not approved",
                "raw data would be committed to Git or reports-private",
                "secret value would be displayed",
                "actual import path is invoked",
                "trading action is requested",
            ),
            final_report_fields=(
                "cache path redacted status",
                "raw file inventory count",
                "redacted summary path",
                "purge/rollback verification",
                "no Git/reports-private raw data verification",
                "cache/import/trading approval flags",
            ),
        ),
        safety_flags={
            "source_only": True,
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
