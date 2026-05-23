"""Cache-only forward-return validation from observation_log (P5 MVP; observation only)."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from invis_alpha_os.data.us_daily_bars_cache import (
    load_us_daily_bars_json_file,
    try_load_cached_us_daily_bars,
)
from invis_alpha_os.product.weekly_us_observation import US_SIGNAL_NOTE_PREFIX, _parse_observation_note
from invis_alpha_os.signals.momentum import DailyBar

SCHEMA_VERSION = 1
DEFAULT_HORIZONS: tuple[int, ...] = (5, 20, 60)


def _parse_event_date(created_at: object) -> date | None:
    if created_at is None:
        return None
    if isinstance(created_at, datetime):
        return created_at.date()
    if isinstance(created_at, date):
        return created_at
    s = str(created_at).strip()
    if not s:
        return None
    if "T" in s:
        s = s.split("T", 1)[0]
    elif " " in s:
        s = s.split(" ", 1)[0]
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _bar_dates(bars: list[DailyBar]) -> list[date]:
    out: list[date] = []
    for b in bars:
        try:
            out.append(date.fromisoformat(str(b["date"])[:10]))
        except ValueError:
            continue
    return out


def _event_bar_index(bars: list[DailyBar], event: date) -> int | None:
    """Last bar index with bar date <= event (fail if no bar on/before event)."""

    dates = _bar_dates(bars)
    if len(dates) != len(bars):
        return None
    idx: int | None = None
    for i, d in enumerate(dates):
        if d <= event:
            idx = i
        else:
            break
    return idx


def _forward_return(bars: list[DailyBar], start_idx: int, horizon: int) -> float | None:
    end_idx = start_idx + horizon
    if end_idx >= len(bars):
        return None
    old = float(bars[start_idx]["close"])
    new = float(bars[end_idx]["close"])
    if old == 0:
        return None
    return (new / old) - 1.0


def _iter_us_signal_rows(observation_path: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if not observation_path.is_file():
        raise FileNotFoundError(f"observation_log missing: {observation_path}")

    rows: list[dict[str, Any]] = []
    skipped: dict[str, int] = defaultdict(int)
    for line_no, line in enumerate(observation_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            skipped["invalid_jsonl"] += 1
            raise ValueError(f"invalid JSONL at line {line_no}: {exc}") from exc
        if not isinstance(row, dict):
            skipped["invalid_row_type"] += 1
            continue
        note = str(row.get("note") or "")
        if US_SIGNAL_NOTE_PREFIX not in note:
            skipped["not_us_signal_row"] += 1
            continue
        sym = row.get("symbol")
        if not sym or not str(sym).strip():
            skipped["missing_symbol"] += 1
            continue
        event = _parse_event_date(row.get("created_at"))
        if event is None:
            skipped["missing_event_date"] += 1
            continue
        parsed = _parse_observation_note(note)
        rows.append(
            {
                "symbol": str(sym).strip().upper(),
                "event_date": event,
                "momentum_label": parsed.get("momentum_label"),
                "status": parsed.get("status", "unknown"),
                "created_at": row.get("created_at"),
            }
        )
    return rows, dict(skipped)


def _load_bars_for_symbol(symbol: str, *, cache_dir: Path | None) -> tuple[list[DailyBar], dict[str, Any]] | None:
    if cache_dir is not None:
        path = cache_dir / f"{symbol}.json"
        if not path.is_file():
            return None
        return load_us_daily_bars_json_file(path, expect_symbol=symbol)
    return try_load_cached_us_daily_bars(symbol)


def compute_us_forward_returns(
    *,
    observation_path: Path,
    cache_dir: Path | None = None,
    path_base: Path | None = None,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Join observation_log US rows to cached bars; compute session-forward returns."""

    from invis_alpha_os.config.paths import OUTPUTS_DIR, ROOT_DIR

    root = path_base or ROOT_DIR
    obs_rows, pre_skipped = _iter_us_signal_rows(observation_path)
    matched: list[dict[str, Any]] = []
    skipped = dict(pre_skipped)
    skipped_reasons: dict[str, int] = defaultdict(int, skipped)

    for row in obs_rows:
        sym = row["symbol"]
        event: date = row["event_date"]
        if reference_date is not None and event > reference_date:
            skipped_reasons["event_after_reference"] += 1
            continue
        loaded = _load_bars_for_symbol(sym, cache_dir=cache_dir)
        if loaded is None:
            skipped_reasons["price_data_missing"] += 1
            continue
        bars, _src = loaded
        idx = _event_bar_index(bars, event)
        if idx is None:
            skipped_reasons["event_date_outside_cache"] += 1
            continue
        horizon_returns: dict[str, float | None] = {}
        any_ok = False
        for h in horizons:
            fr = _forward_return(bars, idx, int(h))
            horizon_returns[str(h)] = fr
            if fr is not None:
                any_ok = True
        if not any_ok:
            skipped_reasons["insufficient_future_bars"] += 1
            continue
        matched.append(
            {
                "symbol": sym,
                "event_date": event.isoformat(),
                "momentum_label": row.get("momentum_label"),
                "status": row.get("status"),
                "horizons": horizon_returns,
            }
        )

    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in matched:
        by_symbol[m["symbol"]].append(m)
        label = str(m.get("momentum_label") or "unknown")
        by_label[label].append(m)

    def _avg_horizon(items: list[dict[str, Any]], h: int) -> float | None:
        vals = [x["horizons"].get(str(h)) for x in items if x["horizons"].get(str(h)) is not None]
        if not vals:
            return None
        return sum(float(v) for v in vals) / len(vals)

    by_symbol_summary = {
        sym: {
            "count": len(items),
            "avg_forward": {str(h): _avg_horizon(items, h) for h in horizons},
        }
        for sym, items in sorted(by_symbol.items())
    }
    by_label_summary = {
        lbl: {
            "count": len(items),
            "avg_forward": {str(h): _avg_horizon(items, h) for h in horizons},
        }
        for lbl, items in sorted(by_label.items())
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(),
        "observation_path": str(observation_path),
        "path_base": str(root),
        "horizons": list(horizons),
        "reference_date": reference_date.isoformat() if reference_date else None,
        "rows_considered": len(obs_rows),
        "rows_matched": len(matched),
        "rows_skipped": sum(skipped_reasons.values()),
        "skipped_reasons": dict(sorted(skipped_reasons.items())),
        "by_symbol": by_symbol_summary,
        "by_signal_label": by_label_summary,
        "examples": matched[:5],
        "observation_only": True,
        "not_investment_advice": True,
        "live_http": False,
    }


def format_us_forward_return_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# US Forward Return Validation — Cache Only",
        "",
        "Observation only — not buy/sell advice.",
        "",
        f"- observation rows considered: {report.get('rows_considered')}",
        f"- matched rows: {report.get('rows_matched')}",
        f"- skipped rows: {report.get('rows_skipped')}",
        f"- horizons (sessions): {', '.join(str(h) for h in report.get('horizons') or [])}",
        "",
        "## Skipped reasons",
    ]
    reasons = report.get("skipped_reasons") or {}
    if reasons:
        for k, v in sorted(reasons.items()):
            lines.append(f"- {k}: {v}")
    else:
        lines.append("- (none)")
    lines.extend(["", "## By signal label (avg forward return)"])
    for lbl, block in (report.get("by_signal_label") or {}).items():
        avgs = block.get("avg_forward") or {}
        parts = [f"{h}d={avgs.get(str(h))}" for h in report.get("horizons") or []]
        lines.append(f"- {lbl} (n={block.get('count')}): {', '.join(parts)}")
    lines.append("")
    return "\n".join(lines)
