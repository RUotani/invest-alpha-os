"""Read-only post-P10 refresh smoke summary (docs/163)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import CONFIG_DIR, OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.product.ops_smoke_report import build_ops_smoke_report
from invis_alpha_os.product.ops_smoke_taxonomy import classify_ops_smoke_strict
from invis_alpha_os.product.us_forward_return_validation import (
    classify_forward_skip_pattern,
    compute_us_forward_returns,
)
from invis_alpha_os.product.us_universe_expansion import build_us_universe_expansion_report

_DEFAULT_STALE_REFRESH_SYMBOLS: tuple[str, ...] = ("MSFT", "NVDA", "GOOGL", "AAPL")


def forward_p3_recommended_actions(
    *,
    skip_pattern: str,
    tier1_missing: list[str],
    stale_skips: int = 0,
    forward_matched: int = 0,
) -> list[str]:
    """Read-only next steps toward forward P3 (docs/161/163; no live HTTP)."""

    if forward_matched > 0:
        return [
            "Re-run validate us-forward-returns --format markdown to confirm sample_quality=usable",
        ]

    actions: list[str] = []
    if tier1_missing:
        preview = ", ".join(tier1_missing[:5])
        if len(tier1_missing) > 5:
            preview += f", … +{len(tier1_missing) - 5}"
        actions.append(
            f"Approval required: P10 tier-1 refresh for missing symbols ({preview}) — docs/162"
        )

    pattern = (skip_pattern or "").strip().lower()
    if pattern == "fresh_log":
        actions.extend(
            [
                "Approval E: weekly-us-observation --write-observation-log --with-peer-sync",
                "Read-only: validate us-forward-returns --backtest-within-cache --format markdown",
                "Accumulate ISO weeks; avoid drawing conclusions from matched=0",
            ]
        )
    elif pattern == "stale_cache":
        syms = ", ".join(_DEFAULT_STALE_REFRESH_SYMBOLS)
        actions.extend(
            [
                f"Approval F: P10 cache refresh for stale tier-1 symbols (e.g. {syms})",
                "Ensure observation notes include as_of= (docs/161)",
                "Then: validate post-refresh-smoke --format markdown",
            ]
        )
    elif pattern == "mixed":
        actions.extend(
            [
                "Approval E + F: weekly log write and tier-1 cache refresh (stale + fresh_log mix)",
                f"Stale skip count={stale_skips}; see docs/161 mixed pattern",
                "Then: validate post-refresh-smoke and snapshot observation-health",
            ]
        )
    elif pattern in {"other", "none", ""}:
        actions.append(
            "Run validate us-forward-returns --format markdown and snapshot observation-health"
        )
    else:
        actions.append(f"See docs/161 for skip_pattern={skip_pattern}")

    return actions


def build_post_refresh_hints_light(
    *,
    path_base: Path | None = None,
    observation_path: Path | None = None,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Lightweight docs/163 hints for observation-health (no full ops-smoke)."""

    root = path_base or ROOT_DIR
    obs = observation_path or (OUTPUTS_DIR / "observation_log" / "observation_log.jsonl")
    cache = cache_dir or (OUTPUTS_DIR / "market_data" / "us_daily_bars")

    tier1_missing: list[str] = []
    try:
        expansion = build_us_universe_expansion_report(
            path_base=root,
            tier="1",
            missing_only=True,
        )
        tier1_missing = list(expansion.get("tier_1_missing_refresh_order") or [])
    except (FileNotFoundError, ValueError):
        tier1_missing = []

    forward: dict[str, Any] = {}
    try:
        forward = compute_us_forward_returns(
            observation_path=obs,
            cache_dir=cache,
            path_base=root,
        )
    except (FileNotFoundError, ValueError):
        forward = {}

    sq = forward.get("sample_quality") or {}
    skipped = forward.get("skipped_reasons") or {}
    matched = int(forward.get("rows_matched") or 0)
    skip_pattern = str(sq.get("skip_pattern") or "")
    stale_skips = int(skipped.get("cache_stale_event_after_cache_end") or 0)
    tier1_ok = not tier1_missing
    forward_ok = matched > 0 and str(sq.get("status") or "") in {"thin", "usable"}
    recommended = forward_p3_recommended_actions(
        skip_pattern=skip_pattern,
        tier1_missing=tier1_missing,
        stale_skips=stale_skips,
        forward_matched=matched,
    )

    return {
        "tier1_missing": tier1_missing,
        "forward_matched": matched,
        "forward_sample_quality": str(sq.get("status") or ""),
        "skip_pattern": skip_pattern,
        "stale_skip_count": stale_skips,
        "recommended_actions": recommended,
        "docs_163_hard_pass": tier1_ok and forward_ok,
        "observation_only": True,
    }


