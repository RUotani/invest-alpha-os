"""Source-only cache path preflight and pilot approval package.

This module records a candidate private/local cache path and prepares the next
cache-write pilot approval package. It performs deterministic string-level
checks only; it never creates directories, writes cache, reads raw OHLCV, calls
providers, imports data, displays secrets, or performs trading actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invis_alpha_os.data.cache_write_operator_signoff_sheet import (
    V68_OPERATOR_SIGNOFF_STATUS,
    build_cache_write_operator_signoff_sheet,
)
from invis_alpha_os.data.cache_write_readiness_gate import FUTURE_CACHE_WRITE_OPERATION
from invis_alpha_os.data.ohlcv_provider_approval import (
    ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
    CACHE_WRITE_APPROVAL_PHRASE,
)


DEFAULT_CANDIDATE_CACHE_PATH = "$HOME/.local/share/invest-alpha-os/private-cache/tiingo-ohlcv"
V69_PREFLIGHT_VERDICT = "preflight_package_ready_but_execution_not_approved"
V69_PACKAGE_STATUS = "source_only_preflight_ready_execution_not_approved"


@dataclass(frozen=True)
class CachePathStructuralCheck:
    check_id: str
    description: str
    status: str
    blocks_future_cache_write_if_failed: bool
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "description": self.description,
            "status": self.status,
            "blocks_future_cache_write_if_failed": self.blocks_future_cache_write_if_failed,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class CachePathPreflight:
    candidate_cache_path: str
    path_input_source: str
    path_expansion_performed: bool
    filesystem_probe_performed: bool
    directory_created: bool
    path_classification: dict[str, Any]
    structural_checks: tuple[CachePathStructuralCheck, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_cache_path": self.candidate_cache_path,
            "path_input_source": self.path_input_source,
            "path_expansion_performed": self.path_expansion_performed,
            "filesystem_probe_performed": self.filesystem_probe_performed,
            "directory_created": self.directory_created,
            "path_classification": dict(self.path_classification),
            "structural_checks": [item.to_dict() for item in self.structural_checks],
        }


@dataclass(frozen=True)
class CacheWritePilotApprovalPackage:
    package_status: str
    operation_name: str
    provider: str
    symbols: tuple[str, ...]
    candidate_cache_path: str
    cache_write_scope: str
    actual_import_scope: str
    trading_scope: str
    raw_data_handling: dict[str, Any]
    required_operator_confirmations: tuple[str, ...]
    approval_phrase_boundary: dict[str, Any]
    stop_conditions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_status": self.package_status,
            "operation_name": self.operation_name,
            "provider": self.provider,
            "symbols": list(self.symbols),
            "candidate_cache_path": self.candidate_cache_path,
            "cache_write_scope": self.cache_write_scope,
            "actual_import_scope": self.actual_import_scope,
            "trading_scope": self.trading_scope,
            "raw_data_handling": dict(self.raw_data_handling),
            "required_operator_confirmations": list(self.required_operator_confirmations),
            "approval_phrase_boundary": dict(self.approval_phrase_boundary),
            "stop_conditions": list(self.stop_conditions),
        }


@dataclass(frozen=True)
class CachePathPreflightApprovalPackage:
    report_date: str
    milestone_version: str
    package_status: str
    signoff16_status: str
    cache_path_preflight: CachePathPreflight
    pilot_approval_package: CacheWritePilotApprovalPackage
    readiness_verdict: dict[str, Any]
    context_summary: dict[str, Any]
    next_cursor_handoff: dict[str, Any]
    safety_flags: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "milestone_version": self.milestone_version,
            "package_status": self.package_status,
            "signoff16_status": self.signoff16_status,
            "cache_path_preflight": self.cache_path_preflight.to_dict(),
            "pilot_approval_package": self.pilot_approval_package.to_dict(),
            "readiness_verdict": dict(self.readiness_verdict),
            "context_summary": dict(self.context_summary),
            "next_cursor_handoff": dict(self.next_cursor_handoff),
            "safety_flags": dict(self.safety_flags),
        }


def _classify_candidate_path(candidate_cache_path: str) -> dict[str, Any]:
    stripped = candidate_cache_path.strip()
    uses_home_variable = stripped.startswith("$HOME/")
    uses_absolute_home = stripped.startswith("~/")
    contains_private_cache_segment = "/private-cache/" in stripped
    provider_scoped = stripped.endswith("/tiingo-ohlcv")
    under_local_share = stripped.startswith("$HOME/.local/share/") or stripped.startswith("~/.local/share/")
    appears_inside_source_git = stripped.startswith("./") or stripped.startswith("src/") or stripped.startswith("data/")
    appears_inside_reports_private = "reports-private" in stripped
    return {
        "candidate_cache_path_present": bool(stripped),
        "uses_home_variable_or_tilde": uses_home_variable or uses_absolute_home,
        "under_local_share": under_local_share,
        "contains_private_cache_segment": contains_private_cache_segment,
        "provider_scoped_tiingo_ohlcv": provider_scoped,
        "appears_inside_source_git": appears_inside_source_git,
        "appears_inside_reports_private": appears_inside_reports_private,
        "structurally_local_or_private": (uses_home_variable or uses_absolute_home) and contains_private_cache_segment,
        "gitignore_requirement": "future_runtime_verify_or_not_applicable_outside_source_git",
        "path_expansion_policy": "do_not_expand_or_print_real_home_in_source_only_report",
    }


def _check(status: bool, check_id: str, description: str, evidence: str) -> CachePathStructuralCheck:
    return CachePathStructuralCheck(
        check_id=check_id,
        description=description,
        status="pass" if status else "fail",
        blocks_future_cache_write_if_failed=True,
        evidence=evidence,
    )


def _build_preflight(candidate_cache_path: str) -> CachePathPreflight:
    classification = _classify_candidate_path(candidate_cache_path)
    checks = (
        _check(
            classification["candidate_cache_path_present"],
            "PATH-01",
            "candidate cache path is recorded",
            candidate_cache_path or "missing",
        ),
        _check(
            classification["uses_home_variable_or_tilde"],
            "PATH-02",
            "candidate path is user-local, not repository-relative",
            "starts with $HOME/ or ~/ without expansion",
        ),
        _check(
            classification["under_local_share"],
            "PATH-03",
            "candidate path is under a private local application data area",
            "$HOME/.local/share or ~/.local/share prefix",
        ),
        _check(
            classification["contains_private_cache_segment"],
            "PATH-04",
            "candidate path includes private-cache segment",
            "private-cache path segment",
        ),
        _check(
            not classification["appears_inside_source_git"],
            "PATH-05",
            "candidate path does not appear inside source Git",
            "string-level repository-relative path check",
        ),
        _check(
            not classification["appears_inside_reports_private"],
            "PATH-06",
            "candidate path does not appear inside reports-private",
            "string-level reports-private path check",
        ),
        _check(
            classification["provider_scoped_tiingo_ohlcv"],
            "PATH-07",
            "candidate path is provider/scope specific",
            "tiingo-ohlcv suffix",
        ),
    )
    return CachePathPreflight(
        candidate_cache_path=candidate_cache_path,
        path_input_source="operator_supplied_candidate_path",
        path_expansion_performed=False,
        filesystem_probe_performed=False,
        directory_created=False,
        path_classification=classification,
        structural_checks=checks,
    )


def build_cache_path_preflight_approval_package(
    *,
    report_date: str,
    candidate_cache_path: str = DEFAULT_CANDIDATE_CACHE_PATH,
) -> CachePathPreflightApprovalPackage:
    signoff = build_cache_write_operator_signoff_sheet(report_date=report_date).to_dict()
    preflight = _build_preflight(candidate_cache_path)
    all_structural_checks_pass = all(item.status == "pass" for item in preflight.structural_checks)
    return CachePathPreflightApprovalPackage(
        report_date=report_date,
        milestone_version="v69",
        package_status=V69_PACKAGE_STATUS,
        signoff16_status=signoff["readiness_verdict"]["operator_signoff_status"],
        cache_path_preflight=preflight,
        pilot_approval_package=CacheWritePilotApprovalPackage(
            package_status="draft_ready_for_future_human_cache_write_approval_not_execution",
            operation_name=FUTURE_CACHE_WRITE_OPERATION,
            provider="Tiingo",
            symbols=("SPY", "QQQ", "AAPL", "NVDA"),
            candidate_cache_path=candidate_cache_path,
            cache_write_scope="future private/local cache pilot only; not approved in v69",
            actual_import_scope="not approved",
            trading_scope="not approved",
            raw_data_handling={
                "raw_ohlcv_expected_in_future_pilot": True,
                "raw_ohlcv_persisted_in_v69": False,
                "raw_api_response_persisted_in_v69": False,
                "git_tracked_raw_data_allowed": False,
                "reports_private_raw_data_allowed": False,
                "redacted_summary_only_allowed": True,
            },
            required_operator_confirmations=(
                "SIGNOFF-16 human review completed",
                "candidate cache path approved by operator",
                "cache path Git-ignore or outside-source status verified at future runtime",
                "retention owner and period recorded",
                "purge dry-run and rollback process accepted",
                "post-purge verification checklist accepted",
                "cache-write approval phrase issued in a separate future runtime context",
            ),
            approval_phrase_boundary={
                "cache_write_approval_phrase_required": True,
                "cache_write_approval_phrase": CACHE_WRITE_APPROVAL_PHRASE,
                "cache_write_approval_phrase_issued": False,
                "actual_import_approval_phrase_required": True,
                "actual_import_approval_phrase": ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
                "actual_import_approval_phrase_issued": False,
                "placeholder_phrase_is_not_runtime_approval": True,
            },
            stop_conditions=(
                "provider live access would be required",
                "cache write would be executed",
                "actual refresh/import would be executed",
                "raw OHLCV would be written to Git or reports-private",
                "env secret would be displayed",
                "trading action would be requested",
            ),
        ),
        readiness_verdict={
            "preflight_verdict": V69_PREFLIGHT_VERDICT if all_structural_checks_pass else "preflight_failed",
            "all_structural_checks_pass": all_structural_checks_pass,
            "cache_write_approval_status": "not_approved",
            "cache_write_execution_status": "not_executed",
            "actual_import_approval_status": "not_approved",
            "actual_import_execution_status": "not_executed",
            "provider_live_access_status": "not_approved_not_executed",
            "raw_ohlcv_persistence_status": "not_approved_not_executed",
            "approval_phrase_issued": False,
            "signoff16_status": V68_OPERATOR_SIGNOFF_STATUS,
        },
        context_summary={
            "v69_preflight_package_available": True,
            "candidate_cache_path": candidate_cache_path,
            "candidate_path_structurally_private_local": preflight.path_classification["structurally_local_or_private"],
            "cache_write_remains_not_approved": True,
            "actual_import_remains_not_approved": True,
            "next_task": "cache_purge_inventory_dryrun_contract_or_future_human_approval_review",
        },
        next_cursor_handoff={
            "handoff_status": "source_only_ready_for_v69b_or_future_human_review",
            "recommended_next_source_only_task": "cache_purge_inventory_dryrun_contract_and_redacted_manifest_schema",
            "future_execution_task": "cursor_local_tiingo_private_cache_write_pilot_after_explicit_approval",
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
            "git_tracked_raw_data_written": False,
            "filesystem_probe_performed": False,
            "directory_created": False,
        },
    )
