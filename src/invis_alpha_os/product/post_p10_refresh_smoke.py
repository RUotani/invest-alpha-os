"""Read-only post-P10 refresh smoke summary (docs/163)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import CONFIG_DIR, OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.product.ops_smoke_report import build_ops_smoke_report
from invis_alpha_os.product.ops_smoke_taxonomy import classify_ops_smoke_strict
from invis_alpha_os.product.peer_sync_forward_validation import compute_peer_sync_forward_join
from invis_alpha_os.product.us_forward_return_validation import (
    classify_forward_skip_pattern,
    compute_us_forward_returns,
    forward_p3_progress,
    observation_log_line_count,
)
from invis_alpha_os.product.us_universe_expansion import build_us_universe_expansion_report

_DEFAULT_STALE_REFRESH_SYMBOLS: tuple[str, ...] = ("MSFT", "NVDA", "GOOGL", "AAPL")


def forward_p3_recommended_actions(
    *,
    skip_pattern: str,
    tier1_missing: list[str],
    stale_skips: int = 0,
    forward_matched: int = 0,
    stale_skip_by_symbol: list[dict[str, Any]] | None = None,
    peer_sync_matched: int = 0,
    resolution_outcomes: dict[str, int] | None = None,
    insufficient_future_share: float | None = None,
    event_date_source_as_of_share: float | None = None,
    l1_write_gate: dict[str, Any] | None = None,
) -> list[str]:
    """Read-only next steps toward forward P3 (docs/161/163; no live HTTP)."""

    if forward_matched >= 10:
        return [
            "Re-run validate us-forward-returns --format markdown to confirm sample_quality=usable",
        ]
    if forward_matched > 0:
        needed = max(0, 10 - forward_matched)
        actions = [
            f"Forward P3: {forward_matched}/10 matched; ~{needed} more rows toward usable (weekly accumulation)",
            ".venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --format markdown",
            ".venv/bin/python -m invis_alpha_os.cli.main validate post-refresh-smoke --format markdown",
        ]
        if peer_sync_matched > 0:
            if peer_sync_matched >= 10:
                actions.append(
                    f"Peer-sync forward: usable ({peer_sync_matched} matched)"
                )
            else:
                ps_needed = max(0, 10 - peer_sync_matched)
                actions.append(
                    f"Peer-sync forward: {peer_sync_matched}/10 matched; ~{ps_needed} more toward usable"
                )
        if stale_skip_by_symbol:
            preview = ", ".join(
                f"{item.get('symbol')}({item.get('count')})" for item in stale_skip_by_symbol[:6]
            )
            actions.append(
                f"Historical stale skips may persist in log: {preview} (docs/161; new writes use fresh cache)"
            )
        if resolution_outcomes:
            insuf = int(resolution_outcomes.get("insufficient_future_bars") or 0)
            stale = int(resolution_outcomes.get("cache_stale_event_after_cache_end") or 0)
            if insuf > max(stale, 1) * 5:
                actions.append(
                    "Dominant skip: insufficient_future_bars — fresh weekly rows need time in cache; "
                    "validate forward-p3-status breakdown after each wave (docs/161)"
                )
        if insufficient_future_share is not None and insufficient_future_share >= 0.9:
            actions.append(
                f"insufficient_future_share={insufficient_future_share:.0%}: calendar time dominates; "
                "extra P10 batches alone unlikely to reach 10/10 matched (docs/161)"
            )
        if (
            event_date_source_as_of_share is not None
            and event_date_source_as_of_share < 0.5
        ):
            actions.append(
                f"event_date_source_as_of_share={event_date_source_as_of_share:.0%}: "
                "many rows use created_at; new weekly writes with as_of= mature over calendar time (docs/161)"
            )
        gate = l1_write_gate or {}
        if gate.get("next_action"):
            actions.append(str(gate["next_action"]))
        elif gate.get("status") == "ready":
            actions.append(
                "L1 ready: validate forward-p3-status p3_weekly_write_plan.write_now_count > 0"
            )
        return actions

    actions: list[str] = []
    if tier1_missing:
        preview = ", ".join(tier1_missing[:5])
        if len(tier1_missing) > 5:
            preview += f", … +{len(tier1_missing) - 5}"
        actions.append(
            f"Gated: P10 tier-1 refresh for missing symbols ({preview}) — docs/162 (chat approval)"
        )

    pattern = (skip_pattern or "").strip().lower()
    if pattern == "fresh_log":
        actions.extend(
            [
                "Gated: weekly-us-observation --write-observation-log --with-peer-sync (chat approval)",
                "Read-only: validate us-forward-returns --backtest-within-cache --format markdown",
                "Accumulate ISO weeks; avoid drawing conclusions from matched=0",
            ]
        )
    elif pattern == "stale_cache":
        syms = ", ".join(_DEFAULT_STALE_REFRESH_SYMBOLS)
        actions.extend(
            [
                f"Gated: P10 cache refresh for stale tier-1 symbols (e.g. {syms}) — docs/162",
                "Ensure observation notes include as_of= (docs/161)",
                "Then: validate post-refresh-smoke --format markdown",
            ]
        )
    elif pattern == "mixed":
        actions.extend(
            [
                "Gated: weekly log write + tier-1 cache refresh (stale + fresh_log mix; chat approval)",
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

    peer_sync_forward: dict[str, Any] = {}
    try:
        peer_sync_forward = compute_peer_sync_forward_join(observation_path=obs)
    except (FileNotFoundError, ValueError):
        peer_sync_forward = {}

    sq = forward.get("sample_quality") or {}
    skipped = forward.get("skipped_reasons") or {}
    matched = int(forward.get("rows_matched") or 0)
    skip_pattern = str(sq.get("skip_pattern") or "")
    stale_skips = int(skipped.get("cache_stale_event_after_cache_end") or 0)
    ps_matched = int(peer_sync_forward.get("rows_matched") or 0)
    ps_sq = peer_sync_forward.get("sample_quality") or {}
    tier1_ok = not tier1_missing
    forward_ok = matched > 0 and str(sq.get("status") or "") in {"thin", "usable"}
    from invis_alpha_os.product.us_signal_iso_week_dedupe import (
        build_p3_l1_write_gate_for_observation,
    )

    l1_gate = build_p3_l1_write_gate_for_observation(
        observation_path=obs,
        stall_diagnosis=forward.get("p3_stall_diagnosis"),
        path_base=root,
    )
    recommended = forward_p3_recommended_actions(
        skip_pattern=skip_pattern,
        tier1_missing=tier1_missing,
        stale_skips=stale_skips,
        forward_matched=matched,
        stale_skip_by_symbol=list(forward.get("stale_skip_by_symbol") or []),
        peer_sync_matched=ps_matched,
        l1_write_gate=l1_gate,
    )

    return {
        "tier1_missing": tier1_missing,
        "observation_log_lines": observation_log_line_count(obs),
        "forward_matched": matched,
        "forward_sample_quality": str(sq.get("status") or ""),
        "forward_p3_progress": sq.get("p3_progress") or forward_p3_progress(matched),
        "peer_sync_forward_matched": ps_matched,
        "peer_sync_sample_quality": str(ps_sq.get("status") or ""),
        "peer_sync_p3_progress": ps_sq.get("p3_progress") or forward_p3_progress(ps_matched),
        "skip_pattern": skip_pattern,
        "stale_skip_count": stale_skips,
        "stale_skip_by_symbol": list(forward.get("stale_skip_by_symbol") or [])[:6],
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

    peer_sync_forward: dict[str, Any] = {}
    try:
        peer_sync_forward = compute_peer_sync_forward_join(observation_path=obs)
    except (FileNotFoundError, ValueError):
        peer_sync_forward = {}

    ops = build_ops_smoke_report(path_base=root)
    tax = classify_ops_smoke_strict(ops)
    ps_matched = int(peer_sync_forward.get("rows_matched") or 0)
    ps_sq = peer_sync_forward.get("sample_quality") or {}

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
            "id": "peer_sync_forward_matched",
            "status": "pass" if ps_matched >= 10 else ("warn" if ps_matched > 0 else "warn"),
            "detail": (
                f"matched={ps_matched} sample_quality={ps_sq.get('status')} "
                f"progress={forward_p3_progress(ps_matched).get('progress_label')}"
            ),
        },
        {
            "id": "peer_forward_usable",
            "status": "pass" if str(ps_sq.get("status") or "") == "usable" else "warn",
            "detail": f"peer_sync_forward quality={ps_sq.get('status')}",
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
    from invis_alpha_os.product.us_signal_iso_week_dedupe import (
        build_p3_l1_write_gate_for_observation,
    )

    l1_gate = build_p3_l1_write_gate_for_observation(
        observation_path=obs,
        stall_diagnosis=forward.get("p3_stall_diagnosis"),
        path_base=root,
    )
    recommended = forward_p3_recommended_actions(
        skip_pattern=skip_pattern,
        tier1_missing=tier1_missing,
        stale_skips=stale_skips,
        forward_matched=matched_rows,
        stale_skip_by_symbol=list(forward.get("stale_skip_by_symbol") or []),
        peer_sync_matched=ps_matched,
        l1_write_gate=l1_gate,
    )

    us_forward = {
        "rows_matched": matched_rows,
        "sample_quality": sq,
        "skip_pattern": skip_pattern,
        "skipped_reasons": skipped,
    }
    peer_sync_forward_out = {
        "rows_matched": ps_matched,
        "sample_quality": ps_sq,
        "skipped_reasons": peer_sync_forward.get("skipped_reasons") or {},
    }
    log_lines = observation_log_line_count(obs)
    return {
        "schema_version": 1,
        "checks": checks,
        "tier1_missing": tier1_missing,
        "observation_log_lines": log_lines,
        "skip_pattern": skip_pattern,
        "forward_validation": us_forward,
        "us_forward": us_forward,
        "peer_sync_forward_validation": peer_sync_forward_out,
        "peer_sync_forward": peer_sync_forward_out,
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
        f"- observation_log_lines: {report.get('observation_log_lines', 0)}",
        f"- skip_pattern: {report.get('skip_pattern') or '(n/a)'}",
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
    p3 = sq.get("p3_progress") or {}
    lines.extend(
        [
            "",
            "## Forward validation",
            f"- matched: {fwd.get('rows_matched', 0)}",
            f"- sample_quality: {sq.get('status')}",
            f"- skip_pattern: {fwd.get('skip_pattern')}",
        ]
    )
    if p3.get("progress_label"):
        lines.append(f"- p3_progress: {p3.get('progress_label')}")
    ps_fwd = report.get("peer_sync_forward_validation") or {}
    ps_sq = ps_fwd.get("sample_quality") or {}
    if ps_fwd:
        lines.extend(
            [
                "",
                "## Peer sync forward",
                f"- matched: {ps_fwd.get('rows_matched', 0)}",
                f"- sample_quality: {ps_sq.get('status')}",
            ]
        )
        ps_p3 = ps_sq.get("p3_progress") or {}
        if ps_p3.get("progress_label"):
            lines.append(f"- p3_progress: {ps_p3.get('progress_label')}")
    for action in report.get("recommended_actions") or []:
        lines.append(f"- recommended: {action}")
    lines.append("")
    return "\n".join(lines)
