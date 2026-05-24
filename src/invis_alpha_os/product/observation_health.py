"""Unified read-only observation_log health report (Wave B)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.observation.us_peer_sync_summary import summarize_peer_sync_observation_log
from invis_alpha_os.product.portfolio_observation_summary import build_portfolio_observation_summary
from invis_alpha_os.product.us_forward_return_validation import (
    forward_validation_next_commands,
)
from invis_alpha_os.product.weekly_us_observation import summarize_us_observation_log


@dataclass(frozen=True)
class ObservationHealthReport:
    observation_path: str
    us_signals: dict[str, Any]
    peer_sync: dict[str, Any]
    portfolio: dict[str, Any]
    forward_validation: dict[str, Any] | None
    log_integrity: dict[str, Any]
    next_commands: list[str]
    observation_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_path": self.observation_path,
            "us_signals": self.us_signals,
            "peer_sync": self.peer_sync,
            "portfolio": self.portfolio,
            "forward_validation": self.forward_validation,
            "log_integrity": self.log_integrity,
            "next_commands": self.next_commands,
            "observation_only": self.observation_only,
        }


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


def build_observation_health_report(
    *,
    path_base: Path | None = None,
    observation_path: Path | None = None,
    cache_dir: Path | None = None,
) -> ObservationHealthReport:
    root = path_base or ROOT_DIR
    obs = observation_path or (OUTPUTS_DIR / "observation_log" / "observation_log.jsonl")
    us = summarize_us_observation_log(obs)
    peer = summarize_peer_sync_observation_log(obs)
    portfolio = build_portfolio_observation_summary(
        path_base=root,
        observation_path=obs,
    ).to_dict()
    integrity = _scan_log_integrity(obs)

    forward: dict[str, Any] | None = None
    if obs.is_file() and int(us.get("us_signal_rows") or 0) > 0:
        try:
            from invis_alpha_os.product.us_forward_return_validation import compute_us_forward_returns

            cache = cache_dir or (OUTPUTS_DIR / "market_data" / "us_daily_bars")
            forward = compute_us_forward_returns(
                observation_path=obs,
                cache_dir=cache,
                path_base=root,
            )
        except (FileNotFoundError, ValueError):
            forward = None

    next_commands: list[str] = [
        ".venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation --dry-run --with-peer-sync",
        ".venv/bin/python -m invis_alpha_os.cli.main log us-signals-summary",
        ".venv/bin/python -m invis_alpha_os.cli.main log peer-sync-summary",
    ]
    if forward:
        sq = forward.get("sample_quality") or {}
        st = str(sq.get("status") or "")
        if st in {"empty", "thin"}:
            next_commands.extend(forward_validation_next_commands())
            next_commands.append(
                "weekly-us-observation --write-observation-log  # explicit approval; writes outputs/"
            )
    elif us.get("status") == "missing":
        next_commands.append(
            "weekly-us-observation --write-observation-log  # explicit approval; writes outputs/"
        )

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
        log_integrity=integrity,
        next_commands=next_commands,
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
        "",
        "## US signals",
        f"- status: {us.get('status')}",
        f"- us_signal_rows: {us.get('us_signal_rows', 0)}",
        f"- by_status: {us.get('by_status', {})}",
        "",
        "## Peer sync rows",
        f"- peer_sync_rows: {peer.get('peer_sync_rows', 0)}",
        f"- by_status: {peer.get('by_status', {})}",
        "",
        "## Portfolio linkage",
        f"- shadow positions: {port.get('shadow_position_count', 0)}",
        f"- resolved links: {port.get('positions_with_resolved_links', 0)}",
        "",
        "## Log integrity",
        f"- total lines: {integrity.get('total_lines', 0)}",
        f"- json_parse_errors: {integrity.get('json_parse_errors', 0)}",
        f"- unclassified_notes: {integrity.get('unclassified_notes', 0)}",
    ]
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
        if sq.get("needed_more_samples"):
            lines.append(f"- needed_more_samples: {sq.get('needed_more_samples')}")
    lines.extend(["", "## Next commands", ""])
    for cmd in report.next_commands:
        lines.append(f"- `{cmd}`")
    lines.append("")
    return "\n".join(lines)


def format_observation_health_json(report: ObservationHealthReport) -> str:
    import json as _json

    return _json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
