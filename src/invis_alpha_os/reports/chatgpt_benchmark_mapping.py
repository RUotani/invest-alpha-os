"""Benchmark mapping helpers for forward validation."""

from __future__ import annotations


US_BENCHMARK_CANDIDATES: tuple[str, ...] = ("SPY", "^GSPC", "VTI")
JP_BENCHMARK_CANDIDATES: tuple[str, ...] = ("TOPIX", "^TOPX", "1306", "1321", "^N225")


def infer_benchmark_for_candidate(*, market: str, ticker: str) -> str | None:
    market_norm = (market or "").strip().upper()
    ticker_norm = (ticker or "").strip().upper()
    if ticker_norm in US_BENCHMARK_CANDIDATES or ticker_norm in JP_BENCHMARK_CANDIDATES:
        return ticker_norm
    if market_norm in ("US", "ETF"):
        return US_BENCHMARK_CANDIDATES[0]
    if market_norm == "JP":
        return JP_BENCHMARK_CANDIDATES[0]
    return None

