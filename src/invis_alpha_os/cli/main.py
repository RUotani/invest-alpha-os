from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import typer

from invis_alpha_os.config import CONFIG_DIR, OUTPUTS_DIR, load_yaml
from invis_alpha_os.data.adapters import EdinetStubAdapter, SecStubAdapter, YFinanceFallbackAdapter
from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.portfolio.shadow_portfolio import ShadowPortfolioService
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
    out.write_text(
        "\n".join(
            [
                f"# Daily Report ({today})",
                "",
                "Phase 0 dummy report.",
                "- Observation only",
                "- No auto trading",
            ]
        ),
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
    jp_count = len(watchlist.get("jp_watchlist", []))
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
    adapters = [YFinanceFallbackAdapter(), EdinetStubAdapter(), SecStubAdapter()]
    for adapter in adapters:
        typer.echo(str(adapter.health()))


def main() -> None:
    app()


if __name__ == "__main__":
    main()

