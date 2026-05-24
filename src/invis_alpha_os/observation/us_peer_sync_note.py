"""US peer_sync observation note format (parse/build; observation only)."""

from __future__ import annotations

import re
from typing import Any

US_PEER_SYNC_NOTE_PREFIX = "us_peer_sync observation_only"


def build_us_peer_sync_observation_note(pair: dict[str, Any]) -> str:
    anchor = str(pair.get("anchor_symbol") or "").strip().upper()
    peer = str(pair.get("peer_symbol") or "").strip().upper()
    status = str(pair.get("status") or "unknown")
    parts = [
        US_PEER_SYNC_NOTE_PREFIX,
        f"anchor={anchor}",
        f"peer={peer}",
        f"status={status}",
    ]
    spread = pair.get("return_spread")
    if isinstance(spread, (int, float)):
        parts.append(f"spread={spread:.6f}")
    corr = pair.get("correlation")
    if isinstance(corr, (int, float)):
        parts.append(f"correlation={corr:.4f}")
    aligned = pair.get("aligned_sessions")
    if aligned is not None:
        parts.append(f"aligned={int(aligned)}")
    parts.append("not buy/sell advice")
    return " ".join(parts)


def parse_us_peer_sync_observation_note(note: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if US_PEER_SYNC_NOTE_PREFIX not in note:
        return out
    for key in ("anchor", "peer", "status"):
        m = re.search(rf"{key}=([^\s]+)", note)
        if m:
            out[key] = m.group(1)
    sm = re.search(r"spread=([^\s]+)", note)
    if sm:
        try:
            out["spread"] = float(sm.group(1))
        except ValueError:
            out["spread"] = sm.group(1)
    cm = re.search(r"correlation=([^\s]+)", note)
    if cm:
        try:
            out["correlation"] = float(cm.group(1))
        except ValueError:
            out["correlation"] = cm.group(1)
    am = re.search(r"aligned=(\d+)", note)
    if am:
        out["aligned"] = int(am.group(1))
    return out
