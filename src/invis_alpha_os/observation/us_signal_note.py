"""US cache signal observation note format (parse/build; observation only)."""

from __future__ import annotations

import re
from typing import Any

US_SIGNAL_NOTE_PREFIX = "us_cache_signal observation_only"


def build_us_signal_observation_note(
    preview: dict[str, Any],
    *,
    veto_triggered: bool | None = None,
    veto_rules: list[str] | None = None,
) -> str:
    status = str(preview.get("status") or "unknown")
    parts = [f"{US_SIGNAL_NOTE_PREFIX} status={status}"]
    label = preview.get("momentum_label")
    if label:
        parts.append(f"momentum_label={label}")
    as_of = preview.get("last_date")
    if as_of:
        parts.append(f"as_of={str(as_of)[:10]}")
    reason = preview.get("reason")
    if reason and status != "ok":
        parts.append(f"reason={reason}")
    if veto_triggered is not None:
        parts.append(f"veto_triggered={'true' if veto_triggered else 'false'}")
        if veto_rules:
            slugged = [str(r).replace(" ", "_") for r in veto_rules if str(r).strip()]
            if slugged:
                parts.append(f"veto_rules={','.join(slugged)}")
    parts.append("not buy/sell advice")
    return " ".join(parts)


def parse_us_signal_observation_note(note: str) -> dict[str, Any]:
    out: dict[str, str | bool | list[str]] = {}
    for key in ("status", "momentum_label", "reason", "as_of"):
        m = re.search(rf"{key}=([^\s]+)", note)
        if m:
            out[key] = m.group(1)
    vm = re.search(r"veto_triggered=(true|false)", note, re.IGNORECASE)
    if vm:
        out["veto_triggered"] = vm.group(1).lower() == "true"
    vr = re.search(r"veto_rules=([^\s]+)", note)
    if vr:
        out["veto_rules"] = [x for x in vr.group(1).split(",") if x]
    return out
