"""Cache-backed quant metrics for Weekly Candidate Brief email cards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

from invis_alpha_os.data.jquants_daily_bars_cache import load_jquants_daily_bars_cache
from invis_alpha_os.data.us_daily_bars_cache import load_us_daily_bars_cache
from invis_alpha_os.signals.momentum import DailyBar, calculate_returns

_JP_MARKET_ALIASES = {"JP", "JPN", "TSE", "TYO"}


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
    freshness_classification: str | None = None
    stale_days: int | None = None
    freshness_reason: str | None = None
    timing_impact: str | None = None


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
        return "不明"
    try:
        d_latest = date.fromisoformat(latest_bar_date)
        d_report = date.fromisoformat(report_date)
    except ValueError:
        return "不明"
    delta = (d_report - d_latest).days
    if delta <= 7:
        return "最新圏"
    return f"要更新（直近データが7日超過: {delta}日）"


def _freshness_details(*, latest_bar_date: str | None, report_date: str) -> tuple[str, int | None, str, str]:
    if not latest_bar_date:
        return (
            "cache_missing",
            None,
            "価格キャッシュが見つからないため鮮度判定不可",
            "実タイミング判断不可。データ更新を優先。",
        )
    try:
        d_latest = date.fromisoformat(latest_bar_date)
        d_report = date.fromisoformat(report_date)
    except ValueError:
        return (
            "cache_missing",
            None,
            "日付形式が不正なため鮮度判定不可",
            "実タイミング判断不可。データ形式確認が必要。",
        )
    delta = max((d_report - d_latest).days, 0)
    if delta <= 7:
        return ("fresh", delta, f"直近データが{delta}日差で最新圏", "通常のタイミング判断が可能。")
    if delta <= 30:
        return (
            "stale",
            delta,
            f"直近データが{delta}日古い",
            "短期タイミング判断の確度低下。監視優先。",
        )
    return (
        "data_update_required",
        delta,
        f"直近データが{delta}日古い",
        "実タイミング判断不可。テーマ深掘りのみ可。",
    )


def _normalize_market(raw_market: str) -> str:
    return raw_market.strip().upper()


def _jp_symbol_candidates(symbol: str) -> list[str]:
    s = symbol.strip()
    base = s[:-2] if s.upper().endswith(".T") else s
    raw = [s, base, f"{base}.T", f"{base} JP", f"{base}.JP"]
    out: list[str] = []
    for item in raw:
        key = item.strip()
        if key and key not in out:
            out.append(key)
    return out


def _load_bars(symbol: str, market: str) -> tuple[list[DailyBar], str, list[str]] | None:
    market_norm = _normalize_market(market)
    if market_norm in _JP_MARKET_ALIASES:
        tried = _jp_symbol_candidates(symbol)
        for candidate in tried:
            loaded = load_jquants_daily_bars_cache(candidate)
            if loaded is None:
                continue
            return loaded[0], f"cache:jquants_daily_bars:{candidate}", tried
        return None
    tried = [symbol.strip()]
    for candidate in tried:
        loaded = load_us_daily_bars_cache(candidate)
        if loaded is None:
            continue
        return loaded[0], f"cache:us_daily_bars:{candidate}", tried
    return None


def compute_candidate_quant_metrics(*, symbol: str, market: str, report_date: str) -> CandidateQuantMetrics:
    market_norm = _normalize_market(market)
    tried_symbols = _jp_symbol_candidates(symbol) if market_norm in _JP_MARKET_ALIASES else [symbol.strip()]
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
            missing_reason=(
                f"キャッシュ未検出（market={market_norm or 'UNKNOWN'}; tried={','.join(tried_symbols)}）"
            ),
            freshness_classification="cache_missing",
            stale_days=None,
            freshness_reason="価格キャッシュが見つからないため鮮度判定不可",
            timing_impact="実タイミング判断不可。データ更新を優先。",
        )
    if len(loaded) == 2:
        bars, source = loaded  # backward-compatible for test monkeypatch
    else:
        bars, source, _ = loaded
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
        missing.append(f"データ本数不足（60日騰落率: {len(closes)}本）")
    if len(closes) < 200:
        missing.append(f"データ本数不足（200日移動平均線: {len(closes)}本）")
    if len(lookback) < 252:
        missing.append(f"一部期間のみの52週レンジ（{len(lookback)}本）")
    if avgv20 is None:
        missing.append("データ本数不足（20日平均出来高）")

    freshness_classification, stale_days, freshness_reason, timing_impact = _freshness_details(
        latest_bar_date=latest_bar_date or None,
        report_date=report_date,
    )
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
        freshness_classification=(
            "partial_history"
            if missing and freshness_classification in {"fresh", "stale"}
            else freshness_classification
        ),
        stale_days=stale_days,
        freshness_reason=freshness_reason,
        timing_impact=timing_impact,
    )


def fmt_num(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "キャッシュ内にデータなし"
    return f"{value:.{digits}f}"


def fmt_pct(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "キャッシュ内にデータなし"
    return f"{value * 100:.{digits}f}%"
