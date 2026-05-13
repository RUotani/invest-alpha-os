from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import typer

from invis_alpha_os.cli.bars_file_symbol import normalize_generic_bars_file_symbol_label
from invis_alpha_os.config import CONFIG_DIR, OUTPUTS_DIR, load_yaml
from invis_alpha_os.config.paths import ROOT_DIR
from invis_alpha_os.config.jp_watchlist import (
    load_jp_watchlist_tickers,
    normalize_jquants_equity_code,
)
from invis_alpha_os.config.us_watchlist import normalize_us_symbol
from invis_alpha_os.data.jquants_daily_bars_cache import (
    save_jquants_daily_bars_cache,
    try_load_cached_daily_bars,
    utc_now_iso,
)
from invis_alpha_os.data.us_daily_bars_cache import save_us_daily_bars_cache
from invis_alpha_os.data.us_provider_preview import build_us_provider_preview_plan
from invis_alpha_os.data.us_provider_live_preview import (
    stooq_live_preview_sanitized_bars,
    stooq_live_preview_shape_digest,
)
from invis_alpha_os.data.us_provider_cache_preview_batch import (
    render_us_provider_cache_preview_batch_markdown,
    run_stooq_cache_preview_batch,
    symbols_from_us_watchlist_file,
)
from invis_alpha_os.data.us_provider_manual_live_batch_smoke import (
    build_us_provider_manual_live_batch_smoke_payload,
    render_manual_live_batch_smoke_markdown,
)
from invis_alpha_os.data.us_provider_scheduled_ingest_plan import (
    build_us_provider_scheduled_ingest_plan,
    merged_symbols_for_scheduled_ingest_plan,
    render_us_provider_scheduled_ingest_plan_markdown,
)
from invis_alpha_os.data.adapters import (
    EdinetStubAdapter,
    JQuantsClient,
    JQuantsStubAdapter,
    SecStubAdapter,
    YFinanceFallbackAdapter,
)
from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.portfolio.shadow_portfolio import ShadowPortfolioService
from invis_alpha_os.reporting.jquants_smoke_summary import (
    build_watchlist_filename_date_slug,
    build_watchlist_smoke_summary_document,
    save_watchlist_smoke_summary_payload,
)
from invis_alpha_os.reports.jquants_watchlist_daily import render_jquants_watchlist_bars_check_section
from invis_alpha_os.reports.momentum_daily import (
    render_momentum_signals_cache_only_section,
    render_momentum_signals_mixed_section,
    render_us_momentum_cache_only_section,
)
from invis_alpha_os.risk.veto_rules import VetoEngine
from invis_alpha_os.signals.momentum import (
    analyze_bars_for_code,
    build_momentum_signals,
    load_bars_json_file,
    momentum_row_public_dict,
    synthetic_bars_for_code,
)
from invis_alpha_os.utils.date_utils import today_jst_iso

app = typer.Typer(help="Laputa Alpha OS CLI (Phase 0-v1.1)")
snapshot_app = typer.Typer(help="Snapshot commands")
log_app = typer.Typer(help="Log commands")
debug_app = typer.Typer(help="Debug commands")

app.add_typer(snapshot_app, name="snapshot")
app.add_typer(log_app, name="log")
app.add_typer(debug_app, name="debug")


def _obs_service() -> ObservationService:
    return ObservationService(
        observation_path=OUTPUTS_DIR / "observation_log" / "observation_log.jsonl",
        outcome_path=OUTPUTS_DIR / "outcome_log" / "outcome_log.jsonl",
    )


def _jp_watchlist_count(jp_rows: object) -> int:
    if not isinstance(jp_rows, list):
        return 0
    total = 0
    for row in jp_rows:
        if isinstance(row, str) and row.strip():
            total += 1
        elif isinstance(row, dict) and str(row.get("ticker", "")).strip():
            total += 1
    return total


def _jquants_report_settings() -> dict[str, Any]:
    data = load_yaml(CONFIG_DIR / "market_data.yaml")
    md = data.get("market_data")
    if not isinstance(md, dict):
        return {}
    adapters = md.get("adapters")
    if not isinstance(adapters, dict):
        return {}
    jq = adapters.get("jquants")
    if not isinstance(jq, dict):
        return {}
    rep = jq.get("report")
    return dict(rep) if isinstance(rep, dict) else {}


def _daily_report_momentum_sections_flags() -> tuple[bool, bool, bool]:
    """JP cache/mixed gates + optional US cache-only gate (default off)."""

    cfg = load_yaml(CONFIG_DIR / "market_data.yaml")
    dr = cfg.get("daily_report")
    if not isinstance(dr, dict):
        return (True, True, False)

    def _as_bool(raw: object, default: bool) -> bool:
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            stripped = raw.strip().lower()
            if stripped in ("true", "1", "yes", "on"):
                return True
            if stripped in ("false", "0", "no", "off", ""):
                return False
        return default

    cache_on = _as_bool(dr.get("include_momentum_cache_only_section", True), default=True)
    mixed_on = _as_bool(dr.get("include_momentum_mixed_section", True), default=True)
    us_on = _as_bool(dr.get("include_us_momentum_cache_only_section", False), default=False)
    return cache_on, mixed_on, us_on


@app.command("status")
def status() -> None:
    typer.echo("Laputa Alpha OS")
    typer.echo("Current Mode: Observation Only + Shadow Portfolio")
    typer.echo("No Auto Trading")


@app.command("config-check")
def config_check() -> None:
    required = [
        "watchlist.yaml",
        "peer_map.yaml",
        "weights.yaml",
        "veto_rules.yaml",
        "market_risk_indicators.yaml",
        "account_rules.yaml",
        "data_confidence.yaml",
        "market_data.yaml",
        "us_watchlist.yaml",
        "us_market_data.yaml",
    ]
    missing = [name for name in required if not (CONFIG_DIR / name).exists()]
    if missing:
        raise typer.Exit(code=1)
    typer.echo("config-check: OK")


@app.command("us-watchlist-preview")
def us_watchlist_preview_command() -> None:
    """Print normalized US observation-universe symbols (no HTTP)."""

    from invis_alpha_os.config.us_watchlist import load_us_watchlist_tickers

    typer.echo("US watchlist symbols:")
    for s in load_us_watchlist_tickers():
        typer.echo(s)


@app.command("daily")
def daily() -> None:
    today = today_jst_iso()
    out = OUTPUTS_DIR / "reports" / "daily" / f"{today}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    watchlist = load_yaml(CONFIG_DIR / "watchlist.yaml")
    jp_n = _jp_watchlist_count(watchlist.get("jp_watchlist", []))
    jquants = JQuantsStubAdapter()
    if jquants.is_enabled():
        jq_line = "J-Quants stub enabled (Phase 1a; no live API yet)"
    else:
        jq_line = "J-Quants disabled / not configured"

    rep_cfg = _jquants_report_settings()
    jq_watchlist_section = ""
    if rep_cfg.get("include_watchlist_bars_check", True):
        jq_watchlist_section = "\n\n" + render_jquants_watchlist_bars_check_section(rep_cfg)

    inc_cache, inc_mixed, inc_us = _daily_report_momentum_sections_flags()
    momentum_sections: list[str] = []
    if inc_cache:
        momentum_sections.append(render_momentum_signals_cache_only_section())
    if inc_mixed:
        momentum_sections.append(render_momentum_signals_mixed_section())
    if inc_us:
        momentum_sections.append(render_us_momentum_cache_only_section())

    momentum_blob = "\n\n".join(momentum_sections)
    if jq_watchlist_section and momentum_blob:
        tail = jq_watchlist_section + "\n\n" + momentum_blob
    elif jq_watchlist_section:
        tail = jq_watchlist_section
    elif momentum_blob:
        tail = "\n\n" + momentum_blob
    else:
        tail = ""
    out.write_text(
        "\n".join(
            [
                f"# Daily Report ({today})",
                "",
                "Phase 0 dummy report.",
                "- Observation only",
                "- No auto trading",
                "",
                "## Japan Signals",
                "- Phase 1a stub",
                f"- {jq_line}",
                f"- Watchlist count: {jp_n}",
            ]
        )
        + tail,
        encoding="utf-8",
    )
    typer.echo(f"daily report created: {out}")


