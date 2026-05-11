"""J-Quants watchlist bars **summary** for daily reports (Task 7).

This module performs **no HTTP** and never reads API keys; it only uses ``watchlist.yaml`` counts
and optional env presence for the data-availability guard.
"""

from __future__ import annotations

from typing import Mapping, Any

from invis_alpha_os.config.jp_watchlist import jquants_daily_bars_ticker_kind, load_jp_watchlist_tickers
from invis_alpha_os.data.adapters.jquants_client import jquants_data_availability_bounds_from_env


def _guard_status_label() -> str:
    lo, hi = jquants_data_availability_bounds_from_env()
    if lo is not None and hi is not None:
        return "enabled (both `JQUANTS_DATA_AVAILABLE_FROM` and `JQUANTS_DATA_AVAILABLE_TO` are set)"
    return "not enabled — set both `JQUANTS_DATA_AVAILABLE_FROM` and `JQUANTS_DATA_AVAILABLE_TO` to activate the guard"


def render_jquants_watchlist_bars_check_section(report_cfg: Mapping[str, Any] | None) -> str:
    """Return markdown for *## J-Quants Watchlist Bars Check* (dry-run summary only, no HTTP)."""

    cfg = dict(report_cfg or {})
    mode = str(cfg.get("mode") or "dry_run_summary")
    if mode != "dry_run_summary":
        mode = "dry_run_summary"

    tickers = load_jp_watchlist_tickers()
    target_count = len(tickers)
    unsupported = sum(1 for t in tickers if jquants_daily_bars_ticker_kind(t) != "ok")
    supported = target_count - unsupported
    guard_line = _guard_status_label()

    lines = [
        "## J-Quants Watchlist Bars Check",
        "",
        "- Mode: dry_run",
        "- Live HTTP: disabled by default",
        "- Target universe: JP watchlist",
        f"- Target count: {target_count}",
        f"- Unsupported code count: {unsupported}",
        f"- Supported code count: {supported}",
        f"- Data availability guard: {guard_line}",
        "- Raw response included: false",
        "- API key displayed: false",
    ]

    if cfg.get("include_local_smoke_record", True):
        lines.extend(
            [
                "",
                "### Local smoke test record",
                "",
                "- **Note**: The lines below are **Task 7 spec-style field examples** (same labels as [09 — local manual test](../../../docs/09_jquants_local_manual_test.md)). "
                "They are **not** pasted from any CLI or API **stdout/stderr**, **not** produced by this `daily` run, **not** “today’s” automated live result, and **no** HTTP runs here.",
                "",
                "- Single code success: 7974 / 2024-02-16 / row_count=1 / source_key=data",
                "- Watchlist limit 3 success: 7011, 6501, 6506 / 2024-02-16 / success_count=3 / error_count=0",
            ]
        )

    return "\n".join(lines)
