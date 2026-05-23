"""Observation-only peer-relative return / correlation checks (cache-only callers).

No HTTP, no broker logic, no trade recommendations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from invis_alpha_os.config.loader import load_yaml
from invis_alpha_os.signals.momentum import DailyBar

_DEFAULT_WINDOW_DAYS = 20
_DEFAULT_DIVERGENCE_THRESHOLD = 0.05
_MIN_CORRELATION_IN_SYNC = 0.5


@dataclass(frozen=True)
class PeerSyncPairResult:
    anchor_symbol: str
    peer_symbol: str
    window_days: int
    aligned_sessions: int
    return_spread: float | None
    correlation: float | None
    status: str
    interpretation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "anchor_symbol": self.anchor_symbol,
            "peer_symbol": self.peer_symbol,
            "window_days": self.window_days,
            "aligned_sessions": self.aligned_sessions,
            "return_spread": self.return_spread,
            "correlation": self.correlation,
            "status": self.status,
            "interpretation": self.interpretation,
        }


def load_peer_map(path: Path) -> dict[str, list[str]]:
    """Load ``config/peer_map.yaml`` (anchor → peer list)."""

    raw = load_yaml(path)
    if not isinstance(raw, dict):
        return {}
    block = raw.get("peer_map")
    if not isinstance(block, dict):
        return {}
    out: dict[str, list[str]] = {}
    for anchor, peers in block.items():
        anchor_s = str(anchor).strip().upper()
        if not anchor_s:
            continue
        peer_list: list[str] = []
        if isinstance(peers, list):
            for p in peers:
                ps = str(p).strip().upper()
                if ps and ps not in peer_list:
                    peer_list.append(ps)
        out[anchor_s] = peer_list
    return out


def _closes_by_date(bars: Sequence[DailyBar]) -> dict[str, float]:
    out: dict[str, float] = {}
    for b in bars:
        d = str(b.get("date", "")).strip()
        if not d:
            continue
        out[d] = float(b["close"])
    return out


def align_close_series(
    bars_anchor: Sequence[DailyBar],
    bars_peer: Sequence[DailyBar],
) -> tuple[list[float], list[float]]:
    """Intersect dates and return oldest-first close series (same length)."""

    a_map = _closes_by_date(bars_anchor)
    b_map = _closes_by_date(bars_peer)
    dates = sorted(set(a_map) & set(b_map))
    if not dates:
        return [], []
    a_closes = [a_map[d] for d in dates]
    b_closes = [b_map[d] for d in dates]
    return a_closes, b_closes


def _daily_log_returns(closes: Sequence[float]) -> list[float]:
    out: list[float] = []
    for i in range(1, len(closes)):
        prev = float(closes[i - 1])
        cur = float(closes[i])
        if prev <= 0 or cur <= 0:
            continue
        out.append(math.log(cur / prev))
    return out


def trailing_correlation(
    returns_a: Sequence[float],
    returns_b: Sequence[float],
    *,
    window: int,
) -> float | None:
    """Pearson correlation on the last ``window`` overlapping daily log returns."""

    if window < 2:
        return None
    n = min(len(returns_a), len(returns_b))
    if n < window:
        return None
    a = [float(x) for x in returns_a[-window:]]
    b = [float(x) for x in returns_b[-window:]]
    mean_a = sum(a) / window
    mean_b = sum(b) / window
    cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b, strict=True))
    var_a = sum((x - mean_a) ** 2 for x in a)
    var_b = sum((y - mean_b) ** 2 for y in b)
    if var_a <= 0 or var_b <= 0:
        return None
    return cov / math.sqrt(var_a * var_b)


def trailing_return_spread(
    closes_anchor: Sequence[float],
    closes_peer: Sequence[float],
    *,
    window: int,
) -> float | None:
    """Anchor minus peer trailing simple return over ``window`` sessions."""

    if window < 1 or len(closes_anchor) < window + 1 or len(closes_peer) < window + 1:
        return None
    def _ret(closes: Sequence[float]) -> float | None:
        old = float(closes[-(window + 1)])
        new = float(closes[-1])
        if old == 0:
            return None
        return (new / old) - 1.0

    ra = _ret(closes_anchor)
    rb = _ret(closes_peer)
    if ra is None or rb is None:
        return None
    return ra - rb


def evaluate_peer_pair(
    anchor_symbol: str,
    peer_symbol: str,
    bars_anchor: Sequence[DailyBar],
    bars_peer: Sequence[DailyBar],
    *,
    window_days: int = _DEFAULT_WINDOW_DAYS,
    divergence_threshold: float = _DEFAULT_DIVERGENCE_THRESHOLD,
) -> PeerSyncPairResult:
    """Classify peer relationship over aligned cache bars (observation only)."""

    anchor = anchor_symbol.strip().upper()
    peer = peer_symbol.strip().upper()
    a_closes, b_closes = align_close_series(bars_anchor, bars_peer)
    aligned = len(a_closes)
    min_needed = window_days + 1
    if aligned < min_needed:
        return PeerSyncPairResult(
            anchor_symbol=anchor,
            peer_symbol=peer,
            window_days=window_days,
            aligned_sessions=aligned,
            return_spread=None,
            correlation=None,
            status="insufficient_data",
            interpretation=(
                f"Need at least {min_needed} aligned sessions; have {aligned}."
            ),
        )
    ret_a = _daily_log_returns(a_closes)
    ret_b = _daily_log_returns(b_closes)
    spread = trailing_return_spread(
        a_closes, b_closes, window=window_days
    )
    corr = trailing_correlation(ret_a, ret_b, window=window_days)
    if spread is None:
        status = "insufficient_data"
        interpretation = "Could not compute trailing return spread."
    elif abs(spread) <= divergence_threshold and (
        corr is None or corr >= _MIN_CORRELATION_IN_SYNC
    ):
        status = "in_sync"
        interpretation = (
            f"Return spread within {divergence_threshold:.0%} and correlation supportive."
        )
    elif spread > divergence_threshold:
        status = "diverged_anchor_outperform"
        interpretation = f"Anchor outperformed peer by {spread:.2%} over {window_days}d."
    else:
        status = "diverged_peer_outperform"
        interpretation = f"Peer outperformed anchor by {-spread:.2%} over {window_days}d."

    return PeerSyncPairResult(
        anchor_symbol=anchor,
        peer_symbol=peer,
        window_days=window_days,
        aligned_sessions=aligned,
        return_spread=spread,
        correlation=corr,
        status=status,
        interpretation=interpretation,
    )


def evaluate_peer_map(
    peer_map: Mapping[str, Sequence[str]],
    bars_by_symbol: Mapping[str, Sequence[DailyBar]],
    *,
    window_days: int = _DEFAULT_WINDOW_DAYS,
    divergence_threshold: float = _DEFAULT_DIVERGENCE_THRESHOLD,
) -> list[PeerSyncPairResult]:
    """Evaluate all anchor→peer edges where both sides have bars."""

    results: list[PeerSyncPairResult] = []
    for anchor, peers in peer_map.items():
        anchor_u = str(anchor).strip().upper()
        a_bars = bars_by_symbol.get(anchor_u)
        if not a_bars:
            continue
        for peer in peers:
            peer_u = str(peer).strip().upper()
            b_bars = bars_by_symbol.get(peer_u)
            if not b_bars:
                results.append(
                    PeerSyncPairResult(
                        anchor_symbol=anchor_u,
                        peer_symbol=peer_u,
                        window_days=window_days,
                        aligned_sessions=0,
                        return_spread=None,
                        correlation=None,
                        status="missing_cache",
                        interpretation="No cached bars for anchor or peer.",
                    )
                )
                continue
            results.append(
                evaluate_peer_pair(
                    anchor_u,
                    peer_u,
                    a_bars,
                    b_bars,
                    window_days=window_days,
                    divergence_threshold=divergence_threshold,
                )
            )
    return results
