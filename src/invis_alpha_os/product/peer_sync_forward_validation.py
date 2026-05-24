"""Join peer_sync observation_log rows to anchor forward returns (read-only)."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from invis_alpha_os.observation.us_peer_sync_note import (
    US_PEER_SYNC_NOTE_PREFIX,
    parse_us_peer_sync_observation_note,
)
from invis_alpha_os.product.jp_peer_sync_loader import try_load_bars_for_peer_sync
from invis_alpha_os.product.us_forward_return_validation import (
    DEFAULT_HORIZONS,
    THIN_SAMPLE_THRESHOLD,
    _event_bar_index,
    _forward_return,
    _horizon_bucket_stats,
    _parse_event_date,
    _sample_quality,
)

# Reuse sample quality helper with extended next commands
def _peer_sync_forward_next_commands() -> list[str]:
    return [
        ".venv/bin/python -m invis_alpha_os.cli.main validate peer-sync-forward-returns --format markdown",
        ".venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --format markdown",
        ".venv/bin/python -m invis_alpha_os.cli.main log peer-sync-summary",
    ]


def _empty_peer_sync_forward_report(
    *,
    observation_path: Path,
    horizons: tuple[int, ...],
    reference_date: date | None,
    peer_sync_at_t_status: str,
    peer_sync_at_t_reason: str,
) -> dict[str, Any]:
    sq = _sample_quality(0)
    sq = {**sq, "next_commands": _peer_sync_forward_next_commands()}
    return {
        "schema_version": 1,
        "observation_path": str(observation_path),
        "horizons": list(horizons),
        "reference_date": reference_date.isoformat() if reference_date else None,
        "peer_sync_rows_considered": 0,
        "rows_matched": 0,
        "rows_skipped": 0,
        "skipped_reasons": {},
        "sample_quality": sq,
        "peer_sync_at_t": {
            "status": peer_sync_at_t_status,
            "reason": peer_sync_at_t_reason,
        },
        "by_peer_sync_status": {},
        "examples": [],
        "observation_only": True,
        "live_http": False,
    }


def _iter_peer_sync_log_rows(observation_path: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if not observation_path.is_file():
        return [], {}

    rows: list[dict[str, Any]] = []
    skipped: dict[str, int] = defaultdict(int)
    for line_no, line in enumerate(observation_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            skipped["invalid_jsonl"] += 1
            raise ValueError(f"invalid JSONL at line {line_no}: {exc}") from exc
        if not isinstance(raw, dict):
            skipped["invalid_row_type"] += 1
            continue
        note = str(raw.get("note") or "")
        if US_PEER_SYNC_NOTE_PREFIX not in note:
            skipped["not_peer_sync_row"] += 1
            continue
        parsed = parse_us_peer_sync_observation_note(note)
        anchor = str(parsed.get("anchor") or raw.get("symbol") or "").strip().upper()
        if not anchor:
            skipped["missing_anchor"] += 1
            continue
        event = _parse_event_date(raw.get("created_at"))
        if event is None:
            skipped["missing_event_date"] += 1
            continue
        rows.append(
            {
                "anchor_symbol": anchor,
                "peer_symbol": str(parsed.get("peer") or "").strip().upper(),
                "peer_sync_status": str(parsed.get("status") or "unknown"),
                "return_spread_at_log": parsed.get("spread"),
                "event_date": event,
                "created_at": raw.get("created_at"),
            }
        )
    return rows, dict(skipped)


def _build_by_peer_sync_status(
    matched: list[dict[str, Any]],
    horizons: tuple[int, ...],
    *,
    thin_sample: bool,
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in matched:
        groups[str(row.get("peer_sync_status") or "unknown")].append(row)
    out: dict[str, Any] = {}
    for key, items in sorted(groups.items()):
        per_h: dict[str, dict[str, Any]] = {}
        for h in horizons:
            vals = [
                x["horizons"].get(str(h))
                for x in items
                if x.get("horizons", {}).get(str(h)) is not None
            ]
            per_h[str(h)] = _horizon_bucket_stats([float(v) for v in vals], thin_sample=thin_sample)
        out[key] = {"count": len(items), "horizons": per_h}
    return out


def _peer_sync_at_t_report(peer_rows: list[dict[str, Any]], matched: list[dict[str, Any]]) -> dict[str, Any]:
    if not peer_rows:
        return {
            "status": "not_in_observation_log",
            "reason": "no us_peer_sync rows in observation_log",
        }
    return {
        "status": "joined",
        "peer_sync_log_rows": len(peer_rows),
        "matched_with_forward": len(matched),
        "statuses_in_log": sorted({str(r.get("peer_sync_status") or "unknown") for r in peer_rows}),
    }


def compute_peer_sync_forward_join(
    *,
    observation_path: Path,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Join peer_sync log rows to anchor-symbol forward returns (cache-only)."""

    if not observation_path.is_file():
        return _empty_peer_sync_forward_report(
            observation_path=observation_path,
            horizons=horizons,
            reference_date=reference_date,
            peer_sync_at_t_status="missing_observation_log",
            peer_sync_at_t_reason="observation_log.jsonl not found; run weekly --write-observation-log after approval",
        )

    peer_rows, pre_skipped = _iter_peer_sync_log_rows(observation_path)
    matched: list[dict[str, Any]] = []
    skipped: dict[str, int] = defaultdict(int, pre_skipped)

    for row in peer_rows:
        anchor: str = row["anchor_symbol"]
        event: date = row["event_date"]
        if reference_date is not None and event > reference_date:
            skipped["event_after_reference"] += 1
            continue
        loaded = try_load_bars_for_peer_sync(anchor)
        if loaded is None:
            skipped["price_data_missing"] += 1
            continue
        bars, cache_src = loaded
        idx = _event_bar_index(bars, event)
        if idx is None:
            skipped["event_date_outside_cache"] += 1
            continue
        horizon_returns: dict[str, float | None] = {}
        any_ok = False
        for h in horizons:
            fr = _forward_return(bars, idx, int(h))
            horizon_returns[str(h)] = fr
            if fr is not None:
                any_ok = True
        if not any_ok:
            skipped["insufficient_future_bars"] += 1
            continue
        matched.append(
            {
                "anchor_symbol": anchor,
                "peer_symbol": row.get("peer_symbol"),
                "peer_sync_status": row.get("peer_sync_status"),
                "return_spread_at_log": row.get("return_spread_at_log"),
                "cache_source": cache_src,
                "event_date": event.isoformat(),
                "horizons": horizon_returns,
            }
        )

    thin = len(matched) < THIN_SAMPLE_THRESHOLD
    sq = _sample_quality(
        len(matched),
        skipped_reasons=dict(skipped),
        signal_rows=len(peer_rows),
    )
    sq = {**sq, "next_commands": _peer_sync_forward_next_commands()}

    return {
        "schema_version": 1,
        "observation_path": str(observation_path),
        "horizons": list(horizons),
        "reference_date": reference_date.isoformat() if reference_date else None,
        "peer_sync_rows_considered": len(peer_rows),
        "rows_matched": len(matched),
        "rows_skipped": sum(skipped.values()),
        "skipped_reasons": dict(sorted(skipped.items())),
        "sample_quality": sq,
        "peer_sync_at_t": _peer_sync_at_t_report(peer_rows, matched),
        "by_peer_sync_status": _build_by_peer_sync_status(matched, horizons, thin_sample=thin),
        "examples": matched[:5],
        "observation_only": True,
        "live_http": False,
    }


