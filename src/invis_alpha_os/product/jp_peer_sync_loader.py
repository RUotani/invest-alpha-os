"""JP bars loader for peer_sync (cache-only; read-only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import CONFIG_DIR, ROOT_DIR
from invis_alpha_os.data.jquants_daily_bars_cache import try_load_cached_daily_bars
from invis_alpha_os.data.us_daily_bars_cache import try_load_cached_us_daily_bars
from invis_alpha_os.signals.momentum import DailyBar
from invis_alpha_os.signals.peer_sync import load_peer_map


def classify_peer_map_symbol(symbol: str) -> str:
    """Return ``us`` or ``jp`` for peer_map wire codes (observation only)."""

    s = str(symbol).strip().upper()
    if not s:
        return "unknown"
    if s.isdigit() or (len(s) == 4 and any(c.isdigit() for c in s) and s.isalnum()):
        return "jp"
    return "us"


def try_load_bars_for_peer_sync(symbol: str) -> tuple[list[DailyBar], str] | None:
    """Load US or JP cache bars for peer_sync (no HTTP)."""

    kind = classify_peer_map_symbol(symbol)
    if kind == "jp":
        loaded = try_load_cached_daily_bars(symbol)
        if loaded is None:
            return None
        bars, _src = loaded
        return bars, "jp_cache"
    loaded = try_load_cached_us_daily_bars(symbol.strip().upper())
    if loaded is None:
        return None
    bars, _src = loaded
    return bars, "us_cache"


def build_jp_peer_sync_readiness_report(
    *,
    path_base: Path | None = None,
    peer_map_path: Path | None = None,
) -> dict[str, Any]:
    """Read-only: which peer_map JP edges have J-Quants cache on disk."""

    root = path_base or ROOT_DIR
    pmap_path = peer_map_path or (CONFIG_DIR / "peer_map.yaml")
    peer_map = load_peer_map(pmap_path)
    jp_symbols: set[str] = set()
    for anchor, peers in peer_map.items():
        if classify_peer_map_symbol(anchor) == "jp":
            jp_symbols.add(str(anchor).strip().upper())
        for p in peers:
            if classify_peer_map_symbol(str(p)) == "jp":
                jp_symbols.add(str(p).strip().upper())

    edges: list[dict[str, Any]] = []
    cached = 0
    missing = 0
    for anchor, peers in peer_map.items():
        a_kind = classify_peer_map_symbol(anchor)
        for peer in peers:
            p_kind = classify_peer_map_symbol(str(peer))
            if a_kind != "jp" and p_kind != "jp":
                continue
            a_cache = (
                try_load_cached_daily_bars(str(anchor)) is not None
                if a_kind == "jp"
                else try_load_cached_us_daily_bars(str(anchor).upper()) is not None
            )
            p_cache = (
                try_load_cached_daily_bars(str(peer)) is not None
                if p_kind == "jp"
                else try_load_cached_us_daily_bars(str(peer).upper()) is not None
            )
            status = "ready" if a_cache and p_cache else "missing_cache"
            if status == "ready":
                cached += 1
            else:
                missing += 1
            edges.append(
                {
                    "anchor": str(anchor).upper(),
                    "peer": str(peer).upper(),
                    "anchor_kind": a_kind,
                    "peer_kind": p_kind,
                    "anchor_cache": a_cache,
                    "peer_cache": p_cache,
                    "status": status,
                }
            )

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(root))
        except ValueError:
            return str(p)

    return {
        "peer_map_path": _rel(pmap_path),
        "jp_symbols_in_map": sorted(jp_symbols),
        "jp_edge_count": len(edges),
        "jp_edges_ready": cached,
        "jp_edges_missing": missing,
        "edges": edges,
        "next_commands": [
            ".venv/bin/python -m invis_alpha_os.cli.main validate jp-peer-sync-readiness --format markdown",
            "J-Quants cache ingest requires explicit approval (no live HTTP in this report)",
        ],
        "observation_only": True,
        "live_http": False,
    }


def format_jp_peer_sync_readiness_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# JP peer_sync readiness (cache-only)",
        "",
        f"- peer_map: `{report.get('peer_map_path')}`",
        f"- JP edges: {report.get('jp_edge_count')} (ready={report.get('jp_edges_ready')} missing={report.get('jp_edges_missing')})",
        "",
        "## Edges",
        "",
    ]
    for edge in report.get("edges") or []:
        lines.append(
            f"- {edge.get('anchor')} → {edge.get('peer')}: {edge.get('status')} "
            f"(anchor_cache={edge.get('anchor_cache')} peer_cache={edge.get('peer_cache')})"
        )
    lines.extend(["", "## Next commands", ""])
    for cmd in report.get("next_commands") or []:
        lines.append(f"- `{cmd}`")
    lines.append("")
    return "\n".join(lines)