@app.command("signals")
def signals_command(
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="No live HTTP. synthetic/cache/cache-only use local or deterministic data only.",
    ),
    source: str = typer.Option(
        "synthetic",
        "--source",
        help="synthetic | cache | cache-only — cache prefers local JSON; cache-only ranks cached tickers only.",
    ),
    no_synthetic_fallback: bool = typer.Option(
        False,
        "--no-synthetic-fallback",
        help="With --source cache, skip tickers without cache (same as --source cache-only).",
    ),
    code: Optional[str] = typer.Option(None, "--code", help="Single ticker (requires --bars-file)."),
    bars_file: Optional[str] = typer.Option(
        None,
        "--bars-file",
        help="Path to JSON array of one OHLCV series (open,high,low,close,volume,date).",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        min=1,
        help="Process only the first N JP watchlist tickers (dry-run).",
    ),
) -> None:
    """Observation-only JP momentum-style flags from daily bars (Main E MVP). Not trading advice."""

    src_norm = source.strip().lower().replace("_", "-")
    if src_norm == "cacheonly":
        src_norm = "cache-only"

    if no_synthetic_fallback:
        if src_norm == "cache":
            src_norm = "cache-only"
        elif src_norm != "cache-only":
            typer.echo(
                "signals: --no-synthetic-fallback is only valid with --source cache or cache-only",
                err=True,
            )
            raise typer.Exit(2)

    if src_norm not in ("synthetic", "cache", "cache-only"):
        typer.echo("signals: --source must be synthetic, cache, or cache-only", err=True)
        raise typer.Exit(2)

    if bars_file:
        if not code:
            typer.echo("signals: --bars-file requires --code", err=True)
            raise typer.Exit(2)
        try:
            label = normalize_generic_bars_file_symbol_label(code)
        except ValueError:
            typer.echo("signals: invalid --code for bars-file symbol label", err=True)
            raise typer.Exit(2)
        try:
            bars = load_bars_json_file(Path(bars_file))
        except (OSError, ValueError, json.JSONDecodeError) as e:
            typer.echo(f"signals: failed to load bars file: {e}", err=True)
            raise typer.Exit(2) from e
        one = analyze_bars_for_code(label, bars)
        payload: dict[str, Any] = {
            "mode": "local_bars_file",
            "bars_data_source": "file",
            "observation_only": True,
            "ranked": [momentum_row_public_dict(one, bars_source="file")] if one else [],
        }
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        raise typer.Exit(0)

    if src_norm == "synthetic" and not dry_run:
        typer.echo(
            "signals: --no-dry-run is not supported for --source synthetic; "
            "use --source cache (local files) or --bars-file + --code.",
            err=True,
        )
        raise typer.Exit(2)

    tickers = load_jp_watchlist_tickers()
    if limit is not None:
        tickers = tickers[:limit]
    mapping, srcmap, skipped_no_cache = _jp_momentum_bar_mapping(src_norm, tickers)
    ranked = build_momentum_signals(mapping)
    mode = "cache_only_dry_run" if src_norm == "cache-only" else (
        "synthetic_dry_run" if src_norm == "synthetic" else "cache_preferred_dry_run"
    )
    bars_label = "cache" if src_norm == "cache-only" else _bars_data_source_label(srcmap)
    out: dict[str, Any] = {
        "mode": mode,
        "bars_data_source": bars_label,
        "observation_only": True,
        "ranked": [
            momentum_row_public_dict(m, bars_source=srcmap.get(m.code, "synthetic")) for m in ranked
        ],
    }
    if src_norm == "cache-only":
        out["skipped_no_cache"] = len(skipped_no_cache)
        out["skipped_no_cache_codes"] = skipped_no_cache
    typer.echo(json.dumps(out, ensure_ascii=False, indent=2))


@app.command("pack")
def pack(ticker: str = typer.Option(..., "--ticker")) -> None:
    today = today_jst_iso()
    out = OUTPUTS_DIR / "research_packs" / f"{ticker}_{today}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "\n".join(
            [
                f"# Research Pack: {ticker}",
                "",
                "Phase 0 dummy pack.",
                "- Thesis: TODO",
                "- Evidence: TODO",
                "- Risks: TODO",
            ]
        ),
        encoding="utf-8",
    )
    typer.echo(f"research pack created: {out}")


@app.command("risks")
def risks() -> None:
    rules = load_yaml(CONFIG_DIR / "veto_rules.yaml")
    engine = VetoEngine(rules=rules)
    demo = engine.evaluate({"market_heat": 0.95, "valuation_stretch": 0.7})
    typer.echo("risk scan (phase 0 stub):")
    typer.echo(f"triggered veto count: {len(demo)}")


@snapshot_app.command("watchlist")
def snapshot_watchlist() -> None:
    watchlist = load_yaml(CONFIG_DIR / "watchlist.yaml")
    jp_count = _jp_watchlist_count(watchlist.get("jp_watchlist", []))
    us = watchlist.get("us_watchlist", {})
    t1 = len(us.get("tier_1_core", []))
    t2 = len(us.get("tier_2_theme_peers", []))
    t3 = len(us.get("tier_3_optional", []))
    typer.echo(f"JP: {jp_count}, US tier1: {t1}, tier2: {t2}, tier3: {t3}")


@snapshot_app.command("shadow-portfolio")
def snapshot_shadow_portfolio() -> None:
    service = ShadowPortfolioService(OUTPUTS_DIR / "shadow_portfolio" / "positions.jsonl")
    positions = service.list_positions()
    typer.echo(f"shadow positions: {len(positions)}")


@log_app.command("outcome")
def log_outcome(
    symbol: str = typer.Option(..., "--symbol"),
    result: str = typer.Option("unknown", "--result"),
    note: Optional[str] = typer.Option(None, "--note"),
) -> None:
    row = _obs_service().log_outcome(symbol=symbol, result=result, note=note)
    typer.echo(f"outcome logged: {row.id}")


@debug_app.command("adapters")
def debug_adapters() -> None:
    adapters = [YFinanceFallbackAdapter(), JQuantsStubAdapter(), EdinetStubAdapter(), SecStubAdapter()]
    for adapter in adapters:
        typer.echo(str(adapter.health()))


@debug_app.command("jquants-status")
def debug_jquants_status() -> None:
    client = JQuantsClient.from_env()
    typer.echo(json.dumps(client.safe_auth_status(), ensure_ascii=False, indent=2))
    typer.echo(
        "(never performs HTTP; see api_version, auth_method, api_key_present, unsupported_api_version, "
        "base_url_present, allow_live_http, configured)"
    )


