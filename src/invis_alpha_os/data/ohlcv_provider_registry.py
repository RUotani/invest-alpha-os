"""OHLCV provider registry core (dry-run planning only; no live HTTP)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any


CANONICAL_OHLCV_COLUMNS: tuple[str, ...] = (
    "ticker",
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "provider",
    "adjustment",
    "source_timestamp",
)

JQUANTS_APPROVAL_PHRASE = "J-Quants gated refreshを実行してよい"
PUBLIC_OHLCV_APPROVAL_PHRASE = "public OHLCV source live fetchを実行してよい"
MANUAL_IMPORT_APPROVAL_PHRASE = "manual JP bars actual importを実行してよい"


class ProviderCapability(str, Enum):
    JP_EQUITY_DAILY = "jp_equity_daily"
    US_EQUITY_DAILY = "us_equity_daily"
    ETF_DAILY = "etf_daily"
    MANUAL_CSV_INGEST = "manual_csv_ingest"
    GATED_LIVE_HTTP = "gated_live_http"
    CACHE_ONLY = "cache_only"


@dataclass(frozen=True)
class ProviderApprovalGate:
    requires_live_http_approval: bool
    requires_cache_write_approval: bool
    approval_phrase: str | None
    risk: str

    def blocks(self, *, allow_live_http: bool, allow_cache_write: bool) -> bool:
        if self.requires_live_http_approval and not allow_live_http:
            return True
        return self.requires_cache_write_approval and not allow_cache_write

    def reason(self, *, allow_live_http: bool, allow_cache_write: bool) -> str:
        if self.requires_live_http_approval and not allow_live_http:
            return "live_http_disabled"
        if self.requires_cache_write_approval and not allow_cache_write:
            return "cache_write_disabled"
        return "allowed_by_inputs"


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    markets: tuple[str, ...]
    role: str
    capabilities: tuple[ProviderCapability, ...]
    priority: int
    live_http: bool
    manual_fallback: bool
    adjustment: str
    source_timestamp_policy: str
    approval_gate: ProviderApprovalGate
    expected_coverage: str
    recommendation: str
    notes: str

    def supports_market(self, market: str) -> bool:
        norm = market.strip().upper()
        return norm in {m.upper() for m in self.markets}

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider_id,
            "markets": list(self.markets),
            "role": self.role,
            "capabilities": [c.value for c in self.capabilities],
            "priority": self.priority,
            "live_http": self.live_http,
            "manual_fallback": self.manual_fallback,
            "adjustment": self.adjustment,
            "source_timestamp_policy": self.source_timestamp_policy,
            "approval_required": self.approval_gate.requires_live_http_approval
            or self.approval_gate.requires_cache_write_approval,
            "approval_phrase": self.approval_gate.approval_phrase,
            "expected_coverage": self.expected_coverage,
            "recommendation": self.recommendation,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ProviderFreshnessScore:
    ticker: str
    market: str
    provider: str
    latest_date: str | None
    reference_date: str
    freshness_status: str
    stale_days: int | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "market": self.market,
            "provider": self.provider,
            "latest_date": self.latest_date,
            "reference_date": self.reference_date,
            "freshness_status": self.freshness_status,
            "stale_days": self.stale_days,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ProviderCoverageMatrix:
    rows: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {"rows": list(self.rows)}


@dataclass(frozen=True)
class ProviderSelection:
    market: str
    ticker: str
    selected_provider: str
    fallback_provider: str | None
    requires_approval: bool
    approval_phrase: str | None
    reason: str
    risk: str
    expected_coverage: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "market": self.market,
            "ticker": self.ticker,
            "selected_provider": self.selected_provider,
            "fallback_provider": self.fallback_provider,
            "requires_approval": self.requires_approval,
            "approval_phrase": self.approval_phrase,
            "reason": self.reason,
            "risk": self.risk,
            "expected_coverage": self.expected_coverage,
        }


class MarketDataProviderRegistry:
    def __init__(self, specs: tuple[ProviderSpec, ...] = ()) -> None:
        self._specs: dict[str, ProviderSpec] = {}
        for spec in specs:
            self.register(spec)

    def register(self, spec: ProviderSpec) -> None:
        if not spec.provider_id.strip():
            raise ValueError("provider_id is required")
        if spec.provider_id in self._specs:
            raise ValueError(f"duplicate provider_id: {spec.provider_id}")
        self._specs[spec.provider_id] = spec

    def get(self, provider_id: str) -> ProviderSpec:
        try:
            return self._specs[provider_id]
        except KeyError as exc:
            raise KeyError(f"unknown provider: {provider_id}") from exc

    def list(self) -> list[ProviderSpec]:
        return sorted(self._specs.values(), key=lambda s: (min(s.priority, 999), s.provider_id))

    def for_market(self, market: str) -> list[ProviderSpec]:
        return [spec for spec in self.list() if spec.supports_market(market)]


@dataclass(frozen=True)
class ProviderPriorityPolicy:
    registry: MarketDataProviderRegistry

    def select(
        self,
        *,
        market: str,
        ticker: str,
        required_date_from: str,
        required_date_to: str,
        freshness_required: bool,
        allow_live_http: bool,
        allow_cache_write: bool,
    ) -> ProviderSelection:
        _ = required_date_from, required_date_to
        candidates = self.registry.for_market(market)
        if not candidates:
            return ProviderSelection(
                market=market,
                ticker=ticker,
                selected_provider="none",
                fallback_provider=None,
                requires_approval=False,
                approval_phrase=None,
                reason="no_provider_for_market",
                risk="high",
                expected_coverage="none",
            )

        allowed: list[ProviderSpec] = [
            spec
            for spec in candidates
            if not spec.approval_gate.blocks(
                allow_live_http=allow_live_http,
                allow_cache_write=allow_cache_write,
            )
        ]
        selected = allowed[0] if allowed else candidates[0]
        fallback = next((s for s in candidates if s.provider_id != selected.provider_id), None)
        blocked = selected.approval_gate.blocks(
            allow_live_http=allow_live_http,
            allow_cache_write=allow_cache_write,
        )
        if blocked:
            reason = selected.approval_gate.reason(
                allow_live_http=allow_live_http,
                allow_cache_write=allow_cache_write,
            )
        elif freshness_required and selected.manual_fallback:
            reason = "freshness_requires_human_supplied_csv_or_approval"
        else:
            reason = "selected_by_market_priority_policy"
        return ProviderSelection(
            market=market,
            ticker=ticker,
            selected_provider=selected.provider_id,
            fallback_provider=fallback.provider_id if fallback else None,
            requires_approval=blocked,
            approval_phrase=selected.approval_gate.approval_phrase if blocked else None,
            reason=reason,
            risk=selected.approval_gate.risk,
            expected_coverage=selected.expected_coverage,
        )


def build_default_ohlcv_provider_registry() -> MarketDataProviderRegistry:
    public_live_gate = ProviderApprovalGate(True, False, PUBLIC_OHLCV_APPROVAL_PHRASE, "medium")
    jquants_gate = ProviderApprovalGate(True, False, JQUANTS_APPROVAL_PHRASE, "medium")
    manual_gate = ProviderApprovalGate(False, True, MANUAL_IMPORT_APPROVAL_PHRASE, "medium")
    return MarketDataProviderRegistry(
        (
            ProviderSpec(
                provider_id="jquants",
                markets=("JP",),
                role="primary",
                capabilities=(ProviderCapability.JP_EQUITY_DAILY, ProviderCapability.GATED_LIVE_HTTP),
                priority=10,
                live_http=True,
                manual_fallback=False,
                adjustment="vendor_adjusted_daily_quotes",
                source_timestamp_policy="fetch_time_when_gated_refresh_runs",
                approval_gate=jquants_gate,
                expected_coverage="JP listed equities including alphanumeric codes such as 285A",
                recommendation="primary_after_explicit_jquants_refresh_approval",
                notes="contract capped; cache-first and no secret printing",
            ),
            ProviderSpec(
                provider_id="stooq_manual",
                markets=("JP", "US", "ETF"),
                role="manual_fallback",
                capabilities=(ProviderCapability.MANUAL_CSV_INGEST, ProviderCapability.JP_EQUITY_DAILY, ProviderCapability.US_EQUITY_DAILY),
                priority=20,
                live_http=False,
                manual_fallback=True,
                adjustment="provider_csv_as_supplied",
                source_timestamp_policy="manual_file_mtime_or_import_time",
                approval_gate=manual_gate,
                expected_coverage="manual files supplied by human dropzone",
                recommendation="fallback_not_primary",
                notes="multi-file CSV fallback; raw broker/manual data must not be printed",
            ),
            ProviderSpec(
                provider_id="yahoo_manual",
                markets=("JP", "US", "ETF"),
                role="manual_fallback",
                capabilities=(ProviderCapability.MANUAL_CSV_INGEST,),
                priority=30,
                live_http=False,
                manual_fallback=True,
                adjustment="manual_export_as_supplied",
                source_timestamp_policy="manual_export_time",
                approval_gate=manual_gate,
                expected_coverage="human browser export dependent",
                recommendation="secondary_manual_fallback",
                notes="kept manual to avoid ToS-unclear automation in source code",
            ),
            ProviderSpec(
                provider_id="stooq_live_gated",
                markets=("US", "ETF", "JP"),
                role="gated_live_fallback",
                capabilities=(ProviderCapability.GATED_LIVE_HTTP, ProviderCapability.US_EQUITY_DAILY, ProviderCapability.ETF_DAILY),
                priority=40,
                live_http=True,
                manual_fallback=False,
                adjustment="stooq_csv_adjustment_unknown",
                source_timestamp_policy="fetch_time",
                approval_gate=public_live_gate,
                expected_coverage="best-effort Stooq symbol coverage",
                recommendation="approval_package_only_until_enabled",
                notes="dry-run plan only in v36",
            ),
            ProviderSpec(
                provider_id="alpha_vantage_gated",
                markets=("US", "ETF"),
                role="gated_live_candidate",
                capabilities=(ProviderCapability.GATED_LIVE_HTTP, ProviderCapability.US_EQUITY_DAILY, ProviderCapability.ETF_DAILY),
                priority=50,
                live_http=True,
                manual_fallback=False,
                adjustment="vendor_adjusted_or_raw_configured_later",
                source_timestamp_policy="fetch_time",
                approval_gate=public_live_gate,
                expected_coverage="US equities and ETFs subject to API quota",
                recommendation="evaluate_license_and_quota_before_live",
                notes="API key value must never be printed",
            ),
            ProviderSpec(
                provider_id="tiingo_gated",
                markets=("US", "ETF"),
                role="paid_live_candidate",
                capabilities=(ProviderCapability.GATED_LIVE_HTTP, ProviderCapability.US_EQUITY_DAILY, ProviderCapability.ETF_DAILY),
                priority=60,
                live_http=True,
                manual_fallback=False,
                adjustment="vendor_adjusted_or_raw_configured_later",
                source_timestamp_policy="fetch_time",
                approval_gate=public_live_gate,
                expected_coverage="US EOD provider candidate",
                recommendation="candidate_if_budget_approved",
                notes="paid/provider ToU review required",
            ),
            ProviderSpec(
                provider_id="polygon_gated",
                markets=("US", "ETF"),
                role="paid_primary_candidate",
                capabilities=(ProviderCapability.GATED_LIVE_HTTP, ProviderCapability.US_EQUITY_DAILY, ProviderCapability.ETF_DAILY),
                priority=70,
                live_http=True,
                manual_fallback=False,
                adjustment="vendor_adjusted_or_raw_configured_later",
                source_timestamp_policy="fetch_time",
                approval_gate=public_live_gate,
                expected_coverage="US primary candidate if budget allows",
                recommendation="long_term_primary_candidate",
                notes="paid/provider ToU review required",
            ),
            ProviderSpec(
                provider_id="eodhd_gated",
                markets=("US", "ETF", "JP"),
                role="paid_global_candidate",
                capabilities=(ProviderCapability.GATED_LIVE_HTTP, ProviderCapability.US_EQUITY_DAILY, ProviderCapability.ETF_DAILY),
                priority=80,
                live_http=True,
                manual_fallback=False,
                adjustment="vendor_adjusted_or_raw_configured_later",
                source_timestamp_policy="fetch_time",
                approval_gate=public_live_gate,
                expected_coverage="global EOD candidate",
                recommendation="defer_until_license_review",
                notes="global paid provider; no live call in v36",
            ),
        )
    )


def build_provider_coverage_matrix(
    registry: MarketDataProviderRegistry,
    *,
    markets: tuple[str, ...] = ("JP", "US", "ETF"),
) -> ProviderCoverageMatrix:
    rows: list[dict[str, Any]] = []
    for market in markets:
        for spec in registry.for_market(market):
            rows.append(
                {
                    "provider": spec.provider_id,
                    "market": market,
                    "role": spec.role,
                    "live_http": spec.live_http,
                    "approval_required": spec.approval_gate.requires_live_http_approval
                    or spec.approval_gate.requires_cache_write_approval,
                    "manual_fallback": spec.manual_fallback,
                    "expected_coverage": spec.expected_coverage,
                    "recommendation": spec.recommendation,
                }
            )
    return ProviderCoverageMatrix(tuple(rows))


def score_provider_freshness(
    *,
    ticker: str,
    market: str,
    provider: str,
    latest_date: str | None,
    reference_date: str,
) -> ProviderFreshnessScore:
    if not latest_date:
        return ProviderFreshnessScore(ticker, market, provider, None, reference_date, "unknown", None, "no_latest_date")
    try:
        latest = date.fromisoformat(latest_date[:10])
        ref = date.fromisoformat(reference_date[:10])
    except ValueError:
        return ProviderFreshnessScore(ticker, market, provider, latest_date, reference_date, "unknown", None, "unparseable_date")
    stale_days = max((ref - latest).days, 0)
    if stale_days <= 7:
        status = "fresh_enough"
    elif stale_days <= 30:
        status = "stale"
    else:
        status = "data_update_required"
    return ProviderFreshnessScore(
        ticker=ticker,
        market=market,
        provider=provider,
        latest_date=latest.isoformat(),
        reference_date=ref.isoformat(),
        freshness_status=status,
        stale_days=stale_days,
        reason=f"stale_days={stale_days}",
    )
