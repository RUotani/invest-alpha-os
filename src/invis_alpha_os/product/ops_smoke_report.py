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
    observation_only: bool = True
    live_http: bool = False

    @property
    def all_ok(self) -> bool:
        return all(c.status == "ok" for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "all_ok": self.all_ok,
            "checks": [c.to_dict() for c in self.checks],
            "observation_health": self.observation_health,
            "peer_sync_pairs": self.peer_sync_pairs,
            "portfolio_positions": self.portfolio_positions,
            "manifest_entries": self.manifest_entries,
            "signals_ok": self.signals_ok,
            "signals_total": self.signals_total,
            "next_commands": self.next_commands,
            "observation_only": self.observation_only,
            "live_http": self.live_http,
        }


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
    status = "ok"
    if parse_err > 0:
        status = "warn"
    elif repeat > 0 or stale_forward:
        status = "warn"
    detail = f"us_signal_rows={us_rows} parse_errors={parse_err}"
    if repeat > 0:
        detail += f" repeat_signals={repeat}"
    if stale_forward:
        detail += " forward_stale_cache=1"
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

    obs_path = OUTPUTS_DIR / "observation_log" / "observation_log.jsonl"
    health = build_observation_health_report(path_base=root, observation_path=obs_path)
    checks.append(_observation_health_check(health))

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
        "## Checks",
        "",
        "| check | status | detail |",
        "| --- | --- | --- |",
    ]
    for c in report.checks:
        lines.append(f"| {c.name} | {c.status} | {c.detail} |")
    lines.extend(["", "## Next commands", ""])
    for cmd in report.next_commands:
        lines.append(f"- `{cmd}`")
    lines.append("")
    return "\n".join(lines)


def format_ops_smoke_json(report: OpsSmokeReport) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
