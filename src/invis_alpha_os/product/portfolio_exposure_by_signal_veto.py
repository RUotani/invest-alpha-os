"""Read-only shadow portfolio exposure by US signal / veto bucket (observation only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.observation.us_signal_note import (
    US_SIGNAL_NOTE_PREFIX,
    parse_us_signal_observation_note,
)
from invis_alpha_os.portfolio.shadow_portfolio import ShadowPortfolioService

VETO_BUCKET_VETO = "veto_triggered"
VETO_BUCKET_CLEAR = "no_veto"
VETO_BUCKET_UNKNOWN = "signal_unknown"
SIGNAL_LABEL_UNKNOWN = "unknown"


def latest_us_signal_context_by_symbol(observation_path: Path) -> dict[str, dict[str, Any]]:
    """Last US cache signal row per symbol (read-only)."""

    by_symbol: dict[str, dict[str, Any]] = {}
    if not observation_path.is_file():
        return by_symbol
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
        sym = str(row.get("symbol") or "").strip().upper()
        if not sym:
            continue
        parsed = parse_us_signal_observation_note(note)
        veto = parsed.get("veto_triggered")
        if veto is True:
            veto_bucket = VETO_BUCKET_VETO
        elif veto is False:
            veto_bucket = VETO_BUCKET_CLEAR
        else:
            veto_bucket = VETO_BUCKET_UNKNOWN
        label = str(parsed.get("momentum_label") or SIGNAL_LABEL_UNKNOWN)
        by_symbol[sym] = {
            "momentum_label": label,
            "veto_bucket": veto_bucket,
            "veto_triggered": veto,
            "observation_id": row.get("id"),
        }
    return by_symbol


def _bucket_stats() -> dict[str, Any]:
    return {"position_count": 0, "total_quantity": 0.0}


def _add_bucket(buckets: dict[str, dict[str, Any]], key: str, quantity: float) -> None:
    block = buckets.setdefault(key, _bucket_stats())
    block["position_count"] += 1
    block["total_quantity"] = round(float(block["total_quantity"]) + quantity, 6)


def build_portfolio_exposure_by_signal_veto(
    *,
    path_base: Path | None = None,
    shadow_path: Path | None = None,
    observation_path: Path | None = None,
) -> dict[str, Any]:
    """Aggregate shadow positions by latest log momentum_label and veto bucket."""

    root = path_base or ROOT_DIR
    shadow = shadow_path or (OUTPUTS_DIR / "shadow_portfolio" / "positions.jsonl")
    obs = observation_path or (OUTPUTS_DIR / "observation_log" / "observation_log.jsonl")
    signal_ctx = latest_us_signal_context_by_symbol(obs)

    try:
        positions = ShadowPortfolioService(shadow).list_positions()
    except (FileNotFoundError, ValueError, OSError):
        positions = []

    by_momentum: dict[str, dict[str, Any]] = {}
    by_veto: dict[str, dict[str, Any]] = {}
    by_composite: dict[str, dict[str, Any]] = {}
    position_rows: list[dict[str, Any]] = []

    for pos in positions:
        sym = str(pos.symbol or "").strip().upper() or "(empty)"
        qty = float(pos.quantity or 0.0)
        ctx = signal_ctx.get(sym)
        if ctx:
            momentum = str(ctx["momentum_label"])
            veto_bucket = str(ctx["veto_bucket"])
        else:
            momentum = SIGNAL_LABEL_UNKNOWN
            veto_bucket = VETO_BUCKET_UNKNOWN
        composite = f"{momentum}|{veto_bucket}"
        _add_bucket(by_momentum, momentum, qty)
        _add_bucket(by_veto, veto_bucket, qty)
        _add_bucket(by_composite, composite, qty)
        position_rows.append(
            {
                "symbol": sym,
                "quantity": qty,
                "momentum_label": momentum,
                "veto_bucket": veto_bucket,
                "observation_id": (ctx or {}).get("observation_id"),
            }
        )

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(root))
        except ValueError:
            return str(p)

    headline = (
        f"{len(positions)} shadow position(s) by signal/veto bucket "
        f"({len(signal_ctx)} symbols with US signal context in log)"
    )
    return {
        "schema_version": 1,
        "observation_only": True,
        "status": "ok" if positions else "empty",
        "shadow_path": _rel(shadow),
        "observation_path": _rel(obs),
        "shadow_position_count": len(positions),
        "symbols_with_signal_context": len(signal_ctx),
        "headline": headline,
        "by_momentum_label": dict(sorted(by_momentum.items())),
        "by_veto_bucket": dict(sorted(by_veto.items())),
        "by_momentum_veto_composite": dict(sorted(by_composite.items())),
        "positions": position_rows[:24],
    }


def format_portfolio_exposure_weekly_one_liner(report: dict[str, Any]) -> str:
    """Single markdown bullet for weekly dry-run when shadow positions exist."""

    count = int(report.get("shadow_position_count") or 0)
    if count == 0:
        return ""
    by_veto = report.get("by_veto_bucket") or {}
    veto_parts = [
        f"{VETO_BUCKET_VETO}={by_veto.get(VETO_BUCKET_VETO, {}).get('position_count', 0)}",
        f"{VETO_BUCKET_CLEAR}={by_veto.get(VETO_BUCKET_CLEAR, {}).get('position_count', 0)}",
        f"{VETO_BUCKET_UNKNOWN}={by_veto.get(VETO_BUCKET_UNKNOWN, {}).get('position_count', 0)}",
    ]
    return (
        f"- portfolio_exposure: {count} shadow position(s); "
        f"{', '.join(veto_parts)} · "
        "detail: snapshot portfolio-exposure-by-signal-veto --format markdown"
    )


def build_observation_report_usefulness_hints(
    *,
    shadow_position_count: int,
    p3_samples_needed: int | None = None,
) -> list[str]:
    """Read-only CLI hints for weekly/P3 monitoring reports (no behavior change)."""

    hints: list[str] = []
    if shadow_position_count > 0:
        hints.append(
            ".venv/bin/python -m invis_alpha_os.cli.main snapshot "
            "portfolio-exposure-by-signal-veto --format markdown"
        )
    hints.append(
        ".venv/bin/python -m invis_alpha_os.cli.main validate p3-path-to-usable --format markdown"
    )
    if p3_samples_needed and p3_samples_needed > 0:
        hints.append(
            ".venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation "
            "--dry-run --format markdown  # P3 + duplicate-week preflight"
        )
    return hints


def format_portfolio_exposure_by_signal_veto_markdown(report: dict[str, Any]) -> str:
    lines = [
        "## Portfolio exposure by signal / veto (read-only)",
        "",
        f"- {report.get('headline', '')}",
        f"- shadow_position_count: {report.get('shadow_position_count', 0)}",
        f"- symbols_with_signal_context: {report.get('symbols_with_signal_context', 0)}",
    ]
    for title, key in (
        ("### By momentum_label", "by_momentum_label"),
        ("### By veto_bucket", "by_veto_bucket"),
        ("### By momentum × veto", "by_momentum_veto_composite"),
    ):
        buckets = report.get(key) or {}
        if buckets:
            lines.extend(["", title])
            for name, stats in buckets.items():
                lines.append(
                    f"- {name}: positions={stats.get('position_count', 0)} "
                    f"qty={stats.get('total_quantity', 0)}"
                )
    positions = report.get("positions") or []
    if positions:
        lines.extend(["", "### Positions (sample)"])
        for row in positions[:12]:
            lines.append(
                f"- {row.get('symbol')}: qty={row.get('quantity')} "
                f"label={row.get('momentum_label')} veto={row.get('veto_bucket')}"
            )
    return "\n".join(lines)
