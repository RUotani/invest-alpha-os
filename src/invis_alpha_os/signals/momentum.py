"""Observation-only momentum-style signals from daily OHLCV bars (Main E MVP).

No HTTP, no broker logic. Callers supply bar series (e.g. J-Quants daily bars rows).

Main O: Momentum Score v2 adds richer dispersion while keeping legacy ``score`` for compatibility.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TypedDict

# --- Horizon defaults (sessions; need h+1 closes for return h→now) -------------
_HORIZONS_DEFAULT: tuple[int, ...] = (5, 20, 60)
_HORIZONS_WITH_120: tuple[int, ...] = (*_HORIZONS_DEFAULT, 120)

# --- Momentum Score v2 (deterministic constants; tweak in one place) ------------
# Returns are fractional (e.g. 0.10 = +10%); thresholds are readable in code + tests.

SCORE_V2_R20_POS = 2
SCORE_V2_R60_POS = 2
SCORE_V2_R120_POS = 1
SCORE_V2_BREAKOUT = 2
SCORE_V2_NEAR_PRIOR_HIGH_PCT_THRESHOLD = (
    -0.05  # within 5% of trailing high window → still "near highs" for ranking spread
)
SCORE_V2_NEAR_PRIOR_HIGH = 1
SCORE_V2_VOLUME_RATIO_THRESHOLD = 2.0  # spike vs trailing average (not spike boolean)
SCORE_V2_VOLUME_RATIO_SCORE = 1
SCORE_V2_PULLBACK_PENALTY = -1  # short pullback vs intact medium uptrend (diagnostic only)
SCORE_V2_OVERHEAT_R20 = 0.5
SCORE_V2_OVERHEAT_R60 = 1.0
SCORE_V2_OVERHEAT_PENALTY = -1
SCORE_V2_MIN_BARS_FULL_CONTEXT = (
    121  # align with enough_120d (121 closes ⇒ 120 trailing sessions incl. returns)
)
SCORE_V2_LIMITED_HISTORY_PENALTY = -1

_PRIOR_HIGH_DAYS_DEFAULT = (
    252  # ~52 weeks of sessions; aligns with breakout / "52w-style" wording in UI
)


class DailyBar(TypedDict):
    """Oldest-first daily bar (dates any ISO-like string)."""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


def _f(x: Any) -> float:
    return float(x)


def bars_from_rows(rows: Iterable[Mapping[str, Any]]) -> list[DailyBar]:
    """Normalize iterable of dict-like rows to ``DailyBar`` (oldest-first; caller should sort)."""

    out: list[DailyBar] = []
    for r in rows:
        out.append(
            {
                "date": str(r.get("date", "")).strip(),
                "open": _f(r.get("open", 0)),
                "high": _f(r.get("high", 0)),
                "low": _f(r.get("low", 0)),
                "close": _f(r.get("close", 0)),
                "volume": _f(r.get("volume", 0)),
            }
        )
    return out


def load_bars_json_file(path: Path) -> list[DailyBar]:
    """Load sanitized local JSON: a list of bar objects."""

    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("bars JSON must be a list")
    return bars_from_rows(data)


# --- Pure calculations -----------------------------------------------------------

def calculate_returns(
    closes: Sequence[float],
    horizons: Sequence[int] = _HORIZONS_DEFAULT,
) -> dict[int, float | None]:
    """Trailing return from ``h`` sessions ago to last close: C[-1]/C[-(h+1)]-1."""

    n = len(closes)
    out: dict[int, float | None] = {}
    for h in horizons:
        if h < 1 or n < h + 1:
            out[int(h)] = None
            continue
        old = float(closes[-(h + 1)])
        new = float(closes[-1])
        if old == 0:
            out[int(h)] = None
        else:
            out[int(h)] = (new / old) - 1.0
    return out


def detect_volume_spike(
    volumes: Sequence[float],
    *,
    multiplier: float = 3.0,
    lookback: int = 25,
) -> tuple[bool, float | None]:
    """Latest volume >= ``multiplier`` × mean of prior ``lookback`` volumes (excludes latest)."""

    if lookback < 1 or len(volumes) < lookback + 1:
        return False, None
    window = volumes[-(lookback + 1) : -1]
    avg = sum(float(x) for x in window) / lookback
    last = float(volumes[-1])
    if avg <= 0:
        return False, avg
    return last >= multiplier * avg, avg


def volume_ratio_25d_prior_mean(volumes: Sequence[float]) -> float | None:
    """Latest volume / mean prior 25 sessions (exclusive of latest bar). Observation-only breadth."""

    lookback = 25
    if len(volumes) < lookback + 1:
        return None
    window = volumes[-(lookback + 1) : -1]
    avg = sum(float(x) for x in window) / lookback
    if avg <= 0:
        return None
    return float(volumes[-1]) / avg


def prior_high_window_stats(
    highs: Sequence[float],
    *,
    prior_days: int = _PRIOR_HIGH_DAYS_DEFAULT,
) -> tuple[float | None, int]:
    """Max ``high`` over up to ``prior_days`` completed sessions before the last bar.

    Returns ``(prior_max_high, bars_used)`` or ``(None, 0)`` if undefined.
    """

    pri = highs[:-1]
    if not pri:
        return None, 0
    take = min(len(pri), prior_days)
    win = pri[-take:]
    return max(float(x) for x in win), take


def high_distance_vs_prior_high_pct(closes: Sequence[float], highs: Sequence[float]) -> float | None:
    """Close[-1] / max(prior-session highs in ~252d window) - 1.

    Near 0 ⇒ trading near recent range top; complements boolean breakout."""
    pm, used = prior_high_window_stats(highs, prior_days=_PRIOR_HIGH_DAYS_DEFAULT)
    if pm is None or used < 1 or len(closes) < 2:
        return None
    c = float(closes[-1])
    if pm == 0:
        return None
    return (c / pm) - 1.0


def detect_high_breakout(
    highs: Sequence[float],
    closes: Sequence[float],
    *,
    prior_days: int = _PRIOR_HIGH_DAYS_DEFAULT,
) -> tuple[bool, float | None]:
    """Latest close >= max high of up to ``prior_days`` completed sessions before last (or shorter window)."""

    pm, used = prior_high_window_stats(highs, prior_days=prior_days)
    if pm is None or used < 1 or len(closes) < 2:
        return False, None
    return float(closes[-1]) >= pm, pm


def overheat_from_returns(r20: float | None, r60: float | None) -> bool:
    """Extreme trailing strength — label only; does not remove from ranking."""

    if r20 is not None and r20 > SCORE_V2_OVERHEAT_R20:
        return True
    if r60 is not None and r60 > SCORE_V2_OVERHEAT_R60:
        return True
    return False


def data_quality_flags(bar_count: int) -> dict[str, bool]:
    """Explicit bar-window sufficiency flags (sessions)."""

    return {
        "enough_60d": bar_count >= 61,
        "enough_120d": bar_count >= 121,
        "enough_252d": bar_count >= 253,
    }


def trend_quality_summary(
    *,
    r20: float | None,
    r60: float | None,
    r120: float | None,
) -> str:
    """Compact alignment label: count positive horizons among those computable."""

    slots: list[tuple[str, float | None]] = [("r20", r20), ("r60", r60), ("r120", r120)]
    defined = [(k, v) for k, v in slots if v is not None]
    if not defined:
        return "no_horizons"
    pos_n = sum(1 for _, v in defined if v is not None and v > 0)
    return f"{pos_n}_of_{len(defined)}_positive"


def compute_score_v2(
    *,
    bar_count: int,
    has_breakout: bool,
    r5: float | None,
    r20: float | None,
    r60: float | None,
    r120: float | None,
    high_dist_pct: float | None,
    vol_ratio_25d: float | None,
    overheat: bool,
) -> tuple[int, dict[str, int]]:
    """Return ``(score_v2, score_v2_components)`` with additive integer parts (explainable breakdown)."""

    parts: dict[str, int] = {}

    def add(key: str, delta: int) -> None:
        if delta != 0:
            parts[key] = parts.get(key, 0) + delta

    if r20 is not None and r20 > 0:
        add("r20_positive", SCORE_V2_R20_POS)
    if r60 is not None and r60 > 0:
        add("r60_positive", SCORE_V2_R60_POS)
    if r120 is not None and r120 > 0:
        add("r120_positive", SCORE_V2_R120_POS)
    if has_breakout:
        add("high_52w_breakout", SCORE_V2_BREAKOUT)

    # Near prior-window high — information beyond boolean breakout when not quite equal.
    if high_dist_pct is not None and high_dist_pct >= SCORE_V2_NEAR_PRIOR_HIGH_PCT_THRESHOLD:
        add("near_prior_high_band", SCORE_V2_NEAR_PRIOR_HIGH)

    if vol_ratio_25d is not None and vol_ratio_25d >= SCORE_V2_VOLUME_RATIO_THRESHOLD:
        add("volume_ratio_25d_hot", SCORE_V2_VOLUME_RATIO_SCORE)

    if r5 is not None and r20 is not None and r5 < 0 and r20 > 0:
        add("short_pullback_within_uptrend", SCORE_V2_PULLBACK_PENALTY)

    if overheat:
        add("overheat_penalty", SCORE_V2_OVERHEAT_PENALTY)

    if bar_count < SCORE_V2_MIN_BARS_FULL_CONTEXT:
        add("limited_history_penalty", SCORE_V2_LIMITED_HISTORY_PENALTY)

    return sum(parts.values()), dict(sorted(parts.items()))


@dataclass(frozen=True)
class MomentumBreakdown:
    code: str
    bar_count: int
    labels: tuple[str, ...]
    score: int
    r5: float | None
    r20: float | None
    r60: float | None
    r120: float | None
    volume_spike: bool
    vol_avg25: float | None
    volume_ratio_25d: float | None
    high_52w_breakout: bool
    high_52w_distance_pct: float | None
    trend_quality: str
    overheat_flag: bool
    data_quality: tuple[tuple[str, bool], ...]
    score_v2: int
    score_v2_components: tuple[tuple[str, int], ...]


def score_momentum_candidate(
    *,
    has_breakout: bool,
    has_vol_spike: bool,
    r20: float | None,
    r60: float | None,
) -> tuple[int, list[str]]:
    """Legacy Main E score: breakout > volume > dual positive momentum (unchanged for tests/UI continuity)."""

    score = 0
    labels: list[str] = []
    if has_breakout:
        score += 3
        labels.append("high_52w_breakout")
    if has_vol_spike:
        score += 2
        labels.append("volume_25d_spike")
    if r20 is not None and r60 is not None and r20 > 0 and r60 > 0:
        score += 1
        labels.append("positive_20d_60d_momentum")
    return score, labels


def analyze_bars_for_code(code: str, bars: Sequence[DailyBar]) -> MomentumBreakdown | None:
    """Single-ticker labels + scores from bar list (oldest first). Empty → ``None``."""

    if not bars:
        return None
    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    closes = [float(b["close"]) for b in bars]
    volumes = [float(b["volume"]) for b in bars]
    _ = lows

    rets = calculate_returns(closes, _HORIZONS_WITH_120)
    r5, r20, r60 = rets.get(5), rets.get(20), rets.get(60)
    r120 = rets.get(120)

    vol_spike, vol_avg = detect_volume_spike(volumes)
    vol_ratio = volume_ratio_25d_prior_mean(volumes)
    breakout, _prior_h = detect_high_breakout(highs, closes)
    high_pct = high_distance_vs_prior_high_pct(closes, highs)

    score, lbl = score_momentum_candidate(
        has_breakout=breakout,
        has_vol_spike=vol_spike,
        r20=r20,
        r60=r60,
    )
    dq = data_quality_flags(len(bars))
    oh = overheat_from_returns(r20, r60)
    tq = trend_quality_summary(r20=r20, r60=r60, r120=r120)
    sv2, comps = compute_score_v2(
        bar_count=len(bars),
        has_breakout=breakout,
        r5=r5,
        r20=r20,
        r60=r60,
        r120=r120,
        high_dist_pct=high_pct,
        vol_ratio_25d=vol_ratio,
        overheat=oh,
    )

    return MomentumBreakdown(
        code=code,
        bar_count=len(bars),
        labels=tuple(lbl),
        score=score,
        r5=r5,
        r20=r20,
        r60=r60,
        r120=r120,
        volume_spike=vol_spike,
        vol_avg25=vol_avg,
        volume_ratio_25d=vol_ratio,
        high_52w_breakout=breakout,
        high_52w_distance_pct=high_pct,
        trend_quality=tq,
        overheat_flag=oh,
        data_quality=tuple(sorted(dq.items())),
        score_v2=sv2,
        score_v2_components=tuple(sorted(comps.items())),
    )

def build_momentum_signals(codes_and_bars: Mapping[str, Sequence[DailyBar]]) -> list[MomentumBreakdown]:
    """Analyze each ticker; rank by score_v2 desc, then r20, r60, code asc."""

    rows: list[MomentumBreakdown] = []
    for code, series in codes_and_bars.items():
        m = analyze_bars_for_code(code, series)
        if m is not None:
            rows.append(m)

    neg_inf = -1e18

    def sort_key(x: MomentumBreakdown) -> tuple[int, float, float, str]:
        r20e = float(x.r20) if x.r20 is not None else neg_inf
        r60e = float(x.r60) if x.r60 is not None else neg_inf
        return (-x.score_v2, -r20e, -r60e, x.code)

    rows.sort(key=sort_key)
    return rows


# --- Deterministic synthetic series (dry-run / tests; no network) ---------------

def _seed_u32(code: str) -> int:
    h = hashlib.sha256(code.encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big")


def momentum_row_public_dict(m: MomentumBreakdown, *, bars_source: str | None = None) -> dict[str, Any]:
    """JSON-safe dict for CLI (no secrets)."""

    out: dict[str, Any] = {
        "code": m.code,
        "bar_count": m.bar_count,
        "labels": list(m.labels),
        "score": m.score,
        "score_v2": m.score_v2,
        "score_v2_components": dict(m.score_v2_components),
        "r5": m.r5,
        "r20": m.r20,
        "r60": m.r60,
        "r120": m.r120,
        "trend_quality": m.trend_quality,
        "volume_25d_spike": m.volume_spike,
        "vol_avg25_prior": m.vol_avg25,
        "volume_ratio_25d": m.volume_ratio_25d,
        "high_52w_breakout": m.high_52w_breakout,
        "high_52w_distance_pct": m.high_52w_distance_pct,
        "overheat_flag": m.overheat_flag,
        "data_quality": dict(m.data_quality),
    }
    if bars_source is not None:
        out["bars_source"] = bars_source
    return out


def synthetic_bars_for_code(code: str, n: int = 320) -> list[DailyBar]:
    """Produce **deterministic** OHLCV for dry-run CLI/daily (no secrets, no API)."""

    if n < 30:
        n = 30
    seed = _seed_u32(code)
    bars: list[DailyBar] = []
    close = 1000.0 + (seed % 500) / 10.0
    vol_base = 50_000 + (seed % 10_000)
    for i in range(n):
        shake = ((seed >> (i % 16)) ^ (i * 1103515245 + 12345)) & 0xFFFF
        drift = (shake % 17 - 8) * 0.15
        close = max(10.0, close + drift)
        high = close + abs(drift) * 0.5 + (shake % 5)
        low = max(5.0, close - abs(drift) * 0.6 - (shake % 3))
        open_ = close - drift * 0.3
        vol = float(vol_base + (shake % 2000))
        if i == n - 1 and (seed % 7 == 0):
            vol = vol * 4.5
        if i == n - 1 and (seed % 11 == 3):
            high = max(high, close * 1.08)
            close = high
        d = f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"
        bars.append(
            {
                "date": d,
                "open": round(open_, 4),
                "high": round(high, 4),
                "low": round(low, 4),
                "close": round(close, 4),
                "volume": round(vol, 2),
            }
        )
    return bars
