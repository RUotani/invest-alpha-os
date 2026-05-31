"""Source-only cache-write pilot execution runbook and approval packet.

This module prepares the future Cursor/local Tiingo private/local cache-write
pilot approval packet. It is not execution and is not approval by itself. It
never calls providers, writes cache, imports data, reads/persists raw OHLCV,
prints secrets, touches reports-private, or performs trading actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invis_alpha_os.data.cache_path_preflight_approval_package import (
    DEFAULT_CANDIDATE_CACHE_PATH,
    build_cache_path_preflight_approval_package,
)
from invis_alpha_os.data.cache_purge_inventory_dryrun_contract import (
    build_cache_purge_inventory_dryrun_contract,
)
from invis_alpha_os.data.cache_write_readiness_gate import FUTURE_CACHE_WRITE_OPERATION
from invis_alpha_os.data.ohlcv_provider_approval import (
    ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
    CACHE_WRITE_APPROVAL_PHRASE,
)


V70_PACKET_STATUS = "source_only_operator_approval_packet_ready_execution_not_approved"
V70_PACKET_VERDICT = "approval_packet_ready_future_phrase_required"
V70_FIRST_SUBSET = ("SPY", "QQQ", "AAPL", "NVDA")


@dataclass(frozen=True)
class PilotRunbookItem:
    item_id: str
    description: str
    required: bool
    current_status: str
    blocks_execution_if_unmet: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "description": self.description,
            "required": self.required,
            "current_status": self.current_status,
            "blocks_execution_if_unmet": self.blocks_execution_if_unmet,
        }


@dataclass(frozen=True)
class CacheWritePilotApprovalPacket:
    report_date: str
    milestone_version: str
    packet_status: str
    future_pilot_identity: dict[str, Any]
    required_preconditions: tuple[PilotRunbookItem, ...]
    required_operator_fields: tuple[PilotRunbookItem, ...]
    forbidden_operations: tuple[PilotRunbookItem, ...]
    output_constraints: dict[str, Any]
    approval_phrase_boundary: dict[str, Any]
    execution_runbook: tuple[PilotRunbookItem, ...]
    readiness_verdict: dict[str, Any]
    context_summary: dict[str, Any]
    next_cursor_handoff: dict[str, Any]
    safety_flags: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "milestone_version": self.milestone_version,
            "packet_status": self.packet_status,
            "future_pilot_identity": dict(self.future_pilot_identity),
            "required_preconditions": [item.to_dict() for item in self.required_preconditions],
            "required_operator_fields": [item.to_dict() for item in self.required_operator_fields],
            "forbidden_operations": [item.to_dict() for item in self.forbidden_operations],
            "output_constraints": dict(self.output_constraints),
            "approval_phrase_boundary": dict(self.approval_phrase_boundary),
            "execution_runbook": [item.to_dict() for item in self.execution_runbook],
            "readiness_verdict": dict(self.readiness_verdict),
            "context_summary": dict(self.context_summary),
            "next_cursor_handoff": dict(self.next_cursor_handoff),
            "safety_flags": dict(self.safety_flags),
        }


def _item(
    item_id: str,
    description: str,
    *,
    status: str = "required_for_future_runtime",
) -> PilotRunbookItem:
    return PilotRunbookItem(
        item_id=item_id,
        description=description,
        required=True,
        current_status=status,
        blocks_execution_if_unmet=True,
    )


def _required_preconditions() -> tuple[PilotRunbookItem, ...]:
    return (
        _item("PRECONDITION-01", "SIGNOFF-16 completed by human"),
        _item("PRECONDITION-02", "v69 cache path preflight accepted"),
        _item("PRECONDITION-03", "v69B purge/inventory dry-run contract accepted"),
        _item("PRECONDITION-04", "candidate cache path verified private/local, outside source Git and reports-private"),
        _item("PRECONDITION-05", "retention owner and period recorded"),
        _item("PRECONDITION-06", "redacted manifest schema accepted"),
        _item("PRECONDITION-07", "future runtime contains exact cache-write approval phrase"),
    )


def _required_operator_fields() -> tuple[PilotRunbookItem, ...]:
    return (
        _item("OPERATOR-01", "operator name or handle recorded"),
        _item("OPERATOR-02", "runtime timestamp recorded"),
        _item("OPERATOR-03", "candidate cache path recorded without expanding home path in public output"),
        _item("OPERATOR-04", "symbol subset SPY, QQQ, AAPL, NVDA confirmed"),
        _item("OPERATOR-05", "redacted output destination confirmed"),
        _item("OPERATOR-06", "stop conditions acknowledged"),
    )


def _forbidden_operations() -> tuple[PilotRunbookItem, ...]:
    return (
        _item("FORBIDDEN-01", "actual refresh/import"),
        _item("FORBIDDEN-02", "manual actual import"),
        _item("FORBIDDEN-03", "trading action or portfolio action"),
        _item("FORBIDDEN-04", "raw OHLCV in Git"),
        _item("FORBIDDEN-05", "raw OHLCV in reports-private"),
        _item("FORBIDDEN-06", "raw OHLCV in GitHub artifacts"),
        _item("FORBIDDEN-07", "raw OHLCV pasted to ChatGPT/Cursor"),
        _item("FORBIDDEN-08", "raw OHLCV in public outputs"),
        _item("FORBIDDEN-09", "raw API response persistence"),
        _item("FORBIDDEN-10", "broker/manual raw data handling"),
        _item("FORBIDDEN-11", "env/secret display"),
    )


def _execution_runbook() -> tuple[PilotRunbookItem, ...]:
    return (
        _item("RUNBOOK-01", "verify future runtime approval phrase before execution", status="not_issued_in_v70"),
        _item("RUNBOOK-02", "verify private/local cache path at future runtime", status="not_executed_in_v70"),
        _item("RUNBOOK-03", "execute only the approved Tiingo cache-write pilot subset in future runtime", status="not_executed_in_v70"),
        _item("RUNBOOK-04", "emit only redacted summary, metadata, pass/fail, aggregate counts", status="not_executed_in_v70"),
        _item("RUNBOOK-05", "run future result review gate after pilot", status="not_executed_in_v70"),
        _item("RUNBOOK-06", "run future purge/inventory dry-run before destructive cleanup", status="not_executed_in_v70"),
    )


def build_cache_write_pilot_approval_packet(
    *,
    report_date: str,
    candidate_cache_path: str = DEFAULT_CANDIDATE_CACHE_PATH,
) -> CacheWritePilotApprovalPacket:
    preflight = build_cache_path_preflight_approval_package(
        report_date=report_date,
        candidate_cache_path=candidate_cache_path,
    ).to_dict()
    purge_contract = build_cache_purge_inventory_dryrun_contract(
        report_date=report_date,
        candidate_cache_path=candidate_cache_path,
    ).to_dict()
    return CacheWritePilotApprovalPacket(
        report_date=report_date,
        milestone_version="v70",
        packet_status=V70_PACKET_STATUS,
        future_pilot_identity={
            "provider": "Tiingo",
            "operation": FUTURE_CACHE_WRITE_OPERATION,
            "first_subset": list(V70_FIRST_SUBSET),
            "candidate_cache_path": candidate_cache_path,
            "data_type": "EOD OHLCV with adjusted fields if provider returns them",
            "storage": "private/local only, Git-ignored, outside repo and outside reports-private",
            "v69_preflight_verdict": preflight["readiness_verdict"]["preflight_verdict"],
            "v69b_contract_verdict": purge_contract["readiness_verdict"]["contract_verdict"],
        },
        required_preconditions=_required_preconditions(),
        required_operator_fields=_required_operator_fields(),
        forbidden_operations=_forbidden_operations(),
        output_constraints={
            "allowed_outputs": (
                "redacted summary",
                "metadata",
                "pass_fail_only",
                "aggregate counts",
                "redacted manifest without raw rows",
            ),
            "forbidden_outputs": (
                "raw OHLCV",
                "raw API response",
                "raw CSV/JSON",
                "broker/manual raw data",
                "secret values",
            ),
            "reports_private_raw_data_allowed": False,
            "git_tracked_raw_data_allowed": False,
            "chatgpt_cursor_raw_paste_allowed": False,
        },
        approval_phrase_boundary={
            "this_package_approves_cache_write": False,
            "cache_write_approval_phrase_required": True,
            "cache_write_approval_phrase": CACHE_WRITE_APPROVAL_PHRASE,
            "cache_write_approval_phrase_issued": False,
            "future_phrase_scope": "specific cache-write pilot described in future approval context only",
            "actual_import_approval_phrase_required": True,
            "actual_import_approval_phrase": ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
            "actual_import_approval_phrase_issued": False,
            "cache_write_does_not_approve_actual_import": True,
            "cache_write_does_not_approve_trading": True,
            "cache_write_does_not_approve_raw_data_in_git_reports_private_or_chat": True,
        },
        execution_runbook=_execution_runbook(),
        readiness_verdict={
            "packet_verdict": V70_PACKET_VERDICT,
            "cache_write_approval_status": "not_approved",
            "cache_write_execution_status": "not_executed",
            "actual_import_approval_status": "not_approved",
            "actual_import_execution_status": "not_executed",
            "trading_action_status": "not_approved_not_executed",
            "raw_ohlcv_persistence_status": "not_approved_not_executed",
            "provider_live_access_status": "not_approved_not_executed",
            "approval_phrase_issued": False,
        },
        context_summary={
            "v70_approval_packet_available": True,
            "candidate_cache_path": candidate_cache_path,
            "provider": "Tiingo",
            "first_subset": list(V70_FIRST_SUBSET),
            "next_task": "cache_write_pilot_result_review_gate_source_only",
        },
        next_cursor_handoff={
            "handoff_status": "source_only_ready_for_v70b_result_review_gate",
            "recommended_next_task": "v70B_cache_write_pilot_result_review_gate",
            "future_execution_not_approved": True,
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
            "live_http_executed": False,
            "tiingo_api_call_executed": False,
            "stooq_live_fetch_executed": False,
            "yahoo_yfinance_live_fetch_executed": False,
            "polygon_live_fetch_executed": False,
            "provider_live_access_executed": False,
            "cache_write_executed": False,
            "actual_refresh_import_executed": False,
            "manual_actual_import_executed": False,
            "raw_ohlcv_read": False,
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
