"""Product-facing orchestration (signals / observation); not operator automation."""

from invis_alpha_os.product.us_forward_return_validation import compute_us_forward_returns
from invis_alpha_os.product.us_universe_expansion import build_us_universe_expansion_report
from invis_alpha_os.product.weekly_us_observation import (
    build_us_watchlist_signals_manifest,
    run_weekly_us_observation_cycle,
    summarize_us_observation_log,
    us_signal_quality_snapshot,
)

__all__ = [
    "build_us_universe_expansion_report",
    "build_us_watchlist_signals_manifest",
    "compute_us_forward_returns",
    "run_weekly_us_observation_cycle",
    "summarize_us_observation_log",
    "us_signal_quality_snapshot",
]
