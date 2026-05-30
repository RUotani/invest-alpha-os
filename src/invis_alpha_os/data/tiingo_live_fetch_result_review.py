"""Source-only Tiingo v63B live-fetch result review.

This module records the redacted v63B pilot result as source-side evidence and
prepares the next no-write data-quality validation plan. It never calls Tiingo
or any other OHLCV provider, writes cache, imports market data, stores raw
provider payloads, displays secrets, or performs trading actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invis_alpha_os.data.ohlcv_provider_registry import PUBLIC_OHLCV_APPROVAL_PHRASE


TIINGO_V63B_PILOT_UNIVERSE: tuple[str, ...] = (
    "AAPL",
    "MSFT",
    "NVDA",
    "AMD",
    "AVGO",
    "TSLA",
    "GOOGL",
    "AMZN",
    "META",
    "JPM",
    "XOM",
    "UNH",
    "SPY",
    "QQQ",
)

TIINGO_V63B_RESULT_VERDICT = "v63b_live_fetch_only_pilot_passed"
TIINGO_CACHE_WRITE_READINESS_VERDICT = "not_ready_cache_write_requires_signoff_16_and_data_quality_validation"
TIINGO_ACTUAL_IMPORT_READINESS_VERDICT = "not_ready_actual_import_requires_cache_write_readiness_first"
TIINGO_NEXT_EXECUTION_TASK = "no_write_cross_provider_data_quality_validation_pilot"

TIINGO_V63B_BASE_FIELDS: tuple[str, ...] = ("date", "open", "high", "low", "close", "volume")
TIINGO_V63B_ADJUSTED_FIELDS: tuple[str, ...] = (
    "adjOpen",
    "adjHigh",
    "adjLow",
    "adjClose",
    "adjVolume",
)


@dataclass(frozen=True)
class TiingoPilotSymbolSummary:
    symbol: str
    status: str
    row_count: int
    base_fields_present: bool
    adjusted_fields_present: bool
    error_class: str | None
    raw_data_persisted: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "status": self.status,
            "row_count": self.row_count,
            "base_fields_present": self.base_fields_present,
            "adjusted_fields_present": self.adjusted_fields_present,
            "error_class": self.error_class,
            "raw_data_persisted": self.raw_data_persisted,
        }


@dataclass(frozen=True)
class TiingoPilotFieldSummary:
    base_fields: tuple[str, ...]
    adjusted_fields: tuple[str, ...]
    base_fields_all_present: bool
    adjusted_fields_all_present: bool
    raw_price_accuracy_proven: bool
    adjusted_calculation_correctness_proven: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_fields": list(self.base_fields),
            "adjusted_fields": list(self.adjusted_fields),
            "base_fields_all_present": self.base_fields_all_present,
            "adjusted_fields_all_present": self.adjusted_fields_all_present,
            "raw_price_accuracy_proven": self.raw_price_accuracy_proven,
            "adjusted_calculation_correctness_proven": self.adjusted_calculation_correctness_proven,
        }


@dataclass(frozen=True)
class TiingoPilotSafetySummary:
    source_only: bool
    live_http_executed_by_this_pack: bool
    tiingo_api_called_by_this_pack: bool
    provider_live_access_executed_by_this_pack: bool
    public_ohlcv_source_live_fetch_executed_by_this_pack: bool
    stooq_yahoo_polygon_live_fetch_executed_by_this_pack: bool
    raw_data_persisted: bool
    reports_private_raw_data_written: bool
    cache_write_executed: bool
    actual_import_executed: bool
    manual_actual_import_executed: bool
    env_secret_displayed: bool
    broker_manual_raw_data_handled: bool
    workflow_dependency_pyproject_changed: bool
    reports_private_touched: bool
    trading_action_executed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_only": self.source_only,
            "live_http_executed_by_this_pack": self.live_http_executed_by_this_pack,
            "tiingo_api_called_by_this_pack": self.tiingo_api_called_by_this_pack,
            "provider_live_access_executed_by_this_pack": self.provider_live_access_executed_by_this_pack,
            "public_ohlcv_source_live_fetch_executed_by_this_pack": (
                self.public_ohlcv_source_live_fetch_executed_by_this_pack
            ),
            "stooq_yahoo_polygon_live_fetch_executed_by_this_pack": (
                self.stooq_yahoo_polygon_live_fetch_executed_by_this_pack
            ),
            "raw_data_persisted": self.raw_data_persisted,
            "reports_private_raw_data_written": self.reports_private_raw_data_written,
            "cache_write_executed": self.cache_write_executed,
            "actual_import_executed": self.actual_import_executed,
            "manual_actual_import_executed": self.manual_actual_import_executed,
            "env_secret_displayed": self.env_secret_displayed,
            "broker_manual_raw_data_handled": self.broker_manual_raw_data_handled,
            "workflow_dependency_pyproject_changed": self.workflow_dependency_pyproject_changed,
            "reports_private_touched": self.reports_private_touched,
            "trading_action_executed": self.trading_action_executed,
        }


@dataclass(frozen=True)
class TiingoLiveFetchPilotResult:
    provider: str
    scenario: str
    operation: str
    result_status: str
    date_range: str
    symbols_total: int
    symbols_success: int
    symbols_failed: int
    row_count_per_symbol: int
    provider_request_count: int
    provider_total_seconds_approx: float
    provider_avg_ms_per_request_approx: int
    field_summary: TiingoPilotFieldSummary
    symbol_summaries: tuple[TiingoPilotSymbolSummary, ...]
    safety: TiingoPilotSafetySummary

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "scenario": self.scenario,
            "operation": self.operation,
            "result_status": self.result_status,
            "date_range": self.date_range,
            "symbols_total": self.symbols_total,
            "symbols_success": self.symbols_success,
            "symbols_failed": self.symbols_failed,
            "row_count_per_symbol": self.row_count_per_symbol,
            "provider_request_count": self.provider_request_count,
            "provider_total_seconds_approx": self.provider_total_seconds_approx,
            "provider_avg_ms_per_request_approx": self.provider_avg_ms_per_request_approx,
            "field_summary": self.field_summary.to_dict(),
            "symbol_summaries": [row.to_dict() for row in self.symbol_summaries],
            "safety": self.safety.to_dict(),
        }


@dataclass(frozen=True)
class TiingoResultReviewVerdict:
    live_fetch_provider_viability: str
    data_quality_validation_readiness: str
    cache_write_readiness: str
    actual_import_readiness: str
    what_was_proven: tuple[str, ...]
    what_was_not_proven: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "live_fetch_provider_viability": self.live_fetch_provider_viability,
            "data_quality_validation_readiness": self.data_quality_validation_readiness,
            "cache_write_readiness": self.cache_write_readiness,
            "actual_import_readiness": self.actual_import_readiness,
            "what_was_proven": list(self.what_was_proven),
            "what_was_not_proven": list(self.what_was_not_proven),
        }


@dataclass(frozen=True)
class CrossProviderValidationCheck:
    check_id: str
    category: str
    providers: tuple[str, ...]
    universe_slice: tuple[str, ...]
    description: str
    tolerance_policy: str
    raw_data_persistence_allowed: bool
    cache_write_approved: bool
    actual_import_approved: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "category": self.category,
            "providers": list(self.providers),
            "universe_slice": list(self.universe_slice),
            "description": self.description,
            "tolerance_policy": self.tolerance_policy,
            "raw_data_persistence_allowed": self.raw_data_persistence_allowed,
            "cache_write_approved": self.cache_write_approved,
            "actual_import_approved": self.actual_import_approved,
        }


@dataclass(frozen=True)
class TiingoDataQualityValidationPlan:
    package_status: str
    operation: str
    providers: tuple[str, ...]
    universe: tuple[str, ...]
    date_range: str
    required_approval_phrase: str
    checks: tuple[CrossProviderValidationCheck, ...]
    expected_redacted_output: tuple[str, ...]
    raw_data_persistence_allowed: bool
    cache_write_approved: bool
    actual_import_approved: bool
    trading_action_approved: bool
    next_recommended_execution: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_status": self.package_status,
            "operation": self.operation,
            "providers": list(self.providers),
            "universe": list(self.universe),
            "date_range": self.date_range,
            "required_approval_phrase": self.required_approval_phrase,
            "checks": [check.to_dict() for check in self.checks],
            "expected_redacted_output": list(self.expected_redacted_output),
            "raw_data_persistence_allowed": self.raw_data_persistence_allowed,
            "cache_write_approved": self.cache_write_approved,
            "actual_import_approved": self.actual_import_approved,
            "trading_action_approved": self.trading_action_approved,
            "next_recommended_execution": self.next_recommended_execution,
        }


@dataclass(frozen=True)
class CacheWriteApprovalPrerequisite:
    prerequisite_id: str
    description: str
    status: str
    blocks_cache_write: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "prerequisite_id": self.prerequisite_id,
            "description": self.description,
            "status": self.status,
            "blocks_cache_write": self.blocks_cache_write,
        }


@dataclass(frozen=True)
class CacheWriteReadinessAssessment:
    cache_write_readiness: str
    actual_import_readiness: str
    cache_write_approved: bool
    actual_import_approved: bool
    prerequisites: tuple[CacheWriteApprovalPrerequisite, ...]
    next_approval_package_needed: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "cache_write_readiness": self.cache_write_readiness,
            "actual_import_readiness": self.actual_import_readiness,
            "cache_write_approved": self.cache_write_approved,
            "actual_import_approved": self.actual_import_approved,
            "prerequisites": [item.to_dict() for item in self.prerequisites],
            "next_approval_package_needed": self.next_approval_package_needed,
        }


@dataclass(frozen=True)
class TiingoNextStepRecommendation:
    recommended_task: str
    approval_phrase_required: str
    stop_conditions: tuple[str, ...]
    explicitly_not_approved: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommended_task": self.recommended_task,
            "approval_phrase_required": self.approval_phrase_required,
            "stop_conditions": list(self.stop_conditions),
            "explicitly_not_approved": list(self.explicitly_not_approved),
        }


@dataclass(frozen=True)
class TiingoLiveFetchResultReviewPack:
    report_date: str
    pilot_result: TiingoLiveFetchPilotResult
    verdict: TiingoResultReviewVerdict
    data_quality_validation_plan: TiingoDataQualityValidationPlan
    cache_write_readiness_assessment: CacheWriteReadinessAssessment
    next_step: TiingoNextStepRecommendation
    risk_register: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "pilot_result": self.pilot_result.to_dict(),
            "verdict": self.verdict.to_dict(),
            "data_quality_validation_plan": self.data_quality_validation_plan.to_dict(),
            "cache_write_readiness_assessment": self.cache_write_readiness_assessment.to_dict(),
            "next_step": self.next_step.to_dict(),
            "risk_register": list(self.risk_register),
        }


def _symbol_summaries() -> tuple[TiingoPilotSymbolSummary, ...]:
    return tuple(
        TiingoPilotSymbolSummary(
            symbol=symbol,
            status="success",
            row_count=604,
            base_fields_present=True,
            adjusted_fields_present=True,
            error_class=None,
            raw_data_persisted=False,
        )
        for symbol in TIINGO_V63B_PILOT_UNIVERSE
    )


def _validation_checks() -> tuple[CrossProviderValidationCheck, ...]:
    providers = ("Tiingo", "Stooq", "Yahoo Finance/yfinance")
    return (
        CrossProviderValidationCheck(
            check_id="DQ-01",
            category="close_adjusted_close_comparison",
            providers=providers,
            universe_slice=TIINGO_V63B_PILOT_UNIVERSE,
            description="Compare close and adjusted close across providers with redacted aggregate deviations only.",
            tolerance_policy="define_before_execution; percentage/absolute tolerances and split-date exceptions required",
            raw_data_persistence_allowed=False,
            cache_write_approved=False,
            actual_import_approved=False,
        ),
        CrossProviderValidationCheck(
            check_id="DQ-02",
            category="row_count_date_coverage_missing_trading_days",
            providers=providers,
            universe_slice=TIINGO_V63B_PILOT_UNIVERSE,
            description="Compare row counts, start/end dates, and missing trading days without saving provider rows.",
            tolerance_policy="calendar-aligned differences must be summarized by count and reason class",
            raw_data_persistence_allowed=False,
            cache_write_approved=False,
            actual_import_approved=False,
        ),
        CrossProviderValidationCheck(
            check_id="DQ-03",
            category="volume_comparison",
            providers=providers,
            universe_slice=TIINGO_V63B_PILOT_UNIVERSE,
            description="Compare volume scale and obvious anomalies across providers.",
            tolerance_policy="large relative deviations require provider-specific explanation before cache approval",
            raw_data_persistence_allowed=False,
            cache_write_approved=False,
            actual_import_approved=False,
        ),
        CrossProviderValidationCheck(
            check_id="DQ-04",
            category="split_sensitive_adjustment_sample",
            providers=providers,
            universe_slice=("NVDA", "TSLA", "AMD"),
            description="Check split-sensitive symbols for adjusted-field continuity and discontinuity warnings.",
            tolerance_policy="split windows require explicit exception handling and redacted evidence summary",
            raw_data_persistence_allowed=False,
            cache_write_approved=False,
            actual_import_approved=False,
        ),
        CrossProviderValidationCheck(
            check_id="DQ-05",
            category="etf_sample_comparison",
            providers=providers,
            universe_slice=("SPY", "QQQ"),
            description="Validate ETF coverage and adjusted-field availability for pilot ETF symbols.",
            tolerance_policy="ETF adjusted fields must be present or gap-classified before cache readiness",
            raw_data_persistence_allowed=False,
            cache_write_approved=False,
            actual_import_approved=False,
        ),
        CrossProviderValidationCheck(
            check_id="DQ-06",
            category="optional_polygon_comparison",
            providers=("Tiingo", "Polygon"),
            universe_slice=TIINGO_V63B_PILOT_UNIVERSE,
            description="Optional comparison if Polygon access is approved in a future no-write task.",
            tolerance_policy="optional provider; absence does not block Tiingo-vs-free-provider validation",
            raw_data_persistence_allowed=False,
            cache_write_approved=False,
            actual_import_approved=False,
        ),
    )


def build_tiingo_live_fetch_result_review_pack(*, report_date: str) -> TiingoLiveFetchResultReviewPack:
    field_summary = TiingoPilotFieldSummary(
        base_fields=TIINGO_V63B_BASE_FIELDS,
        adjusted_fields=TIINGO_V63B_ADJUSTED_FIELDS,
        base_fields_all_present=True,
        adjusted_fields_all_present=True,
        raw_price_accuracy_proven=False,
        adjusted_calculation_correctness_proven=False,
    )
    safety = TiingoPilotSafetySummary(
        source_only=True,
        live_http_executed_by_this_pack=False,
        tiingo_api_called_by_this_pack=False,
        provider_live_access_executed_by_this_pack=False,
        public_ohlcv_source_live_fetch_executed_by_this_pack=False,
        stooq_yahoo_polygon_live_fetch_executed_by_this_pack=False,
        raw_data_persisted=False,
        reports_private_raw_data_written=False,
        cache_write_executed=False,
        actual_import_executed=False,
        manual_actual_import_executed=False,
        env_secret_displayed=False,
        broker_manual_raw_data_handled=False,
        workflow_dependency_pyproject_changed=False,
        reports_private_touched=False,
        trading_action_executed=False,
    )
    pilot_result = TiingoLiveFetchPilotResult(
        provider="Tiingo",
        scenario="public_ohlcv",
        operation="live_fetch_only",
        result_status="pass",
        date_range="2024-01-01 to 2026-05-29",
        symbols_total=len(TIINGO_V63B_PILOT_UNIVERSE),
        symbols_success=len(TIINGO_V63B_PILOT_UNIVERSE),
        symbols_failed=0,
        row_count_per_symbol=604,
        provider_request_count=14,
        provider_total_seconds_approx=14.6,
        provider_avg_ms_per_request_approx=1046,
        field_summary=field_summary,
        symbol_summaries=_symbol_summaries(),
        safety=safety,
    )
    what_was_proven = (
        "Tiingo live-fetch-only pilot reached all 14 approved pilot symbols during v63B.",
        "Each symbol produced 604 rows for the approved pilot date range.",
        "Base fields date/open/high/low/close/volume were present for all symbols.",
        "Adjusted fields adjOpen/adjHigh/adjLow/adjClose/adjVolume were present for all symbols.",
        "v63B preserved no-write/no-import/no-trading discipline and did not persist raw provider payloads.",
    )
    what_was_not_proven = (
        "raw price accuracy not proven",
        "adjusted field calculation correctness not proven",
        "cross-provider consistency not proven",
        "split/dividend adjustment quality not proven",
        "long history completeness not proven",
        "delisted coverage not proven",
        "rate limit stability not proven",
        "cache/database legal suitability not resolved",
    )
    validation_plan = TiingoDataQualityValidationPlan(
        package_status="draft_only_not_approved",
        operation=TIINGO_NEXT_EXECUTION_TASK,
        providers=("Tiingo", "Stooq", "Yahoo Finance/yfinance", "optional Polygon"),
        universe=TIINGO_V63B_PILOT_UNIVERSE,
        date_range="2024-01-01 to latest completed trading day at future execution",
        required_approval_phrase=PUBLIC_OHLCV_APPROVAL_PHRASE,
        checks=_validation_checks(),
        expected_redacted_output=(
            "per-symbol success/failure counts",
            "per-check pass/warn/fail counts",
            "aggregate deviation buckets",
            "missing-date counts",
            "adjusted-field availability summary",
            "no raw OHLCV rows or API responses",
        ),
        raw_data_persistence_allowed=False,
        cache_write_approved=False,
        actual_import_approved=False,
        trading_action_approved=False,
        next_recommended_execution=TIINGO_NEXT_EXECUTION_TASK,
    )
    cache_prerequisites = (
        CacheWriteApprovalPrerequisite(
            prerequisite_id="SIGNOFF-16",
            description="cache legal/storage suitability for Tiingo local/internal storage",
            status="unresolved",
            blocks_cache_write=True,
        ),
        CacheWriteApprovalPrerequisite(
            prerequisite_id="CACHE-LOCATION-DESIGN",
            description="approved cache/database location and ownership design",
            status="not_prepared",
            blocks_cache_write=True,
        ),
        CacheWriteApprovalPrerequisite(
            prerequisite_id="RAW-RETENTION-POLICY",
            description="raw data retention, redaction, and no-commit policy",
            status="not_prepared",
            blocks_cache_write=True,
        ),
        CacheWriteApprovalPrerequisite(
            prerequisite_id="PURGE-ROLLBACK-POLICY",
            description="purge and rollback procedure for any future cache write pilot",
            status="not_prepared",
            blocks_cache_write=True,
        ),
        CacheWriteApprovalPrerequisite(
            prerequisite_id="TERMS-COMPLIANCE-ACK",
            description="human acknowledgement that storage terms are satisfied",
            status="not_signed_off",
            blocks_cache_write=True,
        ),
        CacheWriteApprovalPrerequisite(
            prerequisite_id="DATA-QUALITY-VALIDATION",
            description="no-write cross-provider data-quality validation completed and reviewed",
            status="not_completed",
            blocks_cache_write=True,
        ),
    )
    return TiingoLiveFetchResultReviewPack(
        report_date=report_date,
        pilot_result=pilot_result,
        verdict=TiingoResultReviewVerdict(
            live_fetch_provider_viability=TIINGO_V63B_RESULT_VERDICT,
            data_quality_validation_readiness="ready_to_prepare_no_write_cross_provider_validation_task",
            cache_write_readiness=TIINGO_CACHE_WRITE_READINESS_VERDICT,
            actual_import_readiness=TIINGO_ACTUAL_IMPORT_READINESS_VERDICT,
            what_was_proven=what_was_proven,
            what_was_not_proven=what_was_not_proven,
        ),
        data_quality_validation_plan=validation_plan,
        cache_write_readiness_assessment=CacheWriteReadinessAssessment(
            cache_write_readiness=TIINGO_CACHE_WRITE_READINESS_VERDICT,
            actual_import_readiness=TIINGO_ACTUAL_IMPORT_READINESS_VERDICT,
            cache_write_approved=False,
            actual_import_approved=False,
            prerequisites=cache_prerequisites,
            next_approval_package_needed="cross_provider_no_write_validation_approval_draft_then_cache_write_readiness_package",
        ),
        next_step=TiingoNextStepRecommendation(
            recommended_task=TIINGO_NEXT_EXECUTION_TASK,
            approval_phrase_required=PUBLIC_OHLCV_APPROVAL_PHRASE,
            stop_conditions=(
                "any provider live access without explicit approval",
                "any attempt to persist raw OHLCV rows or API responses",
                "any cache write or actual import request",
                "any secret value display",
            ),
            explicitly_not_approved=(
                "tiingo_api_call_by_this_pack",
                "stooq_yahoo_polygon_live_fetch_by_this_pack",
                "cache_write",
                "actual_refresh_import",
                "manual_actual_import",
                "env_secret_display",
                "broker_manual_raw_data",
                "workflow_dependency_pyproject_change",
                "reports_private_change",
                "trading_action",
            ),
        ),
        risk_register=(
            "v63B proves fetch viability, not price correctness.",
            "Adjusted fields were present, but provider methodology remains unvalidated against peers.",
            "Cache/database storage is still blocked by SIGNOFF-16 and explicit storage policy.",
            "Future validation can compare providers only after a separate no-write live-fetch approval.",
        ),
    )