def _cli_optional_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _jp_momentum_bar_mapping(
    source: str, tickers: list[str]
) -> tuple[dict[str, list], dict[str, str], list[str]]:
    """Build code→bars for momentum; ``skipped_no_cache`` lists wire codes with no cache file (cache-only)."""

    mapping: dict[str, list] = {}
    srcmap: dict[str, str] = {}
    skipped_no_cache: list[str] = []
    for raw in tickers:
        w = normalize_jquants_equity_code(str(raw))
        if w is None:
            continue
        if source == "synthetic":
            mapping[w] = synthetic_bars_for_code(w)
            srcmap[w] = "synthetic"
        elif source == "cache":
            got = try_load_cached_daily_bars(w)
            if got is not None:
                mapping[w], srcmap[w] = got
            else:
                mapping[w] = synthetic_bars_for_code(w)
                srcmap[w] = "synthetic"
        elif source == "cache-only":
            got = try_load_cached_daily_bars(w)
            if got is not None:
                mapping[w], srcmap[w] = got
            else:
                skipped_no_cache.append(w)
        else:
            raise ValueError(f"unexpected signals source: {source!r}")
    return mapping, srcmap, skipped_no_cache


def _bars_data_source_label(srcmap: dict[str, str]) -> str:
    u = set(srcmap.values())
    if u == {"cache"}:
        return "cache"
    if u == {"synthetic"}:
        return "synthetic"
    if not u:
        return "synthetic"
    return "mixed"


def _jquants_daily_quotes_cli_snapshot(
    result: dict[str, Any],
    *,
    code: Optional[str],
    from_date: Optional[str],
    to_date: Optional[str],
    date_opt: Optional[str],
) -> dict[str, Any]:
    """Public fields only — no raw body; ``error_body_preview`` is masked/short when present."""

    st = result.get("status")
    snap: dict[str, Any] = {
        "status": st,
        "code": code,
        "date": date_opt,
        "date_from": from_date,
        "date_to": to_date,
    }

    if st == "validation_error":
        r = result.get("reason")
        if isinstance(r, str):
            snap["reason"] = r
        for k in ("data_available_from", "data_available_to"):
            if k in result:
                snap[k] = result[k]
        return snap

    if st == "success":
        snap["row_count"] = result.get("row_count")
        snap["source_key"] = result.get("source_key")
        return snap

    if st == "dry_run":
        ep = result.get("endpoint")
        if ep:
            snap["endpoint"] = ep
        for k in (
            "endpoint_url_without_query",
            "query_params",
            "full_url_without_secrets",
            "api_key_header_name",
            "api_key_header_present",
            "api_key_value_included",
        ):
            if k in result:
                snap[k] = result[k]
        return snap

    if st == "http_error":
        snap["http_status"] = result.get("http_status")
        if snap["http_status"] is None and isinstance(result.get("code"), int):
            snap["http_status"] = result["code"]
        for k in (
            "endpoint_url_without_query",
            "query_params",
            "full_url_without_secrets",
            "api_key_header_present",
            "api_key_header_name",
            "api_key_value_included",
            "raw_response_included",
            "error_body_preview",
        ):
            if k in result:
                snap[k] = result[k]
        return snap

    for k in ("reason", "endpoint_path", "missing"):
        if k in result:
            snap[k] = result[k]

    return snap


