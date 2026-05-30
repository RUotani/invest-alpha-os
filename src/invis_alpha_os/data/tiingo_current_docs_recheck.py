"""Source-only Tiingo current docs manual recheck pack.

This module turns seed references for Tiingo official documentation into a
manual operator checklist. It never performs live HTTP, calls Tiingo APIs,
accesses providers, writes caches, imports data, reads secrets, handles raw
broker/manual data, or performs trading actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invis_alpha_os.data.us_ohlcv_pilot_approval_bundle import (
    DEFAULT_US_OHLCV_PILOT_DATE_RANGE,
)
from invis_alpha_os.data.us_ohlcv_provider_selection import DEFAULT_US_PILOT_UNIVERSE


TIINGO_RECHECK_VERDICT = "manual_recheck_required_before_live_fetch"
TIINGO_PROVIDER = "Tiingo"
TIINGO_SCENARIO = "public_ohlcv"

REQUIRED_TIINGO_RECHECK_CATEGORIES: tuple[str, ...] = (
    "pricing_plan",
    "api_limits_unique_symbol_limits_request_limits",
    "terms_of_use",
    "redistribution_attribution",
    "local_cache_internal_storage_suitability",
    "eod_endpoint_coverage",
    "adjusted_close_adjusted_ohlc_availability",
    "split_handling",
    "dividend_handling",
    "etf_coverage",
    "adr_coverage",
    "mutual_fund_coverage",
    "delisted_coverage",
    "python_implementation_approach",
    "pilot_universe_compatibility",
)


@dataclass(frozen=True)
class TiingoOfficialDocReference:
    label: str
    url_or_reference: str
    seed_summary: str
    needs_manual_recheck: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "url_or_reference": self.url_or_reference,
            "seed_summary": self.seed_summary,
            "needs_manual_recheck": self.needs_manual_recheck,
        }


@dataclass(frozen=True)
class TiingoManualRecheckItem:
    category: str
    official_source_label: str
    official_source_url_or_reference: str
    seed_evidence_summary: str
    operator_question: str
    required_signoff: str
    evidence_date: str
    needs_manual_recheck: bool
    source_accessed_live: bool
    api_called: bool
    cache_written: bool
    operator_signoff_required: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "official_source_label": self.official_source_label,
            "official_source_url_or_reference": self.official_source_url_or_reference,
            "seed_evidence_summary": self.seed_evidence_summary,
            "operator_question": self.operator_question,
            "required_signoff": self.required_signoff,
            "evidence_date": self.evidence_date,
            "needs_manual_recheck": self.needs_manual_recheck,
            "source_accessed_live": self.source_accessed_live,
            "api_called": self.api_called,
            "cache_written": self.cache_written,
            "operator_signoff_required": self.operator_signoff_required,
        }


@dataclass(frozen=True)
class TiingoCurrentDocsSafety:
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
    explicitly_not_approved: tuple[str, ...]

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
            "explicitly_not_approved": list(self.explicitly_not_approved),
        }


@dataclass(frozen=True)
class TiingoCurrentDocsManualRecheckPack:
    report_date: str
    evidence_date: str
    provider: str
    scenario: str
    pilot_universe: tuple[str, ...]
    pilot_date_range: str
    official_references: tuple[TiingoOfficialDocReference, ...]
    checklist_items: tuple[TiingoManualRecheckItem, ...]
    manual_signoff_checklist: tuple[str, ...]
    blocking_questions_before_live_fetch: tuple[str, ...]
    python_implementation_notes: tuple[str, ...]
    pilot_universe_compatibility_notes: tuple[str, ...]
    next_approval_decision: tuple[str, ...]
    safety: TiingoCurrentDocsSafety
    readiness_verdict: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "evidence_date": self.evidence_date,
            "provider": self.provider,
            "scenario": self.scenario,
            "pilot_universe": list(self.pilot_universe),
            "pilot_date_range": self.pilot_date_range,
            "official_references": [item.to_dict() for item in self.official_references],
            "checklist_items": [item.to_dict() for item in self.checklist_items],
            "manual_signoff_checklist": list(self.manual_signoff_checklist),
            "blocking_questions_before_live_fetch": list(self.blocking_questions_before_live_fetch),
            "python_implementation_notes": list(self.python_implementation_notes),
            "pilot_universe_compatibility_notes": list(self.pilot_universe_compatibility_notes),
            "next_approval_decision": list(self.next_approval_decision),
            "safety": self.safety.to_dict(),
            "readiness_verdict": self.readiness_verdict,
        }


def default_tiingo_official_doc_references() -> tuple[TiingoOfficialDocReference, ...]:
    return (
        TiingoOfficialDocReference(
            label="Tiingo pricing",
            url_or_reference="https://www.tiingo.com/account/billing/pricing",
            seed_summary="Seed snippets indicate individual pricing such as monthly or annual plans; current price must be manually rechecked.",
            needs_manual_recheck=True,
        ),
        TiingoOfficialDocReference(
            label="Tiingo EOD Stock Price API documentation",
            url_or_reference="https://www.tiingo.com/documentation/end-of-day",
            seed_summary="Seed evidence says EOD docs cover daily price data and broad instruments such as US equities, ETFs, mutual funds, ADRs, and Chinese equities.",
            needs_manual_recheck=True,
        ),
        TiingoOfficialDocReference(
            label="Tiingo Terms of Use",
            url_or_reference="https://www.tiingo.com/about/terms",
            seed_summary="Seed evidence says posted API limits may be approximate or changed and redistribution or attribution obligations may apply.",
            needs_manual_recheck=True,
        ),
        TiingoOfficialDocReference(
            label="Tiingo split and dividend API documentation",
            url_or_reference="Tiingo official split/dividend and corporate action documentation",
            seed_summary="Seed evidence says split/dividend docs exist; adjustment method and fields must be manually rechecked.",
            needs_manual_recheck=True,
        ),
    )


def _item(
    *,
    category: str,
    source_label: str,
    source_ref: str,
    seed_summary: str,
    operator_question: str,
    required_signoff: str,
    evidence_date: str,
) -> TiingoManualRecheckItem:
    return TiingoManualRecheckItem(
        category=category,
        official_source_label=source_label,
        official_source_url_or_reference=source_ref,
        seed_evidence_summary=seed_summary,
        operator_question=operator_question,
        required_signoff=required_signoff,
        evidence_date=evidence_date,
        needs_manual_recheck=True,
        source_accessed_live=False,
        api_called=False,
        cache_written=False,
        operator_signoff_required=True,
    )


def default_tiingo_recheck_items(*, evidence_date: str) -> tuple[TiingoManualRecheckItem, ...]:
    return (
        _item(
            category="pricing_plan",
            source_label="Tiingo pricing",
            source_ref="https://www.tiingo.com/account/billing/pricing",
            seed_summary="Seed snippets mention individual pricing; do not treat this as current truth.",
            operator_question="What current plan, monthly/annual price, historical access, and pilot limits apply?",
            required_signoff="operator_confirms_current_plan_and_price_before_live_fetch",
            evidence_date=evidence_date,
        ),
        _item(
            category="api_limits_unique_symbol_limits_request_limits",
            source_label="Tiingo Terms of Use / API documentation",
            source_ref="https://www.tiingo.com/about/terms",
            seed_summary="Seed evidence says API limits may be approximate or changed.",
            operator_question="What current per-minute, per-hour, per-day, unique symbol, and bulk limits apply?",
            required_signoff="operator_confirms_limits_fit_small_pilot_without_cache_write",
            evidence_date=evidence_date,
        ),
        _item(
            category="terms_of_use",
            source_label="Tiingo Terms of Use",
            source_ref="https://www.tiingo.com/about/terms",
            seed_summary="Terms must be reviewed before using provider output in project artifacts.",
            operator_question="Do current terms allow a redacted live-fetch-only pilot and internal review artifacts?",
            required_signoff="operator_confirms_terms_allow_pilot_review",
            evidence_date=evidence_date,
        ),
        _item(
            category="redistribution_attribution",
            source_label="Tiingo Terms of Use",
            source_ref="https://www.tiingo.com/about/terms",
            seed_summary="Redistribution and attribution obligations may apply.",
            operator_question="What attribution, redistribution, or display restrictions apply to pilot outputs?",
            required_signoff="operator_confirms_no_redistribution_violation",
            evidence_date=evidence_date,
        ),
        _item(
            category="local_cache_internal_storage_suitability",
            source_label="Tiingo Terms of Use / pricing",
            source_ref="https://www.tiingo.com/about/terms",
            seed_summary="Cache suitability is not approved and must be separately reviewed.",
            operator_question="Are sanitized local caches or derived storage allowed under current terms?",
            required_signoff="operator_confirms_cache_terms_before_any_cache_write_approval",
            evidence_date=evidence_date,
        ),
        _item(
            category="eod_endpoint_coverage",
            source_label="Tiingo EOD Stock Price API documentation",
            source_ref="https://www.tiingo.com/documentation/end-of-day",
            seed_summary="Seed evidence says EOD docs describe daily price data and broad coverage.",
            operator_question="Does the EOD endpoint cover all pilot symbols and required date range?",
            required_signoff="operator_confirms_eod_endpoint_covers_pilot_scope",
            evidence_date=evidence_date,
        ),
        _item(
            category="adjusted_close_adjusted_ohlc_availability",
            source_label="Tiingo EOD Stock Price API documentation",
            source_ref="https://www.tiingo.com/documentation/end-of-day",
            seed_summary="Adjusted fields and methodology must be manually rechecked.",
            operator_question="Which adjusted close or adjusted OHLC fields exist and what methodology is used?",
            required_signoff="operator_confirms_adjusted_price_fields_and_method",
            evidence_date=evidence_date,
        ),
        _item(
            category="split_handling",
            source_label="Tiingo split API documentation",
            source_ref="Tiingo official split documentation",
            seed_summary="Seed evidence says split docs exist.",
            operator_question="How are splits exposed and how do they affect adjusted and raw fields?",
            required_signoff="operator_confirms_split_handling_for_nvda_tsla_style_cases",
            evidence_date=evidence_date,
        ),
        _item(
            category="dividend_handling",
            source_label="Tiingo dividend API documentation",
            source_ref="Tiingo official dividend documentation",
            seed_summary="Seed evidence says dividend docs exist.",
            operator_question="How are dividends exposed and included or excluded from adjusted fields?",
            required_signoff="operator_confirms_dividend_handling_and_adjustment_policy",
            evidence_date=evidence_date,
        ),
        _item(
            category="etf_coverage",
            source_label="Tiingo EOD Stock Price API documentation",
            source_ref="https://www.tiingo.com/documentation/end-of-day",
            seed_summary="Seed evidence says ETF coverage is included.",
            operator_question="Are SPY and QQQ supported by the EOD endpoint for the pilot range?",
            required_signoff="operator_confirms_spy_qqq_coverage",
            evidence_date=evidence_date,
        ),
        _item(
            category="adr_coverage",
            source_label="Tiingo EOD Stock Price API documentation",
            source_ref="https://www.tiingo.com/documentation/end-of-day",
            seed_summary="Seed evidence says ADR coverage may be included.",
            operator_question="What ADR coverage exists and are symbol mappings explicit?",
            required_signoff="operator_confirms_adr_coverage_and_mapping_caveats",
            evidence_date=evidence_date,
        ),
        _item(
            category="mutual_fund_coverage",
            source_label="Tiingo EOD Stock Price API documentation",
            source_ref="https://www.tiingo.com/documentation/end-of-day",
            seed_summary="Seed evidence says mutual fund coverage may be included.",
            operator_question="What mutual fund coverage exists and is it relevant or excluded for this pilot?",
            required_signoff="operator_confirms_mutual_fund_scope_treatment",
            evidence_date=evidence_date,
        ),
        _item(
            category="delisted_coverage",
            source_label="Tiingo EOD Stock Price API documentation / pricing",
            source_ref="https://www.tiingo.com/documentation/end-of-day",
            seed_summary="Delisted coverage remains unknown until current docs are checked.",
            operator_question="Are delisted securities available on the selected plan, and with what limitations?",
            required_signoff="operator_confirms_delisted_coverage_or_not_assumed",
            evidence_date=evidence_date,
        ),
        _item(
            category="python_implementation_approach",
            source_label="Tiingo API documentation",
            source_ref="Tiingo official API documentation",
            seed_summary="Implementation should use existing project HTTP/redaction patterns in a future task.",
            operator_question="Can a future implementation avoid new dependencies and avoid secret display?",
            required_signoff="operator_confirms_no_workflow_dependency_pyproject_change_required",
            evidence_date=evidence_date,
        ),
        _item(
            category="pilot_universe_compatibility",
            source_label="v49 pilot approval bundle",
            source_ref="source-only v49 pilot universe",
            seed_summary="Pilot universe is fixed before live-fetch-only approval.",
            operator_question="Are all pilot symbols compatible with Tiingo symbol format and selected plan?",
            required_signoff="operator_confirms_pilot_universe_compatible",
            evidence_date=evidence_date,
        ),
    )


def build_tiingo_current_docs_recheck_pack(
    *,
    report_date: str,
) -> TiingoCurrentDocsManualRecheckPack:
    safety = TiingoCurrentDocsSafety(
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
    )
    return TiingoCurrentDocsManualRecheckPack(
        report_date=report_date,
        evidence_date=report_date,
        provider=TIINGO_PROVIDER,
        scenario=TIINGO_SCENARIO,
        pilot_universe=DEFAULT_US_PILOT_UNIVERSE,
        pilot_date_range=DEFAULT_US_OHLCV_PILOT_DATE_RANGE,
        official_references=default_tiingo_official_doc_references(),
        checklist_items=default_tiingo_recheck_items(evidence_date=report_date),
        manual_signoff_checklist=(
            "pricing_plan_signoff",
            "terms_redistribution_attribution_signoff",
            "api_limits_throughput_signoff",
            "adjusted_price_method_signoff",
            "split_dividend_corporate_action_signoff",
            "etf_adr_mutual_fund_delisted_coverage_signoff",
            "cache_suitability_signoff_before_any_cache_write",
            "pilot_universe_compatibility_signoff",
        ),
        blocking_questions_before_live_fetch=(
            "Does the selected Tiingo plan permit this exact live-fetch-only pilot?",
            "Are API limits sufficient for 14 symbols over the pilot date range without cache write?",
            "Are redistribution and attribution restrictions compatible with redacted review artifacts?",
            "Is cache storage prohibited, permitted, or separately licensed?",
            "Can adjusted price and corporate action fields support validation around splits/dividends?",
        ),
        python_implementation_notes=(
            "Future implementation should use existing project CLI and redaction patterns.",
            "No new dependency, workflow, or pyproject change is approved by this pack.",
            "Future code must never print API tokens, raw provider responses, or account identifiers.",
        ),
        pilot_universe_compatibility_notes=(
            "Pilot universe remains AAPL, MSFT, NVDA, AMD, AVGO, TSLA, GOOGL, AMZN, META, JPM, XOM, UNH, SPY, QQQ.",
            "SPY and QQQ ETF support must be manually confirmed.",
            "ADR and delisted coverage are not assumed for pilot success unless current docs confirm them.",
        ),
        next_approval_decision=(
            "Complete manual signoff for every checklist category.",
            "If signoff passes, prepare a separate live-fetch-only approval task.",
            "Do not include cache write or actual import in the first Tiingo live-fetch approval.",
        ),
        safety=safety,
        readiness_verdict=TIINGO_RECHECK_VERDICT,
    )
