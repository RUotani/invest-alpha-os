"""J-Quants watchlist bars **summary** + **readiness** for daily reports (Task 7–8, **Task 10**).

This module performs **no HTTP**, never calls ``urllib``, does not invoke ``JQuantsClient.get_daily_quotes``,
and never reads API keys; it only uses ``watchlist.yaml`` counts, **optional local** ``latest.json`` (sanitized
smoke), optional env for the data-availability guard, and ``market_data.yaml`` ``report`` flags.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from invis_alpha_os.config.jp_watchlist import jquants_daily_bars_ticker_kind, load_jp_watchlist_tickers
from invis_alpha_os.config.paths import ROOT_DIR
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


_DEFAULT_LATEST_REL = "outputs/jquants_smoke/latest.json"

_SAFE_NAMED_KEYS = frozenset(
    {
        "raw_response_included",
        "api_key_displayed",
        "source_key",
    }
)


def _forbidden_smoke_key(name: str) -> bool:
    """Reject secret-ish keys; allowlisted compound names are OK (e.g. ``source_key``)."""

    if name in _SAFE_NAMED_KEYS:
        return False
    n = name.lower().replace("-", "_")
    if n == "raw_response":
        return True
    if n in {"api_key", "authorization", "password", "secret", "credentials", "bearer"}:
        return True
    if re.search(r"x[_-]?api[_-]?key", n):
        return True
    if n in {"token", "access_token", "refreshtoken", "idtoken", "refresh_token", "id_token"}:
        return True
    if n.endswith("_token") or n.endswith("password"):
        return True
    return False


def _walk_for_forbidden_keys(obj: Any) -> bool:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and _forbidden_smoke_key(k):
                return True
            if _walk_for_forbidden_keys(v):
                return True
    elif isinstance(obj, list):
        for it in obj:
            if _walk_for_forbidden_keys(it):
                return True
    return False


def _analyze_smoke_payload(obj: Any) -> tuple[str, bool | None, bool | None]:
    """Return ``(status, raw_unsafe, api_unsafe)``.

    ``status`` is ``safe`` | ``blocked`` | ``invalid``.
    For blocked from unknown structure, raw/api may be ``None`` (shown as unknown in markdown).
    """

    if not isinstance(obj, dict):
        return "invalid", None, None
    ri = obj.get("raw_response_included")
    ad = obj.get("api_key_displayed")
    if ri is True:
        return "blocked", True, True if ad is True else (False if ad is False else None)
    if ad is True:
        return "blocked", False if ri is False else None, True
    if _walk_for_forbidden_keys(obj):
        return "blocked", None, None
    return "safe", False, False


def _load_latest_smoke_json(path: Path) -> tuple[str, Any | None]:
    """Read JSON from disk only. Returns ``(ok|missing|bad, payload_or_none)``."""

    try:
        if not path.is_file():
            return "missing", None
        text = path.read_text(encoding="utf-8")
        payload = json.loads(text)
        return "ok", payload
    except (OSError, UnicodeError, json.JSONDecodeError):
        return "bad", None


def _fmt_scalar(v: Any) -> str:
    if isinstance(v, bool):
        return str(v).lower()
    if v is None:
        return "n/a"
    return str(v)


def _collect_safe_result_codes(rows: Any) -> tuple[list[str], bool]:
    """Collect JP equity codes for display. Sets *bad* if any explicit ``code`` is not wire-safe."""

    codes: list[str] = []
    if not isinstance(rows, list):
        return [], False
    bad = False
    for row in rows:
        if not isinstance(row, dict) or "code" not in row:
            continue
        c = row.get("code")
        s = str(c).strip() if c is not None else ""
        if not s:
            continue
        if jquants_daily_bars_ticker_kind(s) != "ok":
            bad = True
            continue
        codes.append(s)
    return codes, bad


_ALLOWED_SMOKE_MODES = frozenset({"dry_run", "live", "completed", "disabled", "preview"})


def _safe_iso_date(s: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", s))


def _smoke_display_scalars_ok(p: dict[str, Any]) -> bool:
    """Reject tainted summaries: wrong types, oversized strings, or unknown mode."""

    m = p.get("mode")
    if m is not None:
        if not isinstance(m, str) or m.strip() not in _ALLOWED_SMOKE_MODES:
            return False
    d = p.get("date")
    if d is not None:
        if not isinstance(d, str) or not _safe_iso_date(d.strip()):
            return False
    for k in ("date_from", "date_to"):
        v = p.get(k)
        if v is None:
            continue
        if not isinstance(v, str) or not _safe_iso_date(v.strip()):
            return False
    ca = p.get("created_at")
    if ca is not None:
        if not isinstance(ca, str) or len(ca) > 80:
            return False
        if any(ord(c) < 32 for c in ca):
            return False
    for k in (
        "target_count",
        "success_count",
        "error_count",
        "skipped_count",
        "dry_run_count",
        "preview_count",
    ):
        v = p.get(k)
        if v is None:
            continue
        if isinstance(v, bool) or not isinstance(v, int):
            return False
        if v < 0 or v > 10_000_000:
            return False
    ri, ad = p.get("raw_response_included"), p.get("api_key_displayed")
    for b in (ri, ad):
        if b is None:
            continue
        if not isinstance(b, bool):
            return False
    return True


def _resolve_latest_smoke_path(report_cfg: Mapping[str, Any]) -> Path:
    rel = _cfg_str(report_cfg, "latest_smoke_summary_path", _DEFAULT_LATEST_REL)
    # Avoid path traversal outside repo when joining.
    root = ROOT_DIR.resolve()
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return root / _DEFAULT_LATEST_REL
    return candidate


def render_latest_local_smoke_summary_section(report_cfg: Mapping[str, Any] | None) -> str:
    """Markdown for ``### Latest local smoke summary`` (file read only; **no HTTP**)."""

    cfg = dict(report_cfg or {})
    if not _cfg_bool(cfg, "include_latest_smoke_summary", True):
        return ""

    src_display = _cfg_str(cfg, "latest_smoke_summary_path", _DEFAULT_LATEST_REL)
    path = _resolve_latest_smoke_path(cfg)

    live_line = "- Live HTTP during daily: false"
    http_gate = _cfg_str(cfg, "latest_smoke_summary_live_http", "disabled")
    if (http_gate or "").strip().lower() != "disabled":
        live_line = f"- Live HTTP during daily: not disabled in config ({http_gate!r}; daily must not run live)"

    lines = ["", "### Latest local smoke summary", "", f"- Source: {src_display}"]

    st, payload = _load_latest_smoke_json(path)
    if st == "missing":
        lines.extend(
            [
                "- Status: not found",
                "- Note: Run `debug jquants-watchlist-bars ... --save-summary` manually "
                "to create a local sanitized summary.",
                live_line,
            ]
        )
        return "\n".join(lines)

    if st == "bad" or payload is None:
        lines.extend(
            [
                "- Latest local smoke summary: unsafe summary blocked",
                "- Raw response included: unknown",
                "- API key displayed: unknown",
                live_line,
            ]
        )
        return "\n".join(lines)

    status, raw_u, api_u = _analyze_smoke_payload(payload)
    if status == "invalid":
        lines.extend(
            [
                "- Latest local smoke summary: unsafe summary blocked",
                "- Raw response included: unknown",
                "- API key displayed: unknown",
                live_line,
            ]
        )
        return "\n".join(lines)

    if status == "blocked":
        def _u(b: bool | None) -> str:
            if b is True:
                return "true"
            if b is False:
                return "false"
            return "unknown"

        lines.extend(
            [
                "- Latest local smoke summary: unsafe summary blocked",
                f"- Raw response included: {_u(raw_u)}",
                f"- API key displayed: {_u(api_u)}",
                live_line,
            ]
        )
        return "\n".join(lines)

    # safe — only emit whitelisted fields; never echo arbitrary JSON blobs or secrets.
    p = payload
    if not _smoke_display_scalars_ok(p):
        lines.extend(
            [
                "- Latest local smoke summary: unsafe summary blocked",
                "- Raw response included: unknown",
                "- API key displayed: unknown",
                live_line,
            ]
        )
        return "\n".join(lines)

    mode = _fmt_scalar(p.get("mode"))
    date_s = _fmt_scalar(p.get("date"))
    target = _fmt_scalar(p.get("target_count"))
    succ = _fmt_scalar(p.get("success_count"))
    errc = _fmt_scalar(p.get("error_count"))
    dry_c = _fmt_scalar(p.get("dry_run_count"))
    prv_c = _fmt_scalar(p.get("preview_count"))
    skp_c = _fmt_scalar(p.get("skipped_count"))
    raw_inc = _fmt_scalar(p.get("raw_response_included", False))
    api_inc = _fmt_scalar(p.get("api_key_displayed", False))

    codes, bad_codes = _collect_safe_result_codes(p.get("results"))
    if bad_codes:
        lines.extend(
            [
                "- Latest local smoke summary: unsafe summary blocked",
                "- Raw response included: unknown",
                "- API key displayed: unknown",
                live_line,
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            f"- Mode: {mode}",
            f"- Date: {date_s}",
            f"- Target count: {target}",
            f"- Success count: {succ}",
            f"- Error count: {errc}",
            f"- Dry-run count: {dry_c}",
            f"- Preview count: {prv_c}",
            f"- Skipped count: {skp_c}",
            f"- Raw response included: {raw_inc}",
            f"- API key displayed: {api_inc}",
            f"- Result codes: {', '.join(codes) if codes else 'none'}",
            live_line,
        ]
    )
    return "\n".join(lines)


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
                "- Single code success (illus. within subscription window): 7974 / 2024-02-18 / row_count=1 / source_key=data",
                "- Watchlist limit 3: **Task 9.2** narrative + command pattern in "
                "[09 — local manual test](../../../docs/09_jquants_local_manual_test.md) "
                "(illus. JP codes e.g. 7011 / 6501 / 6506; **not** a stdout paste).",
            ]
        )

    body = "\n".join(lines)
    body += render_latest_local_smoke_summary_section(cfg)
    return body
