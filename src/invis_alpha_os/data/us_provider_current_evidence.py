"""Source-only current evidence pack for US OHLCV provider candidates.

This module records seed-only evidence gaps for provider selection. It never
performs live HTTP, provider access, cache writes, imports, secret inspection,
or trading actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invis_alpha_os.data.ohlcv_provider_approval import (
    ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
    CACHE_WRITE_APPROVAL_PHRASE,
)
from invis_alpha_os.data.ohlcv_provider_registry import PUBLIC_OHLCV_APPROVAL_PHRASE


REQUIRED_CURRENT_EVIDENCE_DIMENSIONS: tuple[str, ...] = (
    "current_pricing_terms",
    "cache_suitability",
    "adjusted_price_method",
    "adr_delisted_coverage",
    "bulk_throughput",
)

US_PROVIDER_CURRENT_EVIDENCE_PROVIDERS: tuple[str, ...] = (
    "Tiingo",
    "Polygon.io",
    "Stooq",
    "Alpha Vantage",
    "EODHD",
    "Yahoo Finance / yfinance",
)


@dataclass(frozen=True)
class UsProviderCurrentEvidenceItem:
    provider: str
    current_pricing_terms: str
    cache_suitability: str
    adjusted_price_method: str
    adr_delisted_coverage: str
    bulk_throughput: str
    recommended_role: str
    needs_current_recheck: bool
    evidence_confidence: str
    source_accessed_live: bool
    pilot_readiness: str
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "current_pricing_terms": self.current_pricing_terms,
            "cache_suitability": self.cache_suitability,
            "adjusted_price_method": self.adjusted_price_method,
            "adr_delisted_coverage": self.adr_delisted_coverage,
            "bulk_throughput": self.bulk_throughput,
            "recommended_role": self.recommended_role,
            "needs_current_recheck": self.needs_current_recheck,
            "evidence_confidence": self.evidence_confidence,
            "source_accessed_live": self.source_accessed_live,
            "pilot_readiness": self.pilot_readiness,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class UsProviderCurrentEvidenceSafety:
    source_only: bool
    live_http_executed: bool
    provider_live_access_executed: bool
    cache_write_executed: bool
    actual_refresh_import_executed: bool
    env_secret_displayed: bool
    broker_manual_raw_data_handled: bool
    reports_private_touched: bool
    workflow_dependency_pyproject_changed: bool
    trading_action_executed: bool
    hard_gates_required_for_live_testing: tuple[str, ...]
    explicitly_not_approved: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_only": self.source_only,
            "live_http_executed": self.live_http_executed,
            "provider_live_access_executed": self.provider_live_access_executed,
            "cache_write_executed": self.cache_write_executed,
            "actual_refresh_import_executed": self.actual_refresh_import_executed,
            "env_secret_displayed": self.env_secret_displayed,
            "broker_manual_raw_data_handled": self.broker_manual_raw_data_handled,
            "reports_private_touched": self.reports_private_touched,
            "workflow_dependency_pyproject_changed": self.workflow_dependency_pyproject_changed,
            "trading_action_executed": self.trading_action_executed,
            "hard_gates_required_for_live_testing": list(self.hard_gates_required_for_live_testing),
            "explicitly_not_approved": list(self.explicitly_not_approved),
        }


@dataclass(frozen=True)
class UsProviderCurrentEvidencePack:
    report_date: str
    evidence_date: str
    providers: tuple[UsProviderCurrentEvidenceItem, ...]
    evidence_dimensions: tuple[str, ...]
    current_v46_recommendation: dict[str, str]
    evidence_gaps: tuple[str, ...]
    recommended_first_pilot_recheck: tuple[str, ...]
    safety: UsProviderCurrentEvidenceSafety
    next_approval_request_draft: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "evidence_date": self.evidence_date,
            "providers": [provider.to_dict() for provider in self.providers],
            "evidence_dimensions": list(self.evidence_dimensions),
            "current_v46_recommendation": self.current_v46_recommendation,
            "evidence_gaps": list(self.evidence_gaps),
            "recommended_first_pilot_recheck": list(self.recommended_first_pilot_recheck),
            "safety": self.safety.to_dict(),
            "next_approval_request_draft": list(self.next_approval_request_draft),
        }


def default_us_provider_current_evidence_items() -> tuple[UsProviderCurrentEvidenceItem, ...]:
    seed_confidence = "seed_only / manual_recheck_required"
    return (
        UsProviderCurrentEvidenceItem(
            provider="Tiingo",
            current_pricing_terms="paid_low_candidate_but_current_plan_price_and_usage_terms_unverified",
            cache_suitability="terms_cache_storage_review_required_before_any_cache_write",
            adjusted_price_method="adjusted_daily_data_candidate_but_method_requires_current_doc_and_pilot_recheck",
            adr_delisted_coverage="adr_and_delisted_coverage_unknown_needs_manual_recheck",
            bulk_throughput="medium_to_high_candidate_if_plan_allows_but_throughput_unverified",
            recommended_role="first_pilot_candidate_not_approved",
            needs_current_recheck=True,
            evidence_confidence=seed_confidence,
            source_accessed_live=False,
            pilot_readiness="best_first_recheck_candidate_after_manual_current_evidence_review",
            notes="Keeps v46 first-pilot role, but does not approve live access, cache write, or import.",
        ),
        UsProviderCurrentEvidenceItem(
            provider="Polygon.io",
            current_pricing_terms="paid_high_candidate_with_plan_dependent_cost_terms_unverified",
            cache_suitability="terms_cache_storage_review_required_before_any_cache_write",
            adjusted_price_method="corporate_action_and_adjustment_candidate_but_method_requires_current_doc_and_pilot_recheck",
            adr_delisted_coverage="adr_and_delisted_coverage_possible_but_plan_dependent_needs_manual_recheck",
            bulk_throughput="high_candidate_if_plan_allows_but_throughput_and_rate_limits_unverified",
            recommended_role="production_candidate_not_approved",
            needs_current_recheck=True,
            evidence_confidence=seed_confidence,
            source_accessed_live=False,
            pilot_readiness="production_recheck_candidate_after_cost_terms_review",
            notes="Keeps v46 production-candidate role; cost, plan, and cache terms remain blocking evidence.",
        ),
        UsProviderCurrentEvidenceItem(
            provider="Stooq",
            current_pricing_terms="free_fallback_candidate_but_current_terms_unverified",
            cache_suitability="cache_terms_unclear_and_must_not_be_assumed_for_production_storage",
            adjusted_price_method="adjustment_policy_unclear_requires_manual_current_recheck",
            adr_delisted_coverage="adr_and_delisted_coverage_not_assumed",
            bulk_throughput="fallback_small_batch_or_manual_style_only_not_primary_bulk",
            recommended_role="free_fallback_not_primary",
            needs_current_recheck=True,
            evidence_confidence=seed_confidence,
            source_accessed_live=False,
            pilot_readiness="fallback_recheck_only_not_primary_pilot",
            notes="Useful fallback, but unclear adjustment and cache terms block primary production selection.",
        ),
        UsProviderCurrentEvidenceItem(
            provider="Alpha Vantage",
            current_pricing_terms="free_limited_or_paid_candidate_but_current_limits_and_terms_unverified",
            cache_suitability="terms_cache_storage_review_required_before_any_cache_write",
            adjusted_price_method="adjusted_daily_endpoint_candidate_but_method_requires_current_doc_and_pilot_recheck",
            adr_delisted_coverage="adr_and_delisted_coverage_unknown_needs_manual_recheck",
            bulk_throughput="likely_limited_by_rate_limits_for_broad_screening",
            recommended_role="secondary_candidate_not_primary",
            needs_current_recheck=True,
            evidence_confidence=seed_confidence,
            source_accessed_live=False,
            pilot_readiness="secondary_recheck_after_tiingo_polygon_stooq",
            notes="Rate limits are a likely blocker for broad screening unless current plan evidence disproves it.",
        ),
        UsProviderCurrentEvidenceItem(
            provider="EODHD",
            current_pricing_terms="paid_mid_candidate_but_current_plan_price_and_terms_unverified",
            cache_suitability="terms_cache_storage_review_required_before_any_cache_write",
            adjusted_price_method="adjusted_and_corporate_action_candidate_but_method_requires_current_doc_and_pilot_recheck",
            adr_delisted_coverage="adr_and_delisted_coverage_possible_but_plan_dependent_needs_manual_recheck",
            bulk_throughput="medium_to_high_candidate_if_plan_allows_but_throughput_unverified",
            recommended_role="secondary_paid_candidate_not_approved",
            needs_current_recheck=True,
            evidence_confidence=seed_confidence,
            source_accessed_live=False,
            pilot_readiness="secondary_paid_recheck_after_first_pilot_candidate",
            notes="Potentially relevant paid source, but not ahead of Tiingo/Polygon without current evidence.",
        ),
        UsProviderCurrentEvidenceItem(
            provider="Yahoo Finance / yfinance",
            current_pricing_terms="free_unofficial_research_candidate_but_current_terms_unverified",
            cache_suitability="cache_terms_and_unofficial_stability_not_suitable_for_assumed_production_storage",
            adjusted_price_method="library_style_adjusted_data_available_but_method_requires_current_validation",
            adr_delisted_coverage="adr_possible_but_delisted_coverage_not_assumed",
            bulk_throughput="risky_for_production_bulk_due_unofficial_access_and_stability",
            recommended_role="research_fallback_not_production",
            needs_current_recheck=True,
            evidence_confidence=seed_confidence,
            source_accessed_live=False,
            pilot_readiness="research_only_recheck_not_production_candidate",
            notes="Convenient library path, but unofficial access and terms risk block production recommendation.",
        ),
    )


def build_us_provider_current_evidence_pack(*, report_date: str) -> UsProviderCurrentEvidencePack:
    safety = UsProviderCurrentEvidenceSafety(
        source_only=True,
        live_http_executed=False,
        provider_live_access_executed=False,
        cache_write_executed=False,
        actual_refresh_import_executed=False,
        env_secret_displayed=False,
        broker_manual_raw_data_handled=False,
        reports_private_touched=False,
        workflow_dependency_pyproject_changed=False,
        trading_action_executed=False,
        hard_gates_required_for_live_testing=(
            PUBLIC_OHLCV_APPROVAL_PHRASE,
            CACHE_WRITE_APPROVAL_PHRASE,
            ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
        ),
        explicitly_not_approved=(
            "live_http",
            "provider_live_access",
            "cache_write",
            "actual_refresh_import",
            "manual_import",
            "env_secret_display",
            "broker_manual_raw_data",
            "reports_private_change",
            "workflow_dependency_pyproject_change",
            "trading_action",
        ),
    )
    return UsProviderCurrentEvidencePack(
        report_date=report_date,
        evidence_date=report_date,
        providers=default_us_provider_current_evidence_items(),
        evidence_dimensions=REQUIRED_CURRENT_EVIDENCE_DIMENSIONS,
        current_v46_recommendation={
            "first_pilot_candidate": "Tiingo",
            "production_candidate": "Polygon.io",
            "free_fallback": "Stooq",
            "provider_selected": "false",
            "live_testing_approved": "false",
        },
        evidence_gaps=(
            "current_pricing_terms",
            "cache_suitability",
            "adjusted_price_method",
            "adr_delisted_coverage",
            "bulk_throughput",
        ),
        recommended_first_pilot_recheck=(
            "Manually recheck Tiingo current pricing, plan limits, data redistribution/cache terms, adjusted price method, ADR/delisted coverage, and bulk/rate-limit suitability.",
            "If Tiingo terms or coverage fail, manually recheck Polygon.io as production-style candidate before any live test.",
            "Keep Stooq as fallback evidence only; do not promote it to primary without adjustment and cache-term proof.",
        ),
        safety=safety,
        next_approval_request_draft=(
            "Request manual current documentation review for Tiingo, Polygon.io, and Stooq.",
            "After manual review, request a separate public_ohlcv small pilot approval if evidence is acceptable.",
            "Exclude cache write and actual import from the first live pilot approval.",
        ),
    )
