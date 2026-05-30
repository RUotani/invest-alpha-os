"""Source-only v65 cross-provider validation result review.

This module records the redacted v65 no-write validation facts and formalizes
the Stooq adjustment policy, provider-pair tolerance policy, and cache-write
readiness gate. It never calls Tiingo, Stooq, Yahoo/yfinance, Polygon, or any
provider; it never writes cache, imports data, persists raw OHLCV, displays
secrets, touches reports-private, or performs trading actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from invis_alpha_os.data.tiingo_live_fetch_result_review import (
    TIINGO_ACTUAL_IMPORT_READINESS_VERDICT,
    TIINGO_CACHE_WRITE_READINESS_VERDICT,
    TIINGO_V63B_PILOT_UNIVERSE,
    TIINGO_V63B_RESULT_VERDICT,
)


V65_RESULT_REVIEW_VERDICT = "warn_manual_review_required"
V65_RECLASSIFIED_VERDICT = "warn_reclassified_as_policy_warning_for_stooq_adjustment_mismatch"
TIINGO_ADJUSTED_SERIES_CONFIDENCE = "medium_high_after_yahoo_agreement"
STOOQ_ADJUSTED_SUITABILITY = "not_suitable_unadjusted_only"
STOOQ_BASE_SUITABILITY = "limited_fallback_or_coverage_check"
NEXT_CACHE_STEP = "signoff_16_and_cache_write_readiness_gate_draft"


class ProviderSeriesType(str, Enum):
    ADJUSTED_SERIES = "adjusted_series"
    BASE_SERIES = "base_series"
    COVERAGE_ONLY = "coverage_only"
    OPTIONAL_PRODUCTION_CHECK = "optional_production_check"


class ProviderComparisonSuitability(str, Enum):
    PRIMARY_ADJUSTED_SANITY_CHECK = "primary_adjusted_series_sanity_check"
    BASE_COVERAGE_FALLBACK_ONLY = "base_close_coverage_fallback_only"
    NOT_ADJUSTED_ORACLE = "not_adjusted_series_oracle"
    OPTIONAL_FUTURE_CHECK = "optional_future_production_quality_check"


@dataclass(frozen=True)
class CrossProviderV65ResultSummary:
    verdict: str
    operation: str
    providers_executed: tuple[str, ...]
    polygon_status: str
    universe: tuple[str, ...]
    date_range: str
    required_providers_available: bool
    required_provider_symbols_success: str
    row_count_per_symbol: int
    row_count_consistent: bool
    date_range_consistent: bool
    tiingo_yahoo_adjusted_close_consistency: str
    stooq_adjusted_comparison_suitability: str
    stooq_base_close_comparison_suitability: str
    tolerance_breaches_total: int
    close_breaches: int
    volume_breaches: int
    adjusted_close_tiingo_yahoo_max_deviation_approx_pct: float
    warning_concentration: str
    likely_root_cause: str
    raw_data_persisted: bool
    cache_write_executed: bool
    actual_import_executed: bool
    manual_import_executed: bool
    trading_action_executed: bool
    secret_displayed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "operation": self.operation,
            "providers_executed": list(self.providers_executed),
            "polygon_status": self.polygon_status,
            "universe": list(self.universe),
            "date_range": self.date_range,
            "required_providers_available": self.required_providers_available,
            "required_provider_symbols_success": self.required_provider_symbols_success,
            "row_count_per_symbol": self.row_count_per_symbol,
            "row_count_consistent": self.row_count_consistent,
            "date_range_consistent": self.date_range_consistent,
            "tiingo_yahoo_adjusted_close_consistency": self.tiingo_yahoo_adjusted_close_consistency,
            "stooq_adjusted_comparison_suitability": self.stooq_adjusted_comparison_suitability,
            "stooq_base_close_comparison_suitability": self.stooq_base_close_comparison_suitability,
            "tolerance_breaches_total": self.tolerance_breaches_total,
            "close_breaches": self.close_breaches,
            "volume_breaches": self.volume_breaches,
            "adjusted_close_tiingo_yahoo_max_deviation_approx_pct": (
                self.adjusted_close_tiingo_yahoo_max_deviation_approx_pct
            ),
            "warning_concentration": self.warning_concentration,
            "likely_root_cause": self.likely_root_cause,
            "raw_data_persisted": self.raw_data_persisted,
            "cache_write_executed": self.cache_write_executed,
            "actual_import_executed": self.actual_import_executed,
            "manual_import_executed": self.manual_import_executed,
            "trading_action_executed": self.trading_action_executed,
            "secret_displayed": self.secret_displayed,
        }


@dataclass(frozen=True)
class CrossProviderProviderPairPolicy:
    pair: str
    role: str
    series_type: ProviderSeriesType
    suitability: ProviderComparisonSuitability
    status_after_v65: str
    policy: str
    cache_import_effect: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair": self.pair,
            "role": self.role,
            "series_type": self.series_type.value,
            "suitability": self.suitability.value,
            "status_after_v65": self.status_after_v65,
            "policy": self.policy,
            "cache_import_effect": self.cache_import_effect,
        }


@dataclass(frozen=True)
class StooqAdjustmentPolicy:
    has_adjusted_close: bool
    adjusted_series_oracle: bool
    base_close_role: str
    coverage_role: str
    fallback_role: str
    split_sensitive_warning_interpretation: str
    disable_adjusted_comparison_unless_adjusted_series_available: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_adjusted_close": self.has_adjusted_close,
            "adjusted_series_oracle": self.adjusted_series_oracle,
            "base_close_role": self.base_close_role,
            "coverage_role": self.coverage_role,
            "fallback_role": self.fallback_role,
            "split_sensitive_warning_interpretation": self.split_sensitive_warning_interpretation,
            "disable_adjusted_comparison_unless_adjusted_series_available": (
                self.disable_adjusted_comparison_unless_adjusted_series_available
            ),
        }


@dataclass(frozen=True)
class ProviderPairToleranceClass:
    tolerance_id: str
    name: str
    providers: tuple[str, ...]
    tolerance: str
    policy: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tolerance_id": self.tolerance_id,
            "name": self.name,
            "providers": list(self.providers),
            "tolerance": self.tolerance,
            "policy": self.policy,
        }


@dataclass(frozen=True)
class ToleranceBreachInterpretation:
    symbol: str
    affected_pairs: tuple[str, ...]
    breach_type: str
    interpretation: str
    treat_as_tiingo_failure_by_default: bool
    requires_manual_review: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "affected_pairs": list(self.affected_pairs),
            "breach_type": self.breach_type,
            "interpretation": self.interpretation,
            "treat_as_tiingo_failure_by_default": self.treat_as_tiingo_failure_by_default,
            "requires_manual_review": self.requires_manual_review,
        }


@dataclass(frozen=True)
class CacheWritePrerequisite:
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
class CacheWriteReadinessAfterValidation:
    live_fetch_provider_viability: str
    cross_provider_validation_result: str
    tiingo_adjusted_series_confidence: str
    cache_write_readiness: str
    actual_import_readiness: str
    cache_write_approved: bool
    actual_import_approved: bool
    prerequisites: tuple[CacheWritePrerequisite, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "live_fetch_provider_viability": self.live_fetch_provider_viability,
            "cross_provider_validation_result": self.cross_provider_validation_result,
            "tiingo_adjusted_series_confidence": self.tiingo_adjusted_series_confidence,
            "cache_write_readiness": self.cache_write_readiness,
            "actual_import_readiness": self.actual_import_readiness,
            "cache_write_approved": self.cache_write_approved,
            "actual_import_approved": self.actual_import_approved,
            "prerequisites": [item.to_dict() for item in self.prerequisites],
        }


@dataclass(frozen=True)
class NextValidationOrCacheApprovalStep:
    recommended_next_step: str
    rationale: str
    approval_phrase_issued: bool
    explicitly_not_approved: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommended_next_step": self.recommended_next_step,
            "rationale": self.rationale,
            "approval_phrase_issued": self.approval_phrase_issued,
            "explicitly_not_approved": list(self.explicitly_not_approved),
        }


@dataclass(frozen=True)
class CrossProviderValidationResultReview:
    report_date: str
    result_summary: CrossProviderV65ResultSummary
    provider_pair_policy: tuple[CrossProviderProviderPairPolicy, ...]
    stooq_adjustment_policy: StooqAdjustmentPolicy
    tolerance_policy_refinement: tuple[ProviderPairToleranceClass, ...]
    breach_interpretations: tuple[ToleranceBreachInterpretation, ...]
    cache_write_readiness: CacheWriteReadinessAfterValidation
    next_step: NextValidationOrCacheApprovalStep
    risk_register: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "result_summary": self.result_summary.to_dict(),
            "provider_pair_policy": [item.to_dict() for item in self.provider_pair_policy],
            "stooq_adjustment_policy": self.stooq_adjustment_policy.to_dict(),
            "tolerance_policy_refinement": [item.to_dict() for item in self.tolerance_policy_refinement],
            "breach_interpretations": [item.to_dict() for item in self.breach_interpretations],
            "cache_write_readiness": self.cache_write_readiness.to_dict(),
            "next_step": self.next_step.to_dict(),
            "risk_register": list(self.risk_register),
        }


def _provider_pair_policy() -> tuple[CrossProviderProviderPairPolicy, ...]:
    return (
        CrossProviderProviderPairPolicy(
            pair="Tiingo vs Yahoo adjusted close",
            role="primary adjusted-series sanity check",
            series_type=ProviderSeriesType.ADJUSTED_SERIES,
            suitability=ProviderComparisonSuitability.PRIMARY_ADJUSTED_SANITY_CHECK,
            status_after_v65="passed_strong_signal",
            policy="Use as the primary adjusted-series comparison until optional Polygon is approved.",
            cache_import_effect="supports Tiingo viability but does not approve cache/import by itself",
        ),
        CrossProviderProviderPairPolicy(
            pair="Tiingo vs Stooq close",
            role="base close / coverage / fallback check only",
            series_type=ProviderSeriesType.BASE_SERIES,
            suitability=ProviderComparisonSuitability.BASE_COVERAGE_FALLBACK_ONLY,
            status_after_v65="warning_due_series_definition_mismatch",
            policy="Do not compare Stooq base close as adjusted close when Stooq adjusted field is absent.",
            cache_import_effect="blocks cache/import only until provider-pair policy is applied and reviewed",
        ),
        CrossProviderProviderPairPolicy(
            pair="Yahoo vs Stooq close",
            role="secondary base close / coverage check only",
            series_type=ProviderSeriesType.BASE_SERIES,
            suitability=ProviderComparisonSuitability.BASE_COVERAGE_FALLBACK_ONLY,
            status_after_v65="warning_expected_for_adjusted_sensitive_symbols",
            policy="Use for coverage/base sanity checks, not adjusted-series adjudication.",
            cache_import_effect="manual review required for split-sensitive warnings",
        ),
        CrossProviderProviderPairPolicy(
            pair="Polygon",
            role="optional future production-quality cross-check",
            series_type=ProviderSeriesType.OPTIONAL_PRODUCTION_CHECK,
            suitability=ProviderComparisonSuitability.OPTIONAL_FUTURE_CHECK,
            status_after_v65="skipped_missing_token",
            policy="Optional and cost-sensitive; not required for immediate v65 no-write review.",
            cache_import_effect="may increase confidence later but is not a current blocker by itself",
        ),
    )


def _tolerance_policy_refinement() -> tuple[ProviderPairToleranceClass, ...]:
    return (
        ProviderPairToleranceClass(
            tolerance_id="ADJ-01",
            name="adjusted_series_tolerance",
            providers=("Tiingo adjusted fields", "Yahoo adjusted fields", "optional Polygon adjusted fields"),
            tolerance="adjusted_close_relative_tolerance=0.5%",
            policy="Applies only when both providers expose explicit adjusted series.",
        ),
        ProviderPairToleranceClass(
            tolerance_id="BASE-01",
            name="base_series_tolerance",
            providers=("Stooq base close", "Tiingo close", "Yahoo regular close"),
            tolerance="close_relative_tolerance=0.5%",
            policy="Split-sensitive breach requires manual review, not automatic provider failure.",
        ),
        ProviderPairToleranceClass(
            tolerance_id="VOL-01",
            name="volume_tolerance",
            providers=("Tiingo", "Stooq", "Yahoo Finance chart API", "optional Polygon"),
            tolerance="volume_relative_tolerance=5%",
            policy="Large split-sensitive deviations require manual review.",
        ),
        ProviderPairToleranceClass(
            tolerance_id="COV-01",
            name="coverage_tolerance",
            providers=("Tiingo", "Stooq", "Yahoo Finance chart API", "optional Polygon"),
            tolerance="row_count_tolerance_days=1; date_range_tolerance_days=1",
            policy="Coverage/date gaps are separate from adjusted-series agreement.",
        ),
    )


def _breach_interpretations() -> tuple[ToleranceBreachInterpretation, ...]:
    return (
        ToleranceBreachInterpretation(
            symbol="NVDA",
            affected_pairs=("Stooq vs Tiingo", "Stooq vs Yahoo"),
            breach_type="large_close_or_volume_deviation",
            interpretation="likely Stooq non-adjusted/base series compared with adjusted or differently adjusted series",
            treat_as_tiingo_failure_by_default=False,
            requires_manual_review=True,
        ),
        ToleranceBreachInterpretation(
            symbol="AVGO",
            affected_pairs=("Stooq vs Tiingo", "Stooq vs Yahoo"),
            breach_type="large_close_or_volume_deviation",
            interpretation="likely Stooq non-adjusted/base series compared with adjusted or differently adjusted series",
            treat_as_tiingo_failure_by_default=False,
            requires_manual_review=True,
        ),
    )


def _cache_prerequisites() -> tuple[CacheWritePrerequisite, ...]:
    return (
        CacheWritePrerequisite("SIGNOFF-16", "cache legal/storage suitability", "unresolved", True),
        CacheWritePrerequisite("CACHE-LOCATION", "private/local cache location design", "not_prepared", True),
        CacheWritePrerequisite("RETENTION-POLICY", "raw/derived retention policy", "not_prepared", True),
        CacheWritePrerequisite("PURGE-ROLLBACK", "purge and rollback policy", "not_prepared", True),
        CacheWritePrerequisite("TERMS-ACK", "terms/cache acknowledgement", "not_signed_off", True),
        CacheWritePrerequisite("CACHE-APPROVAL-PHRASE", "cache write approval phrase", "not_issued", True),
        CacheWritePrerequisite("IMPORT-APPROVAL-PHRASE", "actual import approval phrase", "not_issued", True),
        CacheWritePrerequisite("OPTIONAL-SECOND-PASS", "optional Polygon or second validation pass", "optional", False),
    )


def build_cross_provider_validation_result_review(*, report_date: str) -> CrossProviderValidationResultReview:
    summary = CrossProviderV65ResultSummary(
        verdict=V65_RESULT_REVIEW_VERDICT,
        operation="no_write_cross_provider_data_quality_validation",
        providers_executed=("Tiingo", "Stooq", "Yahoo Finance chart API"),
        polygon_status="skipped_missing_token",
        universe=TIINGO_V63B_PILOT_UNIVERSE,
        date_range="2024-01-01 to 2026-05-29",
        required_providers_available=True,
        required_provider_symbols_success="14/14",
        row_count_per_symbol=604,
        row_count_consistent=True,
        date_range_consistent=True,
        tiingo_yahoo_adjusted_close_consistency="pass",
        stooq_adjusted_comparison_suitability=STOOQ_ADJUSTED_SUITABILITY,
        stooq_base_close_comparison_suitability=STOOQ_BASE_SUITABILITY,
        tolerance_breaches_total=21,
        close_breaches=9,
        volume_breaches=12,
        adjusted_close_tiingo_yahoo_max_deviation_approx_pct=0.009,
        warning_concentration="Stooq vs Tiingo/Yahoo, especially NVDA/AVGO",
        likely_root_cause="Stooq non-adjusted close/base series compared against adjusted or differently adjusted series",
        raw_data_persisted=False,
        cache_write_executed=False,
        actual_import_executed=False,
        manual_import_executed=False,
        trading_action_executed=False,
        secret_displayed=False,
    )
    return CrossProviderValidationResultReview(
        report_date=report_date,
        result_summary=summary,
        provider_pair_policy=_provider_pair_policy(),
        stooq_adjustment_policy=StooqAdjustmentPolicy(
            has_adjusted_close=False,
            adjusted_series_oracle=False,
            base_close_role="base close comparison only after series-definition policy is applied",
            coverage_role="coverage/date/row-count fallback provider",
            fallback_role="free fallback provider, not adjusted-series adjudicator",
            split_sensitive_warning_interpretation="manual review required; do not classify Tiingo failure by default",
            disable_adjusted_comparison_unless_adjusted_series_available=True,
        ),
        tolerance_policy_refinement=_tolerance_policy_refinement(),
        breach_interpretations=_breach_interpretations(),
        cache_write_readiness=CacheWriteReadinessAfterValidation(
            live_fetch_provider_viability=TIINGO_V63B_RESULT_VERDICT,
            cross_provider_validation_result=V65_RECLASSIFIED_VERDICT,
            tiingo_adjusted_series_confidence=TIINGO_ADJUSTED_SERIES_CONFIDENCE,
            cache_write_readiness=TIINGO_CACHE_WRITE_READINESS_VERDICT,
            actual_import_readiness=TIINGO_ACTUAL_IMPORT_READINESS_VERDICT,
            cache_write_approved=False,
            actual_import_approved=False,
            prerequisites=_cache_prerequisites(),
        ),
        next_step=NextValidationOrCacheApprovalStep(
            recommended_next_step=NEXT_CACHE_STEP,
            rationale="Tiingo remains viable as first cache candidate, but cache write requires SIGNOFF-16 and storage policy.",
            approval_phrase_issued=False,
            explicitly_not_approved=(
                "tiingo_api_call",
                "stooq_live_fetch",
                "yahoo_yfinance_live_fetch",
                "polygon_live_fetch",
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
        ),
        risk_register=(
            "v65 warnings can be misread as Tiingo failure if Stooq base series is treated as adjusted oracle.",
            "Stooq remains useful for coverage/fallback checks but not adjusted-series validation without adjusted fields.",
            "Tiingo/Yahoo adjusted agreement is strong but still not cache-write approval.",
            "Cache/database storage remains blocked by legal/storage, retention, purge, and approval prerequisites.",
        ),
    )
