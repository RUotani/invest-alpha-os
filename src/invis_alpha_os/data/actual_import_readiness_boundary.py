"""Source-only actual import separation and quarantine boundary.

This module prevents future cache-write pilot approval from being interpreted
as actual refresh/import or trading approval. It is deterministic and offline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invis_alpha_os.data.cache_path_preflight_approval_package import DEFAULT_CANDIDATE_CACHE_PATH
from invis_alpha_os.data.cache_write_pilot_approval_packet import build_cache_write_pilot_approval_packet
from invis_alpha_os.data.cache_write_pilot_result_review_gate import build_cache_write_pilot_result_review_gate
from invis_alpha_os.data.ohlcv_provider_approval import (
    ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
    CACHE_WRITE_APPROVAL_PHRASE,
)


V70C_BOUNDARY_STATUS = "source_only_actual_import_boundary_ready_import_not_approved"
V70C_ACTUAL_IMPORT_READINESS = "not_ready_separate_actual_import_approval_required"


@dataclass(frozen=True)
class ReadinessMatrixRow:
    area: str
    current_status: str
    approval_phrase_required: str | None
    approval_phrase_issued: bool
    execution_allowed_now: bool
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "area": self.area,
            "current_status": self.current_status,
            "approval_phrase_required": self.approval_phrase_required,
            "approval_phrase_issued": self.approval_phrase_issued,
            "execution_allowed_now": self.execution_allowed_now,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ActualImportReadinessBoundary:
    report_date: str
    milestone_version: str
    boundary_status: str
    cache_pilot_scope: dict[str, Any]
    quarantine_boundary: dict[str, Any]
    readiness_matrix: tuple[ReadinessMatrixRow, ...]
    actual_import_prerequisites: tuple[ReadinessMatrixRow, ...]
    approval_phrase_boundary: dict[str, Any]
    readiness_verdict: dict[str, Any]
    context_summary: dict[str, Any]
    next_cursor_handoff: dict[str, Any]
    safety_flags: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "milestone_version": self.milestone_version,
            "boundary_status": self.boundary_status,
            "cache_pilot_scope": dict(self.cache_pilot_scope),
            "quarantine_boundary": dict(self.quarantine_boundary),
            "readiness_matrix": [row.to_dict() for row in self.readiness_matrix],
            "actual_import_prerequisites": [row.to_dict() for row in self.actual_import_prerequisites],
            "approval_phrase_boundary": dict(self.approval_phrase_boundary),
            "readiness_verdict": dict(self.readiness_verdict),
            "context_summary": dict(self.context_summary),
            "next_cursor_handoff": dict(self.next_cursor_handoff),
            "safety_flags": dict(self.safety_flags),
        }


def _matrix_row(
    area: str,
    current_status: str,
    *,
    approval_phrase_required: str | None,
    notes: str,
) -> ReadinessMatrixRow:
    return ReadinessMatrixRow(
        area=area,
        current_status=current_status,
        approval_phrase_required=approval_phrase_required,
        approval_phrase_issued=False,
        execution_allowed_now=False,
        notes=notes,
    )


def _readiness_matrix() -> tuple[ReadinessMatrixRow, ...]:
    return (
        _matrix_row(
            "cache_write_pilot",
            "future_approval_required",
            approval_phrase_required=CACHE_WRITE_APPROVAL_PHRASE,
            notes="Only a future scoped cache-write pilot can be approved by this phrase.",
        ),
        _matrix_row(
            "cache_write_pilot_result_review",
            "not_run",
            approval_phrase_required=None,
            notes="Review gate exists, but no future cache-write pilot result has been produced.",
        ),
        _matrix_row(
            "actual_import",
            "not_ready",
            approval_phrase_required=ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
            notes="Actual refresh/import requires a separate package and explicit future phrase.",
        ),
        _matrix_row(
            "manual_actual_import",
            "not_ready",
            approval_phrase_required="separate_manual_import_approval_required",
            notes="Manual actual import remains outside the cache-write pilot scope.",
        ),
        _matrix_row(
            "trading_action",
            "not_approved",
            approval_phrase_required="separate_trading_approval_required",
            notes="No report or pilot approval can imply portfolio or trading action.",
        ),
    )


def _actual_import_prerequisites() -> tuple[ReadinessMatrixRow, ...]:
    return (
        _matrix_row(
            "PREREQ-01",
            "unmet",
            approval_phrase_required=None,
            notes="cache-write pilot completed",
        ),
        _matrix_row(
            "PREREQ-02",
            "unmet",
            approval_phrase_required=None,
            notes="cache-write pilot result review gate passed or explicitly reviewed",
        ),
        _matrix_row(
            "PREREQ-03",
            "unmet",
            approval_phrase_required=None,
            notes="raw leakage check passed",
        ),
        _matrix_row(
            "PREREQ-04",
            "unmet",
            approval_phrase_required=None,
            notes="cache inventory manifest accepted",
        ),
        _matrix_row(
            "PREREQ-05",
            "unmet",
            approval_phrase_required=None,
            notes="purge and rollback path proven",
        ),
        _matrix_row(
            "PREREQ-06",
            "unmet",
            approval_phrase_required=None,
            notes="data-quality acceptance passed",
        ),
        _matrix_row(
            "PREREQ-07",
            "unmet",
            approval_phrase_required=None,
            notes="actual import approval package created separately",
        ),
        _matrix_row(
            "PREREQ-08",
            "unmet",
            approval_phrase_required=ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
            notes="explicit future actual import approval phrase issued separately",
        ),
    )


def build_actual_import_readiness_boundary(
    *,
    report_date: str,
    candidate_cache_path: str = DEFAULT_CANDIDATE_CACHE_PATH,
) -> ActualImportReadinessBoundary:
    packet = build_cache_write_pilot_approval_packet(
        report_date=report_date,
        candidate_cache_path=candidate_cache_path,
    ).to_dict()
    result_gate = build_cache_write_pilot_result_review_gate(
        report_date=report_date,
        candidate_cache_path=candidate_cache_path,
    ).to_dict()
    return ActualImportReadinessBoundary(
        report_date=report_date,
        milestone_version="v70C",
        boundary_status=V70C_BOUNDARY_STATUS,
        cache_pilot_scope={
            "provider": packet["future_pilot_identity"]["provider"],
            "operation": packet["future_pilot_identity"]["operation"],
            "first_subset": packet["future_pilot_identity"]["first_subset"],
            "candidate_cache_path": candidate_cache_path,
            "cache_write_packet_verdict": packet["readiness_verdict"]["packet_verdict"],
            "result_review_current_verdict": result_gate["readiness_verdict"]["result_review_verdict"],
        },
        quarantine_boundary={
            "pilot_cache_is_quarantined_from_actual_import": True,
            "automatic_promotion_from_cache_to_actual_import_allowed": False,
            "actual_import_requires_separate_package": True,
            "actual_import_requires_separate_future_approval_phrase": True,
            "raw_provider_data_private_local_only": True,
            "raw_provider_data_allowed_in_git": False,
            "raw_provider_data_allowed_in_reports_private": False,
            "raw_provider_data_allowed_in_chatgpt_or_cursor": False,
            "trading_action_separate_and_not_approved": True,
        },
        readiness_matrix=_readiness_matrix(),
        actual_import_prerequisites=_actual_import_prerequisites(),
        approval_phrase_boundary={
            "cache_write_approval_phrase": CACHE_WRITE_APPROVAL_PHRASE,
            "cache_write_approval_phrase_issued": False,
            "cache_write_approval_does_not_imply_actual_import": True,
            "result_review_pass_required_for_actual_import_discussion": True,
            "result_review_pass_not_sufficient_for_actual_import": True,
            "actual_import_approval_phrase": ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
            "actual_import_approval_phrase_issued": False,
            "actual_import_approval_phrase_required_separately": True,
            "trading_action_approval_in_scope": False,
        },
        readiness_verdict={
            "cache_write_pilot_readiness": "future_approval_required",
            "cache_write_pilot_result_review_readiness": "not_run",
            "actual_import_readiness": V70C_ACTUAL_IMPORT_READINESS,
            "manual_actual_import_readiness": "not_ready_separate_manual_import_approval_required",
            "trading_readiness": "not_approved",
            "cache_write_execution_allowed_now": False,
            "actual_import_execution_allowed_now": False,
            "manual_actual_import_execution_allowed_now": False,
            "trading_action_allowed_now": False,
            "raw_ohlcv_fields_emitted": False,
        },
        context_summary={
            "v70c_actual_import_boundary_available": True,
            "actual_import_readiness": V70C_ACTUAL_IMPORT_READINESS,
            "cache_write_approval_does_not_imply_actual_import": True,
            "next_task": "future_cache_write_pilot_requires_explicit_human_cache_write_approval",
        },
        next_cursor_handoff={
            "handoff_status": "source_only_complete_stop_before_hard_gate",
            "recommended_next_task": "wait_for_explicit_cache_write_approval_or_prepare_actual_import_approval_package_source_only",
            "do_not_continue_beyond_v70c_without_new_human_instruction": True,
            "must_not_execute": (
                "provider live access",
                "cache write",
                "actual refresh/import",
                "manual actual import",
                "raw OHLCV persistence",
                "trading action",
            ),
        },
        safety_flags={
            "source_only": True,
            "provider_live_access_executed": False,
            "live_http_executed": False,
            "tiingo_api_call_executed": False,
            "stooq_live_fetch_executed": False,
            "yahoo_yfinance_live_fetch_executed": False,
            "polygon_live_fetch_executed": False,
            "cache_write_executed": False,
            "actual_refresh_import_executed": False,
            "manual_actual_import_executed": False,
            "raw_ohlcv_emitted": False,
            "raw_ohlcv_persisted": False,
            "raw_api_response_persisted": False,
            "reports_private_raw_data_written": False,
            "git_tracked_raw_data_written": False,
            "env_secret_displayed": False,
            "broker_manual_raw_data_handled": False,
            "workflow_dependency_pyproject_changed": False,
            "trading_action_executed": False,
        },
    )
