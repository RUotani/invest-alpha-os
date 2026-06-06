"""Pure price/volume metrics for fixture-only Early Discovery validation."""

from __future__ import annotations

from math import isfinite
from statistics import fmean
from typing import Sequence


def _valid_values(values: Sequence[float], *, minimum: int) -> tuple[float, ...] | None:
    if len(values) < minimum:
        return None
    normalized = tuple(float(value) for value in values)
    if not all(isfinite(value) and value >= 0.0 for value in normalized):
        return None
    return normalized


def compute_recent_return(prices: Sequence[float], window: int) -> float | None:
    """Return trailing price change using fixture/list inputs only."""

    if window < 2:
        return None
    values = _valid_values(prices, minimum=window)
    if values is None:
        return None
    start = values[-window]
    if start <= 0.0:
        return None
    return values[-1] / start - 1.0


def compute_moving_average_deviation(prices: Sequence[float], window: int) -> float | None:
    """Return last price deviation from a trailing moving average."""

    if window < 1:
        return None
    values = _valid_values(prices, minimum=window)
    if values is None:
        return None
    average = fmean(values[-window:])
    if average <= 0.0:
        return None
    return values[-1] / average - 1.0


def compute_volume_inflection(
    volumes: Sequence[float],
    short_window: int = 5,
    base_window: int = 20,
) -> float | None:
    """Compare recent fixture volume with the preceding low/base period."""

    if short_window < 1 or base_window < 1:
        return None
    values = _valid_values(volumes, minimum=short_window + base_window)
    if values is None:
        return None
    recent = fmean(values[-short_window:])
    base = fmean(values[-(short_window + base_window) : -short_window])
    if base <= 0.0:
        return None
    return recent / base - 1.0


def compute_relative_strength_series(
    asset_prices: Sequence[float],
    benchmark_prices: Sequence[float],
) -> list[float]:
    """Return normalized asset/benchmark relative strength with no I/O."""

    length = min(len(asset_prices), len(benchmark_prices))
    if length < 1:
        return []
    assets = _valid_values(asset_prices[-length:], minimum=length)
    benchmarks = _valid_values(benchmark_prices[-length:], minimum=length)
    if assets is None or benchmarks is None or assets[0] <= 0.0 or benchmarks[0] <= 0.0:
        return []
    out: list[float] = []
    for asset, benchmark in zip(assets, benchmarks, strict=True):
        if benchmark <= 0.0:
            return []
        asset_normalized = asset / assets[0]
        benchmark_normalized = benchmark / benchmarks[0]
        out.append(asset_normalized / benchmark_normalized)
    return out


def compute_rs_acceleration(
    asset_prices: Sequence[float],
    benchmark_prices: Sequence[float],
    short_window: int = 5,
    base_window: int = 20,
) -> float | None:
    """Return recent relative-strength slope minus the preceding base slope."""

    if short_window < 2 or base_window < 2:
        return None
    relative_strength = compute_relative_strength_series(asset_prices, benchmark_prices)
    required = short_window + base_window
    if len(relative_strength) < required:
        return None
    recent = relative_strength[-short_window:]
    base = relative_strength[-required:-short_window]
    recent_slope = (recent[-1] - recent[0]) / (short_window - 1)
    base_slope = (base[-1] - base[0]) / (base_window - 1)
    return recent_slope - base_slope
