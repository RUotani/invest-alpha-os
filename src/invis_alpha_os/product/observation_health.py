"""Unified read-only observation_log health report (Wave B)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import CONFIG_DIR, OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.observation.us_peer_sync_summary import summarize_peer_sync_observation_log
from invis_alpha_os.product.portfolio_observation_summary import build_portfolio_observation_summary
from invis_alpha_os.product.jp_peer_sync_loader import classify_peer_map_symbol
from invis_alpha_os.product.portfolio_readiness import evaluate_portfolio_readiness
from invis_alpha_os.signals.peer_sync import load_peer_map
from invis_alpha_os.product.us_forward_return_validation import (
    forward_validation_next_commands,
)
from invis_alpha_os.product.us_universe_expansion import build_us_universe_expansion_report
from invis_alpha_os.product.weekly_us_observation import build_enriched_us_observation_summary


@dataclass(frozen=True)
class ObservationHealthReport:
    observation_path: str
    us_signals: dict[str, Any]
    peer_sync: dict[str, Any]
    portfolio: dict[str, Any]
    forward_validation: dict[str, Any] | None
    peer_sync_forward: dict[str, Any] | None
    log_integrity: dict[str, Any]
    tier1_missing: list[str]
    post_refresh_hints: dict[str, Any]
    next_commands: list[str]
    observation_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "observation_path": self.observation_path,
            "us_signals": self.us_signals,
            "peer_sync": self.peer_sync,
            "portfolio": self.portfolio,
            "forward_validation": self.forward_validation,
            "peer_sync_forward": self.peer_sync_forward,
            "log_integrity": self.log_integrity,
            "tier1_missing": self.tier1_missing,
            "post_refresh_hints": self.post_refresh_hints,
            "next_commands": self.next_commands,
            "observation_only": self.observation_only,
        }
        repeat_summary = self.us_signals.get("repeat_summary")
        if repeat_summary:
            payload["repeat_summary"] = repeat_summary
        return payload


def _scan_log_integrity(observation_path: Path) -> dict[str, Any]:
    if not observation_path.is_file():
        return {
            "status": "missing",
            "total_lines": 0,
            "json_parse_errors": 0,
            "empty_lines": 0,
            "unclassified_notes": 0,
        }
    total = 0
    empty = 0
    parse_errors = 0
    unclassified = 0
    from invis_alpha_os.observation.us_peer_sync_note import US_PEER_SYNC_NOTE_PREFIX
    from invis_alpha_os.observation.us_signal_note import US_SIGNAL_NOTE_PREFIX

    for line in observation_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            empty += 1
            continue
        total += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            parse_errors += 1
            continue
        note = str(row.get("note") or "")
        if US_SIGNAL_NOTE_PREFIX not in note and US_PEER_SYNC_NOTE_PREFIX not in note:
            unclassified += 1
    return {
        "status": "ok",
        "total_lines": total,
        "json_parse_errors": parse_errors,
        "empty_lines": empty,
        "unclassified_notes": unclassified,
    }


def _dedupe_next_commands(commands: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for cmd in commands:
        if cmd in seen:
            continue
        seen.add(cmd)
        out.append(cmd)
    return out


def build_observation_health_report(
    *,
    path_base: Path | None = None,
    observation_path: Path | None = None,
    cache_dir: Path | None = None,
) -> ObservationHealthReport:
    root = path_base or ROOT_DIR
    obs = observation_path or (OUTPUTS_DIR / "observation_log" / "observation_log.jsonl")
    cache = cache_dir or (OUTPUTS_DIR / "market_data" / "us_daily_bars")
    us = build_enriched_us_observation_summary(obs, path_base=root, cache_dir=cache)
    peer = summarize_peer_sync_observation_log(obs)
    portfolio_summary = build_portfolio_observation_summary(
        path_base=root,
        observation_path=obs,
    )
    readiness = evaluate_portfolio_readiness(
        path_base=root,
        observation_path=obs,
        cache_dir=cache,
    )
    portfolio = {
        **portfolio_summary.to_dict(),
        "readiness": readiness,
    }
    integrity = _scan_log_integrity(obs)

    from invis_alpha_os.product.post_p10_refresh_smoke import build_post_refresh_hints_light

    post_refresh_hints = build_post_refresh_hints_light(
        path_base=root,
        observation_path=obs,
        cache_dir=cache,
    )

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

    forward: dict[str, Any] | None = None
    if obs.is_file() and int(us.get("us_signal_rows") or 0) > 0:
        try:
            from invis_alpha_os.product.us_forward_return_validation import compute_us_forward_returns

            forward = compute_us_forward_returns(
                observation_path=obs,
                cache_dir=cache,
                path_base=root,
            )
        except (FileNotFoundError, ValueError):
            forward = None

    peer_sync_forward: dict[str, Any] | None = None
    if obs.is_file() and int(peer.get("peer_sync_rows") or 0) > 0:
        try:
            from invis_alpha_os.product.peer_sync_forward_validation import (
                compute_peer_sync_forward_join,
            )

            peer_sync_forward = compute_peer_sync_forward_join(observation_path=obs)
        except (FileNotFoundError, ValueError):
            peer_sync_forward = None

    next_commands: list[str] = [
        ".venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation --dry-run --with-peer-sync",
        ".venv/bin/python -m invis_alpha_os.cli.main log us-signals-summary",
        ".venv/bin/python -m invis_alpha_os.cli.main log peer-sync-summary",
    ]
    if forward:
        sq = forward.get("sample_quality") or {}
        st = str(sq.get("status") or "")
        if st == "empty":
            next_commands.extend(forward_validation_next_commands())
            next_commands.append(
                "weekly-us-observation --write-observation-log  # explicit approval; writes outputs/"
            )
        elif st == "thin":
            next_commands.extend(forward_validation_next_commands())
            next_commands.append(
                ".venv/bin/python -m invis_alpha_os.cli.main validate post-refresh-smoke --format markdown"
            )
            if not post_refresh_hints.get("docs_163_hard_pass"):
                next_commands.append(
                    "weekly-us-observation --write-observation-log  # explicit approval; writes outputs/"
                )
    elif us.get("status") == "missing":
        next_commands.append(
            "weekly-us-observation --write-observation-log  # explicit approval; writes outputs/"
        )

    if peer_sync_forward:
        ps_sq = peer_sync_forward.get("sample_quality") or {}
        ps_st = str(ps_sq.get("status") or "")
        if ps_st in {"empty", "thin"}:
            for cmd in ps_sq.get("next_commands") or []:
                next_commands.append(cmd)

    pmap_path = (path_base or ROOT_DIR) / "config" / "peer_map.yaml"
    if not pmap_path.is_file():
        pmap_path = CONFIG_DIR / "peer_map.yaml"
    if pmap_path.is_file():
        try:
            peer_map = load_peer_map(pmap_path)
            has_jp = any(
                classify_peer_map_symbol(anchor) == "jp"
                or any(classify_peer_map_symbol(str(p)) == "jp" for p in peers)
                for anchor, peers in peer_map.items()
            )
            if has_jp:
                next_commands.append(
                    ".venv/bin/python -m invis_alpha_os.cli.main validate "
                    "jp-peer-sync-readiness --format markdown"
                )
        except (ValueError, OSError):
            pass

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(root))
        except ValueError:
            return str(p)

    return ObservationHealthReport(
        observation_path=_rel(obs),
        us_signals=us,
        peer_sync=peer,
        portfolio=portfolio,
        forward_validation=forward,
        peer_sync_forward=peer_sync_forward,
        log_integrity=integrity,
        tier1_missing=tier1_missing,
        post_refresh_hints=post_refresh_hints,
        next_commands=_dedupe_next_commands(next_commands),
    )


def format_observation_health_markdown(report: ObservationHealthReport) -> str:
    us = report.us_signals
    peer = report.peer_sync
    port = report.portfolio
    integrity = report.log_integrity
    lines = [
        "# Observation health (read-only)",
        "",
        "Observation only — not buy/sell advice.",
        "",
        f"- observation_log: `{report.observation_path}`",
    ]
    hints = report.post_refresh_hints or {}
    if hints:
        lines.extend(
            [
                "",
                "## Post-refresh hints (docs/163)",
                f"- docs_163_hard_pass: {hints.get('docs_163_hard_pass')}",
                f"- forward_matched: {hints.get('forward_matched', 0)}",
                f"- skip_pattern: {hints.get('skip_pattern') or '(n/a)'}",
            ]
        )
        fwd_p3 = hints.get("forward_p3_progress") or {}
        if fwd_p3.get("progress_label"):
            lines.append(f"- forward_p3_progress: {fwd_p3.get('progress_label')}")
        ps_m = hints.get("peer_sync_forward_matched")
        if ps_m is not None:
            lines.append(f"- peer_sync_forward_matched: {ps_m}")
            ps_p3 = hints.get("peer_sync_p3_progress") or {}
            if ps_p3.get("progress_label"):
                lines.append(f"- peer_sync_p3_progress: {ps_p3.get('progress_label')}")
        stale_top = hints.get("stale_skip_by_symbol") or []
        if stale_top:
            preview = ", ".join(
                f"{item.get('symbol')}({item.get('count')})" for item in stale_top[:5]
            )
            lines.append(f"- stale_skip_symbols: {preview}")
        for action in hints.get("recommended_actions") or []:
            lines.append(f"- forward_p3_action: {action}")
    if report.tier1_missing:
        preview = ", ".join(report.tier1_missing[:8])
        if len(report.tier1_missing) > 8:
            preview += f", … (+{len(report.tier1_missing) - 8})"
        lines.append(f"- tier-1 cache gaps (gated refresh): **{preview}**")
    lines.extend(
        [
            "",
            "## US signals",
            f"- status: {us.get('status')}",
            f"- us_signal_rows: {us.get('us_signal_rows', 0)}",
            f"- by_status: {us.get('by_status', {})}",
        ]
    )
    weekly = us.get("weekly_trend") or {}
    if weekly.get("status"):
        lines.append(
            f"- weekly_trend: {weekly.get('status')} "
            f"(latest={weekly.get('latest_week_count', 0)} prior={weekly.get('prior_week_count', 0)})"
        )
        if weekly.get("trailing_7d_count") is not None:
            lines.append(f"- trailing_7d_count: {weekly.get('trailing_7d_count')}")
        if weekly.get("calendar_week_caveat"):
            lines.append(f"- calendar_week_caveat: {weekly.get('calendar_week_caveat')}")
    repeat_n = us.get("repeat_signal_count")
    repeat_syms = us.get("repeat_signal_symbols") or []
    if repeat_n:
        lines.append(f"- repeat_signal_count: {repeat_n}")
    if repeat_syms:
        preview = ", ".join(repeat_syms[:8])
        if len(repeat_syms) > 8:
            preview += f", … (+{len(repeat_syms) - 8})"
        lines.append(f"- repeat_signal_symbols: {preview}")
    repeat_summary = us.get("repeat_summary") or {}
    repeat_rows = repeat_summary.get("repeat_by_symbol") or []
    if repeat_rows:
        lines.extend(["", "## Repeat summary", ""])
        for item in repeat_rows[:8]:
            if isinstance(item, dict):
                stale = item.get("stale_repeat_flag")
                stale_tag = " stale_repeat" if stale else ""
                lines.append(
                    f"- {item.get('symbol')}: count={item.get('count')} "
                    f"weeks={item.get('consecutive_weeks')}{stale_tag} "
                    f"first={str(item.get('first_seen', ''))[:10]} "
                    f"last={str(item.get('last_seen', ''))[:10]}"
                )
    checklist = us.get("research_checklist") or []
    if checklist:
        lines.extend(["", "## Research checklist", ""])
        for item in checklist[:6]:
            if isinstance(item, dict):
                sym = item.get("symbol") or "—"
                lines.append(
                    f"- [{item.get('category')}] {sym}: {item.get('reason')}"
                )
    lines.extend(
        [
        "",
        "## Peer sync rows",
        f"- peer_sync_rows: {peer.get('peer_sync_rows', 0)}",
        f"- by_status: {peer.get('by_status', {})}",
        ]
    )
    if report.peer_sync_forward:
        ps_fwd = report.peer_sync_forward
        ps_sq = ps_fwd.get("sample_quality") or {}
        ps_at_t = ps_fwd.get("peer_sync_at_t") or {}
        lines.extend(
            [
                "",
                "## Peer sync forward (docs/158)",
                f"- peer_sync_at_t: {ps_at_t.get('status')} — {ps_at_t.get('reason', '')}",
                f"- rows_matched: {ps_fwd.get('rows_matched', 0)}",
                f"- sample_quality: {ps_sq.get('status')} — {ps_sq.get('interpretation', '')}",
            ]
        )
        if ps_sq.get("needed_more_samples"):
            lines.append(f"- needed_more_samples: {ps_sq.get('needed_more_samples')}")
    lines.extend(
        [
        "",
        "## Portfolio linkage",
        f"- shadow positions: {port.get('shadow_position_count', 0)}",
        f"- resolved links: {port.get('positions_with_resolved_links', 0)}",
        ]
    )
    readiness = port.get("readiness") or {}
    if readiness:
        lines.extend(
            [
                "",
                "## Portfolio readiness (docs/154)",
                f"- accepted_tier: {readiness.get('accepted_tier')} — {readiness.get('accepted_tier_label', '')}",
                f"- suggested_percent: {readiness.get('suggested_percent')} (rubric)",
            ]
        )
        human_pct = readiness.get("state_percent_human_accepted")
        if human_pct is not None:
            lines.append(f"- human_accepted_percent: {human_pct}")
        if readiness.get("human_accepted_tier"):
            lines.append(f"- human_accepted_tier: {readiness.get('human_accepted_tier')}")
        if readiness.get("state_percent_matches_rubric"):
            lines.append("- state_percent_matches_rubric: true")
        elif human_pct is not None:
            lines.append(
                f"- state_percent_matches_rubric: false "
                f"(suggested={readiness.get('suggested_percent')})"
            )
        seed_hint = readiness.get("shadow_seed_hint")
        if seed_hint:
            lines.append(f"- shadow_seed_hint: {seed_hint}")
        p1_hint = readiness.get("p1_linkage_hint")
        if p1_hint:
            lines.append(f"- p1_linkage_hint: {p1_hint}")
        p2_hint = readiness.get("p2_weekly_hint")
        if p2_hint:
            lines.append(f"- p2_weekly_hint: {p2_hint}")
        p3_prog = readiness.get("p3_forward_progress") or {}
        if p3_prog.get("progress_label"):
            lines.append(f"- portfolio_p3_forward: {p3_prog.get('progress_label')}")
        if readiness.get("peer_forward_note"):
            lines.append(f"- peer_forward_note: {readiness.get('peer_forward_note')}")
        wt = readiness.get("weekly_trend") or {}
        if wt.get("status"):
            lines.append(
                f"- weekly_trend: {wt.get('status')} "
                f"(latest={wt.get('latest_week_count', 0)} prior={wt.get('prior_week_count', 0)} "
                f"trailing_7d={wt.get('trailing_7d_count', 0)})"
            )
        nxt = readiness.get("next_milestone")
        if isinstance(nxt, dict):
            lines.append(
                f"- next_milestone: {nxt.get('id')} {nxt.get('label')} ({nxt.get('status')})"
            )
        for m in readiness.get("milestones") or []:
            if isinstance(m, dict):
                mark = "✓" if m.get("passed") else "·"
                lines.append(f"- {mark} {m.get('id')} {m.get('label')}: {m.get('detail')}")
    lines.extend(
        [
        "",
        "## Log integrity",
        f"- total lines: {integrity.get('total_lines', 0)}",
        f"- json_parse_errors: {integrity.get('json_parse_errors', 0)}",
        f"- unclassified_notes: {integrity.get('unclassified_notes', 0)}",
        ]
    )
    if report.forward_validation:
        fwd = report.forward_validation
        sq = fwd.get("sample_quality") or {}
        lines.extend(
            [
                "",
                "## Forward validation",
                f"- sample_quality: {sq.get('status')} — {sq.get('interpretation', '')}",
                f"- matched rows: {fwd.get('rows_matched', 0)}",
            ]
        )
        skipped = fwd.get("skipped_reasons") or {}
        if skipped:
            top = max(skipped.items(), key=lambda kv: kv[1])
            lines.append(f"- top skipped_reason: {top[0]} ({top[1]})")
        if sq.get("needed_more_samples"):
            lines.append(f"- needed_more_samples: {sq.get('needed_more_samples')}")
        skip_pat = sq.get("skip_pattern")
        if skip_pat and skip_pat != "none":
            lines.append(f"- skip_pattern: {skip_pat} (docs/161)")
        p3 = sq.get("p3_progress") or {}
        if p3.get("progress_label"):
            lines.append(f"- p3_progress: {p3.get('progress_label')}")
        stale_syms = fwd.get("stale_skip_by_symbol") or []
        if stale_syms:
            preview = ", ".join(
                f"{item.get('symbol')}({item.get('count')})" for item in stale_syms[:5]
            )
            lines.append(f"- stale_skip_symbols: {preview}")
    ps_fwd = report.peer_sync_forward
    if ps_fwd:
        ps_sq = ps_fwd.get("sample_quality") or {}
        lines.extend(
            [
                "",
                "## Peer sync forward validation",
                f"- sample_quality: {ps_sq.get('status')} — {ps_sq.get('interpretation', '')}",
                f"- matched rows: {ps_fwd.get('rows_matched', 0)}",
            ]
        )
        ps_p3 = ps_sq.get("p3_progress") or {}
        if ps_p3.get("progress_label"):
            lines.append(f"- p3_progress: {ps_p3.get('progress_label')}")
        ps_skipped = ps_fwd.get("skipped_reasons") or {}
        if ps_skipped:
            top = max(ps_skipped.items(), key=lambda kv: kv[1])
            lines.append(f"- top skipped_reason: {top[0]} ({top[1]})")
    lines.extend(["", "## Next commands", ""])
    for cmd in report.next_commands:
        lines.append(f"- `{cmd}`")
    lines.append("")
    return "\n".join(lines)


def format_observation_health_json(report: ObservationHealthReport) -> str:
    import json as _json

    return _json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
