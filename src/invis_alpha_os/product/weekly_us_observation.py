"""Weekly US cache-only observation cycle (P4); read-only except opt-in observation_log append."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
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

US_SIGNAL_NOTE_PREFIX = "us_cache_signal observation_only"
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


def _parse_observation_note(note: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ("status", "momentum_label", "reason"):
        m = re.search(rf"{key}=([^\s]+)", note)
        if m:
            out[key] = m.group(1)
    return out


def summarize_us_observation_log(observation_path: Path) -> dict[str, Any]:
    """Summarize US cache signal rows already in observation_log.jsonl."""

    if not observation_path.is_file():
        return {
            "status": "missing",
            "path": str(observation_path),
            "us_signal_rows": 0,
            "by_status": {},
            "symbols": [],
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
        parsed = _parse_observation_note(note)
        rows.append(
            {
                "symbol": row.get("symbol"),
                "created_at": row.get("created_at"),
                "status": parsed.get("status", "unknown"),
                "momentum_label": parsed.get("momentum_label"),
                "reason": parsed.get("reason"),
            }
        )
    by_status: dict[str, int] = {}
    for r in rows:
        st = str(r.get("status") or "unknown")
        by_status[st] = by_status.get(st, 0) + 1
    return {
        "status": "ok",
        "path": str(observation_path),
        "us_signal_rows": len(rows),
        "by_status": by_status,
        "symbols": sorted({str(r["symbol"]) for r in rows if r.get("symbol")}),
        "rows": rows,
        "observation_only": True,
    }


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


def run_weekly_us_observation_cycle(
    *,
    path_base: Path | None = None,
    manifest_out: Path | None = None,
    write_observation_log: bool = False,
    observation_service: ObservationService | None = None,
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
            Path(written), path_base=root, service=observation_service
        )
        if observation_batch_failed(obs_result):
            raise ValueError(f"observation batch failed: {obs_result}")
        obs_summary = summarize_us_observation_log(observation_service.observation_path)

    return WeeklyUsObservationResult(
        manifest=manifest,
        batch_previews=batch,
        quality=quality,
        observation_log=obs_summary,
        manifest_path_written=written,
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


def format_weekly_us_observation_markdown(result: WeeklyUsObservationResult) -> str:
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
            ]
        )
    lines.append("")
    return "\n".join(lines)
