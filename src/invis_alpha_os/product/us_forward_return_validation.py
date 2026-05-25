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
from invis_alpha_os.observation.us_signal_note import (
    US_SIGNAL_NOTE_PREFIX,
    parse_us_signal_observation_note,
)
from invis_alpha_os.product.forward_event_resolution import (
    cache_stale_skip_reason,
    event_bar_index,
    resolve_forward_horizons,
    resolve_observation_event_date,
)
from invis_alpha_os.signals.momentum import DailyBar

SCHEMA_VERSION = 2
DEFAULT_HORIZONS: tuple[int, ...] = (5, 20, 60)
THIN_SAMPLE_THRESHOLD = 10


def classify_forward_skip_pattern(
    skipped_reasons: dict[str, int] | None,
    *,
    signal_rows: int = 0,
) -> str:
    """Classify dominant skip reason for docs/161 fresh-log vs stale-cache (read-only)."""

    if not skipped_reasons or signal_rows <= 0:
        return "none"
    insuf = int(skipped_reasons.get("insufficient_future_bars") or 0)
    stale = int(skipped_reasons.get("cache_stale_event_after_cache_end") or 0)
    if insuf >= signal_rows and stale == 0:
        return "fresh_log"
    if stale >= max(1, signal_rows // 2):
        return "stale_cache"
    if insuf > 0 and stale > 0:
        return "mixed"
    return "other"


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


def forward_validation_next_commands(*, exploratory: bool = False) -> list[str]:
    """Read-only CLI hints after observation_log append (no defaults changed)."""

    cmds = [
        ".venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --format markdown",
        ".venv/bin/python -m invis_alpha_os.cli.main log us-signals-summary",
        ".venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation --dry-run --format markdown",
    ]
    if exploratory:
        cmds.insert(
            1,
            ".venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns "
            "--backtest-within-cache --format markdown  # docs/161 exploratory only",
        )
    return cmds


def _sample_quality(
    matched_count: int,
    *,
    skipped_reasons: dict[str, int] | None = None,
    signal_rows: int = 0,
) -> dict[str, Any]:
    exploratory = False
    if matched_count == 0:
        reason = "no observation rows matched to cache forward windows"
        interpretation = "Do not draw signal-quality conclusions from forward returns yet."
        if signal_rows > 0 and skipped_reasons:
            insuf = int(skipped_reasons.get("insufficient_future_bars") or 0)
            stale = int(skipped_reasons.get("cache_stale_event_after_cache_end") or 0)
            if stale > 0 and stale >= max(1, signal_rows // 2):
                reason = "observation log dates are after cache end"
                interpretation = (
                    "Cache ends before observation timestamps. Refresh US cache (P10 tier-1) "
                    "or re-run with --backtest-within-cache for exploratory in-cache joins only "
                    "(docs/161)."
                )
                exploratory = True
            elif insuf >= signal_rows:
                reason = "observation events are too recent for forward windows"
                interpretation = (
                    "Rows were logged but cache has no future sessions yet. "
                    "Re-run after trading sessions pass or accumulate historical rows (docs/161)."
                )
                exploratory = True
    hints = forward_validation_next_commands(exploratory=exploratory)
    skip_pattern = classify_forward_skip_pattern(skipped_reasons, signal_rows=signal_rows)
    if matched_count == 0:
        return {
            "status": "empty",
            "reason": reason,
            "matched_rows": 0,
            "interpretation": interpretation,
            "needed_more_samples": THIN_SAMPLE_THRESHOLD,
            "skip_pattern": skip_pattern,
            "next_commands": hints,
        }
    if matched_count < THIN_SAMPLE_THRESHOLD:
        return {
            "status": "thin",
            "reason": f"matched rows below minimum threshold ({THIN_SAMPLE_THRESHOLD})",
            "matched_rows": matched_count,
            "interpretation": "Buckets are exploratory only; accumulate more US signal rows.",
            "needed_more_samples": THIN_SAMPLE_THRESHOLD - matched_count,
            "skip_pattern": skip_pattern,
            "next_commands": hints,
        }
    return {
        "status": "usable",
        "reason": "matched rows sufficient for exploratory bucket review",
        "matched_rows": matched_count,
        "interpretation": "Review hit-rate buckets as observation-only diagnostics.",
        "needed_more_samples": 0,
        "skip_pattern": "none",
        "next_commands": hints,
    }


def _veto_at_t_report(obs_rows: list[dict[str, Any]], matched: list[dict[str, Any]]) -> dict[str, Any]:
    with_field = [r for r in obs_rows if r.get("veto_triggered") is not None]
    if not with_field:
        return {
            "status": "not_in_observation_log",
            "reason": "veto-at-t not stored in observation_log notes (legacy rows OK)",
        }
    triggered = sum(1 for r in with_field if r.get("veto_triggered") is True)
    not_triggered = sum(1 for r in with_field if r.get("veto_triggered") is False)
    return {
        "status": "joined",
        "rows_with_veto_field": len(with_field),
        "triggered_at_log": triggered,
        "not_triggered_at_log": not_triggered,
        "matched_with_veto_field": sum(1 for r in matched if r.get("veto_triggered") is not None),
    }


def _build_by_veto_status(
    matched: list[dict[str, Any]],
    horizons: tuple[int, ...],
    *,
    thin_sample: bool,
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in matched:
        vt = row.get("veto_triggered")
        if vt is True:
            key = "triggered"
        elif vt is False:
            key = "not_triggered"
        else:
            key = "unknown"
        groups[key].append(row)
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
        event, event_source = resolve_observation_event_date(
            note=note,
            created_at=row.get("created_at"),
        )
        if event is None:
            skipped["missing_event_date"] += 1
            continue
        parsed = parse_us_signal_observation_note(note)
        rows.append(
            {
                "symbol": str(sym).strip().upper(),
                "event_date": event,
                "event_date_source": event_source,
                "momentum_label": parsed.get("momentum_label"),
                "status": str(parsed.get("status") or "unknown"),
                "veto_triggered": parsed.get("veto_triggered"),
                "veto_rules": parsed.get("veto_rules"),
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
    backtest_within_cache: bool = False,
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
        if event_bar_index(bars, event) is None:
            skipped_reasons["event_date_outside_cache"] += 1
            continue
        stale = cache_stale_skip_reason(event, bars)
        resolved = resolve_forward_horizons(
            bars,
            event,
            horizons,
            backtest_within_cache=backtest_within_cache,
        )
        if resolved is None:
            if stale and not backtest_within_cache:
                skipped_reasons[stale] += 1
            else:
                skipped_reasons["insufficient_future_bars"] += 1
            continue
        idx, horizon_returns, event_resolution = resolved
        matched.append(
            {
                "symbol": sym,
                "event_date": event.isoformat(),
                "event_date_source": row.get("event_date_source"),
                "event_resolution": event_resolution,
                "bar_index": idx,
                "momentum_label": row.get("momentum_label"),
                "status": row.get("status"),
                "veto_triggered": row.get("veto_triggered"),
                "veto_rules": row.get("veto_rules"),
                "horizons": horizon_returns,
            }
        )

    thin = len(matched) < THIN_SAMPLE_THRESHOLD
    quality_buckets = _build_quality_buckets(matched, horizons, thin_sample=thin)
    sample_quality = _sample_quality(
        len(matched),
        skipped_reasons=dict(skipped_reasons),
        signal_rows=len(obs_rows),
    )

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

    from invis_alpha_os.product.peer_sync_forward_validation import compute_peer_sync_forward_join

    peer_sync_forward = compute_peer_sync_forward_join(
        observation_path=observation_path,
        horizons=horizons,
        reference_date=reference_date,
        backtest_within_cache=backtest_within_cache,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(),
        "observation_path": str(observation_path),
        "path_base": str(root),
        "horizons": list(horizons),
        "reference_date": reference_date.isoformat() if reference_date else None,
        "backtest_within_cache": backtest_within_cache,
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
        "veto_at_t": _veto_at_t_report(obs_rows, matched),
        "by_veto_status": _build_by_veto_status(matched, horizons, thin_sample=thin),
        "peer_sync_forward": peer_sync_forward,
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
        f"- interpretation: {sq.get('interpretation', '')}",
    ]
    skip_pat = sq.get("skip_pattern")
    if skip_pat and skip_pat != "none":
        lines.append(f"- skip_pattern: {skip_pat} (docs/161)")
    if sq.get("status") in {"empty", "thin"}:
        lines.append(f"- needed_more_samples: {sq.get('needed_more_samples')}")
    lines.extend(
        [
        "",
        "### Suggested next commands (read-only)",
        ]
    )
    for cmd in sq.get("next_commands") or []:
        lines.append(f"- `{cmd}`")
    lines.extend(
        [
        "",
        f"- observation rows considered: {report.get('rows_considered')}",
        f"- matched rows: {report.get('rows_matched')}",
        f"- skipped rows: {report.get('rows_skipped')}",
        f"- horizons (sessions): {', '.join(str(h) for h in report.get('horizons') or [])}",
        "",
        "## Skipped reasons",
        ]
    )
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
    veto_at_t = report.get("veto_at_t") or {}
    lines.extend(["", "## Veto-at-t"])
    lines.append(f"- status: {veto_at_t.get('status')}")
    lines.append(f"- detail: {veto_at_t.get('reason', veto_at_t)}")
    by_veto = report.get("by_veto_status") or {}
    if by_veto:
        lines.append("")
        lines.append("### By veto status (matched rows)")
        for key, block in sorted(by_veto.items()):
            lines.append(f"- {key}: count={block.get('count')}")
    ps_fwd = report.get("peer_sync_forward") or {}
    ps_at_t = ps_fwd.get("peer_sync_at_t") or {}
    lines.extend(["", "## Peer sync × forward (read-only join)"])
    lines.append(f"- peer_sync_at_t: {ps_at_t.get('status')}")
    if ps_at_t.get("reason"):
        lines.append(f"- detail: {ps_at_t.get('reason')}")
    if ps_at_t.get("peer_sync_log_rows") is not None:
        lines.append(f"- peer_sync log rows: {ps_at_t.get('peer_sync_log_rows')}")
        lines.append(f"- matched with forward: {ps_at_t.get('matched_with_forward')}")
    by_ps = ps_fwd.get("by_peer_sync_status") or {}
    if by_ps:
        lines.append("")
        lines.append("### By peer_sync_status (matched rows)")
        for key, block in sorted(by_ps.items()):
            lines.append(f"- {key}: count={block.get('count')}")
    lines.append("")
    return "\n".join(lines)
