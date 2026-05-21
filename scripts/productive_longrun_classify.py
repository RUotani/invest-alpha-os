#!/usr/bin/env python3
"""Classify productive longrun terminal outcomes (read-only evidence inspection)."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def classify_productive_interruption(
    evidence_path: Path,
    *,
    dev_loop_rc: int,
    min_runtime_minutes: int,
    max_prs: int,
    near_min_margin_minutes: int = 30,
) -> str:
    """Return ``interrupted_after_productive_cap`` when rc looks like SIGINT near productive cap."""
    if dev_loop_rc not in {130, 143}:
        return ""
    if not evidence_path.is_file():
        return ""
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    longrun = evidence.get("longrun") if isinstance(evidence.get("longrun"), dict) else {}
    longrun_state = str(longrun.get("longrun_state") or evidence.get("longrun_state") or "").strip()
    if longrun_state not in {"heartbeat_waiting", "cap_reached_waiting"}:
        return ""
    cap = longrun.get("cap_reached") if isinstance(longrun.get("cap_reached"), dict) else {}
    prs_created = int(evidence.get("prs_created") or 0)
    cap_prs = bool(cap.get("prs"))
    cap_tasks = bool(cap.get("tasks"))
    if not cap_prs and not cap_tasks and prs_created < max(1, max_prs - 1):
        return ""
    try:
        elapsed = float(longrun.get("elapsed_minutes") or 0)
    except (TypeError, ValueError):
        elapsed = 0.0
    if elapsed < float(min_runtime_minutes - near_min_margin_minutes):
        return ""
    return "interrupted_after_productive_cap"


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) < 4:
        return 1
    label = classify_productive_interruption(
        Path(args[0]),
        dev_loop_rc=int(args[1]),
        min_runtime_minutes=int(args[2]),
        max_prs=int(args[3]),
    )
    if label:
        print(label)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
