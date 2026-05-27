"""Cache-backed quant metrics for Weekly Candidate Brief email cards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

from invis_alpha_os.data.jquants_daily_bars_cache import load_jquants_daily_bars_cache
from invis_alpha_os.data.us_daily_bars_cache import load_us_daily_bars_cache
from invis_alpha_os.signals.momentum import DailyBar, calculate_returns


@dataclass(frozen=True)
class CandidateQuantMetrics:
    symbol: str
    source: str
    latest_bar_date: str | None
    latest_close: float | None
    ret_5d_pct: float | None
    ret_20d_pct: float | None
    ret_60d_pct: float | None
    ma_25: float | None
    ma_75: float | None
    ma_200: float | None
    dist_ma_25_pct: float | None
    dist_ma_75_pct: float | None
    dist_ma_200_pct: float | None
    high_52w: float | None
    low_52w: float | None
    dist_52w_high_pct: float | None
    dist_52w_low_pct: float | None
    latest_volume: float | None
    avg_volume_20d: float | None
    volume_ratio_20d: float | None
    freshness_label: str
    missing_reason: str | None


def _mean_last(vals: Sequence[float], n: int) -> float | None:
    if len(vals) < n:
        return None
    w = vals[-n:]
    return sum(w) / float(n) if w else None


def _dist(latest: float | None, base: float | None) -> float | None:
    if latest is None or base is None or base == 0:
        return None
    return latest / base - 1.0


def _freshness_label(*, latest_bar_date: str | None, report_date: str) -> str:
    if not latest_bar_date:
        return "unknown"
    try:
        d_latest = date.fromisoformat(latest_bar_date)
        d_report = date.fromisoformat(report_date)
    except ValueError:
        return "unknown"
    delta = (d_report - d_latest).days
    if delta <= 7:
        return "fresh"
    return f"stale: latest bar older than 7 calendar days ({delta}d)"


def _load_bars(symbol: str, market: str) -> tuple[list[DailyBar], str] | None:
    if market == "JP":
        loaded = load_jquants_daily_bars_cache(symbol)
        if loaded is None:
            return None
        return loaded[0], "cache:jquants_daily_bars"
    loaded = load_us_daily_bars_cache(symbol)
    if loaded is None:
        return None
    return loaded[0], "cache:us_daily_bars"


def compute_candidate_quant_metrics(*, symbol: str, market: str, report_date: str) -> CandidateQuantMetrics:
    loaded = _load_bars(symbol, market)
    if loaded is None:
        return CandidateQuantMetrics(
            symbol=symbol,
            source="cache",
            latest_bar_date=None,
            latest_close=None,
            ret_5d_pct=None,
            ret_20d_pct=None,
            ret_60d_pct=None,
            ma_25=None,
            ma_75=None,
            ma_200=None,
            dist_ma_25_pct=None,
            dist_ma_75_pct=None,
            dist_ma_200_pct=None,
            high_52w=None,
            low_52w=None,
            dist_52w_high_pct=None,
            dist_52w_low_pct=None,
            latest_volume=None,
            avg_volume_20d=None,
            volume_ratio_20d=None,
            freshness_label="unknown",
            missing_reason="cache file not found or invalid",
        )
    bars, source = loaded
    closes = [float(b["close"]) for b in bars]
    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    volumes = [float(b["volume"]) for b in bars]
    latest_close = closes[-1] if closes else None
    latest_volume = volumes[-1] if volumes else None
    latest_bar_date = str(bars[-1].get("date", "")).strip() if bars else None
    returns = calculate_returns(closes, (5, 20, 60))

    ma25 = _mean_last(closes, 25)
    ma75 = _mean_last(closes, 75)
    ma200 = _mean_last(closes, 200)

    lookback = closes[-252:] if len(closes) >= 252 else closes
    high52 = max(highs[-252:] if len(highs) >= 252 else highs) if highs else None
    low52 = min(lows[-252:] if len(lows) >= 252 else lows) if lows else None
    avgv20 = _mean_last(volumes, 20)

    missing: list[str] = []
    if len(closes) < 60:
        missing.append(f"insufficient bars for 60D return (got {len(closes)})")
    if len(closes) < 200:
        missing.append(f"insufficient bars for 200D MA (got {len(closes)})")
    if len(lookback) < 252:
        missing.append(f"partial 52W range (got {len(lookback)} bars)")
    if avgv20 is None:
        missing.append("insufficient bars for 20D volume average")

    return CandidateQuantMetrics(
        symbol=symbol,
        source=source,
        latest_bar_date=latest_bar_date or None,
        latest_close=latest_close,
        ret_5d_pct=returns.get(5),
        ret_20d_pct=returns.get(20),
        ret_60d_pct=returns.get(60),
        ma_25=ma25,
        ma_75=ma75,
        ma_200=ma200,
        dist_ma_25_pct=_dist(latest_close, ma25),
        dist_ma_75_pct=_dist(latest_close, ma75),
        dist_ma_200_pct=_dist(latest_close, ma200),
        high_52w=high52,
        low_52w=low52,
        dist_52w_high_pct=_dist(latest_close, high52),
        dist_52w_low_pct=_dist(latest_close, low52),
        latest_volume=latest_volume,
        avg_volume_20d=avgv20,
        volume_ratio_20d=_dist(latest_volume, avgv20) + 1.0 if latest_volume is not None and avgv20 not in (None, 0) else None,
        freshness_label=_freshness_label(latest_bar_date=latest_bar_date or None, report_date=report_date),
        missing_reason="; ".join(missing) if missing else None,
    )


def fmt_num(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "not available in cache"
    return f"{value:.{digits}f}"


def fmt_pct(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "not available in cache"
    return f"{value * 100:.{digits}f}%"
