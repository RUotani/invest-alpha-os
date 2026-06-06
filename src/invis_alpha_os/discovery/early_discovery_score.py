"""Early Discovery score helper (fixture/cache-only; not a buy signal)."""

from __future__ import annotations

EARLY_DISCOVERY_SCORE_THRESHOLD = 0.55
HARD_OVERHEAT_R20 = 0.70
HARD_OVERHEAT_R60 = 1.50


def compute_early_discovery_score(
    *,
    ret_20d: float | None,
    ret_60d: float | None,
    overheat: bool,
) -> float:
    """Higher when moderate positive momentum without hard overheat."""

    if overheat:
        return 0.0
    r20 = float(ret_20d) if ret_20d is not None else 0.0
    r60 = float(ret_60d) if ret_60d is not None else 0.0
    if r20 >= HARD_OVERHEAT_R20 or r60 >= HARD_OVERHEAT_R60:
        return 0.0
    # Sweet spot: early/accel band, not exhausted.
    momentum = max(0.0, min(r20, 0.35)) / 0.35
    stability = max(0.0, min(r60, 0.40)) / 0.40
    return round(0.6 * momentum + 0.4 * stability, 4)


def is_hard_overheat(*, ret_20d: float | None, ret_60d: float | None) -> bool:
    if ret_20d is not None and ret_20d >= HARD_OVERHEAT_R20:
        return True
    if ret_60d is not None and ret_60d >= HARD_OVERHEAT_R60:
        return True
    return False
