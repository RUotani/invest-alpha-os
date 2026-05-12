"""Observation-only momentum-style signals from daily OHLCV bars (Main E MVP).

No HTTP, no broker logic. Callers supply bar series (e.g. J-Quants daily bars rows).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TypedDict

# --- Data shape -----------------------------------------------------------------

_HORIZONS_DEFAULT: tuple[int, ...] = (5, 20, 60)


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


def detect_high_breakout(
    highs: Sequence[float],
    closes: Sequence[float],
    *,
    prior_days: int = 252,
) -> tuple[bool, float | None]:
    """Latest close >= max high of up to ``prior_days`` completed sessions before last (or shorter window)."""

    if len(highs) != len(closes) or len(closes) < 2:
        return False, None
    pri = highs[:-1]
    if not pri:
        return False, None
    take = min(len(pri), prior_days)
    win = pri[-take:]
    prior_max = max(float(x) for x in win)
    return float(closes[-1]) >= prior_max, prior_max


@dataclass(frozen=True)
class MomentumBreakdown:
    code: str
    bar_count: int
    labels: tuple[str, ...]
    score: int
    r5: float | None
    r20: float | None
    r60: float | None
    volume_spike: bool
    vol_avg25: float | None
    high_52w_breakout: bool


def score_momentum_candidate(
    *,
    has_breakout: bool,
    has_vol_spike: bool,
    r20: float | None,
    r60: float | None,
) -> tuple[int, list[str]]:
    """Simple transparent score: breakout > volume > dual positive momentum."""

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
    """Single-ticker labels + score from bar list (oldest first). Empty → ``None``."""

    if not bars:
        return None
    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    closes = [float(b["close"]) for b in bars]
    volumes = [float(b["volume"]) for b in bars]
    _ = lows  # reserved for future filters
    rets = calculate_returns(closes, _HORIZONS_DEFAULT)
    vol_spike, vol_avg = detect_volume_spike(volumes)
    breakout, _prior_h = detect_high_breakout(highs, closes)
    score, lbl = score_momentum_candidate(
        has_breakout=breakout,
        has_vol_spike=vol_spike,
        r20=rets.get(20),
        r60=rets.get(60),
    )
    return MomentumBreakdown(
        code=code,
        bar_count=len(bars),
        labels=tuple(lbl),
        score=score,
        r5=rets.get(5),
        r20=rets.get(20),
        r60=rets.get(60),
        volume_spike=vol_spike,
        vol_avg25=vol_avg,
        high_52w_breakout=breakout,
    )


def build_momentum_signals(codes_and_bars: Mapping[str, Sequence[DailyBar]]) -> list[MomentumBreakdown]:
    """Analyze each ticker; rank by score desc, then ``r20`` desc."""

    rows: list[MomentumBreakdown] = []
    for code, series in codes_and_bars.items():
        m = analyze_bars_for_code(code, series)
        if m is not None:
            rows.append(m)

    def sort_key(x: MomentumBreakdown) -> tuple[int, float]:
        r20 = x.r20 if x.r20 is not None else -1e9
        return (-x.score, -r20)

    rows.sort(key=sort_key)
    return rows


# --- Deterministic synthetic series (dry-run / tests; no network) ---------------

def _seed_u32(code: str) -> int:
    h = hashlib.sha256(code.encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big")


def momentum_row_public_dict(m: MomentumBreakdown) -> dict[str, Any]:
    """JSON-safe dict for CLI (no secrets)."""

    return {
        "code": m.code,
        "bar_count": m.bar_count,
        "labels": list(m.labels),
        "score": m.score,
        "r5": m.r5,
        "r20": m.r20,
        "r60": m.r60,
        "volume_25d_spike": m.volume_spike,
        "vol_avg25_prior": m.vol_avg25,
        "high_52w_breakout": m.high_52w_breakout,
    }


def synthetic_bars_for_code(code: str, n: int = 320) -> list[DailyBar]:
    """Produce **deterministic** OHLCV for dry-run CLI/daily (no secrets, no API)."""

    if n < 30:
        n = 30
    seed = _seed_u32(code)
    bars: list[DailyBar] = []
    close = 1000.0 + (seed % 500) / 10.0
    vol_base = 50_000 + (seed % 10_000)
    for i in range(n):
        # quasi-random walk + occasional volume spike on last bar for some seeds
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
