"""Early Discovery score helper (fixture/cache-only; not a buy signal)."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

EARLY_DISCOVERY_SCORE_THRESHOLD = 0.55
HARD_OVERHEAT_R20 = 0.70
HARD_OVERHEAT_R60 = 1.50
V15_CASH_RATIO_GATE = 0.15
V15_SINGLE_STOCK_RATIO_GATE = 0.15
V15_HARD_OVERHEAT_RECENT_RETURN = 0.70
V15_HARD_OVERHEAT_MA_DEVIATION = 0.40

V15_PROVISIONAL_WEIGHTS: dict[str, float] = {
    "recent_return": 0.20,
    "ma_deviation": 0.15,
    "volume_inflection": 0.30,
    "rs_acceleration": 0.35,
}


@dataclass(frozen=True)
class EarlyDiscoveryInputs:
    """Nullable fixture inputs; unknown observations must stay unknown."""

    theme_phase: str | None = None
    recent_return: float | None = None
    ma_deviation: float | None = None
    volume_inflection: float | None = None
    rs_acceleration: float | None = None
    portfolio_cash_ratio: float | None = None
    single_stock_ratio: float | None = None


@dataclass(frozen=True)
class EarlyDiscoveryScore:
    """Uncalibrated fixture score and explicit missing/blocking reasons."""

    score: float | None
    reasons: tuple[str, ...]
    missing: tuple[str, ...]
    blocked_by: tuple[str, ...]


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


def _bounded_positive(value: float, *, ceiling: float) -> float:
    return max(0.0, min(float(value), ceiling)) / ceiling


def evaluate_early_discovery_score(inputs: EarlyDiscoveryInputs) -> EarlyDiscoveryScore:
    """Evaluate an uncalibrated fixture-only score without classifying a trade."""

    metric_names = ("recent_return", "ma_deviation", "volume_inflection", "rs_acceleration")
    missing = tuple(
        name
        for name in ("theme_phase", *metric_names)
        if getattr(inputs, name) is None
        or (name in metric_names and not isfinite(float(getattr(inputs, name))))
    )
    blocked: list[str] = []
    reasons: list[str] = ["fixture_only_not_performance_evidence", "weights_uncalibrated"]

    if inputs.portfolio_cash_ratio is not None and inputs.portfolio_cash_ratio < V15_CASH_RATIO_GATE:
        blocked.append("portfolio_cash_gate")
    if inputs.single_stock_ratio is not None and inputs.single_stock_ratio > V15_SINGLE_STOCK_RATIO_GATE:
        blocked.append("single_stock_ratio_gate")
    if (
        inputs.recent_return is not None
        and inputs.recent_return >= V15_HARD_OVERHEAT_RECENT_RETURN
    ) or (
        inputs.ma_deviation is not None
        and inputs.ma_deviation >= V15_HARD_OVERHEAT_MA_DEVIATION
    ):
        blocked.append("hard_overheat")
    if inputs.theme_phase not in {None, "early", "accel", "acceleration"}:
        blocked.append("theme_phase_not_early_or_acceleration")
    if inputs.volume_inflection is not None and isfinite(inputs.volume_inflection) and inputs.volume_inflection <= 0.0:
        blocked.append("volume_not_inflecting")
    if inputs.rs_acceleration is not None and isfinite(inputs.rs_acceleration) and inputs.rs_acceleration <= 0.0:
        blocked.append("relative_strength_not_improving")

    if missing:
        return EarlyDiscoveryScore(
            score=None,
            reasons=tuple(reasons),
            missing=missing,
            blocked_by=tuple(blocked),
        )

    assert inputs.recent_return is not None
    assert inputs.ma_deviation is not None
    assert inputs.volume_inflection is not None
    assert inputs.rs_acceleration is not None
    score = (
        V15_PROVISIONAL_WEIGHTS["recent_return"]
        * _bounded_positive(inputs.recent_return, ceiling=0.30)
        + V15_PROVISIONAL_WEIGHTS["ma_deviation"]
        * _bounded_positive(inputs.ma_deviation, ceiling=0.20)
        + V15_PROVISIONAL_WEIGHTS["volume_inflection"]
        * _bounded_positive(inputs.volume_inflection, ceiling=1.00)
        + V15_PROVISIONAL_WEIGHTS["rs_acceleration"]
        * _bounded_positive(inputs.rs_acceleration, ceiling=0.05)
    )
    reasons.extend(
        (
            f"theme_phase={inputs.theme_phase}",
            "relative_strength_improving" if inputs.rs_acceleration > 0 else "relative_strength_not_improving",
            "volume_inflecting" if inputs.volume_inflection > 0 else "volume_not_inflecting",
        )
    )
    return EarlyDiscoveryScore(
        score=round(score, 4),
        reasons=tuple(reasons),
        missing=(),
        blocked_by=tuple(blocked),
    )
