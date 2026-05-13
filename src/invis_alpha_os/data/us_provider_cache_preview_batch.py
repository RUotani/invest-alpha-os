"""Multi-symbol US Stooq cache preview aggregation (**Main R5–R5.2**).

No unattended bulk behaviors: **`write_cache`** requests are rejected at the envelope level (**use single-symbol **`debug us-provider-cache-preview`** + gates for writes**).

Each symbol runs **`stooq_live_preview_sanitized_bars`** with the same **`live`** flag and **`write_cache=False`** (writes are never performed in batch).

**Main R5.1** adds **`operator_summary`** on the batch envelope (**triage buckets only**, still **no raw vendor payloads**, **no cache writes**).

**Main R5.2** adds **`render_us_provider_cache_preview_batch_markdown`** — human-readable summary (**no row-level vendor material**; use JSON for **`results[]`**).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from invis_alpha_os.config.us_watchlist import load_us_watchlist_tickers, normalize_us_symbol
from invis_alpha_os.data.us_provider_live_preview import stooq_live_preview_sanitized_bars
from invis_alpha_os.data.us_provider_preview import us_cache_target_relpath

_VENDOR_FORMAT_PARSE_REASONS: frozenset[str] = frozenset(
    {
        "stooq_payload_html_like",
        "empty_csv",
        "stooq_csv_delimiter_drift",
        "stooq_csv_missing_required_columns",
        "stooq_csv_parse_failed",
        "stooq_csv_no_rows",
        "csv_parse_failed",
        "csv_decode_failed",
        "cache_persist_refused",
    },
)

_SYMBOL_SLUG_MAPPING_REASONS: frozenset[str] = frozenset({"stooq_vendor_no_data"})

_ACTION_HINTS: dict[tuple[str, str | None], str] = {
    ("dry_run", None): "Safe default. For gated live per symbol use single-symbol tooling or pass --live with CONFIRM_US_LIVE_HTTP=YES (batch repeats per symbol only when operator invokes it explicitly).",
    ("preview_ok", None): "Live parse succeeded; optional single-symbol --write-cache with CONFIRM_US_CACHE_WRITE=YES if persistence is desired (not via batch API).",
    ("success", None): "Writes occur only outside this batch envelope (unexpected here because batch forces write_cache=False).",
    ("validation_error", "live_http_not_confirmed"): "Set CONFIRM_US_LIVE_HTTP=YES before --live.",
    ("validation_error", "cache_write_not_confirmed"): "Cosmetic in batch — batch never triggers cache write prompts.",
    ("validation_error", "provider_api_key_required"): "Set STOOQ_APIKEY in environment only.",
    ("validation_error", "invalid_symbol"): "Fix symbol / normalization.",
    ("parse_error", "stooq_payload_html_like"): "Treat as HTML/non-CSV; diagnostics only.",
    ("parse_error", "stooq_vendor_no_data"): "Ticker / *.us slug / listing type.",
    ("parse_error", "empty_csv"): "Empty body after HTTP 200.",
    ("parse_error", "stooq_csv_delimiter_drift"): "Delimiter mismatch heuristic.",
    ("parse_error", "stooq_csv_missing_required_columns"): "Header schema differs from strict parser.",
    ("parse_error", "stooq_csv_parse_failed"): "Row-level strict parse rejection.",
    ("parse_error", "stooq_csv_no_rows"): "No usable data rows.",
    ("parse_error", "csv_parse_failed"): "Malformed CSV envelope for reader.",
    ("parse_error", "csv_decode_failed"): "Non-UTF-8 decoded body.",
    ("http_error", "network_or_timeout"): "Transport-layer failure.",
    ("validation_error", "batch_cache_write_not_supported"): "Unset write-cache for batch.",
    ("validation_error", "unsupported_provider"): "Use stooq_preview.",
}


_SUMMARY_TABLE_ORDER: tuple[str, ...] = (
    "dry_run",
    "preview_ok",
    "success",
    "validation_error",
    "parse_error",
    "transport_error",
)


def _operator_summary_zeros() -> dict[str, int]:
    """Batch-level operator buckets (**Main R5.1**) — aligned with **`docs/12`** matrix classes."""

    return {
        "safe_dry_run_count": 0,
        "single_symbol_write_candidate_count": 0,
        "needs_api_key_count": 0,
        "symbol_mapping_review_count": 0,
        "vendor_format_review_count": 0,
        "transport_retry_candidate_count": 0,
        "invalid_symbol_count": 0,
        "blocked_cache_write_count": 0,
    }


def _md_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def _normalize_summary_dict(payload: dict[str, Any]) -> dict[str, int]:
    raw = payload.get("summary")
    out: dict[str, int] = {k: 0 for k in _SUMMARY_TABLE_ORDER}
    if not isinstance(raw, dict):
        return out
    for k in _SUMMARY_TABLE_ORDER:
        try:
            out[k] = int(raw.get(k, 0))
        except (TypeError, ValueError):
            out[k] = 0
    return out


def _normalize_operator_summary_dict(payload: dict[str, Any]) -> dict[str, int]:
    z = _operator_summary_zeros()
    raw = payload.get("operator_summary")
    if not isinstance(raw, dict):
        return z
    for k in z:
        try:
            z[k] = int(raw.get(k, 0))
        except (TypeError, ValueError):
            z[k] = 0
    return z


def _recommended_operator_action_lines(payload: dict[str, Any]) -> list[str]:
    top = str(payload.get("status") or "unknown")
    rs = payload.get("reason")
    reason = rs if isinstance(rs, str) else None
    osum = _normalize_operator_summary_dict(payload)

    def c(key: str) -> int:
        return int(osum.get(key, 0))

    if top == "validation_error":
        if reason == "unsupported_provider":
            return ["Fix `--provider`: multi-symbol batch supports `stooq_preview` only."]
        if reason == "batch_cache_write_not_supported":
            return [
                "Batch cannot persist cache. Omit `--write-cache` here; run `debug us-provider-cache-preview` "
                + "for one symbol with explicit cache-write gates when needed.",
            ]
        if reason == "empty_symbol_batch":
            return ["Provide `--symbols` and/or `--from-watchlist` before re-running."]
        return ["Envelope validation failed — inspect JSON `reason` / `detail` and `docs/12_us_provider_failure_operator_playbook.md`."]

    hints: list[str] = []

    if c("needs_api_key_count") > 0:
        hints.append(
            f"Configure **STOOQ_APIKEY** in environment only for **{c('needs_api_key_count')}** symbol(s); "
            "never commit secrets or stash vendor bodies in-repo.",
        )
    if c("transport_retry_candidate_count") > 0:
        hints.append(
            f"**{c('transport_retry_candidate_count')}** symbol(s) need transport / HTTP review — "
            "**bounded human-only** retries per `docs/12` (no unattended loops).",
        )
    if c("invalid_symbol_count") > 0:
        hints.append(
            f"**{c('invalid_symbol_count')}** invalid symbol token(s) — fix ticker / normalization before gated live probes.",
        )
    if c("vendor_format_review_count") > 0:
        hints.append(
            f"**{c('vendor_format_review_count')}** row(s) look like vendor **format/schema** drift — rely on **`reason` / `body_kind`** in JSON `results[]` only.",
        )
    if c("symbol_mapping_review_count") > 0:
        hints.append(
            f"**{c('symbol_mapping_review_count')}** row(s) suggest **`.us` / listing-class** mapping review per `docs/11` / `docs/12` (still no raw payloads).",
        )
    if c("blocked_cache_write_count") > 0:
        hints.append(
            f"**{c('blocked_cache_write_count')}** symbol(s) show **`preview_ok`** without **`cache_write_allowed`** — inspect JSON rows for safety edges before persistence.",
        )
    if c("single_symbol_write_candidate_count") > 0:
        hints.append(
            f"**{c('single_symbol_write_candidate_count')}** symbol(s) may proceed to gated **`debug us-provider-cache-preview --write-cache`**; batch intentionally remains write-free.",
        )

    if hints:
        return hints

    sym_ct = int(payload.get("symbol_count") or 0)
    live_pf = bool(payload.get("live_http_performed"))
    cw_pf = bool(payload.get("cache_write_performed"))

    if sym_ct <= 0:
        return ["No per-symbol rows in this batch."]
    if c("safe_dry_run_count") == sym_ct:
        return ["Safe dry-run only. No live HTTP or cache write occurred."]
    if live_pf or cw_pf:
        return [
            "Live / cache-write flags surfaced on the envelope — open JSON `results[]` for per-symbol **`status` / `reason`** against `docs/12`.",
        ]
    return [
        "Mixed dry-run posture — triage **`results[]`** in JSON alongside `docs/12` (**no vendor raw bodies**, **batch does not persist cache**).",
    ]


def render_us_provider_cache_preview_batch_markdown(payload: dict[str, Any]) -> str:
    """Render a compact operator-facing Markdown recap (**Main R5.2**) — envelope + counts only (**no **`results[]`**, **no secrets**).

    Safe for dashboards / tickets containing **counts and statuses** extracted from **`run_stooq_cache_preview_batch`** payloads.
    """

    lines: list[str] = [
        "# US Provider Batch Preview Summary",
        "",
        f"- Provider: {_md_scalar(payload.get('provider'))}".rstrip(),
        f"- Status: {_md_scalar(payload.get('status'))}".rstrip(),
        f"- Symbols: {_md_scalar(payload.get('symbol_count'))}".rstrip(),
        f"- Observation only: {_md_scalar(payload.get('observation_only'))}".rstrip(),
    ]

    if str(payload.get("status") or "") == "validation_error" and isinstance(payload.get("reason"), str):
        lines.append(f"- Reason: {_md_scalar(payload['reason'])}")

    wc_req = payload.get("write_cache_requested")
    lines.append(f"- Live HTTP requested: {_md_scalar(payload.get('live_http_requested'))}".rstrip())
    if wc_req is not None:
        lines.append(f"- Write cache requested: {_md_scalar(wc_req)}".rstrip())

    lines.extend(
        [
            "",
            "## Safety",
            "",
            f"- Live HTTP performed: {_md_scalar(payload.get('live_http_performed'))}".rstrip(),
            f"- Cache write performed: {_md_scalar(payload.get('cache_write_performed'))}".rstrip(),
            f"- Raw response included: {_md_scalar(payload.get('raw_response_included'))}".rstrip(),
            "",
            "## Summary",
            "",
            "| bucket | count |",
            "|---|---:|",
        ],
    )

    sm = _normalize_summary_dict(payload)
    for key in _SUMMARY_TABLE_ORDER:
        lines.append(f"| {key} | {sm[key]} |")

    om = _normalize_operator_summary_dict(payload)
    ops_keys = tuple(_operator_summary_zeros().keys())
    lines.extend(
        [
            "",
            "## Operator summary",
            "",
            "| bucket | count |",
            "|---|---:|",
        ],
    )
    for key in ops_keys:
        lines.append(f"| {key} | {om[key]} |")

    lines.extend(
        [
            "",
            "## Recommended operator action",
            "",
        ],
    )
    action_lines = _recommended_operator_action_lines(payload)
    if action_lines:
        lines.append("\n\n".join(action_lines))
        lines.append("")

    lines.extend(
        [
            "## Safety notes",
            "",
            "- This Markdown report **omits** per-symbol **`results[]`**. Use **`debug us-provider-cache-preview-batch` without `--markdown`** (JSON) for row-level **`status` / `reason` / `body_kind`** — still **no vendor raw bodies** in tooling output.",
            "- **Batch never writes cache**; gated persistence uses **`debug us-provider-cache-preview`** with explicit env gates.",
            "- **Never** commit API keys, `.env`, or vendor dumps; keep **`STOOQ_APIKEY`** in local environment only.",
            "",
        ],
    )

    return "\n".join(lines).rstrip() + "\n"


def _action_hint(status: str, reason: str | None) -> str:
    return _ACTION_HINTS.get(
        (status, reason),
        _ACTION_HINTS.get((status, None), "See docs/12_us_provider_failure_operator_playbook.md and response_diagnostics when present."),
    )


def compute_operator_summary_from_rows(results: list[dict[str, Any]]) -> dict[str, int]:
    """Summarize **`results[]`** for triage (**no raw payloads**). Rows may overlap matrix rows; buckets are intentional."""

    agg = _operator_summary_zeros()
    for rw in results:
        st = str(rw.get("status") or "unknown")
        rs = rw.get("reason")
        reason = rs if isinstance(rs, str) else None

        if st == "dry_run":
            agg["safe_dry_run_count"] += 1

        if st == "validation_error" and reason == "invalid_symbol":
            agg["invalid_symbol_count"] += 1

        if st == "validation_error" and reason == "provider_api_key_required":
            agg["needs_api_key_count"] += 1

        if reason in _SYMBOL_SLUG_MAPPING_REASONS:
            agg["symbol_mapping_review_count"] += 1

        if st == "parse_error" and reason in _VENDOR_FORMAT_PARSE_REASONS:
            agg["vendor_format_review_count"] += 1

        if st == "http_error":
            agg["transport_retry_candidate_count"] += 1

        if bool(rw.get("cache_write_allowed")):
            agg["single_symbol_write_candidate_count"] += 1

        # Parse succeeded live but batch policy / safety refused a write hint (e.g. raw-response edge cases).
        if st == "preview_ok" and not bool(rw.get("cache_write_allowed")):
            agg["blocked_cache_write_count"] += 1

    return agg


def _row_from_payload(norm: str, payload: dict[str, Any]) -> dict[str, Any]:
    diag = payload.get("response_diagnostics")
    bk = diag.get("body_kind") if isinstance(diag, dict) else None

    rs = payload.get("reason")
    reason_out: str | None = rs if isinstance(rs, str) else None

    st = str(payload.get("status") or "unknown")

    could_single_write = (
        st == "preview_ok"
        and bool(payload.get("live_http_performed"))
        and payload.get("raw_response_included") is False
    )
    wc_allowed = False
    wc_blocked_reason = "bulk_cache_writes_disabled_use_single_symbol_us_provider_cache_preview"
    if could_single_write:
        wc_allowed = True
        wc_blocked_reason = None

    return {
        "symbol": norm,
        "status": st,
        "reason": reason_out,
        "body_kind": bk,
        "cache_target": us_cache_target_relpath(norm),
        "live_http_performed": bool(payload.get("live_http_performed")),
        "cache_write_performed": bool(payload.get("cache_write_performed")),
        "raw_response_included": bool(payload.get("raw_response_included")),
        "cache_write_allowed": wc_allowed,
        "cache_write_blocked_reason": wc_blocked_reason,
        "operator_next_action": _action_hint(st, reason_out),
    }


def _dedupe_preserve_order(normals: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for n in normals:
        if n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out


def run_stooq_cache_preview_batch(
    symbols: list[str],
    *,
    provider: str = "stooq_preview",
    live: bool = False,
    write_cache: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    """Dry-run aggregated preview by default; optional gated **``live``** per symbol (**no bulk cache write**).

    Args:
        symbols: Raw symbol strings (**normalized**, invalid tokens become **`validation_error`** rows).
        provider: **`stooq_preview`** only in Main R5.
        live: When **True**, each symbol runs up to **one** gated vendor GET (same **`CONFIRM_US_LIVE_HTTP=YES`** contract as Main R4).
        write_cache: Rejected (**use single-symbol **`debug us-provider-cache-preview`** when writes are intentional**).
        limit: Trim **normalized** universe to first **N** after dedupe.
    """

    if provider.strip() != "stooq_preview":
        return {
            "status": "validation_error",
            "reason": "unsupported_provider",
            "provider": provider.strip(),
            "live_http_requested": live,
            "write_cache_requested": write_cache,
            "live_http_performed": False,
            "cache_write_performed": False,
            "raw_response_included": False,
            "symbol_count": 0,
            "results": [],
            "summary": {
                "dry_run": 0,
                "preview_ok": 0,
                "success": 0,
                "validation_error": 0,
                "parse_error": 0,
                "transport_error": 0,
            },
            "operator_summary": _operator_summary_zeros(),
            "observation_only": True,
        }

    if write_cache:
        return {
            "status": "validation_error",
            "reason": "batch_cache_write_not_supported",
            "provider": "stooq_preview",
            "live_http_requested": live,
            "write_cache_requested": True,
            "live_http_performed": False,
            "cache_write_performed": False,
            "raw_response_included": False,
            "symbol_count": 0,
            "results": [],
            "summary": {
                "dry_run": 0,
                "preview_ok": 0,
                "success": 0,
                "validation_error": 0,
                "parse_error": 0,
                "transport_error": 0,
            },
            "detail": (
                "Main R5 batch never performs cache writes. Use debug us-provider-cache-preview "
                "for a single normalized symbol with CONFIRM_US_CACHE_WRITE=YES and --write-cache."
            ),
            "operator_summary": _operator_summary_zeros(),
            "observation_only": True,
        }

    normed: list[str] = []
    results: list[dict[str, Any]] = []

    for raw in symbols:
        stripped = raw.strip()
        if not stripped:
            continue
        n = normalize_us_symbol(stripped)
        if n is None:
            results.append(
                {
                    "symbol": stripped[:32],
                    "status": "validation_error",
                    "reason": "invalid_symbol",
                    "body_kind": None,
                    "cache_target": "",
                    "live_http_performed": False,
                    "cache_write_performed": False,
                    "raw_response_included": False,
                    "cache_write_allowed": False,
                    "cache_write_blocked_reason": "invalid_symbol",
                    "operator_next_action": _action_hint("validation_error", "invalid_symbol"),
                },
            )
            continue
        normed.append(n)

    normed = _dedupe_preserve_order(normed)
    if isinstance(limit, int) and limit > 0:
        normed = normed[:limit]

    if not normed and not results:
        return {
            "status": "validation_error",
            "reason": "empty_symbol_batch",
            "provider": "stooq_preview",
            "live_http_requested": live,
            "write_cache_requested": False,
            "live_http_performed": False,
            "cache_write_performed": False,
            "raw_response_included": False,
            "symbol_count": 0,
            "results": [],
            "summary": {
                "dry_run": 0,
                "preview_ok": 0,
                "success": 0,
                "validation_error": 0,
                "parse_error": 0,
                "transport_error": 0,
            },
            "detail": "No valid symbols after normalization (and no invalid rows emitted).",
            "operator_summary": _operator_summary_zeros(),
            "observation_only": True,
        }

    aggregated_live = False
    aggregated_wr = False
    aggregated_cache_wr = False

    for norm in normed:
        payload = stooq_live_preview_sanitized_bars(norm, live=live, write_cache=False)
        aggregated_live |= bool(payload.get("live_http_performed"))
        aggregated_wr |= bool(payload.get("raw_response_included"))
        aggregated_cache_wr |= bool(payload.get("cache_write_performed"))
        results.append(_row_from_payload(norm, payload))

    summary: dict[str, int] = {
        "dry_run": 0,
        "preview_ok": 0,
        "success": 0,
        "validation_error": 0,
        "parse_error": 0,
        "transport_error": 0,
    }
    for rw in results:
        st = str(rw.get("status") or "unknown")
        if st == "http_error":
            summary["transport_error"] += 1
        elif st in summary:
            summary[st] += 1
        else:
            summary.setdefault("validation_error", 0)
            summary["validation_error"] += 1

    return {
        "status": "batch_preview_ok",
        "provider": "stooq_preview",
        "live_http_requested": live,
        "write_cache_requested": False,
        "live_http_performed": aggregated_live,
        "cache_write_performed": aggregated_cache_wr,
        "raw_response_included": aggregated_wr,
        "symbol_count": len(results),
        "results": results,
        "summary": summary,
        "operator_summary": compute_operator_summary_from_rows(results),
        "observation_only": True,
    }


def symbols_from_us_watchlist_file(*, limit: int | None = None, path_override: Path | None = None) -> list[str]:
    """Normalized tickers from **`us_watchlist.yaml`** (existing order + YAML dedupe)."""

    ticks = load_us_watchlist_tickers(path_override)
    if isinstance(limit, int) and limit > 0:
        ticks = ticks[:limit]
    return ticks