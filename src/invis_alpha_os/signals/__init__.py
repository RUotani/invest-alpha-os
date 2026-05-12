"""Signals package (Main E momentum MVP in ``signals.momentum``)."""

from invis_alpha_os.signals.momentum import (
    DailyBar,
    analyze_bars_for_code,
    build_momentum_signals,
    calculate_returns,
    detect_high_breakout,
    detect_volume_spike,
)

__all__ = [
    "DailyBar",
    "analyze_bars_for_code",
    "build_momentum_signals",
    "calculate_returns",
    "detect_high_breakout",
    "detect_volume_spike",
]
