"""Cache-only peer_sync report (observation only)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import CONFIG_DIR, ROOT_DIR
from invis_alpha_os.data.us_daily_bars_cache import try_load_cached_us_daily_bars
from invis_alpha_os.signals.momentum import DailyBar
from invis_alpha_os.signals.peer_sync import evaluate_peer_map, load_peer_map


@dataclass(frozen=True)
class PeerSyncCacheOnlyReport:
    peer_map_path: str
    pairs: list[dict[str, Any]]
    summary: dict[str, int]
    next_commands: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "peer_map_path": self.peer_map_path,
            "pairs": self.pairs,
            "summary": self.summary,
            "next_commands": self.next_commands,
        }


def _summary_counts(pairs: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in pairs:
        st = str(row.get("status", "unknown"))
        counts[st] = counts.get(st, 0) + 1
    return counts


def build_peer_sync_cache_only_report(
    *,
    path_base: Path | None = None,
    peer_map_path: Path | None = None,
    window_days: int = 20,
    divergence_threshold: float = 0.05,
) -> PeerSyncCacheOnlyReport:
    root = path_base or ROOT_DIR
    pmap_path = peer_map_path or (CONFIG_DIR / "peer_map.yaml")
    peer_map = load_peer_map(pmap_path)
    symbols: set[str] = set(peer_map)
    for peers in peer_map.values():
        symbols.update(peers)

    bars_by_symbol: dict[str, list[DailyBar]] = {}
    for sym in sorted(symbols):
        loaded = try_load_cached_us_daily_bars(sym)
        if loaded is None:
            continue
        bars, _src = loaded
        bars_by_symbol[sym] = bars

    results = evaluate_peer_map(
        peer_map,
        bars_by_symbol,
        window_days=window_days,
        divergence_threshold=divergence_threshold,
    )
    pair_dicts = [r.to_dict() for r in results]
    summary = _summary_counts(pair_dicts)
    next_commands = [
        "Add peers in config/peer_map.yaml (anchor → list).",
        ".venv/bin/python -m invis_alpha_os.cli.main validate peer-sync --format markdown",
        "weekly-us-observation --dry-run  # optional; peer_sync not yet in weekly cycle",
    ]
    return PeerSyncCacheOnlyReport(
        peer_map_path=str(pmap_path.relative_to(root) if pmap_path.is_relative_to(root) else pmap_path),
        pairs=pair_dicts,
        summary=summary,
        next_commands=next_commands,
    )


def format_peer_sync_cache_only_markdown(report: PeerSyncCacheOnlyReport) -> str:
    lines = [
        "# Peer sync (cache-only)",
        "",
        f"- peer_map: `{report.peer_map_path}`",
        f"- pairs evaluated: {len(report.pairs)}",
        "",
        "## Summary",
        "",
    ]
    if report.summary:
        for status, count in sorted(report.summary.items()):
            lines.append(f"- `{status}`: {count}")
    else:
        lines.append("- (no pairs)")
    lines.extend(["", "## Pairs", ""])
    if not report.pairs:
        lines.append("_No peer_map edges or all missing cache._")
    else:
        lines.append("| anchor | peer | status | spread | corr | aligned |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for row in report.pairs:
            spread = row.get("return_spread")
            corr = row.get("correlation")
            spread_s = f"{spread:.2%}" if isinstance(spread, (int, float)) else "—"
            corr_s = f"{corr:.2f}" if isinstance(corr, (int, float)) else "—"
            lines.append(
                "| {anchor} | {peer} | {status} | {spread} | {corr} | {aligned} |".format(
                    anchor=row.get("anchor_symbol", ""),
                    peer=row.get("peer_symbol", ""),
                    status=row.get("status", ""),
                    spread=spread_s,
                    corr=corr_s,
                    aligned=row.get("aligned_sessions", 0),
                )
            )
        lines.extend(["", "### Interpretation", ""])
        for row in report.pairs:
            interp = row.get("interpretation")
            if interp:
                lines.append(
                    f"- **{row.get('anchor_symbol')} → {row.get('peer_symbol')}**: {interp}"
                )
    lines.extend(["", "## Next commands", ""])
    for cmd in report.next_commands:
        lines.append(f"- `{cmd}`")
    lines.append("")
    return "\n".join(lines)


def format_peer_sync_cache_only_json(report: PeerSyncCacheOnlyReport) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
