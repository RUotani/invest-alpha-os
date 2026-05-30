"""Source-only Tiingo manual signoff review sheet and evidence ledger.

This module converts the v52 Tiingo current-docs recheck pack into an auditable
operator ledger. It never performs live HTTP, calls Tiingo APIs, accesses live
providers, writes caches, imports data, displays secrets, handles raw data, or
performs trading actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from invis_alpha_os.data.tiingo_current_docs_recheck import (
    build_tiingo_current_docs_recheck_pack,
)


TIINGO_MANUAL_SIGNOFF_VERDICT = "manual_signoff_incomplete_live_fetch_not_approved"

REQUIRED_TIINGO_SIGNOFF_SECTIONS: tuple[str, ...] = (
    "pricing_plan",
    "subscription_entitlement",
    "terms_of_use",
    "redistribution_attribution",
    "api_limits_request_limits",
    "unique_symbol_universe_limits",
    "eod_historical_ohlcv_endpoint",
    "adjusted_price_methodology",
    "split_handling",
    "dividend_handling",
    "corporate_actions",
    "etf_coverage",
    "adr_coverage",
    "mutual_fund_coverage",
    "delisted_coverage",
    "cache_suitability_local_storage",
    "pilot_universe_compatibility",
    "pilot_date_range_compatibility",
    "python_implementation_path",
    "secret_handling",
    "redaction_handling",
    "no_write_discipline",
    "rollback_cleanup_expectations",
    "verification_criteria",
)


class TiingoManualReviewStatus(str, Enum):
    UNREVIEWED = "unreviewed"
    REVIEWED_PASS = "reviewed_pass"
    REVIEWED_FAIL = "reviewed_fail"
    NEEDS_ESCALATION = "needs_escalation"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class TiingoManualSignoffItem:
    item_id: str
    section: str
    question: str
    why_it_matters: str
    official_source_reference: str
    required_evidence: str
    operator_answer_placeholder: str
    operator_signoff_status: TiingoManualReviewStatus
    blocking_if_unanswered: bool
    blocks_live_fetch: bool
    blocks_cache_write: bool
    blocks_actual_import: bool
    requires_secret_or_token: bool
    source_accessed_live: bool
    api_called: bool
    cache_written: bool
    actual_import_executed: bool
    trading_action_executed: bool
    needs_manual_current_recheck: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "section": self.section,
            "question": self.question,
            "why_it_matters": self.why_it_matters,
            "official_source_reference": self.official_source_reference,
            "required_evidence": self.required_evidence,
            "operator_answer_placeholder": self.operator_answer_placeholder,
            "operator_signoff_status": self.operator_signoff_status.value,
            "blocking_if_unanswered": self.blocking_if_unanswered,
            "blocks_live_fetch": self.blocks_live_fetch,
            "blocks_cache_write": self.blocks_cache_write,
            "blocks_actual_import": self.blocks_actual_import,
            "requires_secret_or_token": self.requires_secret_or_token,
            "source_accessed_live": self.source_accessed_live,
            "api_called": self.api_called,
            "cache_written": self.cache_written,
            "actual_import_executed": self.actual_import_executed,
            "trading_action_executed": self.trading_action_executed,
            "needs_manual_current_recheck": self.needs_manual_current_recheck,
        }


@dataclass(frozen=True)
class TiingoManualSignoffSafety:
    source_only: bool
    live_http_executed: bool
    tiingo_api_called: bool
    provider_live_access_executed: bool
    public_ohlcv_source_live_fetch_executed: bool
    cache_write_executed: bool
    actual_refresh_import_executed: bool
    manual_actual_import_executed: bool
    env_secret_displayed: bool
    broker_manual_raw_data_handled: bool
    workflow_dependency_pyproject_changed: bool
    reports_private_touched: bool
    trading_action_executed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_only": self.source_only,
            "live_http_executed": self.live_http_executed,
            "tiingo_api_called": self.tiingo_api_called,
            "provider_live_access_executed": self.provider_live_access_executed,
            "public_ohlcv_source_live_fetch_executed": self.public_ohlcv_source_live_fetch_executed,
            "cache_write_executed": self.cache_write_executed,
            "actual_refresh_import_executed": self.actual_refresh_import_executed,
            "manual_actual_import_executed": self.manual_actual_import_executed,
            "env_secret_displayed": self.env_secret_displayed,
            "broker_manual_raw_data_handled": self.broker_manual_raw_data_handled,
            "workflow_dependency_pyproject_changed": self.workflow_dependency_pyproject_changed,
            "reports_private_touched": self.reports_private_touched,
            "trading_action_executed": self.trading_action_executed,
        }


@dataclass(frozen=True)
class TiingoApprovalEvidenceSummary:
    total_items: int
    unreviewed_items: int
    blocking_live_fetch_items: int
    blocking_cache_write_items: int
    blocking_actual_import_items: int
    default_status: TiingoManualReviewStatus
    live_fetch_approved: bool
    cache_write_approved: bool
    actual_import_approved: bool
    primary_blocker: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_items": self.total_items,
            "unreviewed_items": self.unreviewed_items,
            "blocking_live_fetch_items": self.blocking_live_fetch_items,
            "blocking_cache_write_items": self.blocking_cache_write_items,
            "blocking_actual_import_items": self.blocking_actual_import_items,
            "default_status": self.default_status.value,
            "live_fetch_approved": self.live_fetch_approved,
            "cache_write_approved": self.cache_write_approved,
            "actual_import_approved": self.actual_import_approved,
            "primary_blocker": self.primary_blocker,
        }


@dataclass(frozen=True)
class TiingoManualSignoffLedger:
    report_date: str
    provider: str
    scenario: str
    pilot_universe: tuple[str, ...]
    pilot_date_range: str
    signoff_items: tuple[TiingoManualSignoffItem, ...]
    evidence_summary: TiingoApprovalEvidenceSummary
    safety: TiingoManualSignoffSafety
    explicitly_not_approved: tuple[str, ...]
    final_verdict: str
    next_human_action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "provider": self.provider,
            "scenario": self.scenario,
            "pilot_universe": list(self.pilot_universe),
            "pilot_date_range": self.pilot_date_range,
            "signoff_items": [item.to_dict() for item in self.signoff_items],
            "evidence_summary": self.evidence_summary.to_dict(),
            "safety": self.safety.to_dict(),
            "explicitly_not_approved": list(self.explicitly_not_approved),
            "final_verdict": self.final_verdict,
            "next_human_action": self.next_human_action,
        }


def _signoff_item(
    *,
    idx: int,
    section: str,
    question: str,
    why_it_matters: str,
    official_source_reference: str,
    required_evidence: str,
    blocks_live_fetch: bool = True,
    blocks_cache_write: bool = False,
    blocks_actual_import: bool = False,
    requires_secret_or_token: bool = False,
) -> TiingoManualSignoffItem:
    return TiingoManualSignoffItem(
        item_id=f"TIINGO-SIGNOFF-{idx:02d}",
        section=section,
        question=question,
        why_it_matters=why_it_matters,
        official_source_reference=official_source_reference,
        required_evidence=required_evidence,
        operator_answer_placeholder="[operator to fill]",
        operator_signoff_status=TiingoManualReviewStatus.UNREVIEWED,
        blocking_if_unanswered=True,
        blocks_live_fetch=blocks_live_fetch,
        blocks_cache_write=blocks_cache_write,
        blocks_actual_import=blocks_actual_import,
        requires_secret_or_token=requires_secret_or_token,
        source_accessed_live=False,
        api_called=False,
        cache_written=False,
        actual_import_executed=False,
        trading_action_executed=False,
        needs_manual_current_recheck=True,
    )


def default_tiingo_manual_signoff_items() -> tuple[TiingoManualSignoffItem, ...]:
    rows = (
        ("pricing_plan", "Confirm current Tiingo plan price and plan tier.", "Pricing affects pilot feasibility and recurring cost.", "Tiingo pricing page", "current price, billing cadence, trial constraints"),
        ("subscription_entitlement", "Confirm selected plan permits historical EOD access for pilot symbols.", "Entitlement gaps can make pilot results misleading.", "Tiingo pricing / account entitlement docs", "plan entitlement notes"),
        ("terms_of_use", "Confirm current terms permit a redacted live-fetch-only pilot.", "Terms violations can block any provider use.", "Tiingo Terms of Use", "terms excerpt or operator summary"),
        ("redistribution_attribution", "Confirm redistribution and attribution obligations for pilot outputs.", "Outputs may need attribution or may not be redistributable.", "Tiingo Terms of Use", "attribution and redistribution notes"),
        ("api_limits_request_limits", "Confirm request limits for the pilot date range.", "Rate limits can block a 14-symbol pilot.", "Tiingo API docs / Terms of Use", "per-minute, per-day, retry, and burst limits"),
        ("unique_symbol_universe_limits", "Confirm unique symbol or universe limits.", "Symbol limits can silently constrain the pilot universe.", "Tiingo API docs / pricing", "unique symbol limits and plan caps"),
        ("eod_historical_ohlcv_endpoint", "Confirm EOD historical OHLCV endpoint covers the pilot.", "Wrong endpoint or missing history blocks the pilot.", "Tiingo EOD docs", "endpoint name, fields, date range support"),
        ("adjusted_price_methodology", "Confirm adjusted close or adjusted OHLC methodology.", "Adjustment mismatch changes signal validation.", "Tiingo EOD docs", "adjusted field names and methodology summary"),
        ("split_handling", "Confirm split handling around split-sensitive symbols.", "Splits can distort raw and adjusted prices.", "Tiingo split docs", "split endpoint or field behavior"),
        ("dividend_handling", "Confirm dividend handling in adjusted fields.", "Dividend treatment affects total-return interpretation.", "Tiingo dividend docs", "dividend endpoint or adjustment behavior"),
        ("corporate_actions", "Confirm broader corporate action availability.", "Corporate actions affect long historical validation.", "Tiingo corporate action docs", "supported corporate action types"),
        ("etf_coverage", "Confirm SPY and QQQ ETF support.", "ETF coverage is required for pilot regime checks.", "Tiingo EOD docs", "ETF support evidence for SPY and QQQ"),
        ("adr_coverage", "Confirm ADR coverage and symbol caveats.", "ADR support affects future universe expansion.", "Tiingo EOD docs", "ADR coverage and mapping notes"),
        ("mutual_fund_coverage", "Confirm mutual fund coverage or declare out of scope.", "Coverage claims should not bleed into pilot assumptions.", "Tiingo EOD docs", "mutual fund support or exclusion note"),
        ("delisted_coverage", "Confirm delisted coverage or explicitly do not assume it.", "Survivorship bias matters for later production evaluation.", "Tiingo EOD docs / pricing", "delisted support status"),
        ("cache_suitability_local_storage", "Confirm whether local cache/internal storage is permitted.", "Cache write remains blocked until terms allow it.", "Tiingo Terms of Use", "cache/storage permission summary"),
        ("pilot_universe_compatibility", "Confirm all 14 pilot symbols are valid Tiingo symbols.", "Symbol mapping errors can invalidate pilot output.", "v49 pilot universe + Tiingo docs", "symbol compatibility notes"),
        ("pilot_date_range_compatibility", "Confirm date range 2024-01-01 to future latest completed trading day is supported.", "Date gaps can masquerade as provider failures.", "Tiingo EOD docs", "date range support notes"),
        ("python_implementation_path", "Confirm future implementation can use existing project patterns.", "New dependencies or workflow changes are not approved.", "project implementation policy", "implementation path without pyproject/workflow changes"),
        ("secret_handling", "Confirm future task will use secrets without displaying values.", "Secret leakage is a hard stop.", "project redaction policy", "secret handling procedure"),
        ("redaction_handling", "Confirm future outputs are redacted shape digests only.", "Raw provider payloads must not be committed.", "project redaction policy", "redaction checklist"),
        ("no_write_discipline", "Confirm future pilot cannot write cache/import artifacts.", "No-write discipline separates fetch validation from state changes.", "v49 approval bundle", "no-write checklist"),
        ("rollback_cleanup_expectations", "Confirm rollback expectations for a live-fetch-only pilot.", "Unexpected writes must be detectable and stoppable.", "v49 approval bundle", "rollback/no-write expectation"),
        ("verification_criteria", "Confirm success/failure criteria before live fetch.", "Undefined verification can convert a failed pilot into ambiguous output.", "v49 approval bundle", "verification criteria summary"),
    )
    cache_write_sections = {"cache_suitability_local_storage", "no_write_discipline", "rollback_cleanup_expectations"}
    actual_import_sections = {"cache_suitability_local_storage", "no_write_discipline", "verification_criteria"}
    secret_sections = {"secret_handling"}
    return tuple(
        _signoff_item(
            idx=idx,
            section=section,
            question=question,
            why_it_matters=why_it_matters,
            official_source_reference=reference,
            required_evidence=evidence,
            blocks_cache_write=section in cache_write_sections,
            blocks_actual_import=section in actual_import_sections,
            requires_secret_or_token=section in secret_sections,
        )
        for idx, (section, question, why_it_matters, reference, evidence) in enumerate(rows, start=1)
    )


def build_tiingo_manual_signoff_ledger(*, report_date: str) -> TiingoManualSignoffLedger:
    recheck = build_tiingo_current_docs_recheck_pack(report_date=report_date)
    items = default_tiingo_manual_signoff_items()
    live_blockers = sum(1 for item in items if item.blocks_live_fetch)
    cache_blockers = sum(1 for item in items if item.blocks_cache_write)
    import_blockers = sum(1 for item in items if item.blocks_actual_import)
    return TiingoManualSignoffLedger(
        report_date=report_date,
        provider=recheck.provider,
        scenario=recheck.scenario,
        pilot_universe=recheck.pilot_universe,
        pilot_date_range=recheck.pilot_date_range,
        signoff_items=items,
        evidence_summary=TiingoApprovalEvidenceSummary(
            total_items=len(items),
            unreviewed_items=len(items),
            blocking_live_fetch_items=live_blockers,
            blocking_cache_write_items=cache_blockers,
            blocking_actual_import_items=import_blockers,
            default_status=TiingoManualReviewStatus.UNREVIEWED,
            live_fetch_approved=False,
            cache_write_approved=False,
            actual_import_approved=False,
            primary_blocker="manual_signoff_incomplete",
        ),
        safety=TiingoManualSignoffSafety(
            source_only=True,
            live_http_executed=False,
            tiingo_api_called=False,
            provider_live_access_executed=False,
            public_ohlcv_source_live_fetch_executed=False,
            cache_write_executed=False,
            actual_refresh_import_executed=False,
            manual_actual_import_executed=False,
            env_secret_displayed=False,
            broker_manual_raw_data_handled=False,
            workflow_dependency_pyproject_changed=False,
            reports_private_touched=False,
            trading_action_executed=False,
        ),
        explicitly_not_approved=(
            "tiingo_api_call",
            "provider_live_access",
            "public_ohlcv_source_live_fetch",
            "cache_write",
            "actual_refresh_import",
            "manual_actual_import",
            "env_secret_display",
            "broker_manual_raw_data",
            "workflow_dependency_pyproject_change",
            "reports_private_change",
            "trading_action",
        ),
        final_verdict=TIINGO_MANUAL_SIGNOFF_VERDICT,
        next_human_action="human_operator_fills_signoff_fields_and_attaches_current_doc_evidence",
    )
