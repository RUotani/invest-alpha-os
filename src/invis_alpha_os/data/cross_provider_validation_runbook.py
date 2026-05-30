"""Source-only cross-provider OHLCV data-quality validation runbook.

This module prepares the approval package, operator runbook, tolerance policy,
redacted output schema, stop conditions, and Cursor handoff for a future
no-write cross-provider validation. It never calls Tiingo, Stooq, Yahoo,
yfinance, Polygon, or any provider; it never writes cache, imports data,
persists raw OHLCV, displays secrets, or performs trading actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invis_alpha_os.data.ohlcv_provider_registry import PUBLIC_OHLCV_APPROVAL_PHRASE
from invis_alpha_os.data.tiingo_live_fetch_result_review import (
    TIINGO_ACTUAL_IMPORT_READINESS_VERDICT,
    TIINGO_CACHE_WRITE_READINESS_VERDICT,
    TIINGO_V63B_PILOT_UNIVERSE,
    TIINGO_V63B_RESULT_VERDICT,
)


CROSS_PROVIDER_VALIDATION_OPERATION = "no_write_cross_provider_data_quality_validation"
CROSS_PROVIDER_RUNBOOK_VERDICT = "ready_for_separate_explicit_approval_not_approved"
CROSS_PROVIDER_CURSOR_HANDOFF_STATUS = "draft_only_do_not_execute_without_approval_phrase"


@dataclass(frozen=True)
class CrossProviderValidationProviderScope:
    required_providers: tuple[str, ...]
    optional_providers: tuple[str, ...]
    provider_roles: dict[str, str]
    provider_live_access_executed_by_this_pack: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_providers": list(self.required_providers),
            "optional_providers": list(self.optional_providers),
            "provider_roles": dict(self.provider_roles),
            "provider_live_access_executed_by_this_pack": self.provider_live_access_executed_by_this_pack,
        }


@dataclass(frozen=True)
class CrossProviderValidationUniverse:
    symbols: tuple[str, ...]
    sample_groups: dict[str, tuple[str, ...]]
    date_range: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbols": list(self.symbols),
            "sample_groups": {key: list(value) for key, value in self.sample_groups.items()},
            "date_range": self.date_range,
        }


@dataclass(frozen=True)
class CrossProviderValidationCheck:
    check_id: str
    category: str
    description: str
    required: bool
    compute_now: bool
    blocks_cache_import_on_major_disagreement: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "category": self.category,
            "description": self.description,
            "required": self.required,
            "compute_now": self.compute_now,
            "blocks_cache_import_on_major_disagreement": self.blocks_cache_import_on_major_disagreement,
        }


@dataclass(frozen=True)
class CrossProviderTolerancePolicy:
    row_count_tolerance_days: int
    date_range_tolerance_days: int
    close_relative_tolerance_pct: float
    adjusted_close_relative_tolerance_pct: float
    volume_relative_tolerance_pct: float
    split_sensitive_requires_manual_review: bool
    missing_day_requires_investigation: bool
    provider_disagreement_requires_no_cache_import: bool
    policy_note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_count_tolerance_days": self.row_count_tolerance_days,
            "date_range_tolerance_days": self.date_range_tolerance_days,
            "close_relative_tolerance_pct": self.close_relative_tolerance_pct,
            "adjusted_close_relative_tolerance_pct": self.adjusted_close_relative_tolerance_pct,
            "volume_relative_tolerance_pct": self.volume_relative_tolerance_pct,
            "split_sensitive_requires_manual_review": self.split_sensitive_requires_manual_review,
            "missing_day_requires_investigation": self.missing_day_requires_investigation,
            "provider_disagreement_requires_no_cache_import": self.provider_disagreement_requires_no_cache_import,
            "policy_note": self.policy_note,
        }


@dataclass(frozen=True)
class CrossProviderRedactedOutputSchema:
    allowed_fields: tuple[str, ...]
    forbidden_fields: tuple[str, ...]
    reports_private_raw_data_forbidden: bool
    raw_ohlcv_rows_allowed: bool
    raw_provider_responses_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_fields": list(self.allowed_fields),
            "forbidden_fields": list(self.forbidden_fields),
            "reports_private_raw_data_forbidden": self.reports_private_raw_data_forbidden,
            "raw_ohlcv_rows_allowed": self.raw_ohlcv_rows_allowed,
            "raw_provider_responses_allowed": self.raw_provider_responses_allowed,
        }


@dataclass(frozen=True)
class CrossProviderStopCondition:
    label: str
    description: str
    stop_immediately: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "description": self.description,
            "stop_immediately": self.stop_immediately,
        }


@dataclass(frozen=True)
class CrossProviderNoWriteSafetyControl:
    source_only: bool
    tiingo_api_call_executed: bool
    stooq_live_fetch_executed: bool
    yahoo_yfinance_live_fetch_executed: bool
    polygon_live_fetch_executed: bool
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
    raw_ohlcv_persisted: bool
    raw_api_response_persisted: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_only": self.source_only,
            "tiingo_api_call_executed": self.tiingo_api_call_executed,
            "stooq_live_fetch_executed": self.stooq_live_fetch_executed,
            "yahoo_yfinance_live_fetch_executed": self.yahoo_yfinance_live_fetch_executed,
            "polygon_live_fetch_executed": self.polygon_live_fetch_executed,
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
            "raw_ohlcv_persisted": self.raw_ohlcv_persisted,
            "raw_api_response_persisted": self.raw_api_response_persisted,
        }


@dataclass(frozen=True)
class CrossProviderValidationApprovalPackage:
    package_status: str
    operation: str
    providers: tuple[str, ...]
    optional_providers: tuple[str, ...]
    universe: tuple[str, ...]
    date_range: str
    future_approval_phrase: str
    approval_phrase_issued: bool
    separate_explicit_approval_required: bool
    raw_data_persistence_allowed: bool
    cache_write_approved: bool
    actual_import_approved: bool
    manual_import_approved: bool
    trading_action_approved: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_status": self.package_status,
            "operation": self.operation,
            "providers": list(self.providers),
            "optional_providers": list(self.optional_providers),
            "universe": list(self.universe),
            "date_range": self.date_range,
            "future_approval_phrase": self.future_approval_phrase,
            "approval_phrase_issued": self.approval_phrase_issued,
            "separate_explicit_approval_required": self.separate_explicit_approval_required,
            "raw_data_persistence_allowed": self.raw_data_persistence_allowed,
            "cache_write_approved": self.cache_write_approved,
            "actual_import_approved": self.actual_import_approved,
            "manual_import_approved": self.manual_import_approved,
            "trading_action_approved": self.trading_action_approved,
        }


@dataclass(frozen=True)
class CrossProviderValidationRunbook:
    preconditions: tuple[str, ...]
    operator_steps: tuple[str, ...]
    verification_steps: tuple[str, ...]
    cleanup_verification: tuple[str, ...]
    expected_artifacts: tuple[str, ...]
    forbidden_artifacts: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "preconditions": list(self.preconditions),
            "operator_steps": list(self.operator_steps),
            "verification_steps": list(self.verification_steps),
            "cleanup_verification": list(self.cleanup_verification),
            "expected_artifacts": list(self.expected_artifacts),
            "forbidden_artifacts": list(self.forbidden_artifacts),
        }


@dataclass(frozen=True)
class CrossProviderReadinessVerdict:
    cross_provider_validation_execution_readiness: str
    cache_write_readiness: str
    actual_import_readiness: str
    rationale: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cross_provider_validation_execution_readiness": self.cross_provider_validation_execution_readiness,
            "cache_write_readiness": self.cache_write_readiness,
            "actual_import_readiness": self.actual_import_readiness,
            "rationale": list(self.rationale),
        }


@dataclass(frozen=True)
class CrossProviderNextCursorHandoff:
    handoff_status: str
    required_approval_phrase: str
    execution_scope: str
    no_write_rules: tuple[str, ...]
    output_rules: tuple[str, ...]
    final_report_fields: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "handoff_status": self.handoff_status,
            "required_approval_phrase": self.required_approval_phrase,
            "execution_scope": self.execution_scope,
            "no_write_rules": list(self.no_write_rules),
            "output_rules": list(self.output_rules),
            "final_report_fields": list(self.final_report_fields),
        }


@dataclass(frozen=True)
class CrossProviderValidationRunbookPack:
    report_date: str
    current_state: dict[str, Any]
    provider_scope: CrossProviderValidationProviderScope
    universe: CrossProviderValidationUniverse
    validation_checks: tuple[CrossProviderValidationCheck, ...]
    tolerance_policy: CrossProviderTolerancePolicy
    redacted_output_schema: CrossProviderRedactedOutputSchema
    safety_controls: CrossProviderNoWriteSafetyControl
    stop_conditions: tuple[CrossProviderStopCondition, ...]
    approval_package: CrossProviderValidationApprovalPackage
    runbook: CrossProviderValidationRunbook
    readiness_verdict: CrossProviderReadinessVerdict
    cursor_handoff: CrossProviderNextCursorHandoff

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "current_state": dict(self.current_state),
            "provider_scope": self.provider_scope.to_dict(),
            "universe": self.universe.to_dict(),
            "validation_checks": [check.to_dict() for check in self.validation_checks],
            "tolerance_policy": self.tolerance_policy.to_dict(),
            "redacted_output_schema": self.redacted_output_schema.to_dict(),
            "safety_controls": self.safety_controls.to_dict(),
            "stop_conditions": [condition.to_dict() for condition in self.stop_conditions],
            "approval_package": self.approval_package.to_dict(),
            "runbook": self.runbook.to_dict(),
            "readiness_verdict": self.readiness_verdict.to_dict(),
            "cursor_handoff": self.cursor_handoff.to_dict(),
        }


def _validation_checks() -> tuple[CrossProviderValidationCheck, ...]:
    rows = (
        ("DQ-01", "symbol_availability_comparison", "Check symbol availability across required providers."),
        ("DQ-02", "row_count_comparison", "Compare row counts by symbol/provider."),
        ("DQ-03", "date_min_date_max_comparison", "Compare earliest and latest covered dates."),
        ("DQ-04", "trading_day_coverage_comparison", "Compare covered trading days without storing rows."),
        ("DQ-05", "missing_day_comparison", "Summarize missing-day counts and reason classes."),
        ("DQ-06", "close_price_difference", "Summarize close-price relative deviations."),
        ("DQ-07", "adjusted_close_difference", "Summarize adjusted-close relative deviations."),
        ("DQ-08", "volume_difference", "Summarize volume relative deviations and scale anomalies."),
        ("DQ-09", "adjusted_field_availability", "Compare adjusted-field presence booleans."),
        ("DQ-10", "split_sensitive_sample_checks", "Manually review split-sensitive samples."),
        ("DQ-11", "etf_sample_checks", "Check SPY and QQQ ETF samples."),
        ("DQ-12", "error_class_normalization", "Normalize provider error classes."),
        ("DQ-13", "provider_latency_summary", "Summarize provider latency without request payloads."),
    )
    return tuple(
        CrossProviderValidationCheck(
            check_id=check_id,
            category=category,
            description=description,
            required=True,
            compute_now=False,
            blocks_cache_import_on_major_disagreement=True,
        )
        for check_id, category, description in rows
    )


def _stop_conditions() -> tuple[CrossProviderStopCondition, ...]:
    rows = (
        ("approval_phrase_missing", "The future explicit approval phrase has not been provided."),
        ("provider_token_missing", "A token/account required by a selected provider is unavailable."),
        ("secret_displayed", "Any secret, token, auth header, or credential value would be displayed."),
        ("raw_ohlcv_printed", "Raw OHLCV rows or daily prices would be printed."),
        ("raw_ohlcv_persisted", "Raw OHLCV rows, CSV series, or JSON market data would be persisted."),
        ("cache_write_attempted", "Any cache/database write path is attempted."),
        ("actual_import_attempted", "Any actual refresh/import or manual import path is attempted."),
        ("dependency_change_required", "Execution would require dependency, pyproject, workflow, or Makefile changes."),
        ("rate_limit_blocks_most_symbols", "Provider rate limits block most of the 14-symbol universe."),
        ("provider_terms_warning", "Provider terms/compliance warning appears during setup."),
        ("large_discrepancy_above_tolerance", "Provider disagreement exceeds tolerance and lacks explanation."),
        ("reports_private_raw_data_risk", "reports-private would receive raw rows, prices, or provider responses."),
    )
    return tuple(CrossProviderStopCondition(label=label, description=description, stop_immediately=True) for label, description in rows)


def build_cross_provider_validation_runbook_pack(*, report_date: str) -> CrossProviderValidationRunbookPack:
    required_providers = ("Tiingo", "Stooq", "Yahoo Finance/yfinance")
    optional_providers = ("Polygon",)
    date_range = "2024-01-01 to latest completed trading day at future execution"
    universe = CrossProviderValidationUniverse(
        symbols=TIINGO_V63B_PILOT_UNIVERSE,
        sample_groups={
            "mega_cap_tech": ("AAPL", "MSFT", "GOOGL", "AMZN", "META"),
            "ai_semiconductor_high_beta": ("NVDA", "AMD", "AVGO", "TSLA"),
            "sector_diversifiers": ("JPM", "XOM", "UNH"),
            "etf_samples": ("SPY", "QQQ"),
        },
        date_range=date_range,
    )
    redacted_schema = CrossProviderRedactedOutputSchema(
        allowed_fields=(
            "symbol_provider_pass_fail",
            "row_count",
            "date_coverage",
            "field_presence_booleans",
            "difference_summary_statistics",
            "max_min_deviation_summary",
            "error_class",
            "no_write_flags",
            "redaction_flags",
        ),
        forbidden_fields=(
            "raw_ohlcv_rows",
            "raw_provider_responses",
            "csv_price_series",
            "json_raw_market_data",
            "individual_daily_prices",
            "token_or_auth_headers",
        ),
        reports_private_raw_data_forbidden=True,
        raw_ohlcv_rows_allowed=False,
        raw_provider_responses_allowed=False,
    )
    safety = CrossProviderNoWriteSafetyControl(
        source_only=True,
        tiingo_api_call_executed=False,
        stooq_live_fetch_executed=False,
        yahoo_yfinance_live_fetch_executed=False,
        polygon_live_fetch_executed=False,
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
        raw_ohlcv_persisted=False,
        raw_api_response_persisted=False,
    )
    return CrossProviderValidationRunbookPack(
        report_date=report_date,
        current_state={
            "tiingo_v63b_provider_viability": TIINGO_V63B_RESULT_VERDICT,
            "tiingo_v63b_symbols_total": 14,
            "tiingo_v63b_symbols_success": 14,
            "tiingo_v63b_base_fields_present": True,
            "tiingo_v63b_adjusted_fields_present": True,
            "v64_unproven_items": [
                "raw price accuracy",
                "adjusted calculation correctness",
                "cross-provider consistency",
                "split/dividend quality",
                "long-history completeness",
                "delisted coverage",
                "rate-limit stability",
                "cache/database legal suitability",
            ],
        },
        provider_scope=CrossProviderValidationProviderScope(
            required_providers=required_providers,
            optional_providers=optional_providers,
            provider_roles={
                "Tiingo": "v63B live-fetch-only provider viability passed",
                "Stooq": "free fallback and comparison provider",
                "Yahoo Finance/yfinance": "convenient comparison-only provider, not production primary",
                "Polygon": "optional production-quality comparison if token/account is available later",
            },
            provider_live_access_executed_by_this_pack=False,
        ),
        universe=universe,
        validation_checks=_validation_checks(),
        tolerance_policy=CrossProviderTolerancePolicy(
            row_count_tolerance_days=1,
            date_range_tolerance_days=1,
            close_relative_tolerance_pct=0.5,
            adjusted_close_relative_tolerance_pct=0.5,
            volume_relative_tolerance_pct=5.0,
            split_sensitive_requires_manual_review=True,
            missing_day_requires_investigation=True,
            provider_disagreement_requires_no_cache_import=True,
            policy_note=(
                "Tolerance is for red-flag detection, not proof of correctness; major disagreement blocks cache/import."
            ),
        ),
        redacted_output_schema=redacted_schema,
        safety_controls=safety,
        stop_conditions=_stop_conditions(),
        approval_package=CrossProviderValidationApprovalPackage(
            package_status="draft_only_not_approved",
            operation=CROSS_PROVIDER_VALIDATION_OPERATION,
            providers=required_providers,
            optional_providers=optional_providers,
            universe=TIINGO_V63B_PILOT_UNIVERSE,
            date_range=date_range,
            future_approval_phrase=PUBLIC_OHLCV_APPROVAL_PHRASE,
            approval_phrase_issued=False,
            separate_explicit_approval_required=True,
            raw_data_persistence_allowed=False,
            cache_write_approved=False,
            actual_import_approved=False,
            manual_import_approved=False,
            trading_action_approved=False,
        ),
        runbook=CrossProviderValidationRunbook(
            preconditions=(
                "Human explicitly approves the future public OHLCV no-write validation phrase.",
                "Provider terms and token requirements are checked without displaying secret values.",
                "Output path is restricted to redacted aggregate summaries only.",
            ),
            operator_steps=(
                "Run future validation in no-write mode only after explicit approval.",
                "Compare required providers for the 14-symbol universe and date range.",
                "Record pass/fail, coverage, field presence, deviations, latency, and error classes only.",
                "Stop immediately if any stop condition is hit.",
            ),
            verification_steps=(
                "Verify no cache/database files changed.",
                "Verify no raw OHLCV rows, CSV series, JSON raw market data, or provider responses were written.",
                "Verify reports-private receives redacted summary only if separately synced by an approved process.",
                "Verify cache-write and actual-import readiness remain false unless separately approved later.",
            ),
            cleanup_verification=(
                "Inspect git status for source-only changes.",
                "Inspect output directories for forbidden raw artifacts.",
                "Delete local temporary raw scratch files if a future execution unexpectedly creates any.",
            ),
            expected_artifacts=(
                "redacted cross-provider validation markdown summary",
                "redacted cross-provider validation JSON summary",
                "operator final report with no-write flags",
            ),
            forbidden_artifacts=redacted_schema.forbidden_fields,
        ),
        readiness_verdict=CrossProviderReadinessVerdict(
            cross_provider_validation_execution_readiness=CROSS_PROVIDER_RUNBOOK_VERDICT,
            cache_write_readiness=TIINGO_CACHE_WRITE_READINESS_VERDICT,
            actual_import_readiness=TIINGO_ACTUAL_IMPORT_READINESS_VERDICT,
            rationale=(
                "v64B prepares the approval/runbook, but does not issue approval.",
                "Future no-write validation requires an explicit human approval phrase.",
                "Cache write remains separate because storage legality and data-quality evidence are unresolved.",
                "Actual import remains downstream of cache-write readiness and separate approval.",
            ),
        ),
        cursor_handoff=CrossProviderNextCursorHandoff(
            handoff_status=CROSS_PROVIDER_CURSOR_HANDOFF_STATUS,
            required_approval_phrase=PUBLIC_OHLCV_APPROVAL_PHRASE,
            execution_scope="future no-write Tiingo/Stooq/Yahoo-yfinance comparison with optional Polygon",
            no_write_rules=(
                "do not write cache",
                "do not import market data",
                "do not persist raw OHLCV or provider responses",
                "do not display secrets",
                "do not touch reports-private with raw data",
            ),
            output_rules=(
                "redacted aggregate summary only",
                "symbol/provider pass/fail and counts only",
                "deviation summary statistics only",
                "no individual daily prices",
            ),
            final_report_fields=(
                "providers attempted",
                "symbols total/success/fail",
                "checks pass/warn/fail",
                "tolerance exceptions",
                "stop conditions triggered",
                "no-write verification",
                "cache/import readiness remains false",
            ),
        ),
    )
