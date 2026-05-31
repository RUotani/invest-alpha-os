"""Source-only cache purge/inventory dry-run contract.

This module defines a reversible future cache-write pilot contract and redacted
manifest schema. It does not list directories, read files, delete files, read
raw OHLCV, call providers, write cache, import data, display secrets, or perform
trading actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invis_alpha_os.data.cache_path_preflight_approval_package import (
    DEFAULT_CANDIDATE_CACHE_PATH,
    build_cache_path_preflight_approval_package,
)


V69B_CONTRACT_STATUS = "source_only_dryrun_contract_ready_no_deletion_no_raw_read"
V69B_VERDICT = "purge_inventory_dryrun_contract_ready_execution_not_approved"


@dataclass(frozen=True)
class RedactedManifestField:
    field_name: str
    field_type: str
    allowed: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "field_type": self.field_type,
            "allowed": self.allowed,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PurgeDryRunContractStep:
    step_id: str
    description: str
    execution_mode: str
    destructive_action_allowed: bool
    raw_ohlcv_read_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "execution_mode": self.execution_mode,
            "destructive_action_allowed": self.destructive_action_allowed,
            "raw_ohlcv_read_allowed": self.raw_ohlcv_read_allowed,
        }


@dataclass(frozen=True)
class CachePurgeInventoryDryrunContract:
    report_date: str
    milestone_version: str
    contract_status: str
    candidate_cache_path: str
    v69_preflight_verdict: str
    dryrun_semantics: dict[str, Any]
    redacted_manifest_allowed_fields: tuple[RedactedManifestField, ...]
    redacted_manifest_forbidden_fields: tuple[RedactedManifestField, ...]
    cache_file_classification: tuple[dict[str, Any], ...]
    purge_target_selection_semantics: tuple[PurgeDryRunContractStep, ...]
    orphan_raw_file_check_semantics: tuple[PurgeDryRunContractStep, ...]
    post_purge_verification_checklist: tuple[PurgeDryRunContractStep, ...]
    rollback_checklist: tuple[PurgeDryRunContractStep, ...]
    readiness_verdict: dict[str, Any]
    context_summary: dict[str, Any]
    next_cursor_handoff: dict[str, Any]
    safety_flags: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "milestone_version": self.milestone_version,
            "contract_status": self.contract_status,
            "candidate_cache_path": self.candidate_cache_path,
            "v69_preflight_verdict": self.v69_preflight_verdict,
            "dryrun_semantics": dict(self.dryrun_semantics),
            "redacted_manifest_allowed_fields": [
                item.to_dict() for item in self.redacted_manifest_allowed_fields
            ],
            "redacted_manifest_forbidden_fields": [
                item.to_dict() for item in self.redacted_manifest_forbidden_fields
            ],
            "cache_file_classification": [dict(item) for item in self.cache_file_classification],
            "purge_target_selection_semantics": [
                item.to_dict() for item in self.purge_target_selection_semantics
            ],
            "orphan_raw_file_check_semantics": [
                item.to_dict() for item in self.orphan_raw_file_check_semantics
            ],
            "post_purge_verification_checklist": [
                item.to_dict() for item in self.post_purge_verification_checklist
            ],
            "rollback_checklist": [item.to_dict() for item in self.rollback_checklist],
            "readiness_verdict": dict(self.readiness_verdict),
            "context_summary": dict(self.context_summary),
            "next_cursor_handoff": dict(self.next_cursor_handoff),
            "safety_flags": dict(self.safety_flags),
        }


def _allowed_manifest_fields() -> tuple[RedactedManifestField, ...]:
    return (
        RedactedManifestField("provider_name", "string", True, "provider label only"),
        RedactedManifestField("asset_scope_label", "string", True, "coarse scope label only"),
        RedactedManifestField("symbol_count", "integer", True, "aggregate count only"),
        RedactedManifestField("file_count", "integer", True, "aggregate count only"),
        RedactedManifestField("date_range_label", "string", True, "coarse range label only"),
        RedactedManifestField("schema_version", "string", True, "manifest schema version"),
        RedactedManifestField("created_at_label", "string", True, "coarse generated label"),
        RedactedManifestField("hash_presence_boolean", "boolean", True, "hash present flag without values"),
        RedactedManifestField("raw_rows_count_optional_aggregate", "integer", True, "aggregate count only"),
        RedactedManifestField("no_raw_rows_embedded_boolean", "boolean", True, "must be true"),
    )


def _forbidden_manifest_fields() -> tuple[RedactedManifestField, ...]:
    return (
        RedactedManifestField("open", "number_or_series", False, "raw OHLCV row value"),
        RedactedManifestField("high", "number_or_series", False, "raw OHLCV row value"),
        RedactedManifestField("low", "number_or_series", False, "raw OHLCV row value"),
        RedactedManifestField("close", "number_or_series", False, "raw OHLCV row value"),
        RedactedManifestField("adj_close", "number_or_series", False, "adjusted raw OHLCV row value"),
        RedactedManifestField("volume", "number_or_series", False, "raw OHLCV row value"),
        RedactedManifestField("raw_api_response", "object_or_text", False, "provider raw response"),
        RedactedManifestField("per_row_ohlcv_data", "array", False, "raw per-row market data"),
        RedactedManifestField("secret_values", "string", False, "secret disclosure risk"),
        RedactedManifestField("broker_manual_raw_data", "object_or_text", False, "forbidden data boundary mix"),
    )


def _step(
    step_id: str,
    description: str,
    *,
    mode: str = "contract_only_not_executed",
) -> PurgeDryRunContractStep:
    return PurgeDryRunContractStep(
        step_id=step_id,
        description=description,
        execution_mode=mode,
        destructive_action_allowed=False,
        raw_ohlcv_read_allowed=False,
    )


def build_cache_purge_inventory_dryrun_contract(
    *,
    report_date: str,
    candidate_cache_path: str = DEFAULT_CANDIDATE_CACHE_PATH,
) -> CachePurgeInventoryDryrunContract:
    preflight = build_cache_path_preflight_approval_package(
        report_date=report_date,
        candidate_cache_path=candidate_cache_path,
    ).to_dict()
    v69_verdict = preflight["readiness_verdict"]["preflight_verdict"]
    return CachePurgeInventoryDryrunContract(
        report_date=report_date,
        milestone_version="v69B",
        contract_status=V69B_CONTRACT_STATUS,
        candidate_cache_path=candidate_cache_path,
        v69_preflight_verdict=v69_verdict,
        dryrun_semantics={
            "no_file_deletion_executed": True,
            "no_raw_ohlcv_read": True,
            "no_provider_api_call": True,
            "no_cache_write": True,
            "no_actual_import": True,
            "candidate_cache_path_remains_candidate_only": True,
            "destructive_purge_requires_future_explicit_approval": True,
            "redacted_manifest_metadata_only": True,
        },
        redacted_manifest_allowed_fields=_allowed_manifest_fields(),
        redacted_manifest_forbidden_fields=_forbidden_manifest_fields(),
        cache_file_classification=(
            {
                "classification_id": "CACHE-FILE-01",
                "label": "future_tiingo_ohlcv_raw_cache_file",
                "selection_mode": "schema_contract_only_no_filesystem_scan",
                "raw_read_allowed": False,
                "delete_allowed": False,
            },
            {
                "classification_id": "CACHE-FILE-02",
                "label": "future_redacted_manifest_file",
                "selection_mode": "schema_contract_only_no_filesystem_scan",
                "raw_read_allowed": False,
                "delete_allowed": False,
            },
            {
                "classification_id": "CACHE-FILE-03",
                "label": "future_orphan_raw_file_candidate",
                "selection_mode": "name_and_manifest_contract_only_no_filesystem_scan",
                "raw_read_allowed": False,
                "delete_allowed": False,
            },
        ),
        purge_target_selection_semantics=(
            _step("PURGE-TARGET-01", "select only files under approved future candidate cache path"),
            _step("PURGE-TARGET-02", "exclude source Git, reports-private, and public output paths"),
            _step("PURGE-TARGET-03", "emit redacted aggregate counts only in dry-run report"),
            _step("PURGE-TARGET-04", "require future destructive purge approval before deletion"),
        ),
        orphan_raw_file_check_semantics=(
            _step("ORPHAN-01", "compare future cache inventory against redacted manifest identifiers only"),
            _step("ORPHAN-02", "flag unknown raw files without reading row data"),
            _step("ORPHAN-03", "stop if file appears outside approved private/local cache path"),
        ),
        post_purge_verification_checklist=(
            _step("VERIFY-01", "confirm no selected raw cache files remain after future approved purge"),
            _step("VERIFY-02", "confirm no raw files were committed to Git or reports-private"),
            _step("VERIFY-03", "confirm redacted manifest contains no OHLCV rows"),
            _step("VERIFY-04", "record aggregate file_count and no_raw_rows_embedded_boolean only"),
        ),
        rollback_checklist=(
            _step("ROLLBACK-01", "stop future cache-write pilot if purge dry-run contract fails"),
            _step("ROLLBACK-02", "preserve source-only decision record without raw data"),
            _step("ROLLBACK-03", "require human review before any retry"),
        ),
        readiness_verdict={
            "contract_verdict": V69B_VERDICT,
            "v69_preflight_verdict": v69_verdict,
            "cache_write_approval_status": "not_approved",
            "cache_write_execution_status": "not_executed",
            "actual_import_approval_status": "not_approved",
            "actual_import_execution_status": "not_executed",
            "purge_execution_status": "not_executed",
            "destructive_purge_approval_status": "not_approved",
            "redacted_manifest_schema_status": "metadata_only_no_raw_rows",
        },
        context_summary={
            "v69b_contract_available": True,
            "candidate_cache_path": candidate_cache_path,
            "redacted_manifest_schema_available": True,
            "purge_dryrun_contract_available": True,
            "next_task": "v70_cursor_local_tiingo_private_cache_write_pilot_runbook_still_not_execution_approval",
        },
        next_cursor_handoff={
            "handoff_status": "source_only_ready_for_v70_runbook_not_execution",
            "recommended_next_task": "v70_cursor_local_tiingo_private_cache_write_pilot_runbook",
            "do_not_start_without_future_approval_phrase": True,
            "must_not_execute": (
                "provider live access",
                "cache write",
                "actual refresh/import",
                "raw OHLCV persistence",
                "destructive purge",
                "trading action",
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
            "raw_ohlcv_read": False,
            "raw_ohlcv_persisted": False,
            "raw_api_response_persisted": False,
            "reports_private_raw_data_written": False,
            "git_tracked_raw_data_written": False,
            "filesystem_scan_executed": False,
            "file_deletion_executed": False,
            "env_secret_displayed": False,
            "broker_manual_raw_data_handled": False,
            "workflow_dependency_pyproject_changed": False,
            "trading_action_executed": False,
        },
    )
