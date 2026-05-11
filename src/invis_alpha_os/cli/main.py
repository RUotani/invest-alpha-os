from __future__ import annotations

from datetime import date

from typing import Any, Optional

import json

import typer

from invis_alpha_os.config import CONFIG_DIR, OUTPUTS_DIR, load_yaml
from invis_alpha_os.config.jp_watchlist import (
    jquants_daily_bars_ticker_kind,
    load_jp_watchlist_tickers,
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
from invis_alpha_os.reports.jquants_watchlist_daily import render_jquants_watchlist_bars_check_section
from invis_alpha_os.risk.veto_rules import VetoEngine

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
    ]
    missing = [name for name in required if not (CONFIG_DIR / name).exists()]
    if missing:
        raise typer.Exit(code=1)
    typer.echo("config-check: OK")


@app.command("daily")
def daily() -> None:
    today = date.today().isoformat()
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
        + jq_watchlist_section,
        encoding="utf-8",
    )
    typer.echo(f"daily report created: {out}")


@app.command("pack")
def pack(ticker: str = typer.Option(..., "--ticker")) -> None:
    today = date.today().isoformat()
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
) -> None:
    """Batch daily-bars check for ``jp_watchlist`` (Phase 1a Task 6). Default: dry-run."""

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
            if jquants_daily_bars_ticker_kind(code) != "ok":
                results.append(
                    _result_row_no_raw({"code": code, "status": "skipped_unsupported_code", "raw_response_included": False})
                )
                continue
            prv = client.build_v2_daily_bars_request_preview(code, date=dn, from_date=fn, to_date=tn)
            results.append(_result_row_no_raw(_watchlist_preview_row(code, prv)))
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
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
        raise typer.Exit(0)

    for code in tickers:
        if jquants_daily_bars_ticker_kind(code) != "ok":
            results.append(_result_row_no_raw({"code": code, "status": "skipped_unsupported_code"}))
            continue
        res = client.get_daily_quotes(code, date=dn, from_date=fn, to_date=tn, attempt_live=live)
        snap = _jquants_daily_quotes_cli_snapshot(res, code=code, from_date=fn, to_date=tn, date_opt=dn)
        results.append(_result_row_no_raw(snap))

    if not live:
        out = {"status": "dry_run", **base_meta, "results": results}
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()

