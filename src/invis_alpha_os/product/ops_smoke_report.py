"""Read-only consolidated ops smoke report (no writes, no HTTP)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import CONFIG_DIR, OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.product.observation_health import build_observation_health_report
from invis_alpha_os.product.peer_sync_cache_only import build_peer_sync_cache_only_report
from invis_alpha_os.product.portfolio_observation_summary import build_portfolio_observation_summary
from invis_alpha_os.product.ops_smoke_taxonomy import classify_ops_smoke_strict
from invis_alpha_os.product.us_forward_return_validation import p3_monitoring_next_commands
from invis_alpha_os.product.weekly_us_observation import (
    build_us_watchlist_signals_manifest,
    us_signal_quality_snapshot,
)


@dataclass(frozen=True)
class OpsSmokeCheck:
    name: str
    status: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


@dataclass(frozen=True)
class OpsSmokeReport:
    checks: list[OpsSmokeCheck]
    observation_health: dict[str, Any]
    peer_sync_pairs: int
    portfolio_positions: int
    manifest_entries: int
    signals_ok: int
    signals_total: int
    next_commands: list[str]
    p3_path_line: str | None = None
    portfolio_exposure_line: str | None = None
    observation_only: bool = True
    live_http: bool = False

    @property
    def all_ok(self) -> bool:
        return all(c.status == "ok" for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "all_ok": self.all_ok,
            "checks": [c.to_dict() for c in self.checks],
            "observation_health": self.observation_health,
            "peer_sync_pairs": self.peer_sync_pairs,
            "portfolio_positions": self.portfolio_positions,
            "manifest_entries": self.manifest_entries,
            "signals_ok": self.signals_ok,
            "signals_total": self.signals_total,
            "next_commands": self.next_commands,
            "p3_path_line": self.p3_path_line,
            "portfolio_exposure_line": self.portfolio_exposure_line,
            "observation_only": self.observation_only,
            "live_http": self.live_http,
        }
        payload["strict_taxonomy"] = classify_ops_smoke_strict(self)
        return payload


def _watchlist_manifest_status(entries: int, missing: int) -> str:
    if entries == 0:
        return "fail"
    if missing > 0:
        return "warn"
    return "ok"


def _signal_quality_snapshot_status(signals_ok: int, signals_total: int) -> str:
    if signals_total == 0 or signals_ok < signals_total:
        return "fail"
    return "ok"


def _observation_health_check(health: Any) -> OpsSmokeCheck:
    integrity = health.log_integrity
    parse_err = int(integrity.get("json_parse_errors") or 0)
    us = health.us_signals
    repeat = int(us.get("repeat_signal_count") or 0)
    us_rows = int(us.get("us_signal_rows") or 0)
    fwd = health.forward_validation
    fwd_matched = int(fwd.get("rows_matched") or 0) if isinstance(fwd, dict) else 0
    stale_forward = False
    if isinstance(fwd, dict):
        sq = fwd.get("sample_quality") or {}
        reason = str(sq.get("reason") or "")
        skipped = fwd.get("skipped_reasons") or {}
        stale_forward = (
            fwd_matched == 0
            and us_rows > 0
            and (
                "cache end" in reason
                or int(skipped.get("cache_stale_event_after_cache_end") or 0) > 0
            )
        )
    tier1_gaps = list(getattr(health, "tier1_missing", None) or [])
    ps_fwd = getattr(health, "peer_sync_forward", None)
    peer_sync_forward_thin = False
    peer_rows = int((getattr(health, "peer_sync", None) or {}).get("peer_sync_rows") or 0)
    if isinstance(ps_fwd, dict) and peer_rows > 0:
        ps_sq = ps_fwd.get("sample_quality") or {}
        peer_sync_forward_thin = str(ps_sq.get("status") or "") in {"empty", "thin"}
    repeat_summary = us.get("repeat_summary") or {}
    stale_repeat = sum(
        1
        for item in (repeat_summary.get("repeat_by_symbol") or [])
        if isinstance(item, dict) and item.get("stale_repeat_flag")
    )
    status = "ok"
    if parse_err > 0:
        status = "warn"
    elif repeat > 0 or stale_forward or tier1_gaps or peer_sync_forward_thin or stale_repeat > 0:
        status = "warn"
    detail = f"us_signal_rows={us_rows} parse_errors={parse_err}"
    if repeat > 0:
        detail += f" repeat_signals={repeat}"
    if stale_forward:
        detail += " forward_stale_cache=1"
    if tier1_gaps:
        detail += f" tier1_gaps={len(tier1_gaps)}"
    if peer_sync_forward_thin:
        detail += " peer_sync_forward_thin=1"
    if stale_repeat > 0:
        detail += f" stale_repeat_flags={stale_repeat}"
    if isinstance(fwd, dict):
        from invis_alpha_os.product.us_forward_return_validation import us_forward_p3_axis

        p3_axis = us_forward_p3_axis(fwd)
        us_p3 = p3_axis.get("p3_progress") or {}
        if us_p3.get("progress_label"):
            detail += (
                f" us_p3={us_p3.get('progress_label')}"
                f" rows_matched_all={p3_axis.get('rows_matched_all', 0)}"
            )
    if isinstance(ps_fwd, dict):
        peer_p3 = (ps_fwd.get("sample_quality") or {}).get("p3_progress") or {}
        if peer_p3.get("progress_label"):
            detail += f" peer_p3={peer_p3.get('progress_label')}"
    return OpsSmokeCheck(name="observation_health", status=status, detail=detail)


def build_ops_smoke_report(*, path_base: Path | None = None) -> OpsSmokeReport:
    root = path_base or ROOT_DIR
    checks: list[OpsSmokeCheck] = []

    manifest = build_us_watchlist_signals_manifest(path_base=root)
    entries = len(manifest.get("entries") or [])
    missing = len(manifest.get("missing_cache_symbols") or [])
    checks.append(
        OpsSmokeCheck(
            name="watchlist_manifest",
            status=_watchlist_manifest_status(entries, missing),
            detail=f"entries={entries} missing_cache={missing}",
        )
    )

    quality = us_signal_quality_snapshot(path_base=root)
    sig_ok = int(quality.get("signals_ok") or 0)
    sig_total = int(quality.get("symbol_count") or 0)
    checks.append(
        OpsSmokeCheck(
            name="signal_quality_snapshot",
            status=_signal_quality_snapshot_status(sig_ok, sig_total),
            detail=f"signals_ok={sig_ok}/{sig_total}",
        )
    )

    peer = build_peer_sync_cache_only_report(path_base=root)
    peer_pairs = len(peer.pairs)
    checks.append(
        OpsSmokeCheck(
            name="peer_sync_report",
            status="ok",
            detail=f"pairs_evaluated={peer_pairs}",
        )
    )

    portfolio = build_portfolio_observation_summary(path_base=root)
    checks.append(
        OpsSmokeCheck(
            name="portfolio_summary",
            status="ok",
            detail=f"shadow_positions={portfolio.shadow_position_count}",
        )
    )
    acceptance_path = root / "config" / "portfolio_observation_acceptance.yaml"
    if acceptance_path.is_file():
        from invis_alpha_os.product.portfolio_readiness import evaluate_portfolio_readiness

        readiness = evaluate_portfolio_readiness(path_base=root)
        human_pct = readiness.get("state_percent_human_accepted")
        rubric_tier = readiness.get("accepted_tier")
        checks.append(
            OpsSmokeCheck(
                name="portfolio_human_acceptance",
                status="ok",
                detail=(
                    f"human_percent={human_pct} human_tier={readiness.get('human_accepted_tier')} "
                    f"rubric_tier={rubric_tier} "
                    f"matches_rubric={readiness.get('state_percent_matches_rubric')}"
                ),
            )
        )

    obs_path = OUTPUTS_DIR / "observation_log" / "observation_log.jsonl"
    if not obs_path.is_file():
        obs_path = root / "outputs" / "observation_log" / "observation_log.jsonl"
    health = build_observation_health_report(path_base=root, observation_path=obs_path)
    checks.append(_observation_health_check(health))

    p3_path_line: str | None = None
    portfolio_exposure_line: str | None = None
    if obs_path.is_file():
        from invis_alpha_os.product.p3_path_to_usable import (
            build_weekly_p3_path_preflight,
            format_p3_path_weekly_one_liner,
        )

        p3_preflight = build_weekly_p3_path_preflight(path_base=root, observation_path=obs_path)
        if p3_preflight:
            p3_path_line = format_p3_path_weekly_one_liner(p3_preflight)

        from invis_alpha_os.product.portfolio_exposure_by_signal_veto import (
            build_portfolio_exposure_by_signal_veto,
            format_portfolio_exposure_weekly_one_liner,
        )

        shadow_file = OUTPUTS_DIR / "shadow_portfolio" / "positions.jsonl"
        if not shadow_file.is_file():
            shadow_file = root / "outputs" / "shadow_portfolio" / "positions.jsonl"
        if shadow_file.is_file():
            exposure = build_portfolio_exposure_by_signal_veto(
                path_base=root,
                shadow_path=shadow_file,
                observation_path=obs_path,
            )
            if int(exposure.get("shadow_position_count") or 0) > 0:
                portfolio_exposure_line = format_portfolio_exposure_weekly_one_liner(exposure)

    pmap = CONFIG_DIR / "peer_map.yaml"
    checks.append(
        OpsSmokeCheck(
            name="peer_map_config",
            status="ok" if pmap.is_file() else "warn",
            detail=str(pmap.relative_to(root) if pmap.is_file() and pmap.is_relative_to(root) else pmap),
        )
    )

    next_commands = [
        ".venv/bin/python -m invis_alpha_os.cli.main validate ops-smoke --format markdown",
        ".venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation --dry-run --with-peer-sync",
        ".venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format json",
        ".venv/bin/python -m invis_alpha_os.cli.main validate post-refresh-smoke --format markdown",
        *p3_monitoring_next_commands(),
        ".venv/bin/python -m invis_alpha_os.cli.main validate jp-peer-sync-readiness --format markdown",
        ".venv/bin/python -m invis_alpha_os.cli.main log evidence-manifest "
        "--task-id ops_smoke_YYYYMMDD --report-date YYYY-MM-DD --summary read-only preflight",
        "weekly-us-observation --write-observation-log  # human approval; writes outputs/",
    ]

    return OpsSmokeReport(
        checks=checks,
        observation_health=health.to_dict(),
        peer_sync_pairs=peer_pairs,
        portfolio_positions=portfolio.shadow_position_count,
        manifest_entries=entries,
        signals_ok=sig_ok,
        signals_total=sig_total,
        next_commands=next_commands,
        p3_path_line=p3_path_line,
        portfolio_exposure_line=portfolio_exposure_line,
    )


def format_ops_smoke_markdown(report: OpsSmokeReport) -> str:
    lines = [
        "# Ops smoke (read-only)",
        "",
        f"- all_ok: **{report.all_ok}**",
        f"- manifest entries: {report.manifest_entries}",
        f"- signals ok: {report.signals_ok}/{report.signals_total}",
        f"- peer_sync pairs: {report.peer_sync_pairs}",
        f"- shadow positions: {report.portfolio_positions}",
        "",
    ]
    snapshot_lines = [ln for ln in (report.p3_path_line, report.portfolio_exposure_line) if ln]
    if snapshot_lines:
        lines.extend(["## P3 & portfolio snapshot", ""])
        lines.extend(snapshot_lines)
        lines.append("")
    lines.extend(
        [
            "## Checks",
            "",
            "| check | status | detail |",
            "| --- | --- | --- |",
        ]
    )
    for c in report.checks:
        lines.append(f"| {c.name} | {c.status} | {c.detail} |")
    tax = classify_ops_smoke_strict(report)
    lines.extend(
        [
            "",
            "## Strict taxonomy",
            "",
            f"- taxonomy: **{tax.get('taxonomy')}**",
            f"- strict_exit_hint: {tax.get('strict_exit_hint')}",
            f"- reasons: {', '.join(tax.get('reasons') or []) or '(none)'}",
            f"- interpretation: {tax.get('interpretation')}",
            "",
            "## Operator one-pager",
            "",
            "- Weekly copy-paste: `docs/160_product_weekly_operator_one_pager.md`",
            "- Evidence manifest: see `log evidence-manifest` in next commands",
            "",
            "## Next commands",
            "",
        ]
    )
    for cmd in report.next_commands:
        lines.append(f"- `{cmd}`")
    lines.append("")
    return "\n".join(lines)


def format_ops_smoke_json(report: OpsSmokeReport) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