def build_post_p10_refresh_smoke_summary(
    *,
    path_base: Path | None = None,
    observation_path: Path | None = None,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Aggregate docs/163 checks without live HTTP or cache writes."""

    root = path_base or ROOT_DIR
    obs = observation_path or (OUTPUTS_DIR / "observation_log" / "observation_log.jsonl")
    cache = cache_dir or (OUTPUTS_DIR / "market_data" / "us_daily_bars")

    tier1_missing: list[str] = []
    try:
        expansion = build_us_universe_expansion_report(
            path_base=root,
            tier="1",
            missing_only=True,
        )
        tier1_missing = list(expansion.get("tier_1_missing_refresh_order") or [])
    except (FileNotFoundError, ValueError):
        tier1_missing = []

    forward: dict[str, Any] = {}
    try:
        forward = compute_us_forward_returns(
            observation_path=obs,
            cache_dir=cache,
            path_base=root,
        )
    except (FileNotFoundError, ValueError):
        forward = {}

    sq = forward.get("sample_quality") or {}
    skipped = forward.get("skipped_reasons") or {}
    signal_rows = int(forward.get("rows_considered") or 0)
    skip_pattern = str(sq.get("skip_pattern") or classify_forward_skip_pattern(skipped, signal_rows=signal_rows))

    ops = build_ops_smoke_report(path_base=root)
    tax = classify_ops_smoke_strict(ops)

    checks: list[dict[str, Any]] = [
        {
            "id": "tier1_missing",
            "status": "pass" if not tier1_missing else "warn",
            "detail": f"count={len(tier1_missing)} symbols={tier1_missing[:5]}",
        },
        {
            "id": "forward_matched",
            "status": "pass" if int(forward.get("rows_matched") or 0) > 0 else "warn",
            "detail": f"matched={forward.get('rows_matched', 0)} sample_quality={sq.get('status')}",
        },
        {
            "id": "forward_not_empty",
            "status": "pass" if str(sq.get("status") or "") != "empty" else "warn",
            "detail": str(sq.get("reason") or ""),
        },
        {
            "id": "stale_skip_low",
            "status": "pass"
            if int(skipped.get("cache_stale_event_after_cache_end") or 0) == 0
            else "warn",
            "detail": f"cache_stale_skips={skipped.get('cache_stale_event_after_cache_end', 0)}",
        },
        {
            "id": "ops_smoke_strict",
            "status": "pass" if tax.get("taxonomy") == "PASS" else "expected_blocked",
            "detail": f"taxonomy={tax.get('taxonomy')} reasons={tax.get('reasons')}",
        },
    ]
    matched_rows = int(forward.get("rows_matched") or 0)
    stale_skips = int(skipped.get("cache_stale_event_after_cache_end") or 0)
    hard_pass = (
        not tier1_missing
        and matched_rows > 0
        and str(sq.get("status") or "") in {"thin", "usable"}
    )
    recommended = forward_p3_recommended_actions(
        skip_pattern=skip_pattern,
        tier1_missing=tier1_missing,
        stale_skips=stale_skips,
        forward_matched=matched_rows,
    )

    return {
        "schema_version": 1,
        "checks": checks,
        "tier1_missing": tier1_missing,
        "forward_validation": {
            "rows_matched": forward.get("rows_matched", 0),
            "sample_quality": sq,
            "skip_pattern": skip_pattern,
            "skipped_reasons": skipped,
        },
        "recommended_actions": recommended,
        "ops_smoke_taxonomy": tax,
        "docs_163_hard_pass": hard_pass,
        "observation_only": True,
        "live_http": False,
    }


def format_post_p10_refresh_smoke_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Post-P10 refresh smoke (read-only)",
        "",
        "Observation only — not buy/sell advice.",
        "",
        f"- docs_163_hard_pass: **{report.get('docs_163_hard_pass')}**",
        "",
        "## Checks",
        "",
        "| id | status | detail |",
        "| --- | --- | --- |",
    ]
    for c in report.get("checks") or []:
        if isinstance(c, dict):
            lines.append(f"| {c.get('id')} | {c.get('status')} | {c.get('detail')} |")
    fwd = report.get("forward_validation") or {}
    sq = fwd.get("sample_quality") or {}
    lines.extend(
        [
            "",
            "## Forward validation",
            f"- matched: {fwd.get('rows_matched', 0)}",
            f"- sample_quality: {sq.get('status')}",
            f"- skip_pattern: {fwd.get('skip_pattern')}",
        ]
    )
    for action in report.get("recommended_actions") or []:
        lines.append(f"- recommended: {action}")
    lines.append("")
    return "\n".join(lines)
