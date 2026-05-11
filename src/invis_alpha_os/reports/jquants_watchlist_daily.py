"""J-Quants watchlist bars **summary** + **readiness** for daily reports (Task 7–8).

This module performs **no HTTP** and never reads API keys; it only uses ``watchlist.yaml`` counts,
optional env for the data-availability guard, and ``market_data.yaml`` ``report`` flags.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from invis_alpha_os.config.jp_watchlist import jquants_daily_bars_ticker_kind, load_jp_watchlist_tickers
from invis_alpha_os.data.adapters.jquants_client import jquants_data_availability_bounds_from_env


def _guard_bounds() -> tuple[date | None, date | None]:
    return jquants_data_availability_bounds_from_env()


def _guard_enabled() -> bool:
    lo, hi = _guard_bounds()
    return lo is not None and hi is not None


def _guard_label_short() -> str:
    return "enabled" if _guard_enabled() else "not enabled"


def _cfg_bool(cfg: Mapping[str, Any], key: str, default: bool = False) -> bool:
    v = cfg.get(key, default)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "on"}
    return bool(v)


def _cfg_str(cfg: Mapping[str, Any], key: str, default: str = "") -> str:
    v = cfg.get(key, default)
    return str(v).strip() if v is not None else default


def _load_jp_watchlist_tickers_safe() -> tuple[list[str], str | None]:
    try:
        return load_jp_watchlist_tickers(), None
    except Exception:
        return [], "watchlist_load_failed"


@dataclass(frozen=True)
class JQuantsDryRunFacts:
    """Single snapshot from watchlist.yaml + env (no HTTP); built once per report render."""

    watchlist_load_error: str | None
    tickers: tuple[str, ...]
    unsupported_codes: tuple[str, ...]
    supported: int
    target_count: int
    guard_enabled: bool


def collect_jquants_dry_run_facts() -> JQuantsDryRunFacts:
    tickers_raw, werr = _load_jp_watchlist_tickers_safe()
    guard_on = _guard_enabled()
    if werr:
        return JQuantsDryRunFacts(
            watchlist_load_error=werr,
            tickers=(),
            unsupported_codes=(),
            supported=0,
            target_count=0,
            guard_enabled=guard_on,
        )
    tup = tuple(tickers_raw)
    unsup = tuple(t for t in tup if jquants_daily_bars_ticker_kind(t) != "ok")
    unsupported_n = len(unsup)
    return JQuantsDryRunFacts(
        watchlist_load_error=None,
        tickers=tup,
        unsupported_codes=unsup,
        supported=len(tup) - unsupported_n,
        target_count=len(tup),
        guard_enabled=guard_on,
    )


@dataclass(frozen=True)
class JQuantsDailyReadinessState:
    """Dry-run readiness (no HTTP)."""

    level: str  # green | yellow | red
    readiness_line_enabled: bool


def classify_jquants_daily_readiness(
    *,
    supported: int,
    watchlist_load_error: str | None,
    guard_enabled: bool,
    include_smoke_record: bool,
    raw_response_included: bool,
    api_key_displayed: bool,
    live_http_in_daily: str,
    readiness_green_requires_data_guard: bool,
    readiness_green_requires_smoke_record: bool,
) -> str:
    """Return ``green`` | ``yellow`` | ``red`` (Task 8, dry-run only)."""

    live = (live_http_in_daily or "").strip().lower()

    def _fatal_red() -> bool:
        return bool(
            watchlist_load_error
            or supported <= 0
            or raw_response_included
            or api_key_displayed
            or live != "disabled"
        )

    if _fatal_red():
        return "red"

    green = supported > 0
    if readiness_green_requires_data_guard and not guard_enabled:
        green = False
    if readiness_green_requires_smoke_record and not include_smoke_record:
        green = False

    if green:
        return "green"
    if supported > 0:
        return "yellow"
    return "red"


def evaluate_jquants_daily_readiness(
    cfg: Mapping[str, Any] | None, facts: JQuantsDryRunFacts
) -> JQuantsDailyReadinessState:
    """Classify readiness from one ``facts`` snapshot + report config (**no HTTP**)."""

    c = dict(cfg or {})

    readiness_line_enabled = _cfg_bool(c, "readiness_enabled", True)
    raw_included = _cfg_bool(c, "raw_response_included", False)
    api_shown = _cfg_bool(c, "api_key_displayed", False)
    live_daily = _cfg_str(c, "live_http_in_daily", "disabled")
    green_need_guard = _cfg_bool(c, "readiness_green_requires_data_guard", True)
    green_need_smoke = _cfg_bool(c, "readiness_green_requires_smoke_record", True)

    smoke_on = _cfg_bool(c, "include_local_smoke_record", True)

    level = classify_jquants_daily_readiness(
        supported=facts.supported,
        watchlist_load_error=facts.watchlist_load_error,
        guard_enabled=facts.guard_enabled,
        include_smoke_record=smoke_on,
        raw_response_included=raw_included,
        api_key_displayed=api_shown,
        live_http_in_daily=live_daily,
        readiness_green_requires_data_guard=green_need_guard,
        readiness_green_requires_smoke_record=green_need_smoke,
    )

    return JQuantsDailyReadinessState(
        level=level,
        readiness_line_enabled=readiness_line_enabled,
    )


_SMOKE_LINE_OK = (
    "- Local smoke test: documented reference (subsection below; **not executed** by daily)"
)
_SMOKE_W3_LINE_OK = (
    "- Watchlist limit 3 smoke test: documented reference (subsection below; **not executed** by daily)"
)


def render_jquants_watchlist_bars_check_section(report_cfg: Mapping[str, Any] | None) -> str:
    """Return markdown for *## J-Quants Watchlist Bars Check* (dry-run summary only, no HTTP)."""

    cfg = dict(report_cfg or {})

    facts = collect_jquants_dry_run_facts()
    rs = evaluate_jquants_daily_readiness(cfg, facts)

    werr = facts.watchlist_load_error
    unsupported_codes = facts.unsupported_codes
    unsupported = len(unsupported_codes)
    supported = facts.supported
    target_count = facts.target_count

    guard_short = _guard_label_short()
    smoke_on = _cfg_bool(cfg, "include_local_smoke_record", True)
    include_unsup_list = _cfg_bool(cfg, "include_unsupported_codes", True)

    raw_line = "- Raw response included: false"
    if _cfg_bool(cfg, "raw_response_included", False):
        raw_line = "- Raw response included: true"
    api_line = "- API key displayed: false"
    if _cfg_bool(cfg, "api_key_displayed", False):
        api_line = "- API key displayed: true"

    if werr:
        smoke_single = "- Local smoke test: unavailable (watchlist load failed)"
        smoke_w3 = "- Watchlist limit 3 smoke test: unavailable (watchlist load failed)"
    elif smoke_on:
        smoke_single = _SMOKE_LINE_OK
        smoke_w3 = _SMOKE_W3_LINE_OK
    else:
        smoke_single = "- Local smoke test: not included"
        smoke_w3 = "- Watchlist limit 3 smoke test: not included"

    live_daily_cfg = _cfg_str(cfg, "live_http_in_daily", "disabled")
    live_human = (
        "- Live HTTP: disabled by default"
        if live_daily_cfg.lower() == "disabled"
        else f"- Live HTTP: not disabled in config ({live_daily_cfg!r}; readiness expects `disabled`)"
    )

    lines: list[str] = ["## J-Quants Watchlist Bars Check", ""]

    if rs.readiness_line_enabled:
        level_title = rs.level[:1].upper() + rs.level[1:] if rs.level else rs.level
        lines.append(f"- Readiness: {level_title}")

    lines.extend(
        [
            "- Mode: dry_run",
            live_human,
            "- Target universe: JP watchlist",
            f"- Target count: {target_count}",
            f"- Supported code count: {supported}",
            f"- Unsupported code count: {unsupported}",
        ]
    )

    if include_unsup_list:
        if werr:
            lines.append("- Unsupported codes skipped: unavailable (watchlist load failed)")
        elif unsupported_codes:
            codes_joined = ", ".join(unsupported_codes)
            lines.append(f"- Unsupported codes skipped: {codes_joined}")
        else:
            lines.append("- Unsupported codes skipped: none")

    lines.extend(
        [
            f"- Data availability guard: {guard_short}",
            smoke_single,
            smoke_w3,
            raw_line,
            api_line,
        ]
    )

    if smoke_on and not werr:
        lines.extend(
            [
                "",
                "### Local smoke test record",
                "",
                "- **Note**: The lines below are **Task 7 spec-style field examples** "
                "(same labels as "
                "[09 — local manual test](../../../docs/09_jquants_local_manual_test.md)). "
                "They are **not** pasted from any CLI or API **stdout/stderr**, **not** produced by this "
                "`daily` run, **not** “today’s” automated live result, and **no** HTTP runs here.",
                "",
                "- Single code success (illus. within subscription window): 7974 / 2024-02-17 / row_count=1 / source_key=data",
                "- Watchlist limit 3: **Task 9.2** narrative + command pattern in "
                "[09 — local manual test](../../../docs/09_jquants_local_manual_test.md) "
                "(illus. JP codes e.g. 7011 / 6501 / 6506; **not** a stdout paste).",
            ]
        )

    return "\n".join(lines)
