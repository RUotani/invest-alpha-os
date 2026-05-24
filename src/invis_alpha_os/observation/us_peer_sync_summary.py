"""Summarize peer_sync rows in observation_log (read-only)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from invis_alpha_os.observation.us_peer_sync_note import (
    US_PEER_SYNC_NOTE_PREFIX,
    parse_us_peer_sync_observation_note,
)


def summarize_peer_sync_observation_log(observation_path: Path) -> dict[str, Any]:
    if not observation_path.is_file():
        return {
            "status": "missing",
            "path": str(observation_path),
            "peer_sync_rows": 0,
            "by_status": {},
            "pairs": [],
            "observation_only": True,
        }
    rows: list[dict[str, Any]] = []
    for line in observation_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        note = str(row.get("note") or "")
        if US_PEER_SYNC_NOTE_PREFIX not in note:
            continue
        parsed = parse_us_peer_sync_observation_note(note)
        rows.append(
            {
                "id": row.get("id"),
                "symbol": row.get("symbol"),
                "anchor": parsed.get("anchor"),
                "peer": parsed.get("peer"),
                "status": parsed.get("status"),
            }
        )
    by_status = dict(Counter(str(r.get("status") or "unknown") for r in rows))
    return {
        "status": "ok",
        "path": str(observation_path),
        "peer_sync_rows": len(rows),
        "by_status": by_status,
        "pairs": rows,
        "observation_only": True,
    }
