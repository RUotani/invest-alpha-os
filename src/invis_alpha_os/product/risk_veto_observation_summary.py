"""Read-only veto counts from observation_log US signal notes (risk; observation only)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from invis_alpha_os.observation.us_signal_note import (
    US_SIGNAL_NOTE_PREFIX,
    parse_us_signal_observation_note,
)


def summarize_risk_veto_observation_log(
    observation_path: Path,
    *,
    symbol_limit: int = 12,
) -> dict[str, Any]:
    """Aggregate veto_triggered / veto_rules from logged US cache signal rows."""

    if not observation_path.is_file():
        return {
            "schema_version": 1,
            "status": "missing",
            "us_signal_rows_scanned": 0,
            "veto_triggered_rows": 0,
            "veto_triggered_share": None,
            "veto_rules_counts": {},
            "veto_symbols": [],
            "observation_only": True,
        }

    scanned = 0
    veto_rows = 0
    rule_counts: Counter[str] = Counter()
    veto_symbols: list[str] = []

    for line in observation_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        note = str(row.get("note") or "")
        if US_SIGNAL_NOTE_PREFIX not in note:
            continue
        scanned += 1
        parsed = parse_us_signal_observation_note(note)
        if not parsed.get("veto_triggered"):
            continue
        veto_rows += 1
        sym = str(row.get("symbol") or "").strip().upper()
        if sym and sym not in veto_symbols:
            veto_symbols.append(sym)
        for rule in parsed.get("veto_rules") or []:
            rule_counts[str(rule).replace("_", " ")] += 1

    share = (veto_rows / scanned) if scanned else None
    return {
        "schema_version": 1,
        "status": "ok" if scanned else "empty",
        "us_signal_rows_scanned": scanned,
        "veto_triggered_rows": veto_rows,
        "veto_triggered_share": round(share, 4) if share is not None else None,
        "veto_rules_counts": dict(rule_counts.most_common(8)),
        "veto_symbols": veto_symbols[:symbol_limit],
        "headline": (
            f"{veto_rows}/{scanned} US signal log rows with veto_triggered=true"
            if scanned
            else "no US signal rows in observation_log"
        ),
        "observation_only": True,
    }


def format_risk_veto_observation_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "## Risk veto (observation log; read-only)",
        "",
        f"- {summary.get('headline', '')}",
        f"- status: {summary.get('status', '')}",
        f"- veto_triggered_rows: {summary.get('veto_triggered_rows', 0)}",
    ]
    if summary.get("veto_triggered_share") is not None:
        lines.append(f"- veto_triggered_share: {summary.get('veto_triggered_share')}")
    rules = summary.get("veto_rules_counts") or {}
    if rules:
        lines.append(f"- veto_rules_counts: {rules}")
    syms = summary.get("veto_symbols") or []
    if syms:
        lines.append(f"- veto_symbols: {', '.join(syms)}")
    return "\n".join(lines)
