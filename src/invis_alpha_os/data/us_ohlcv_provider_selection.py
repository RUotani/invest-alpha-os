"""Source-only US OHLCV provider selection matrix and pilot design.

This module compares provider candidates for future US OHLCV validation. It
does not perform live HTTP, fetch provider data, write caches, import data,
read secrets, or inspect broker/manual raw data.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from invis_alpha_os.data.ohlcv_provider_approval import (
    ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
    CACHE_WRITE_APPROVAL_PHRASE,
)
from invis_alpha_os.data.ohlcv_provider_registry import PUBLIC_OHLCV_APPROVAL_PHRASE


class UsProviderCostTier(str, Enum):
    FREE = "free"
    FREE_LIMITED = "free_limited"
    PAID_LOW = "paid_low"
    PAID_MID = "paid_mid"
    PAID_HIGH = "paid_high"
    REQUIRES_CURRENT_PRICE_CHECK = "requires_current_price_check"


REQUIRED_US_PROVIDER_DIMENSIONS: tuple[str, ...] = (
    "us_stock_coverage",
    "etf_coverage",
    "adr_coverage",
    "delisted_coverage",
    "historical_depth",
    "daily_ohlcv_availability",
    "adjusted_close_or_adjusted_ohlc_support",
    "split_dividend_corporate_action_support",
    "bulk_suitability",
    "rate_limit_risk",
    "api_stability",
    "python_implementation_effort",
    "terms_cache_suitability_review_needed",
    "cost_tier",
    "fit_for_pilot",
    "fit_for_production",
    "fit_for_fallback",
)

DEFAULT_US_PILOT_UNIVERSE: tuple[str, ...] = (
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


@dataclass(frozen=True)
class UsOhlcvProviderCandidate:
    provider: str
    cost_tier: UsProviderCostTier
    us_stock_coverage: str
    etf_coverage: str
    adr_coverage: str
    delisted_coverage: str
    historical_depth: str
    daily_ohlcv_availability: str
    adjusted_close_or_adjusted_ohlc_support: str
    split_dividend_corporate_action_support: str
    bulk_suitability: str
    rate_limit_risk: str
    api_stability: str
    python_implementation_effort: str
    terms_cache_suitability_review_needed: bool
    fit_for_pilot: str
    fit_for_production: str
    fit_for_fallback: str
    evidence_status: str
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "cost_tier": self.cost_tier.value,
            "us_stock_coverage": self.us_stock_coverage,
            "etf_coverage": self.etf_coverage,
            "adr_coverage": self.adr_coverage,
            "delisted_coverage": self.delisted_coverage,
            "historical_depth": self.historical_depth,
            "daily_ohlcv_availability": self.daily_ohlcv_availability,
            "adjusted_close_or_adjusted_ohlc_support": self.adjusted_close_or_adjusted_ohlc_support,
            "split_dividend_corporate_action_support": self.split_dividend_corporate_action_support,
            "bulk_suitability": self.bulk_suitability,
            "rate_limit_risk": self.rate_limit_risk,
            "api_stability": self.api_stability,
            "python_implementation_effort": self.python_implementation_effort,
            "terms_cache_suitability_review_needed": self.terms_cache_suitability_review_needed,
            "fit_for_pilot": self.fit_for_pilot,
            "fit_for_production": self.fit_for_production,
            "fit_for_fallback": self.fit_for_fallback,
            "evidence_status": self.evidence_status,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class UsOhlcvProviderRanking:
    best_first_pilot_provider: str
    best_production_candidate: str
    best_low_cost_candidate: str
    best_free_fallback: str
    provider_requiring_further_research: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "best_first_pilot_provider": self.best_first_pilot_provider,
            "best_production_candidate": self.best_production_candidate,
            "best_low_cost_candidate": self.best_low_cost_candidate,
            "best_free_fallback": self.best_free_fallback,
            "provider_requiring_further_research": list(self.provider_requiring_further_research),
        }


@dataclass(frozen=True)
class UsOhlcvPilotDesign:
    pilot_universe: tuple[str, ...]
    pilot_date_range: str
    provider_candidates_to_test: tuple[str, ...]
    success_criteria: tuple[str, ...]
    failure_criteria: tuple[str, ...]
    data_quality_checks: tuple[str, ...]
    adjustment_checks: tuple[str, ...]
    volume_checks: tuple[str, ...]
    symbol_mapping_checks: tuple[str, ...]
    rate_limit_checks: tuple[str, ...]
    cache_write_approved: bool
    actual_import_approved: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "pilot_universe": list(self.pilot_universe),
            "pilot_date_range": self.pilot_date_range,
            "provider_candidates_to_test": list(self.provider_candidates_to_test),
            "success_criteria": list(self.success_criteria),
            "failure_criteria": list(self.failure_criteria),
            "data_quality_checks": list(self.data_quality_checks),
            "adjustment_checks": list(self.adjustment_checks),
            "volume_checks": list(self.volume_checks),
            "symbol_mapping_checks": list(self.symbol_mapping_checks),
            "rate_limit_checks": list(self.rate_limit_checks),
            "cache_write_approved": self.cache_write_approved,
            "actual_import_approved": self.actual_import_approved,
        }


@dataclass(frozen=True)
class UsOhlcvSelectionSafety:
    source_only: bool
    live_http_executed: bool
    public_ohlcv_source_live_fetch_executed: bool
    cache_write_executed: bool
    actual_refresh_import_executed: bool
    env_secret_displayed: bool
    broker_manual_raw_data_handled: bool
    reports_private_touched: bool
    trading_action_executed: bool
    hard_gates_required_for_live_test: tuple[str, ...]
    explicitly_not_approved: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_only": self.source_only,
            "live_http_executed": self.live_http_executed,
            "public_ohlcv_source_live_fetch_executed": self.public_ohlcv_source_live_fetch_executed,
            "cache_write_executed": self.cache_write_executed,
            "actual_refresh_import_executed": self.actual_refresh_import_executed,
            "env_secret_displayed": self.env_secret_displayed,
            "broker_manual_raw_data_handled": self.broker_manual_raw_data_handled,
            "reports_private_touched": self.reports_private_touched,
            "trading_action_executed": self.trading_action_executed,
            "hard_gates_required_for_live_test": list(self.hard_gates_required_for_live_test),
            "explicitly_not_approved": list(self.explicitly_not_approved),
        }


@dataclass(frozen=True)
class UsOhlcvProviderSelectionMatrix:
    report_date: str
    providers: tuple[UsOhlcvProviderCandidate, ...]
    evaluation_dimensions: tuple[str, ...]
    ranking: UsOhlcvProviderRanking
    pilot_design: UsOhlcvPilotDesign
    safety: UsOhlcvSelectionSafety
    missing_evidence: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "providers": [provider.to_dict() for provider in self.providers],
            "evaluation_dimensions": list(self.evaluation_dimensions),
            "ranking": self.ranking.to_dict(),
            "pilot_design": self.pilot_design.to_dict(),
            "safety": self.safety.to_dict(),
            "missing_evidence": list(self.missing_evidence),
        }


def default_us_ohlcv_provider_candidates() -> tuple[UsOhlcvProviderCandidate, ...]:
    return (
        UsOhlcvProviderCandidate(
            provider="Stooq",
            cost_tier=UsProviderCostTier.FREE,
            us_stock_coverage="partial_us_large_cap_and_etf",
            etf_coverage="available_for_common_etfs_needs_validation",
            adr_coverage="unknown_needs_validation",
            delisted_coverage="not_assumed",
            historical_depth="good_for_many_symbols_needs_symbol_level_validation",
            daily_ohlcv_availability="yes_needs_live_shape_validation",
            adjusted_close_or_adjusted_ohlc_support="unclear_adjustment_policy_review_needed",
            split_dividend_corporate_action_support="not_assumed",
            bulk_suitability="manual_or_small_batch_fallback",
            rate_limit_risk="low_to_medium_unknown",
            api_stability="unofficial_or_file_endpoint_style_review_needed",
            python_implementation_effort="low",
            terms_cache_suitability_review_needed=True,
            fit_for_pilot="medium",
            fit_for_production="low_until_adjustment_terms_validated",
            fit_for_fallback="high_for_free_research_fallback",
            evidence_status="source_only_assumption_from_existing_registry",
            notes="Good first free fallback candidate, but adjustment and cache terms must be checked before production.",
        ),
        UsOhlcvProviderCandidate(
            provider="Alpha Vantage",
            cost_tier=UsProviderCostTier.FREE_LIMITED,
            us_stock_coverage="broad_us_common_stock_claim_needs_validation",
            etf_coverage="likely_common_etfs_needs_validation",
            adr_coverage="unknown_needs_validation",
            delisted_coverage="not_assumed",
            historical_depth="daily_history_available_needs_depth_validation",
            daily_ohlcv_availability="yes_needs_live_shape_validation",
            adjusted_close_or_adjusted_ohlc_support="adjusted_daily_endpoint_likely_needs_current_doc_review",
            split_dividend_corporate_action_support="possible_adjusted_series_needs_validation",
            bulk_suitability="limited_by_rate_limits",
            rate_limit_risk="high_for_broad_screening",
            api_stability="moderate_needs_current_doc_review",
            python_implementation_effort="low",
            terms_cache_suitability_review_needed=True,
            fit_for_pilot="medium",
            fit_for_production="low_to_medium_if_paid_limits_fit",
            fit_for_fallback="medium",
            evidence_status="requires_current_doc_and_limit_check",
            notes="Useful API-style pilot candidate, but free-tier rate limits are likely unsuitable for broad coverage.",
        ),
        UsOhlcvProviderCandidate(
            provider="Yahoo Finance / yfinance",
            cost_tier=UsProviderCostTier.FREE_LIMITED,
            us_stock_coverage="broad_but_unofficial_needs_validation",
            etf_coverage="broad_but_unofficial_needs_validation",
            adr_coverage="possible_needs_validation",
            delisted_coverage="not_assumed",
            historical_depth="good_for_many_symbols_needs_validation",
            daily_ohlcv_availability="yes_needs_live_shape_validation",
            adjusted_close_or_adjusted_ohlc_support="available_in_library_style_needs_validation",
            split_dividend_corporate_action_support="available_in_library_style_needs_validation",
            bulk_suitability="risky_for_production_bulk",
            rate_limit_risk="medium_to_high_unofficial",
            api_stability="unofficial_breakage_risk",
            python_implementation_effort="low",
            terms_cache_suitability_review_needed=True,
            fit_for_pilot="medium",
            fit_for_production="low_without_terms_and_stability_acceptance",
            fit_for_fallback="medium_research_only",
            evidence_status="existing_dependency_but_not_selected",
            notes="Convenient for research, but unofficial stability and cache terms block production selection.",
        ),
        UsOhlcvProviderCandidate(
            provider="Polygon.io",
            cost_tier=UsProviderCostTier.PAID_HIGH,
            us_stock_coverage="broad_candidate_needs_plan_check",
            etf_coverage="broad_candidate_needs_plan_check",
            adr_coverage="likely_candidate_needs_validation",
            delisted_coverage="possible_plan_dependent_needs_check",
            historical_depth="strong_candidate_plan_dependent",
            daily_ohlcv_availability="yes_needs_live_shape_validation",
            adjusted_close_or_adjusted_ohlc_support="corporate_action_support_candidate_needs_validation",
            split_dividend_corporate_action_support="strong_candidate_needs_validation",
            bulk_suitability="high_if_plan_allows",
            rate_limit_risk="plan_dependent",
            api_stability="high_candidate",
            python_implementation_effort="medium",
            terms_cache_suitability_review_needed=True,
            fit_for_pilot="high",
            fit_for_production="high_if_cost_and_terms_accepted",
            fit_for_fallback="low_due_cost",
            evidence_status="requires_current_plan_terms_price_check",
            notes="Best production-style candidate for broad US coverage if cost and terms are acceptable.",
        ),
        UsOhlcvProviderCandidate(
            provider="Tiingo",
            cost_tier=UsProviderCostTier.PAID_LOW,
            us_stock_coverage="broad_candidate_needs_plan_check",
            etf_coverage="candidate_needs_validation",
            adr_coverage="unknown_needs_validation",
            delisted_coverage="unknown_needs_validation",
            historical_depth="strong_candidate_needs_validation",
            daily_ohlcv_availability="yes_needs_live_shape_validation",
            adjusted_close_or_adjusted_ohlc_support="adjusted_data_candidate_needs_validation",
            split_dividend_corporate_action_support="candidate_needs_validation",
            bulk_suitability="medium_to_high_if_plan_allows",
            rate_limit_risk="plan_dependent",
            api_stability="medium_to_high_candidate",
            python_implementation_effort="medium",
            terms_cache_suitability_review_needed=True,
            fit_for_pilot="high",
            fit_for_production="medium_to_high_if_terms_fit",
            fit_for_fallback="medium_paid_low_cost",
            evidence_status="requires_current_plan_terms_price_check",
            notes="Recommended first paid pilot candidate because it may balance quality, implementation effort, and cost.",
        ),
        UsOhlcvProviderCandidate(
            provider="EODHD",
            cost_tier=UsProviderCostTier.PAID_MID,
            us_stock_coverage="broad_candidate_needs_plan_check",
            etf_coverage="candidate_needs_validation",
            adr_coverage="candidate_needs_validation",
            delisted_coverage="possible_plan_dependent_needs_check",
            historical_depth="strong_candidate_needs_validation",
            daily_ohlcv_availability="yes_needs_live_shape_validation",
            adjusted_close_or_adjusted_ohlc_support="adjusted_and_corporate_action_candidate_needs_validation",
            split_dividend_corporate_action_support="candidate_needs_validation",
            bulk_suitability="medium_to_high_if_plan_allows",
            rate_limit_risk="plan_dependent",
            api_stability="medium_to_high_candidate",
            python_implementation_effort="medium",
            terms_cache_suitability_review_needed=True,
            fit_for_pilot="medium_to_high",
            fit_for_production="medium_to_high_if_terms_fit",
            fit_for_fallback="low_to_medium_paid",
            evidence_status="requires_current_plan_terms_price_check",
            notes="Production candidate if coverage, adjustments, and terms are validated against pilot checks.",
        ),
    )


def build_us_ohlcv_provider_selection_matrix(*, report_date: str) -> UsOhlcvProviderSelectionMatrix:
    providers = default_us_ohlcv_provider_candidates()
    ranking = UsOhlcvProviderRanking(
        best_first_pilot_provider="Tiingo",
        best_production_candidate="Polygon.io",
        best_low_cost_candidate="Tiingo",
        best_free_fallback="Stooq",
        provider_requiring_further_research=("EODHD", "Alpha Vantage", "Yahoo Finance / yfinance"),
    )
    pilot = UsOhlcvPilotDesign(
        pilot_universe=DEFAULT_US_PILOT_UNIVERSE,
        pilot_date_range="source_only_suggested_range: 2024-01-01 to latest_completed_trading_day_at_future_live_test",
        provider_candidates_to_test=("Tiingo", "Polygon.io", "Stooq"),
        success_criteria=(
            "All pilot symbols return daily OHLCV rows for the approved date range.",
            "Adjusted close or adjusted OHLC policy is documented and reproducible.",
            "SPY and QQQ ETF rows are present with plausible volume.",
            "No ticker is silently remapped without an explicit symbol mapping note.",
            "Rate-limit behavior is acceptable for a small pilot without retries hiding failures.",
        ),
        failure_criteria=(
            "Any approved pilot symbol is missing without a documented provider reason.",
            "Adjusted prices cannot be reconciled around splits or dividends.",
            "Volume is zero, null, or implausible for liquid symbols without explanation.",
            "Terms/cache review blocks storage of derived cache artifacts.",
            "Provider requires secret display, workflow changes, dependency changes, or pyproject changes.",
        ),
        data_quality_checks=(
            "Required columns: ticker, date, open, high, low, close, volume, provider, adjustment, source_timestamp.",
            "OHLC relationship check: low <= open/high/close <= high where values are present.",
            "No duplicate ticker/date rows after normalization.",
            "All dates are trading dates and sorted ascending per ticker.",
        ),
        adjustment_checks=(
            "Compare raw close vs adjusted close policy when provider exposes both.",
            "Check known split-sensitive symbols in pilot universe, especially NVDA and TSLA.",
            "Record whether dividends are included in adjustment method.",
        ),
        volume_checks=(
            "Volume is numeric and non-negative.",
            "Liquid megacaps and ETFs should not have persistent zero volume.",
            "Large volume discontinuities require split/corporate-action explanation.",
        ),
        symbol_mapping_checks=(
            "AAPL, MSFT, NVDA, AMD, AVGO, TSLA, GOOGL, AMZN, META, JPM, XOM, UNH must remain US common stock symbols.",
            "SPY and QQQ must be classified as ETF_DAILY.",
            "Provider-specific suffix or exchange mappings must be explicit.",
        ),
        rate_limit_checks=(
            "Record documented per-minute/per-day limits before live pilot.",
            "Pilot must not rely on unlimited retry loops.",
            "Bulk screening feasibility must be estimated separately from small pilot success.",
        ),
        cache_write_approved=False,
        actual_import_approved=False,
    )
    safety = UsOhlcvSelectionSafety(
        source_only=True,
        live_http_executed=False,
        public_ohlcv_source_live_fetch_executed=False,
        cache_write_executed=False,
        actual_refresh_import_executed=False,
        env_secret_displayed=False,
        broker_manual_raw_data_handled=False,
        reports_private_touched=False,
        trading_action_executed=False,
        hard_gates_required_for_live_test=(
            PUBLIC_OHLCV_APPROVAL_PHRASE,
            CACHE_WRITE_APPROVAL_PHRASE,
            ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
        ),
        explicitly_not_approved=(
            "live_http",
            "public_ohlcv_source_live_fetch",
            "cache_write",
            "actual_refresh_import",
            "manual_actual_import",
            "env_secret_display",
            "broker_manual_raw_data",
            "workflow_dependency_pyproject_change",
            "trading_action",
        ),
    )
    missing = (
        "Current provider pricing and plan limits must be checked outside this source-only task.",
        "Terms/cache suitability must be reviewed before storing provider-derived artifacts.",
        "Adjusted price methodology must be validated with live pilot evidence.",
        "Delisted coverage and ADR coverage remain unverified.",
        "Bulk screening throughput remains unknown until a separately approved live pilot.",
    )
    _ = report_date
    return UsOhlcvProviderSelectionMatrix(
        report_date=report_date,
        providers=providers,
        evaluation_dimensions=REQUIRED_US_PROVIDER_DIMENSIONS,
        ranking=ranking,
        pilot_design=pilot,
        safety=safety,
        missing_evidence=missing,
    )
