"""Cache-only forward-return validation from observation_log (P5/P7; observation only)."""

from __future__ import annotations

import json
import statistics
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

SCHEMA_VERSION = 2
DEFAULT_HORIZONS: tuple[int, ...] = (5, 20, 60)
THIN_SAMPLE_THRESHOLD = 10


def parse_positive_horizons(raw: str) -> tuple[int, ...]:
    """Parse comma-separated positive integer session horizons (fail-closed)."""

    text = (raw or "").strip()
    if not text:
        raise ValueError("horizons must not be empty")
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        raise ValueError("horizons must not be empty")
    out: list[int] = []
    for part in parts:
        if not part.isdigit():
            raise ValueError(f"horizon must be a positive integer: {part!r}")
        value = int(part)
        if value <= 0:
            raise ValueError(f"horizon must be positive: {value}")
        out.append(value)
    return tuple(out)


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


def _horizon_bucket_stats(values: list[float], *, thin_sample: bool) -> dict[str, Any]:
    n = len(values)
    if n == 0:
        return {
            "count": 0,
            "avg_forward": None,
            "median_forward": None,
            "hit_rate_positive": None,
            "hit_rate_gt_2pct": None,
            "hit_rate_lt_minus_2pct": None,
            "best": None,
            "worst": None,
            "thin_sample": thin_sample,
        }
    return {
        "count": n,
        "avg_forward": sum(values) / n,
        "median_forward": statistics.median(values),
        "hit_rate_positive": sum(1 for v in values if v > 0) / n,
        "hit_rate_gt_2pct": sum(1 for v in values if v > 0.02) / n,
        "hit_rate_lt_minus_2pct": sum(1 for v in values if v < -0.02) / n,
        "best": max(values),
        "worst": min(values),
        "thin_sample": thin_sample,
    }


def _build_quality_buckets(
    matched: list[dict[str, Any]],
    horizons: tuple[int, ...],
    *,
    thin_sample: bool,
) -> dict[str, Any]:
    by_label: dict[str, dict[str, dict[str, Any]]] = {}
    global_buckets: dict[str, dict[str, Any]] = {}

    for h in horizons:
        key = str(h)
        all_vals: list[float] = []
        label_vals: dict[str, list[float]] = defaultdict(list)
        for row in matched:
            val = row.get("horizons", {}).get(key)
            if val is None:
                continue
            fv = float(val)
            all_vals.append(fv)
            label = str(row.get("momentum_label") or "unknown")
            label_vals[label].append(fv)
        global_buckets[key] = _horizon_bucket_stats(all_vals, thin_sample=thin_sample)
        for lbl, vals in sorted(label_vals.items()):
            by_label.setdefault(lbl, {})[key] = _horizon_bucket_stats(vals, thin_sample=thin_sample)

    return {"global": global_buckets, "by_signal_label": by_label}


def _sample_quality(matched_count: int) -> dict[str, Any]:
    if matched_count == 0:
        return {
            "status": "empty",
            "reason": "no observation rows matched to cache forward windows",
            "matched_rows": 0,
        }
    if matched_count < THIN_SAMPLE_THRESHOLD:
        return {
            "status": "thin",
            "reason": f"matched rows below minimum threshold ({THIN_SAMPLE_THRESHOLD})",
            "matched_rows": matched_count,
        }
    return {
        "status": "usable",
        "reason": "matched rows sufficient for exploratory bucket review",
        "matched_rows": matched_count,
    }


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

    from invis_alpha_os.config.paths import ROOT_DIR

    root = path_base or ROOT_DIR
    obs_rows, pre_skipped = _iter_us_signal_rows(observation_path)
    matched: list[dict[str, Any]] = []
    skipped_reasons: dict[str, int] = defaultdict(int, pre_skipped)

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

    thin = len(matched) < THIN_SAMPLE_THRESHOLD
    quality_buckets = _build_quality_buckets(matched, horizons, thin_sample=thin)
    sample_quality = _sample_quality(len(matched))

    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in matched:
        by_symbol[m["symbol"]].append(m)
        by_label[str(m.get("momentum_label") or "unknown")].append(m)

    def _avg_horizon(items: list[dict[str, Any]], h: int) -> float | None:
        vals = [x["horizons"].get(str(h)) for x in items if x["horizons"].get(str(h)) is not None]
        if not vals:
            return None
        return sum(float(v) for v in vals) / len(vals)

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
        "sample_quality": sample_quality,
        "quality_buckets": quality_buckets,
        "by_symbol": {
            sym: {"count": len(items), "avg_forward": {str(h): _avg_horizon(items, h) for h in horizons}}
            for sym, items in sorted(by_symbol.items())
        },
        "by_signal_label": {
            lbl: {"count": len(items), "avg_forward": {str(h): _avg_horizon(items, h) for h in horizons}}
            for lbl, items in sorted(by_label.items())
        },
        "examples": matched[:5],
        "veto_at_t": {
            "status": "not_in_observation_log",
            "reason": "veto-at-t not stored in observation_log notes; use weekly quality snapshot (P5 v3)",
        },
        "observation_only": True,
        "not_investment_advice": True,
        "live_http": False,
    }


def format_us_forward_return_markdown(report: dict[str, Any]) -> str:
    sq = report.get("sample_quality") or {}
    lines = [
        "# US Forward Return Validation — Cache Only",
        "",
        "Observation only — not buy/sell advice.",
        "",
        f"**Sample quality**: {sq.get('status')} — {sq.get('reason')}",
        f"- matched rows: {sq.get('matched_rows', report.get('rows_matched'))}",
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

    lines.extend(["", "## Quality buckets (global)"])
    global_buckets = (report.get("quality_buckets") or {}).get("global") or {}
    for h in report.get("horizons") or []:
        b = global_buckets.get(str(h)) or {}
        lines.append(
            f"- {h}d: n={b.get('count')} avg={b.get('avg_forward')} "
            f"hit+={b.get('hit_rate_positive')} hit>2%={b.get('hit_rate_gt_2pct')} "
            f"hit<-2%={b.get('hit_rate_lt_minus_2pct')}"
        )

    lines.extend(["", "## By signal label"])
    label_buckets = (report.get("quality_buckets") or {}).get("by_signal_label") or {}
    for lbl, per_h in sorted(label_buckets.items()):
        parts: list[str] = []
        for h in report.get("horizons") or []:
            b = per_h.get(str(h)) or {}
            parts.append(f"{h}d n={b.get('count')} hit+={b.get('hit_rate_positive')}")
        lines.append(f"- {lbl}: {', '.join(parts)}")
    lines.append("")
    return "\n".join(lines)