def format_peer_sync_forward_markdown(report: dict[str, Any]) -> str:
    sq = report.get("sample_quality") or {}
    ps = report.get("peer_sync_at_t") or {}
    lines = [
        "# Peer sync × forward returns (cache-only)",
        "",
        "Observation only — not buy/sell advice.",
        "",
        f"**Sample quality**: {sq.get('status')} — {sq.get('reason')}",
        f"- peer_sync log rows: {report.get('peer_sync_rows_considered')}",
        f"- matched with forward returns: {report.get('rows_matched')}",
        f"- peer_sync_at_t: {ps.get('status')}",
    ]
    if ps.get("statuses_in_log"):
        lines.append(f"- statuses in log: {ps.get('statuses_in_log')}")
    lines.extend(["", "## By peer_sync_status", ""])
    by_st = report.get("by_peer_sync_status") or {}
    if not by_st:
        lines.append("_No matched rows._")
    else:
        for status, block in sorted(by_st.items()):
            lines.append(f"- **{status}**: n={block.get('count')}")
            for h, b in (block.get("horizons") or {}).items():
                lines.append(
                    f"  - {h}d: hit+={b.get('hit_rate_positive')} avg={b.get('avg_forward')}"
                )
    lines.extend(["", "## Next commands", ""])
    for cmd in sq.get("next_commands") or []:
        lines.append(f"- `{cmd}`")
    lines.append("")
    return "\n".join(lines)
