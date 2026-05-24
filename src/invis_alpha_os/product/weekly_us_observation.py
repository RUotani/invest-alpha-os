"""Weekly US cache-only observation cycle (P4); read-only except opt-in observation_log append."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import ROOT_DIR
from invis_alpha_os.config.us_watchlist import load_us_watchlist_tickers
from invis_alpha_os.config.loader import load_yaml
from invis_alpha_os.config.paths import CONFIG_DIR
from invis_alpha_os.data.us_cache_signals import build_us_cache_signals_preview
from invis_alpha_os.data.us_cache_signals_batch_manifest import (
    build_us_cache_signals_previews_from_batch_manifest,
    parse_us_cache_signals_batch_manifest_payload,
)
from invis_alpha_os.data.us_daily_bars_cache import try_load_cached_us_daily_bars
from invis_alpha_os.data.us_daily_bars_metrics import compute_us_daily_bars_basic_metrics
from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.observation.us_signals_batch import (
    log_us_signals_batch_observations,
    observation_batch_failed,
)
from invis_alpha_os.risk.veto_rules import VetoEngine, build_momentum_veto_result
from invis_alpha_os.signals.momentum import analyze_bars_for_code

from invis_alpha_os.observation.us_signal_note import (
    US_SIGNAL_NOTE_PREFIX,
    parse_us_signal_observation_note,
)

# Backward-compatible alias for tests/imports
_parse_observation_note = parse_us_signal_observation_note
_MANIFEST_REL_CACHE = "outputs/market_data/us_daily_bars/{symbol}.json"


def build_us_watchlist_signals_manifest(
    *,
    path_base: Path | None = None,
    source: str = "weekly_us_observation",
) -> dict[str, Any]:
    """Build in-memory batch manifest for current US watchlist (no directory scan)."""

    root = path_base or ROOT_DIR
    entries: list[dict[str, str]] = []
    missing_cache: list[str] = []
    for sym in load_us_watchlist_tickers():
        rel = _MANIFEST_REL_CACHE.format(symbol=sym)
        if not (root / rel).is_file():
            missing_cache.append(sym)
            continue
        entries.append({"symbol": sym, "cache_path": rel})
    return {
        "schema_version": 1,
        "source": source,
        "entries": entries,
        "missing_cache_symbols": missing_cache,
    }


def summarize_us_observation_log(
    observation_path: Path,
    *,
    missing_cache_symbols: list[str] | None = None,
    quality_snapshot: dict[str, Any] | None = None,
    forward_sample_quality: dict[str, Any] | None = None,
    aged_signal_days: int = 7,
) -> dict[str, Any]:
    """Summarize US cache signal rows already in observation_log.jsonl."""

    if not observation_path.is_file():
        checklist = _build_research_checklist(
            [],
            {},
            [],
            signal_aging_days_max=None,
            missing_cache_symbols=missing_cache_symbols or [],
            forward_sample_quality=forward_sample_quality,
            quality_snapshot=quality_snapshot,
            aged_signal_days=aged_signal_days,
        )
        return {
            "status": "missing",
            "path": str(observation_path),
            "us_signal_rows": 0,
            "by_status": {},
            "symbols": [],
            "research_checklist": checklist,
            "weekly_trend": compute_us_signal_weekly_trend([]),
            "repeat_summary": compute_repeat_signal_summary([]),
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
        if US_SIGNAL_NOTE_PREFIX not in note:
            continue
        parsed = parse_us_signal_observation_note(note)
        rows.append(
            {
                "symbol": row.get("symbol"),
                "created_at": row.get("created_at"),
                "status": parsed.get("status", "unknown"),
                "momentum_label": parsed.get("momentum_label"),
                "reason": parsed.get("reason"),
                "note": note,
            }
        )
    by_status: dict[str, int] = {}
    sym_counts: Counter[str] = Counter()
    today = date.today()
    aging_days: list[int] = []
    for r in rows:
        st = str(r.get("status") or "unknown")
        by_status[st] = by_status.get(st, 0) + 1
        sym = r.get("symbol")
        if sym:
            sym_counts[str(sym)] += 1
        created = r.get("created_at")
        if created:
            if isinstance(created, datetime):
                d0 = created.date()
            elif isinstance(created, date):
                d0 = created
            else:
                try:
                    d0 = date.fromisoformat(str(created)[:10])
                except ValueError:
                    d0 = None
            if d0 is not None:
                aging_days.append(max(0, (today - d0).days))
    repeat_symbols = sorted([s for s, n in sym_counts.items() if n > 1])
    aging_max = max(aging_days) if aging_days else None
    checklist = _build_research_checklist(
        rows,
        by_status,
        repeat_symbols,
        signal_aging_days_max=aging_max,
        missing_cache_symbols=missing_cache_symbols or [],
        forward_sample_quality=forward_sample_quality,
        quality_snapshot=quality_snapshot,
        aged_signal_days=aged_signal_days,
    )
    return {
        "status": "ok",
        "path": str(observation_path),
        "us_signal_rows": len(rows),
        "by_status": by_status,
        "symbols": sorted({str(r["symbol"]) for r in rows if r.get("symbol")}),
        "repeat_signal_symbols": repeat_symbols,
        "repeat_signal_count": sum(n - 1 for n in sym_counts.values() if n > 1),
        "signal_aging_days_max": aging_max,
        "signal_aging_days_avg": (sum(aging_days) / len(aging_days)) if aging_days else None,
        "rows": rows,
        "observation_only": True,
        "research_checklist": checklist,
        "weekly_trend": compute_us_signal_weekly_trend(rows),
        "repeat_summary": compute_repeat_signal_summary(rows),
    }


def _parse_row_created_at(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            d0 = date.fromisoformat(text[:10])
            return datetime.combine(d0, datetime.min.time())
        except ValueError:
            return None


def _trailing_consecutive_weeks(weeks: list[tuple[int, int]]) -> int:
    if not weeks:
        return 0
    ords = sorted(date.fromisocalendar(y, w, 1).toordinal() for y, w in weeks)
    best = 1
    run = 1
    for i in range(1, len(ords)):
        if ords[i] - ords[i - 1] == 7:
            run += 1
        else:
            run = 1
        best = max(best, run)
    return best


def compute_repeat_signal_summary(
    rows: list[dict[str, Any]],
    *,
    stale_repeat_weeks: int = 2,
) -> dict[str, Any]:
    """Repeat signal grouping (raw rows preserved; summary only)."""

    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        sym = row.get("symbol")
        if sym:
            by_symbol[str(sym)].append(row)

    repeat_by_symbol: list[dict[str, Any]] = []
    repeat_by_label: Counter[str] = Counter()

    for sym, sym_rows in sorted(by_symbol.items()):
        if len(sym_rows) < 2:
            continue
        dts: list[datetime] = []
        labels: list[str] = []
        for row in sym_rows:
            dt = _parse_row_created_at(row.get("created_at"))
            if dt is not None:
                dts.append(dt)
            label = row.get("momentum_label")
            if label:
                repeat_by_label[str(label)] += 1
                labels.append(str(label))
        if not dts:
            continue
        dts.sort()
        weeks = list({(d.isocalendar().year, d.isocalendar().week) for d in dts})
        consecutive = _trailing_consecutive_weeks(weeks)
        repeat_by_symbol.append(
            {
                "symbol": sym,
                "count": len(sym_rows),
                "first_seen": dts[0].isoformat(),
                "last_seen": dts[-1].isoformat(),
                "consecutive_weeks": consecutive,
                "momentum_labels": sorted(set(labels)),
                "stale_repeat_flag": consecutive >= stale_repeat_weeks,
            }
        )

    return {
        "repeat_by_symbol": repeat_by_symbol,
        "repeat_by_label": dict(repeat_by_label),
        "repeat_symbol_count": len(repeat_by_symbol),
        "observation_only": True,
    }


def compute_us_signal_weekly_trend(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """ISO-week US signal row counts for docs/154 P2 (read-only)."""

    week_counts: Counter[tuple[int, int]] = Counter()
    for row in rows:
        created = row.get("created_at")
        if isinstance(created, datetime):
            iso = created.isocalendar()
            week_counts[(iso.year, iso.week)] += 1
            continue
        if isinstance(created, date):
            iso = created.isocalendar()
            week_counts[(iso.year, iso.week)] += 1
            continue
        text = str(created or "").strip()
        if not text:
            continue
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            iso = dt.isocalendar()
            week_counts[(iso.year, iso.week)] += 1
        except ValueError:
            try:
                d0 = date.fromisoformat(text[:10])
                iso = d0.isocalendar()
                week_counts[(iso.year, iso.week)] += 1
            except ValueError:
                continue

    sorted_weeks = sorted(week_counts.keys())
    weekly_counts = {f"{y}-W{w:02d}": week_counts[(y, w)] for y, w in sorted_weeks}
    base: dict[str, Any] = {
        "weekly_counts": weekly_counts,
        "latest_week": None,
        "prior_week": None,
        "latest_week_count": 0,
        "prior_week_count": 0,
        "delta": 0,
        "status": "insufficient_history",
    }
    if len(sorted_weeks) < 2:
        if len(sorted_weeks) == 1:
            y, w = sorted_weeks[0]
            base["latest_week"] = f"{y}-W{w:02d}"
            base["latest_week_count"] = week_counts[(y, w)]
        return base

    latest, prior = sorted_weeks[-1], sorted_weeks[-2]
    latest_c = week_counts[latest]
    prior_c = week_counts[prior]
    delta = latest_c - prior_c
    if delta > 0:
        status = "growing"
    elif delta == 0:
        status = "flat"
    else:
        status = "declining"
    return {
        "weekly_counts": weekly_counts,
        "latest_week": f"{latest[0]}-W{latest[1]:02d}",
        "prior_week": f"{prior[0]}-W{prior[1]:02d}",
        "latest_week_count": latest_c,
        "prior_week_count": prior_c,
        "delta": delta,
        "status": status,
    }


def build_enriched_us_observation_summary(
    observation_path: Path,
    *,
    path_base: Path | None = None,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """US observation_log summary with manifest/quality/forward enrichment (read-only)."""

    root = path_base or ROOT_DIR
    manifest = build_us_watchlist_signals_manifest(path_base=root)
    quality = us_signal_quality_snapshot(path_base=root)
    forward_sq: dict[str, Any] | None = None
    if observation_path.is_file():
        try:
            from invis_alpha_os.product.us_forward_return_validation import compute_us_forward_returns

            cache = cache_dir or (root / "outputs" / "market_data" / "us_daily_bars")
            fwd = compute_us_forward_returns(
                observation_path=observation_path,
                cache_dir=cache if cache.is_dir() else None,
                path_base=root,
            )
            forward_sq = fwd.get("sample_quality")
        except (FileNotFoundError, ValueError):
            forward_sq = None
    return summarize_us_observation_log(
        observation_path,
        missing_cache_symbols=list(manifest.get("missing_cache_symbols") or []),
        quality_snapshot=quality,
        forward_sample_quality=forward_sq,
    )


def _checklist_item(
    *,
    category: str,
    symbol: str | None,
    reason: str,
    next_action: str,
) -> dict[str, str]:
    return {
        "category": category,
        "symbol": symbol or "",
        "reason": reason,
        "next_action": next_action,
    }


def _build_research_checklist(
    rows: list[dict[str, Any]],
    by_status: dict[str, int],
    repeat_symbols: list[str],
    *,
    signal_aging_days_max: int | None,
    missing_cache_symbols: list[str],
    forward_sample_quality: dict[str, Any] | None,
    quality_snapshot: dict[str, Any] | None,
    aged_signal_days: int,
) -> list[dict[str, str]]:
    """Structured observation-only research items (no buy/sell wording)."""

    items: list[dict[str, str]] = []
    for sym in repeat_symbols[:8]:
        items.append(
            _checklist_item(
                category="repeat_signal",
                symbol=sym,
                reason="multiple US signal observations logged for symbol",
                next_action="review note history and momentum label changes",
            )
        )
    if signal_aging_days_max is not None and signal_aging_days_max >= aged_signal_days:
        items.append(
            _checklist_item(
                category="aged_signal",
                symbol=None,
                reason=f"oldest US signal observation is {signal_aging_days_max} days old",
                next_action="re-run weekly-us-observation and compare to current cache",
            )
        )
    for sym in sorted(missing_cache_symbols)[:8]:
        items.append(
            _checklist_item(
                category="missing_cache",
                symbol=sym,
                reason="watchlist symbol has no US daily bars cache file",
                next_action="schedule gated cache refresh when approved",
            )
        )
    stale = int(by_status.get("stale", 0) or 0)
    if stale:
        items.append(
            _checklist_item(
                category="aged_signal",
                symbol=None,
                reason=f"{stale} observation row(s) marked stale in log",
                next_action="inspect cache freshness and re-log after refresh",
            )
        )
    insufficient = int(by_status.get("insufficient", 0) or 0)
    if insufficient:
        items.append(
            _checklist_item(
                category="missing_cache",
                symbol=None,
                reason=f"{insufficient} observation row(s) with insufficient bars",
                next_action="verify bar count in cache JSON before next observation",
            )
        )
    fq = forward_sample_quality or {}
    if fq.get("status") in {"thin", "empty"}:
        items.append(
            _checklist_item(
                category="thin_forward_validation",
                symbol=None,
                reason=str(fq.get("reason") or "forward-return sample too small"),
                next_action="accumulate more observation_log rows before quality conclusions",
            )
        )
    if quality_snapshot:
        for row in quality_snapshot.get("rows") or []:
            if row.get("veto_triggered"):
                sym = str(row.get("symbol") or "")
                rules = row.get("veto_rules") or []
                items.append(
                    _checklist_item(
                        category="veto_review",
                        symbol=sym,
                        reason=f"veto triggered ({', '.join(str(r) for r in rules[:3])})",
                        next_action="review momentum context; observation only",
                    )
                )
    if not rows and not items:
        items.append(
            _checklist_item(
                category="missing_cache",
                symbol=None,
                reason="no US signal rows in observation_log",
                next_action="run weekly-us-observation --write-observation-log when ready",
            )
        )
    if not items:
        items.append(
            _checklist_item(
                category="repeat_signal",
                symbol=None,
                reason="no urgent checklist items from current observation_log",
                next_action="continue weekly cache-only monitoring",
            )
        )
    return items


def us_signal_quality_snapshot(*, path_base: Path | None = None) -> dict[str, Any]:
    """Per-symbol cache metrics + momentum + veto (read-only; no HTTP)."""

    root = path_base or ROOT_DIR
    veto_engine = VetoEngine(rules=load_yaml(CONFIG_DIR / "veto_rules.yaml"))
    symbols = load_us_watchlist_tickers()
    rows: list[dict[str, Any]] = []
    for sym in symbols:
        loaded = try_load_cached_us_daily_bars(sym)
        if loaded is None:
            rows.append({"symbol": sym, "cache_status": "missing_or_invalid"})
            continue
        bars, _src = loaded
        metrics = compute_us_daily_bars_basic_metrics(bars)
        mom = analyze_bars_for_code(sym, bars)
        veto = build_momentum_veto_result(mom, veto_engine) if mom else {"triggered": False}
        preview = build_us_cache_signals_preview(
            root / _MANIFEST_REL_CACHE.format(symbol=sym), expect_symbol=sym
        )
        rows.append(
            {
                "symbol": sym,
                "cache_status": "ok",
                "signals_status": preview.get("status"),
                "momentum_label": preview.get("momentum_label"),
                "return_5d": metrics.get("return_5d"),
                "return_20d": metrics.get("return_20d"),
                "volume_status": metrics.get("volume_status"),
                "veto_triggered": bool(veto.get("triggered")),
                "veto_rules": veto.get("rules") if veto.get("triggered") else [],
            }
        )
    ok_signals = sum(1 for r in rows if r.get("signals_status") == "ok")
    veto_count = sum(1 for r in rows if r.get("veto_triggered"))
    return {
        "status": "ok",
        "symbol_count": len(symbols),
        "signals_ok": ok_signals,
        "veto_triggered_count": veto_count,
        "rows": rows,
        "observation_only": True,
        "live_http": False,
    }


@dataclass
class WeeklyUsObservationResult:
    manifest: dict[str, Any]
    batch_previews: dict[str, Any]
    quality: dict[str, Any]
    observation_log: dict[str, Any] | None
    manifest_path_written: str | None
    peer_sync: dict[str, Any] | None = None


def run_weekly_us_observation_cycle(
    *,
    path_base: Path | None = None,
    manifest_out: Path | None = None,
    write_observation_log: bool = False,
    observation_service: ObservationService | None = None,
    include_peer_sync: bool = False,
) -> WeeklyUsObservationResult:
    """Run cache-only US signal batch + optional observation_log append."""

    root = path_base or ROOT_DIR
    manifest = build_us_watchlist_signals_manifest(path_base=root)
    written: str | None = None
    if manifest_out is not None:
        manifest_out.parent.mkdir(parents=True, exist_ok=True)
        manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written = str(manifest_out)

    parsed = parse_us_cache_signals_batch_manifest_payload(manifest)
    if parsed is None:
        batch = {
            "status": "invalid",
            "reason": "manifest_invalid",
            "previews": [],
            "entry_count": 0,
            "live_http": False,
        }
    elif written:
        batch = build_us_cache_signals_previews_from_batch_manifest(
            Path(written), path_base=root
        )
    else:
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(manifest, tf, ensure_ascii=False)
            tf.flush()
            tmp = Path(tf.name)
        try:
            batch = build_us_cache_signals_previews_from_batch_manifest(tmp, path_base=root)
        finally:
            tmp.unlink(missing_ok=True)

    quality = us_signal_quality_snapshot(path_base=root)
    obs_summary: dict[str, Any] | None = None
    if write_observation_log:
        if observation_service is None:
            raise ValueError("observation_service required when write_observation_log=True")
        if written is None:
            raise ValueError("manifest_out path required when write_observation_log=True")
        obs_result = log_us_signals_batch_observations(
            Path(written),
            path_base=root,
            service=observation_service,
            quality_snapshot=quality,
        )
        if observation_batch_failed(obs_result):
            raise ValueError(f"observation batch failed: {obs_result}")
        obs_summary = build_enriched_us_observation_summary(
            observation_service.observation_path,
            path_base=root,
        )

    peer_sync_payload: dict[str, Any] | None = None
    if include_peer_sync:
        from invis_alpha_os.product.peer_sync_cache_only import build_peer_sync_cache_only_report

        peer_sync_payload = build_peer_sync_cache_only_report(path_base=root).to_dict()

    if obs_summary is None:
        from invis_alpha_os.config.paths import OUTPUTS_DIR as _outputs

        default_obs = _outputs / "observation_log" / "observation_log.jsonl"
        if default_obs.is_file():
            obs_summary = build_enriched_us_observation_summary(
                default_obs,
                path_base=root,
            )

    return WeeklyUsObservationResult(
        manifest=manifest,
        batch_previews=batch,
        quality=quality,
        observation_log=obs_summary,
        manifest_path_written=written,
        peer_sync=peer_sync_payload,
    )


def us_cache_expansion_report(
    *,
    path_base: Path | None = None,
    discover_limit: int = 25,
) -> dict[str, Any]:
    """Read-only gap report: watchlist vs on-disk cache vs discovery candidates (P3/US)."""

    from invis_alpha_os.discovery.us_universe_scanner import scan_us_universe

    root = path_base or ROOT_DIR
    watchlist = load_us_watchlist_tickers()
    cached: list[str] = []
    missing: list[str] = []
    for sym in watchlist:
        rel = _MANIFEST_REL_CACHE.format(symbol=sym)
        if (root / rel).is_file():
            cached.append(sym)
        else:
            missing.append(sym)
    discovery = scan_us_universe(limit=discover_limit)
    discover_syms = [c.symbol for c in discovery.candidates]
    discover_without_cache = [
        s
        for s in discover_syms
        if s not in cached and not (root / _MANIFEST_REL_CACHE.format(symbol=s)).is_file()
    ]
    return {
        "status": "ok",
        "watchlist_count": len(watchlist),
        "cache_file_count": len(cached),
        "missing_cache_on_watchlist": missing,
        "discovery_candidates": len(discover_syms),
        "discovery_without_cache_file": discover_without_cache[:discover_limit],
        "observation_only": True,
        "live_http": False,
    }


def format_weekly_us_observation_markdown(
    result: WeeklyUsObservationResult,
    *,
    path_base: Path | None = None,
) -> str:
    m = result.manifest
    b = result.batch_previews
    q = result.quality
    lines = [
        "# Weekly US observation (cache-only)",
        "",
        "Observation only — not buy/sell advice.",
        "",
        "## Manifest",
        f"- entries: {len(m.get('entries') or [])}",
        f"- missing cache on watchlist: {len(m.get('missing_cache_symbols') or [])}",
        "",
        "## Signals batch",
        f"- status: {b.get('status')}",
        f"- previews: {b.get('entry_count')}",
        "",
        "## Quality snapshot",
        f"- signals ok: {q.get('signals_ok')}/{q.get('symbol_count')}",
        f"- veto triggered: {q.get('veto_triggered_count')}",
    ]
    if result.observation_log:
        o = result.observation_log
        lines.extend(
            [
                "",
                "## Observation log",
                f"- us_signal_rows: {o.get('us_signal_rows')}",
                f"- by_status: {o.get('by_status')}",
                f"- signal aging (days, avg/max): {o.get('signal_aging_days_avg')} / {o.get('signal_aging_days_max')}",
                f"- repeat signal symbols: {', '.join(o.get('repeat_signal_symbols') or []) or '(none)'}",
            ]
        )
        checklist = o.get("research_checklist") or []
        if checklist:
            lines.extend(["", "## Next research checklist (observe only)"])
            for item in checklist:
                if isinstance(item, dict):
                    sym = item.get("symbol") or "—"
                    lines.append(
                        f"- [{item.get('category')}] {sym}: {item.get('reason')} → {item.get('next_action')}"
                    )
                else:
                    lines.append(f"- {item}")

    root = path_base or ROOT_DIR
    obs_path = root / "outputs" / "observation_log" / "observation_log.jsonl"
    if obs_path.is_file() and (result.observation_log or {}).get("us_signal_rows", 0) > 0:
        try:
            from invis_alpha_os.product.us_forward_return_validation import compute_us_forward_returns

            fwd = compute_us_forward_returns(observation_path=obs_path, path_base=root)
            sq = fwd.get("sample_quality") or {}
            from invis_alpha_os.product.us_forward_return_validation import (
                forward_validation_next_commands,
            )

            lines.extend(
                [
                    "",
                    "## Forward validation summary",
                    f"- sample quality: {sq.get('status')} — {sq.get('reason')}",
                    f"- matched rows: {fwd.get('rows_matched')}",
                    f"- interpretation: {sq.get('interpretation', '')}",
                ]
            )
            if sq.get("status") in {"empty", "thin"}:
                lines.append(f"- needed_more_samples: {sq.get('needed_more_samples')}")
            lines.extend(["", "### Suggested next commands"])
            for cmd in forward_validation_next_commands():
                lines.append(f"- `{cmd}`")
            veto = fwd.get("veto_at_t") or {}
            lines.append(f"- veto-at-t status: {veto.get('status')}")
            gb = (fwd.get("quality_buckets") or {}).get("global") or {}
            for h in fwd.get("horizons") or []:
                bucket = gb.get(str(h)) or {}
                if bucket.get("count"):
                    lines.append(
                        f"- {h}d: hit_rate_positive={bucket.get('hit_rate_positive')} "
                        f"(n={bucket.get('count')})"
                    )
        except (FileNotFoundError, ValueError):
            pass

    try:
        from invis_alpha_os.product.us_universe_expansion import build_us_universe_expansion_report

        exp = build_us_universe_expansion_report(path_base=root, tier="1", missing_only=True)
        tier1 = exp.get("tier_1_missing_refresh_order") or []
        if tier1:
            lines.extend(["", "## US tier-1 cache gaps (gated refresh order)"])
            for sym in tier1[:10]:
                lines.append(f"- {sym}")
            if len(tier1) > 10:
                lines.append(f"- … +{len(tier1) - 10} more")
    except (FileNotFoundError, ValueError):
        pass

    if result.peer_sync:
        ps = result.peer_sync
        summary = ps.get("summary") or {}
        lines.extend(
            [
                "",
                "## Peer sync (cache-only)",
                f"- pairs evaluated: {len(ps.get('pairs') or [])}",
            ]
        )
        if summary:
            for status, count in sorted(summary.items()):
                lines.append(f"- `{status}`: {count}")
        diverged = [
            p
            for p in (ps.get("pairs") or [])
            if isinstance(p, dict)
            and str(p.get("status", "")).startswith("diverged")
        ]
        if diverged:
            lines.append("")
            lines.append("### Diverged pairs (observe only)")
            for row in diverged[:5]:
                spread = row.get("return_spread")
                spread_s = f"{spread:.2%}" if isinstance(spread, (int, float)) else "—"
                lines.append(
                    f"- {row.get('anchor_symbol')} vs {row.get('peer_symbol')}: "
                    f"{row.get('status')} (spread {spread_s})"
                )

    lines.extend(
        [
            "",
            "## Ops smoke (read-only)",
            "- `validate ops-smoke --format markdown`",
            "- `snapshot observation-health --format json`",
            "",
            "## Operator one-pager (docs/160)",
            "- Weekly copy-paste: `docs/160_product_weekly_operator_one_pager.md`",
            "- Evidence manifest: `.venv/bin/python -m invis_alpha_os.cli.main log evidence-manifest "
            "--task-id weekly_preflight_YYYYMMDD --report-date YYYY-MM-DD`",
        ]
    )
    lines.append("")
    return "\n".join(lines)
