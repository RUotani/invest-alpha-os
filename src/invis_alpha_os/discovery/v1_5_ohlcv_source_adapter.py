"""v1.5 read-only OHLCV source adapter (fixture-only default; live gated)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

from invis_alpha_os.discovery.early_discovery_score import EarlyDiscoveryInputs
from invis_alpha_os.discovery.price_volume_metrics import (
    compute_moving_average_deviation,
    compute_recent_return,
    compute_rs_acceleration,
    compute_volume_inflection,
)

V15_READONLY_APPROVAL_PHRASE = (
    "承認: v1.5 read-only price/volume MVP validationのみ YES / "
    "cache write・broker・trading・import・secret表示 NO"
)

V15_RECENT_RETURN_WINDOW = 20
V15_MA_DEVIATION_WINDOW = 20
V15_VOLUME_SHORT_WINDOW = 5
V15_VOLUME_BASE_WINDOW = 20
V15_RS_SHORT_WINDOW = 5
V15_RS_BASE_WINDOW = 20


class V15OhlcvAdapterMode(str, Enum):
    FIXTURE_ONLY = "fixture_only"
    LIVE_READ_ONLY = "live_read_only"


@dataclass(frozen=True)
class OhlcvBar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class OhlcvSeries:
    symbol: str
    market: str
    bars: tuple[OhlcvBar, ...]
    source: str
    adjustment: str = "unknown"


@dataclass(frozen=True)
class V15ReadonlyGateResult:
    allowed: bool
    reason: str
    adapter_mode: V15OhlcvAdapterMode
    approval_phrase: str | None = None


class V15OhlcvSourceAdapter(ABC):
    """Abstract read-only OHLCV source for v1.5 validation (no cache write)."""

    name: str = "abstract"
    mode: V15OhlcvAdapterMode = V15OhlcvAdapterMode.FIXTURE_ONLY

    @abstractmethod
    def fetch_series(self, symbol: str, *, market: str) -> OhlcvSeries | None:
        raise NotImplementedError

    def health(self) -> dict[str, str]:
        return {
            "adapter": self.name,
            "mode": self.mode.value,
            "cache_write": "forbidden",
            "network": "disabled" if self.mode == V15OhlcvAdapterMode.FIXTURE_ONLY else "gated",
        }


class FixtureV15OhlcvSourceAdapter(V15OhlcvSourceAdapter):
    """In-memory fixture adapter; never performs network or file I/O."""

    name = "fixture_v15"
    mode = V15OhlcvAdapterMode.FIXTURE_ONLY

    def __init__(self, fixtures: Mapping[str, OhlcvSeries]) -> None:
        self._fixtures = dict(fixtures)

    def fetch_series(self, symbol: str, *, market: str) -> OhlcvSeries | None:
        series = self._fixtures.get(symbol)
        if series is None:
            return None
        if series.market.strip().upper() != market.strip().upper():
            return None
        return series


def evaluate_v15_readonly_gate(
    *,
    adapter_mode: V15OhlcvAdapterMode,
    allow_live_fetch: bool = False,
    approval_phrase: str | None = None,
) -> V15ReadonlyGateResult:
    """Return whether the adapter mode may run under current approvals."""

    if adapter_mode == V15OhlcvAdapterMode.FIXTURE_ONLY:
        return V15ReadonlyGateResult(
            allowed=True,
            reason="fixture_only_no_approval_required",
            adapter_mode=adapter_mode,
        )
    if allow_live_fetch and approval_phrase == V15_READONLY_APPROVAL_PHRASE:
        return V15ReadonlyGateResult(
            allowed=True,
            reason="live_read_only_explicitly_approved",
            adapter_mode=adapter_mode,
            approval_phrase=approval_phrase,
        )
    return V15ReadonlyGateResult(
        allowed=False,
        reason="live_read_only_not_approved",
        adapter_mode=adapter_mode,
        approval_phrase=V15_READONLY_APPROVAL_PHRASE,
    )


def _closes(series: OhlcvSeries) -> tuple[float, ...]:
    return tuple(bar.close for bar in series.bars)


def _volumes(series: OhlcvSeries) -> tuple[float, ...]:
    return tuple(bar.volume for bar in series.bars)


def build_early_discovery_inputs_from_series(
    asset: OhlcvSeries,
    *,
    benchmark: OhlcvSeries | None = None,
    theme_phase: str | None = None,
    portfolio_cash_ratio: float | None = None,
    single_stock_ratio: float | None = None,
) -> EarlyDiscoveryInputs:
    """Map fixture OHLCV series into EarlyDiscoveryInputs via pure metrics."""

    prices = _closes(asset)
    volumes = _volumes(asset)
    recent_return = compute_recent_return(prices, V15_RECENT_RETURN_WINDOW)
    ma_deviation = compute_moving_average_deviation(prices, V15_MA_DEVIATION_WINDOW)
    volume_inflection = compute_volume_inflection(
        volumes,
        short_window=V15_VOLUME_SHORT_WINDOW,
        base_window=V15_VOLUME_BASE_WINDOW,
    )
    rs_acceleration: float | None = None
    if benchmark is not None:
        rs_acceleration = compute_rs_acceleration(
            prices,
            _closes(benchmark),
            short_window=V15_RS_SHORT_WINDOW,
            base_window=V15_RS_BASE_WINDOW,
        )
    return EarlyDiscoveryInputs(
        theme_phase=theme_phase,
        recent_return=recent_return,
        ma_deviation=ma_deviation,
        volume_inflection=volume_inflection,
        rs_acceleration=rs_acceleration,
        portfolio_cash_ratio=portfolio_cash_ratio,
        single_stock_ratio=single_stock_ratio,
    )


def bars_from_closes_volumes(
    *,
    symbol: str,
    market: str,
    closes: Sequence[float],
    volumes: Sequence[float],
    source: str = "fixture",
) -> OhlcvSeries:
    """Build a minimal fixture series from parallel close/volume arrays."""

    length = min(len(closes), len(volumes))
    bars = tuple(
        OhlcvBar(
            date=f"day-{index:03d}",
            open=float(closes[index]),
            high=float(closes[index]),
            low=float(closes[index]),
            close=float(closes[index]),
            volume=float(volumes[index]),
        )
        for index in range(length)
    )
    return OhlcvSeries(symbol=symbol, market=market, bars=bars, source=source)