def _watchlist_preview_row(code: str, prv: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {"code": code}
    st = prv.get("status")
    row["status"] = st
    if st == "validation_error":
        if isinstance(prv.get("reason"), str):
            row["reason"] = prv["reason"]
        for k in ("data_available_from", "data_available_to"):
            if k in prv:
                row[k] = prv[k]
        row["raw_response_included"] = prv.get("raw_response_included", False)
        return row
    for k in (
        "endpoint_url_without_query",
        "query_params",
        "full_url_without_secrets",
        "api_key_header_name",
        "api_key_header_present",
        "api_key_value_included",
        "reason",
    ):
        if k in prv:
            row[k] = prv[k]
    row["raw_response_included"] = prv.get("raw_response_included", False)
    return row


def _result_row_no_raw(row: dict[str, Any]) -> dict[str, Any]:
    if "raw_response_included" not in row:
        row["raw_response_included"] = False
    return row


def _watchlist_bars_cache_row(
    *,
    code: str,
    status: str,
    row_count: Any = None,
    sanitized_bar_count: Any = None,
    cache_written_to: Any = None,
    reason: Any = None,
    full_url_without_secrets: Any = None,
    http_status: Any = None,
    error_body_preview: Any = None,
) -> dict[str, Any]:
    """Public summary row for ``jquants-watchlist-bars-cache`` (optional safe preview URL in dry-run)."""

    row: dict[str, Any] = {
        "code": code,
        "status": status,
        "row_count": row_count,
        "sanitized_bar_count": sanitized_bar_count,
        "cache_written_to": cache_written_to,
        "reason": reason,
    }
    if full_url_without_secrets is not None:
        row["full_url_without_secrets"] = full_url_without_secrets
    if http_status is not None:
        row["http_status"] = http_status
    if error_body_preview is not None:
        row["error_body_preview"] = error_body_preview
    return _result_row_no_raw(row)


def _reason_from_snap_for_row(status_str: str, snap: dict[str, Any], result: dict[str, Any]) -> str:
    """Non-empty public reason for error rows (never raw API body)."""

    r = snap.get("reason")
    if isinstance(r, str) and r.strip():
        return r
    rx = result.get("reason")
    if isinstance(rx, str) and rx.strip():
        return rx
    if status_str == "http_error":
        hs = snap.get("http_status")
        if hs is None and isinstance(snap.get("code"), int):
            hs = int(snap["code"])
        if isinstance(hs, int):
            return f"http_status_{hs}"
        ebp = snap.get("error_body_preview")
        if isinstance(ebp, str) and ebp.strip():
            return "http_error_masked_preview"
        return "http_error_unknown"
    return status_str


def _watchlist_bars_cache_row_from_snap(code: str, snap: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    st = str(snap.get("status") or result.get("status") or "error")
    reason = _reason_from_snap_for_row(st, snap, result)
    row: dict[str, Any] = {
        "code": code,
        "status": st,
        "row_count": snap.get("row_count"),
        "sanitized_bar_count": None,
        "cache_written_to": None,
        "reason": reason,
    }
    if st == "http_error":
        hs = snap.get("http_status")
        if hs is None and isinstance(result.get("code"), int):
            hs = int(result["code"])
        if isinstance(hs, int):
            row["http_status"] = hs
        # Bulk summary: omit body-derived previews; use http_status + reason only (Main L gate).
        row["raw_response_included"] = False
    else:
        row["raw_response_included"] = bool(snap.get("raw_response_included", False))
    return _result_row_no_raw(row)


def _parse_codes_csv(codes: Optional[str]) -> tuple[list[str], list[str]] | None:
    """Return ``(wire_codes, skipped_raw_tokens)`` or ``None`` if ``codes`` is empty."""

    if codes is None or not str(codes).strip():
        return None
    wire_out: list[str] = []
    skipped: list[str] = []
    for part in str(codes).split(","):
        p = part.strip()
        if not p:
            continue
        w = normalize_jquants_equity_code(p)
        if w is None:
            skipped.append(p)
        else:
            wire_out.append(w)
    return (wire_out, skipped)


def _norm_watchlist_codes_csv_requested(codes_csv: Optional[str]) -> Optional[str]:
    if codes_csv is None or not str(codes_csv).strip():
        return None
    parts = [p.strip() for p in str(codes_csv).split(",") if p.strip()]
    if not parts:
        return None
    return ",".join(parts)


def _resolve_watchlist_bars_cache_tickers(
    *,
    codes_csv: Optional[str],
    limit: Optional[int],
) -> tuple[list[str], list[str]]:
    """Return ``(tickers, skipped_unsupported_from_codes_csv)``."""

    parsed = _parse_codes_csv(codes_csv)
    if parsed is not None:
        wire_list, skipped = parsed
        tickers = wire_list if limit is None else wire_list[:limit]
        return tickers, skipped
    tickers_all = load_jp_watchlist_tickers()
    tickers = tickers_all if limit is None else tickers_all[:limit]
    return tickers, []


def _maybe_save_watchlist_smoke_summary(
    out: dict[str, Any],
    *,
    save_summary: bool,
    preview_request: bool,
    date_opt: Optional[str],
    from_date: Optional[str],
    to_date: Optional[str],
    limit: Optional[int],
) -> dict[str, Any]:
    if not save_summary or preview_request:
        return out
    slug = build_watchlist_filename_date_slug(date_opt, from_date, to_date)
    lim = str(limit) if limit is not None else "all"
    payload = build_watchlist_smoke_summary_document(out)
    main_rel, latest_rel = save_watchlist_smoke_summary_payload(payload, date_slug=slug, limit_display=lim)
    merged = dict(out)
    merged["summary_saved_to"] = main_rel
    merged["latest_summary_saved_to"] = latest_rel
    return merged


@debug_app.command("jquants-watchlist-bars")
def debug_jquants_watchlist_bars(
    date: Optional[str] = typer.Option(
        None,
        "--date",
        help="Single day YYYY-MM-DD or YYYYMMDD (mutually exclusive with --from-date/--to-date).",
    ),
    from_date: Optional[str] = typer.Option(None, "--from-date", help="Range start (requires --to-date for paired use)."),
    to_date: Optional[str] = typer.Option(None, "--to-date", help="Range end (requires --from-date for paired use)."),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        min=1,
        help="Process only the first N tickers from jp_watchlist (order preserved).",
    ),
    live: bool = typer.Option(False, "--live", help="Perform live HTTP when all gates allow it."),
    preview_request: bool = typer.Option(False, "--preview-request", help="Show V2 request preview per ticker; never HTTP."),
    save_summary: bool = typer.Option(
        False,
        "--save-summary",
        help="Write sanitized summary JSON under outputs/jquants_smoke/ (not used with --preview-request).",
    ),
) -> None:
    """Batch daily-bars check for ``jp_watchlist`` (Phase 1a Task 6). Default: dry-run. Task 9.1 smoke JSON splits ``dry_run_count`` vs ``error_count``."""

    client = JQuantsClient.from_env()
    dn = _cli_optional_str(date)
    fn = _cli_optional_str(from_date)
    tn = _cli_optional_str(to_date)

    if (fn is not None) ^ (tn is not None):
        view = _jquants_daily_quotes_cli_snapshot(
            {
                "status": "validation_error",
                "reason": "watchlist_range_requires_both_from_and_to",
                "raw_response_included": False,
            },
            code=None,
            from_date=fn,
            to_date=tn,
            date_opt=dn,
        )
        typer.echo(json.dumps(view, ensure_ascii=False, indent=2))
        raise typer.Exit(1)

    verr = client.validate_daily_quotes_cli_args(None, date=dn, from_date=fn, to_date=tn)
    if verr is not None:
        view = _jquants_daily_quotes_cli_snapshot(verr, code=None, from_date=fn, to_date=tn, date_opt=dn)
        typer.echo(json.dumps(view, ensure_ascii=False, indent=2))
        raise typer.Exit(1)

    try:
        tickers_all = load_jp_watchlist_tickers()
    except (FileNotFoundError, ValueError, OSError) as e:
        typer.echo(json.dumps({"status": "error", "detail": str(e), "raw_response_included": False}, ensure_ascii=False, indent=2))
        raise typer.Exit(1) from e

    tickers = tickers_all if limit is None else tickers_all[:limit]
    base_meta: dict[str, Any] = {
        "date": dn,
        "date_from": fn,
        "date_to": tn,
        "target_count": len(tickers),
        "raw_response_included": False,
    }

    results: list[dict[str, Any]] = []

    if preview_request:
        for code in tickers:
            wire = normalize_jquants_equity_code(code)
            if wire is None:
                results.append(
                    _result_row_no_raw(
                        {"code": (code or "").strip(), "status": "skipped_unsupported_code", "raw_response_included": False}
                    )
                )
                continue
            prv = client.build_v2_daily_bars_request_preview(wire, date=dn, from_date=fn, to_date=tn)
            results.append(_result_row_no_raw(_watchlist_preview_row(wire, prv)))
        out = {"status": "preview", **base_meta, "results": results}
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
        raise typer.Exit(0)

    if not live and not client.is_enabled():
        out = {
            "status": "disabled",
            "reason": "JQUANTS_ENABLED=false",
            **base_meta,
            "results": [],
        }
        out = _maybe_save_watchlist_smoke_summary(
            out,
            save_summary=save_summary,
            preview_request=False,
            date_opt=dn,
            from_date=fn,
            to_date=tn,
            limit=limit,
        )
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
        raise typer.Exit(0)

    for code in tickers:
        wire = normalize_jquants_equity_code(code)
        if wire is None:
            results.append(_result_row_no_raw({"code": (code or "").strip(), "status": "skipped_unsupported_code"}))
            continue
        res = client.get_daily_quotes(wire, date=dn, from_date=fn, to_date=tn, attempt_live=live)
        snap = _jquants_daily_quotes_cli_snapshot(res, code=wire, from_date=fn, to_date=tn, date_opt=dn)
        results.append(_result_row_no_raw(snap))

    if not live:
        out = {"status": "dry_run", **base_meta, "results": results}
        out = _maybe_save_watchlist_smoke_summary(
            out,
            save_summary=save_summary,
            preview_request=False,
            date_opt=dn,
            from_date=fn,
            to_date=tn,
            limit=limit,
        )
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
        raise typer.Exit(0)

    non_skip = [r for r in results if r.get("status") != "skipped_unsupported_code"]
    success_count = sum(1 for r in non_skip if r.get("status") == "success")
    error_count = len(non_skip) - success_count
    out = {
        "status": "completed",
        **base_meta,
        "success_count": success_count,
        "error_count": error_count,
        "results": results,
    }
    out = _maybe_save_watchlist_smoke_summary(
        out,
        save_summary=save_summary,
        preview_request=False,
        date_opt=dn,
        from_date=fn,
        to_date=tn,
        limit=limit,
    )
    typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
    if error_count == 0:
        raise typer.Exit(0)
    raise typer.Exit(1)


@debug_app.command("jquants-daily-quotes")
def debug_jquants_daily_quotes(
    code: Optional[str] = typer.Option(None, "--code", help="Equity code (optional; V2 accepts code-only queries)."),
    from_date: Optional[str] = typer.Option(
        None,
        "--from-date",
        help="Range start (YYYY-MM-DD or YYYYMMDD); sent as query `from` on V2 as YYYYMMDD.",
    ),
    to_date: Optional[str] = typer.Option(
        None,
        "--to-date",
        help="Range end (YYYY-MM-DD or YYYYMMDD); sent as query `to` on V2 as YYYYMMDD.",
    ),
    date: Optional[str] = typer.Option(
        None,
        "--date",
        help="Single day (YYYY-MM-DD or YYYYMMDD); query `date` on V2 as YYYYMMDD. Mutually exclusive with from/to.",
    ),
    live: bool = typer.Option(False, "--live", help="Allow live HTTP (requires JQUANTS_ALLOW_LIVE_HTTP=true)"),
    preview_request: bool = typer.Option(
        False,
        "--preview-request",
        help="Print V2 safe request preview only (never performs HTTP).",
    ),
) -> None:
    client = JQuantsClient.from_env()

    cn = _cli_optional_str(code)
    dn = _cli_optional_str(date)
    fn = _cli_optional_str(from_date)
    tn = _cli_optional_str(to_date)

    verr = client.validate_daily_quotes_cli_args(cn, date=dn, from_date=fn, to_date=tn)
    if verr is not None:
        view = _jquants_daily_quotes_cli_snapshot(verr, code=cn, from_date=fn, to_date=tn, date_opt=dn)
        typer.echo(json.dumps(view, ensure_ascii=False, indent=2))
        raise typer.Exit(1)

    if preview_request:
        prv = client.build_v2_daily_bars_request_preview(cn, date=dn, from_date=fn, to_date=tn)
        typer.echo(json.dumps(prv, ensure_ascii=False, indent=2))
        raise typer.Exit(0)

    if not client.is_enabled():
        view = _jquants_daily_quotes_cli_snapshot(
            {"status": "disabled", "reason": "JQUANTS_ENABLED=false"},
            code=cn,
            from_date=fn,
            to_date=tn,
            date_opt=dn,
        )
        typer.echo(json.dumps(view, ensure_ascii=False, indent=2))
        raise typer.Exit(1 if live else 0)

    result = client.get_daily_quotes(cn, date=dn, from_date=fn, to_date=tn, attempt_live=live)
    view = _jquants_daily_quotes_cli_snapshot(result, code=cn, from_date=fn, to_date=tn, date_opt=dn)
    typer.echo(json.dumps(view, ensure_ascii=False, indent=2))
    if not live:
        raise typer.Exit(0)
    if result.get("status") == "success":
        raise typer.Exit(0)
    raise typer.Exit(1)


@debug_app.command("jquants-daily-bars-cache")
def debug_jquants_daily_bars_cache(
    code: str = typer.Option(..., "--code", help="Equity code (normalized digits/letters)."),
    from_date: str = typer.Option(
        ...,
        "--from-date",
        help="Range start YYYY-MM-DD or YYYYMMDD (pairs with --to-date).",
    ),
    to_date: str = typer.Option(
        ...,
        "--to-date",
        help="Range end YYYY-MM-DD or YYYYMMDD (pairs with --from-date).",
    ),
    live: bool = typer.Option(False, "--live", help="Perform live HTTP when gates allow."),
    write_cache: bool = typer.Option(
        False,
        "--write-cache",
        help="After live success, write sanitized rows to outputs/market_data/jquants_daily_bars/{code}.json.",
    ),
    debug_shape: bool = typer.Option(
        False,
        "--debug-shape",
        help="With --live (+ CONFIRM_LIVE_HTTP=YES), include safe shape_digest on sanitized_empty; never writes cache.",
    ),
) -> None:
    """Dry-run request preview by default. Live + side effects need CONFIRM_LIVE_HTTP=YES."""

    client = JQuantsClient.from_env()
    cn_raw = code.strip()
    w = normalize_jquants_equity_code(cn_raw)
    if w is None:
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "invalid_equity_code",
                    "code": cn_raw,
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise typer.Exit(1)
    cn = w
    fn = from_date.strip()
    tn = to_date.strip()

    if debug_shape and not live:
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "debug_shape_requires_live",
                    "detail": "Use --live with --debug-shape (and CONFIRM_LIVE_HTTP=YES) for HTTP shape diagnostics.",
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            err=True,
        )
        raise typer.Exit(2)

    if write_cache and not live:
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "write_cache_requires_live",
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise typer.Exit(2)

    verr = client.validate_daily_quotes_cli_args(cn, date=None, from_date=fn, to_date=tn)
    if verr is not None:
        view = _jquants_daily_quotes_cli_snapshot(verr, code=cn, from_date=fn, to_date=tn, date_opt=None)
        typer.echo(json.dumps(view, ensure_ascii=False, indent=2))
        raise typer.Exit(1)

    if not live:
        prv = client.build_v2_daily_bars_request_preview(cn, from_date=fn, to_date=tn)
        out = {**prv, "live_http": False, "write_cache": False, "raw_response_included": False}
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
        raise typer.Exit(0 if prv.get("status") == "ok" else 1)

    if live and (write_cache or debug_shape) and os.environ.get("CONFIRM_LIVE_HTTP") != "YES":
        typer.echo(
            json.dumps(
                {
                    "status": "live_blocked",
                    "reason": "confirm_live_http_required",
                    "detail": "Set CONFIRM_LIVE_HTTP=YES for --write-cache and/or --debug-shape live HTTP.",
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            err=True,
        )
        raise typer.Exit(2)

    want_sanitize = write_cache or debug_shape
    result = client.get_daily_quotes(
        cn,
        from_date=fn,
        to_date=tn,
        attempt_live=True,
        return_sanitized_bars=want_sanitize,
        include_shape_digest=debug_shape,
    )
    effective_write = write_cache and not debug_shape

    if want_sanitize and result.get("status") == "sanitized_empty":
        payload: dict[str, Any] = {
            "status": "sanitized_empty",
            "reason": result.get("reason"),
            "code": cn,
            "row_count": result.get("row_count"),
            "source_key": result.get("source_key"),
            "detail": "API returned rows but none mapped to OHLCV; cache not written.",
            "raw_response_included": False,
        }
        sd = result.get("shape_digest")
        if sd is not None:
            payload["shape_digest"] = sd
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2), err=True)
        raise typer.Exit(1)

    if effective_write and result.get("status") == "success":
        bars = result.get("sanitized_bars")
        if not isinstance(bars, list):
            bars = []
        if not bars:
            typer.echo(
                json.dumps(
                    {
                        "status": "success",
                        "code": cn,
                        "row_count": result.get("row_count"),
                        "sanitized_bar_count": 0,
                        "cache_written_to": None,
                        "cache_skipped": "no_sanitized_rows",
                        "raw_response_included": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            raise typer.Exit(0)
        path = save_jquants_daily_bars_cache(
            cn,
            bars,
            source="jquants_v2_equities_bars_daily",
            fetched_at=utc_now_iso(),
            generated_at=None,
        )
        snap = {
            "status": "success",
            "code": cn,
            "row_count": result.get("row_count"),
            "sanitized_bar_count": len(bars),
            "cache_written_to": str(path.relative_to(ROOT_DIR)).replace("\\", "/"),
            "raw_response_included": False,
        }
        typer.echo(json.dumps(snap, ensure_ascii=False, indent=2))
        raise typer.Exit(0)

    view = _jquants_daily_quotes_cli_snapshot(result, code=cn, from_date=fn, to_date=tn, date_opt=None)
    view["write_cache"] = False
    view["debug_shape"] = debug_shape
    typer.echo(json.dumps(view, ensure_ascii=False, indent=2))
    raise typer.Exit(0 if result.get("status") == "success" else 1)


@debug_app.command("us-daily-bars-cache-import")
def debug_us_daily_bars_cache_import(
    symbol: str = typer.Option(..., "--symbol", help="US symbol (normalized for cache filename)."),
    bars_file: Path = typer.Option(..., "--bars-file", help="JSON array of sanitized OHLCV rows."),
    asset_class: Optional[str] = typer.Option(
        None,
        "--asset-class",
        help="Optional persisted label (e.g. us_equity, us_etf).",
    ),
    source: str = typer.Option(
        "local_fixture",
        "--source",
        help="Stored in cache JSON metadata (must not resemble secrets).",
    ),
    write_cache: bool = typer.Option(
        False,
        "--write-cache",
        help="Write outputs/market_data/us_daily_bars/{symbol}.json; default is preview only.",
    ),
) -> None:
    """Import local US OHLCV JSON into on-disk cache (no HTTP)."""

    norm = normalize_us_symbol(symbol.strip())
    if norm is None:
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "invalid_symbol",
                    "symbol_input": symbol,
                    "live_http": False,
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            err=True,
        )
        raise typer.Exit(2)

    p = Path(bars_file)
    if not p.is_file():
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "bars_file_not_found",
                    "path": str(p),
                    "live_http": False,
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            err=True,
        )
        raise typer.Exit(2)

    try:
        bars = load_bars_json_file(p)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "bars_parse_failed",
                    "detail": (
                        "Expected a UTF-8 JSON array of sanitized OHLCV objects "
                        "(date, open, high, low, close, volume)."
                    ),
                    "live_http": False,
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            err=True,
        )
        raise typer.Exit(2)

    rows: list[dict[str, Any]] = [dict(b) for b in bars]
    rel = f"outputs/market_data/us_daily_bars/{norm}.json"

    ac = asset_class.strip() if isinstance(asset_class, str) and asset_class.strip() else None

    if not write_cache:
        typer.echo(
            json.dumps(
                {
                    "status": "dry_run",
                    "symbol": norm,
                    "bar_count": len(rows),
                    "cache_would_write_to": rel,
                    "live_http": False,
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise typer.Exit(0)

    try:
        path = save_us_daily_bars_cache(
            norm,
            rows,
            asset_class=ac,
            source=source.strip(),
            fetched_at=utc_now_iso(),
        )
    except ValueError as e:
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "refused_cache_write",
                    "detail": str(e),
                    "live_http": False,
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            err=True,
        )
        raise typer.Exit(2) from e

    try:
        rel_path = path.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        rel_path = path.relative_to(path.anchor).as_posix() if path.is_absolute() else path.as_posix()
        markers = ("outputs/market_data/us_daily_bars/", "market_data/us_daily_bars/")
        if not any(rel_path.startswith(p) for p in markers):
            rel_path = f"outputs/market_data/us_daily_bars/{norm}.json"

    typer.echo(
        json.dumps(
            {
                "status": "success",
                "symbol": norm,
                "bar_count": len(rows),
                "cache_written_to": rel_path,
                "live_http": False,
                "raw_response_included": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@debug_app.command("us-provider-preview")
def debug_us_provider_preview(
    symbol: str = typer.Option(..., "--symbol", help="US symbol (normalized for preview/cache path)."),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        help="alpha_vantage_preview | stooq_preview | manual_file (defaults to config/us_market_data.yaml).",
    ),
) -> None:
    """Emit JSON URL/query preview for a planned US provider (Main R2; no HTTP)."""

    payload = build_us_provider_preview_plan(symbol, provider)
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload.get("status") != "preview_ok":
        raise typer.Exit(2)


@debug_app.command("us-provider-live-preview")
def debug_us_provider_live_preview(
    symbol: str = typer.Option(..., "--symbol", help="Single US symbol (Main R3: MSFT smoke path)."),
    provider: str = typer.Option(
        ...,
        "--provider",
        help="stooq_preview only (Main R3).",
    ),
    live: bool = typer.Option(
        False,
        "--live",
        help="Perform one gated HTTP GET (requires CONFIRM_US_LIVE_HTTP=YES). Default: dry_run, no HTTP.",
    ),
) -> None:
    """Stooq-only shape digest preview. No cache write; never emits raw CSV."""

    prov = provider.strip()
    if prov != "stooq_preview":
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "unsupported_provider",
                    "provider_input": prov,
                    "detail": "Main R3 implements stooq_preview only.",
                    "live_http_performed": False,
                    "raw_response_included": False,
                    "cache_write_performed": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        raise typer.Exit(2)

    payload = stooq_live_preview_shape_digest(symbol, live=live)
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    st = payload.get("status")
    if st == "dry_run" or st == "live_preview_ok":
        raise typer.Exit(0)
    if st == "validation_error":
        raise typer.Exit(2)
    raise typer.Exit(1)


@debug_app.command("us-provider-cache-preview")
def debug_us_provider_cache_preview(
    symbol: str = typer.Option(..., "--symbol", help="Single US symbol (Main R4: MSFT smoke path)."),
    provider: str = typer.Option(
        ...,
        "--provider",
        help="stooq_preview only (Main R4).",
    ),
    live: bool = typer.Option(
        False,
        "--live",
        help="Perform one gated Stooq HTTP GET (requires CONFIRM_US_LIVE_HTTP=YES).",
    ),
    write_cache: bool = typer.Option(
        False,
        "--write-cache",
        help="Persist sanitized bars (requires CONFIRM_US_CACHE_WRITE=YES; implies successful parse after live GET).",
    ),
) -> None:
    """Stooq → strict sanitized OHLCV; optional gated cache write. Never emits raw CSV."""

    prov = provider.strip()
    if prov != "stooq_preview":
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "unsupported_provider",
                    "provider_input": prov,
                    "detail": "Main R4 implements stooq_preview only.",
                    "live_http_performed": False,
                    "raw_response_included": False,
                    "cache_write_performed": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        raise typer.Exit(2)

    payload = stooq_live_preview_sanitized_bars(symbol, live=live, write_cache=write_cache)
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    st = payload.get("status")
    if st in ("dry_run", "preview_ok", "success"):
        raise typer.Exit(0)
    if st == "validation_error":
        raise typer.Exit(2)
    raise typer.Exit(1)


@debug_app.command("us-provider-cache-preview-batch")
def debug_us_provider_cache_preview_batch(
    symbols_csv: Optional[str] = typer.Option(
        None,
        "--symbols",
        help="Comma-separated US symbols (merged after --from-watchlist when both set).",
    ),
    from_watchlist: bool = typer.Option(
        False,
        "--from-watchlist",
        help="Include symbols from config/us_watchlist.yaml (normalized; YAML-native dedupe).",
    ),
    provider: str = typer.Option("stooq_preview", "--provider", help="stooq_preview only (Main R5)."),
    live: bool = typer.Option(
        False,
        "--live",
        help="Perform gated Stooq HTTP GET per symbol (requires CONFIRM_US_LIVE_HTTP=YES). Operator-only.",
    ),
    write_cache: bool = typer.Option(
        False,
        "--write-cache",
        help="Batch rejects cache writes Main R5; use debug us-provider-cache-preview.",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        min=1,
        help="Maximum normalized symbols processed after merging inputs (invalid rows unaffected).",
    ),
    markdown: bool = typer.Option(
        False,
        "--markdown",
        help="Emit copy-ready Markdown recap (counts only; JSON canonical for results[]). Main R5.3.",
    ),
) -> None:
    """Multi-symbol Stooq cache preview aggregation (dry-run default; optional gated live loop)."""

    merged: list[str] = []
    if from_watchlist:
        merged.extend(symbols_from_us_watchlist_file())
    if symbols_csv:
        merged.extend([p.strip() for p in str(symbols_csv).split(",") if p.strip()])
    out = run_stooq_cache_preview_batch(
        merged,
        provider=provider,
        live=live,
        write_cache=write_cache,
        limit=limit,
    )
    if markdown:
        typer.echo(render_us_provider_cache_preview_batch_markdown(out), nl=False)
    else:
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
    st_top = str(out.get("status") or "")
    if st_top == "validation_error":
        raise typer.Exit(2)
    raise typer.Exit(0)


@debug_app.command("us-provider-scheduled-ingest-plan")
def debug_us_provider_scheduled_ingest_plan(
    symbols_csv: Optional[str] = typer.Option(
        None,
        "--symbols",
        help="Comma-separated US symbols (merged after --from-watchlist when both set).",
    ),
    from_watchlist: bool = typer.Option(
        False,
        "--from-watchlist",
        help="Include symbols from config/us_watchlist.yaml (normalized; YAML-native dedupe).",
    ),
    provider: str = typer.Option("stooq_preview", "--provider", help="stooq_preview only (Main R6.1 plan)."),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        min=1,
        help="Maximum normalized symbols after merge (invalid rows unaffected).",
    ),
    markdown: bool = typer.Option(
        False,
        "--markdown",
        help="Emit copy-ready Markdown plan (JSON canonical for plan_rows). Main R6.1.",
    ),
) -> None:
    """Dry-run scheduled ingest plan (**no HTTP**, **no cache write**, **no scheduler**)."""

    merged, fw, csv_ok = merged_symbols_for_scheduled_ingest_plan(
        from_watchlist=from_watchlist,
        symbols_csv=symbols_csv,
    )
    out = build_us_provider_scheduled_ingest_plan(
        merged,
        provider=provider,
        from_watchlist_used=fw,
        symbols_csv_provided=csv_ok,
        limit_param=limit,
    )
    if markdown:
        typer.echo(render_us_provider_scheduled_ingest_plan_markdown(out), nl=False)
    else:
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
    st_top = str(out.get("status") or "")
    if st_top == "validation_error":
        raise typer.Exit(2)
    raise typer.Exit(0)


@debug_app.command("us-provider-manual-live-batch-smoke")
def debug_us_provider_manual_live_batch_smoke(
    symbols_csv: Optional[str] = typer.Option(
        None,
        "--symbols",
        help="Comma-separated US symbols (merged after --from-watchlist when both set).",
    ),
    from_watchlist: bool = typer.Option(
        False,
        "--from-watchlist",
        help="Include symbols from config/us_watchlist.yaml (normalized; YAML-native dedupe).",
    ),
    provider: str = typer.Option(
        "stooq_preview",
        "--provider",
        help="stooq_preview only (R6.3 dry-run / R6.4.0 preflight / R6.4.1 bounded live preview).",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        min=1,
        help="Maximum normalized symbols after merge (invalid rows unaffected).",
    ),
    max_http: int = typer.Option(
        0,
        "--max-http",
        min=0,
        help="HTTP cap per run; zero with --live or --execute-live-http is validation_error.",
    ),
    live: bool = typer.Option(
        False,
        "--live",
        help="Required for --preflight and --execute-live-http; alone returns scaffold refusal.",
    ),
    preflight: bool = typer.Option(
        False,
        "--preflight",
        help="Validate gate + cap readiness (R6.4.0); requires --live; no vendor HTTP unless --execute-live-http also set.",
    ),
    execute_live_http: bool = typer.Option(
        False,
        "--execute-live-http",
        help="R6.4.1: bounded live HTTP; requires --live --preflight + CONFIRM_US_LIVE_HTTP=YES + CONFIRM_US_MANUAL_BATCH_SMOKE=YES + --max-http > 0; no cache write.",
    ),
    evaluate_cache_write: bool = typer.Option(
        False,
        "--evaluate-cache-write",
        help="R6.5.1 refusal scaffold only: evaluates cache-write intent and always refuses; no cache write.",
    ),
    execute_cache_write: bool = typer.Option(
        False,
        "--execute-cache-write",
        help="R6.5.7: production cache write; requires --live --preflight --execute-live-http --evaluate-cache-write + all 3 env gates + --max-http > 0.",
    ),
    markdown: bool = typer.Option(
        False,
        "--markdown",
        help="Emit copy-ready Markdown recap (JSON canonical).",
    ),
) -> None:
    """Manual live batch smoke (**R6.5.7**): production cache write + refusal scaffold + bounded live HTTP."""

    merged, fw, csv_ok = merged_symbols_for_scheduled_ingest_plan(
        from_watchlist=from_watchlist,
        symbols_csv=symbols_csv,
    )
    out = build_us_provider_manual_live_batch_smoke_payload(
        merged,
        provider=provider,
        from_watchlist_used=fw,
        symbols_csv_provided=csv_ok,
        limit_param=limit,
        max_http=max_http,
        live_requested=live,
        preflight_requested=preflight,
        execute_live_http_requested=execute_live_http,
        evaluate_cache_write_requested=evaluate_cache_write,
        execute_cache_write_requested=execute_cache_write,
    )
    if markdown:
        typer.echo(render_manual_live_batch_smoke_markdown(out), nl=False)
    else:
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
    st_top = str(out.get("status") or "")
    if st_top == "validation_error":
        raise typer.Exit(2)
    raise typer.Exit(0)


@debug_app.command("jquants-watchlist-bars-cache")
def debug_jquants_watchlist_bars_cache(
    from_date: str = typer.Option(
        ...,
        "--from-date",
        help="Range start YYYY-MM-DD or YYYYMMDD (pairs with --to-date).",
    ),
    to_date: str = typer.Option(
        ...,
        "--to-date",
        help="Range end YYYY-MM-DD or YYYYMMDD (pairs with --from-date).",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        min=1,
        help="Process only the first N JP watchlist tickers (order preserved).",
    ),
    live: bool = typer.Option(
        False,
        "--live",
        help="Bulk live HTTP (requires JQUANTS_ALLOW_LIVE_HTTP=true and CONFIRM_LIVE_HTTP=YES).",
    ),
    write_cache: bool = typer.Option(
        False,
        "--write-cache",
        help="Write sanitized cache per code (requires --live; CONFIRM_LIVE_HTTP=YES is required for any --live).",
    ),
    codes: Optional[str] = typer.Option(
        None,
        "--codes",
        help="Comma-separated wire codes (overrides jp_watchlist). Invalid tokens become skipped rows in results.",
    ),
) -> None:
    """Bulk JP watchlist → V2 daily bars; default dry-run previews only (no HTTP, no cache writes)."""

    fn = from_date.strip()
    tn = to_date.strip()
    client = JQuantsClient.from_env()

    if write_cache and not live:
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "write_cache_requires_live",
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            err=True,
        )
        raise typer.Exit(2)

    if live and os.environ.get("CONFIRM_LIVE_HTTP") != "YES":
        typer.echo(
            json.dumps(
                {
                    "status": "live_blocked",
                    "reason": "confirm_live_http_required",
                    "detail": "Set CONFIRM_LIVE_HTTP=YES for any bulk --live HTTP (read-only or --write-cache).",
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            err=True,
        )
        raise typer.Exit(2)

    verr = client.validate_daily_quotes_cli_args(None, date=None, from_date=fn, to_date=tn)
    if verr is not None:
        view = _jquants_daily_quotes_cli_snapshot(verr, code=None, from_date=fn, to_date=tn, date_opt=None)
        typer.echo(json.dumps(view, ensure_ascii=False, indent=2))
        raise typer.Exit(1)

    try:
        tickers, csv_skipped_tokens = _resolve_watchlist_bars_cache_tickers(codes_csv=codes, limit=limit)
    except (FileNotFoundError, ValueError, OSError) as e:
        typer.echo(
            json.dumps({"status": "error", "reason": "watchlist_load_failed", "detail": str(e), "raw_response_included": False}),
            ensure_ascii=False,
            indent=2,
        )
        raise typer.Exit(1) from e

    if _parse_codes_csv(codes) is not None and not tickers:
        typer.echo(
            json.dumps(
                {
                    "status": "validation_error",
                    "reason": "codes_csv_no_valid_wire_codes",
                    "skipped_unsupported_code_tokens": csv_skipped_tokens,
                    "raw_response_included": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        raise typer.Exit(1)

    codes_mode = _parse_codes_csv(codes) is not None
    target_total = len(tickers) + len(csv_skipped_tokens) if codes_mode else len(tickers)

    results: list[dict[str, Any]] = []
    for bad in csv_skipped_tokens:
        results.append(
            _watchlist_bars_cache_row(
                code=bad,
                status="skipped_unsupported_code",
                reason="invalid_jquants_wire_code",
            )
        )
    cache_written_count = 0
    effective_write = bool(write_cache)

    if not live:
        for raw in tickers:
            wire = normalize_jquants_equity_code(str(raw))
            if wire is None:
                results.append(
                    _watchlist_bars_cache_row(
                        code=(str(raw) or "").strip(),
                        status="skipped_unsupported_code",
                        reason="invalid_jquants_wire_code",
                    )
                )
                continue
            prv = client.build_v2_daily_bars_request_preview(wire, date=None, from_date=fn, to_date=tn)
            if prv.get("status") == "ok":
                results.append(
                    _watchlist_bars_cache_row(
                        code=wire,
                        status="preview_ok",
                        full_url_without_secrets=prv.get("full_url_without_secrets"),
                    )
                )
            else:
                rsn = prv.get("reason")
                results.append(
                    _watchlist_bars_cache_row(
                        code=wire,
                        status="preview_error",
                        reason=str(rsn) if isinstance(rsn, str) else "preview_failed",
                    )
                )

        skipped_count = sum(1 for r in results if r.get("status") == "skipped_unsupported_code")
        non_skip = [r for r in results if r.get("status") != "skipped_unsupported_code"]
        success_count = sum(1 for r in non_skip if r.get("status") == "preview_ok")
        error_count = len(non_skip) - success_count
        out: dict[str, Any] = {
            "status": "dry_run",
            "mode": "jquants_watchlist_cache_preview",
            "date_from": fn,
            "date_to": tn,
            "target_count": target_total,
            "success_count": success_count,
            "error_count": error_count,
            "skipped_count": skipped_count,
            "cache_written_count": 0,
            "failed_codes": [str(r.get("code")) for r in non_skip if r.get("status") != "preview_ok"],
            "results": results,
            "live_http_performed": False,
            "raw_response_included": False,
        }
        crq = _norm_watchlist_codes_csv_requested(codes)
        if crq is not None:
            out["codes_requested"] = crq
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
        raise typer.Exit(0 if error_count == 0 else 1)

    for raw in tickers:
        wire = normalize_jquants_equity_code(str(raw))
        if wire is None:
            results.append(
                _watchlist_bars_cache_row(
                    code=(str(raw) or "").strip(),
                    status="skipped_unsupported_code",
                    reason="invalid_jquants_wire_code",
                )
            )
            continue

        result = client.get_daily_quotes(
            wire,
            date=None,
            from_date=fn,
            to_date=tn,
            attempt_live=True,
            return_sanitized_bars=True,
        )
        st = result.get("status")

        if st == "success":
            rc = result.get("row_count")
            sb = result.get("sanitized_bar_count")
            if not isinstance(sb, int):
                sbl = result.get("sanitized_bars")
                sb = len(sbl) if isinstance(sbl, list) else None
            path_rel: str | None = None
            if effective_write:
                bars = result.get("sanitized_bars")
                if isinstance(bars, list) and bars:
                    path = save_jquants_daily_bars_cache(
                        wire,
                        bars,
                        source="jquants_v2_equities_bars_daily",
                        fetched_at=utc_now_iso(),
                        generated_at=None,
                    )
                    try:
                        path_rel = str(path.relative_to(ROOT_DIR)).replace("\\", "/")
                    except ValueError:
                        path_rel = str(path).replace("\\", "/")
                    cache_written_count += 1
                else:
                    st = "cache_not_written"
                    result = dict(result)
                    result["reason"] = "no_sanitized_rows"
            results.append(
                _watchlist_bars_cache_row(
                    code=wire,
                    status=st if isinstance(st, str) else "error",
                    row_count=rc if isinstance(rc, int) else None,
                    sanitized_bar_count=sb,
                    cache_written_to=path_rel,
                    reason=result.get("reason") if st == "cache_not_written" else None,
                )
            )
            continue

        if st == "sanitized_empty":
            results.append(
                _watchlist_bars_cache_row(
                    code=wire,
                    status="sanitized_empty",
                    row_count=result.get("row_count"),
                    sanitized_bar_count=0,
                    cache_written_to=None,
                    reason=result.get("reason") if isinstance(result.get("reason"), str) else "sanitized_empty",
                )
            )
            continue

        snap = _jquants_daily_quotes_cli_snapshot(result, code=wire, from_date=fn, to_date=tn, date_opt=None)
        results.append(_watchlist_bars_cache_row_from_snap(wire, snap, result))

    skipped_count = sum(1 for r in results if r.get("status") == "skipped_unsupported_code")
    non_skip = [r for r in results if r.get("status") != "skipped_unsupported_code"]
    success_count = sum(1 for r in non_skip if r.get("status") == "success")
    error_count = len(non_skip) - success_count
    failed_codes_live = [str(r.get("code")) for r in non_skip if r.get("status") != "success"]
    out_live: dict[str, Any] = {
        "status": "completed",
        "mode": "jquants_watchlist_cache_live",
        "date_from": fn,
        "date_to": tn,
        "target_count": target_total,
        "success_count": success_count,
        "error_count": error_count,
        "skipped_count": skipped_count,
        "cache_written_count": cache_written_count,
        "failed_codes": failed_codes_live,
        "results": results,
        "live_http_performed": True,
        "raw_response_included": False,
    }
    crq_live = _norm_watchlist_codes_csv_requested(codes)
    if crq_live is not None:
        out_live["codes_requested"] = crq_live
    typer.echo(json.dumps(out_live, ensure_ascii=False, indent=2))

    raise typer.Exit(0 if error_count == 0 else 1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()

