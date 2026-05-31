"""Source-only future cache-write pilot result review gate.

This module defines how a future cache-write pilot result must be reviewed
without storing or displaying raw OHLCV. It is deterministic and represents the
current pre-run state as not_run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invis_alpha_os.data.cache_path_preflight_approval_package import DEFAULT_CANDIDATE_CACHE_PATH
from invis_alpha_os.data.cache_write_pilot_approval_packet import V70_FIRST_SUBSET, build_cache_write_pilot_approval_packet


V70B_REVIEW_STATUS = "source_only_result_review_gate_ready_pilot_not_run"
V70B_CURRENT_VERDICT = "not_run"
V70B_ALLOWED_VERDICTS = (
    "pass_cache_write_pilot_review",
    "warn_manual_review_required",
    "fail_raw_leakage_detected",
    "fail_path_policy_violation",
    "fail_provider_scope_mismatch",
    "fail_missing_purge_contract",
    "not_run",
)


@dataclass(frozen=True)
class ReviewCriterion:
    criterion_id: str
    description: str
    allowed_output: str
    current_status: str
    raw_values_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "description": self.description,
            "allowed_output": self.allowed_output,
            "current_status": self.current_status,
            "raw_values_allowed": self.raw_values_allowed,
        }


@dataclass(frozen=True)
class CacheWritePilotResultReviewGate:
    report_date: str
    milestone_version: str
    review_status: str
    future_pilot_scope: dict[str, Any]
    acceptance_criteria: tuple[ReviewCriterion, ...]
    allowed_result_fields: tuple[str, ...]
    forbidden_result_fields: tuple[str, ...]
    verdict_policy: dict[str, Any]
    readiness_verdict: dict[str, Any]
    context_summary: dict[str, Any]
    next_cursor_handoff: dict[str, Any]
    safety_flags: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "milestone_version": self.milestone_version,
            "review_status": self.review_status,
            "future_pilot_scope": dict(self.future_pilot_scope),
            "acceptance_criteria": [item.to_dict() for item in self.acceptance_criteria],
            "allowed_result_fields": list(self.allowed_result_fields),
            "forbidden_result_fields": list(self.forbidden_result_fields),
            "verdict_policy": dict(self.verdict_policy),
            "readiness_verdict": dict(self.readiness_verdict),
            "context_summary": dict(self.context_summary),
            "next_cursor_handoff": dict(self.next_cursor_handoff),
            "safety_flags": dict(self.safety_flags),
        }


def _criterion(criterion_id: str, description: str, allowed_output: str) -> ReviewCriterion:
    return ReviewCriterion(
        criterion_id=criterion_id,
        description=description,
        allowed_output=allowed_output,
        current_status="pending_future_pilot_result",
        raw_values_allowed=False,
    )


def _criteria() -> tuple[ReviewCriterion, ...]:
    return (
        _criterion("REVIEW-01", "provider attempted / not attempted metadata", "boolean/enum only"),
        _criterion("REVIEW-02", "symbol coverage summary", "aggregate counts and symbol labels only"),
        _criterion("REVIEW-03", "date range summary", "coarse date range label only"),
        _criterion("REVIEW-04", "row count summary", "aggregate counts only"),
        _criterion("REVIEW-05", "base/adjusted field presence summary", "presence booleans only"),
        _criterion("REVIEW-06", "duplicate date check summary", "aggregate counts only"),
        _criterion("REVIEW-07", "missing date policy summary", "policy enum and aggregate counts only"),
        _criterion("REVIEW-08", "split/dividend adjustment sanity summary if available", "pass/warn/fail only"),
        _criterion("REVIEW-09", "redacted manifest check", "metadata-only manifest status"),
        _criterion("REVIEW-10", "raw leakage check", "pass/fail and location category only"),
        _criterion("REVIEW-11", "cache path policy check", "pass/fail only"),
        _criterion("REVIEW-12", "Git/reports-private exclusion check", "pass/fail only"),
        _criterion("REVIEW-13", "purge dry-run availability", "pass/fail only"),
        _criterion("REVIEW-14", "post-purge verification availability", "pass/fail only"),
    )


def build_cache_write_pilot_result_review_gate(
    *,
    report_date: str,
    candidate_cache_path: str = DEFAULT_CANDIDATE_CACHE_PATH,
) -> CacheWritePilotResultReviewGate:
    packet = build_cache_write_pilot_approval_packet(
        report_date=report_date,
        candidate_cache_path=candidate_cache_path,
    ).to_dict()
    return CacheWritePilotResultReviewGate(
        report_date=report_date,
        milestone_version="v70B",
        review_status=V70B_REVIEW_STATUS,
        future_pilot_scope={
            "provider": "Tiingo",
            "operation": "tiingo_private_local_cache_write_pilot",
            "symbols": list(V70_FIRST_SUBSET),
            "candidate_cache_path": candidate_cache_path,
            "approval_packet_verdict": packet["readiness_verdict"]["packet_verdict"],
        },
        acceptance_criteria=_criteria(),
        allowed_result_fields=(
            "provider_attempted",
            "symbols_requested_count",
            "symbols_success_count",
            "date_range_label",
            "row_count_aggregate",
            "field_presence_booleans",
            "duplicate_date_count",
            "missing_date_policy_status",
            "adjustment_sanity_status",
            "redacted_manifest_status",
            "raw_leakage_status",
            "cache_path_policy_status",
            "git_reports_private_exclusion_status",
            "purge_dryrun_available",
            "post_purge_verification_available",
            "final_verdict",
        ),
        forbidden_result_fields=(
            "open",
            "high",
            "low",
            "close",
            "adj_close",
            "volume",
            "raw_api_response",
            "per_row_ohlcv_data",
            "secret_values",
            "broker_manual_raw_data",
        ),
        verdict_policy={
            "allowed_verdicts": list(V70B_ALLOWED_VERDICTS),
            "current_verdict": V70B_CURRENT_VERDICT,
            "pass_requires_no_raw_leakage": True,
            "pass_requires_cache_path_policy_pass": True,
            "pass_requires_redacted_manifest": True,
            "pass_requires_purge_contract": True,
            "pass_does_not_approve_actual_import": True,
            "pass_does_not_approve_trading": True,
        },
        readiness_verdict={
            "result_review_verdict": V70B_CURRENT_VERDICT,
            "pilot_has_run": False,
            "cache_write_pilot_review_ready": True,
            "actual_import_readiness": "not_ready_result_review_not_run_and_separate_approval_required",
            "trading_readiness": "not_approved",
            "raw_ohlcv_fields_emitted": False,
        },
        context_summary={
            "v70b_result_review_gate_available": True,
            "current_verdict": V70B_CURRENT_VERDICT,
            "next_task": "actual_import_separation_quarantine_boundary_source_only",
        },
        next_cursor_handoff={
            "handoff_status": "source_only_ready_for_v70c_actual_import_boundary",
            "recommended_next_task": "v70C_actual_import_separation_quarantine_boundary",
            "must_not_execute": (
                "provider live access",
                "cache write",
                "actual refresh/import",
                "raw OHLCV persistence",
                "trading action",
            ),
        },
        safety_flags={
            "source_only": True,
            "provider_live_access_executed": False,
            "live_http_executed": False,
            "tiingo_api_call_executed": False,
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
