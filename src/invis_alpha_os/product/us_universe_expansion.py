"""US 30+ expansion plan — config-first, read-only gap vs cache (P6)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from invis_alpha_os.config.loader import load_yaml
from invis_alpha_os.config.paths import CONFIG_DIR, ROOT_DIR
from invis_alpha_os.config.us_watchlist import load_us_watchlist_tickers, normalize_us_symbol
from invis_alpha_os.data.us_cache_signals import build_us_cache_signals_preview
from invis_alpha_os.product.weekly_us_observation import _MANIFEST_REL_CACHE

EXPANSION_CONFIG = CONFIG_DIR / "us_universe_expansion_30.yaml"
_REQUIRED_ENTRY_KEYS = frozenset({"symbol", "tier", "theme", "reason"})


def _parse_target_entry(raw: object, *, line_hint: str) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise ValueError(f"{line_hint}: entry must be a mapping")
    missing = _REQUIRED_ENTRY_KEYS - set(raw.keys())
    if missing:
        raise ValueError(f"{line_hint}: missing fields {sorted(missing)}")
    sym = normalize_us_symbol(str(raw["symbol"]))
    if sym is None:
        raise ValueError(f"{line_hint}: invalid symbol {raw.get('symbol')!r}")
    tier = str(raw["tier"]).strip()
    theme = str(raw["theme"]).strip()
    reason = str(raw["reason"]).strip()
    if not tier or not theme or not reason:
        raise ValueError(f"{line_hint}: tier/theme/reason must be non-empty")
    return {
        "symbol": sym,
        "tier": tier,
        "theme": theme,
        "reason": reason,
    }


def load_us_universe_expansion_config(path: Path | None = None) -> dict[str, Any]:
    """Load and validate expansion YAML (fail-closed on schema issues)."""

    p = path or EXPANSION_CONFIG
    if not p.is_file():
        raise FileNotFoundError(f"expansion config missing: {p}")
    data = load_yaml(p)
    if not isinstance(data, dict):
        raise ValueError("expansion config root must be a mapping")
    if int(data.get("schema_version", 0)) != 1:
        raise ValueError("expansion config schema_version must be 1")
    targets_raw = data.get("targets")
    if not isinstance(targets_raw, list) or not targets_raw:
        raise ValueError("expansion config targets must be a non-empty list")

    seen: set[str] = set()
    targets: list[dict[str, str]] = []
    for i, raw in enumerate(targets_raw):
        entry = _parse_target_entry(raw, line_hint=f"targets[{i}]")
        if entry["symbol"] in seen:
            raise ValueError(f"duplicate symbol in expansion config: {entry['symbol']}")
        seen.add(entry["symbol"])
        targets.append(entry)

    return {
        "schema_version": 1,
        "universe_name": str(data.get("universe_name") or "us_expansion_30"),
        "description": str(data.get("description") or ""),
        "targets": targets,
    }


def build_us_universe_expansion_report(
    *,
    path_base: Path | None = None,
    config_path: Path | None = None,
    tier: str | None = None,
    missing_only: bool = False,
) -> dict[str, Any]:
    """Compare expansion config to on-disk cache + parse_ok previews."""

    root = path_base or ROOT_DIR
    cfg = load_us_universe_expansion_config(config_path)
    watchlist = set(load_us_watchlist_tickers())
    existing_cache: list[str] = []
    for sym in {t["symbol"] for t in cfg["targets"]} | watchlist:
        rel = _MANIFEST_REL_CACHE.format(symbol=sym)
        if (root / rel).is_file():
            existing_cache.append(sym)
    existing_cache = sorted(set(existing_cache))

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    parse_ok: list[str] = []
    parse_fail: list[str] = []
    for t in cfg["targets"]:
        sym = t["symbol"]
        rel = _MANIFEST_REL_CACHE.format(symbol=sym)
        cache_path = root / rel
        has_cache = cache_path.is_file()
        preview_status = None
        if has_cache:
            preview = build_us_cache_signals_preview(cache_path, expect_symbol=sym)
            preview_status = preview.get("status")
            if preview_status == "ok":
                parse_ok.append(sym)
            else:
                parse_fail.append(sym)
        else:
            missing.append(sym)
        rows.append(
            {
                **t,
                "in_current_watchlist": sym in watchlist,
                "has_cache_file": has_cache,
                "signals_preview_status": preview_status,
            }
        )

    tier_order = {"1": 0, "2": 1, "3": 2}
    missing_rows = [x for x in rows if not x["has_cache_file"]]

    def _sort_key(row: dict[str, Any]) -> tuple[int, str]:
        return (tier_order.get(str(row["tier"]), 9), str(row["symbol"]))

    refresh_order = [r["symbol"] for r in sorted(missing_rows, key=_sort_key)]
    tier_1_missing = [r["symbol"] for r in sorted(missing_rows, key=_sort_key) if str(r["tier"]) == "1"]

    filtered_rows = rows
    if missing_only:
        filtered_rows = [r for r in rows if not r["has_cache_file"]]
    if tier is not None:
        filtered_rows = [r for r in filtered_rows if str(r["tier"]) == str(tier)]
    filtered_refresh = [r["symbol"] for r in sorted(filtered_rows, key=_sort_key)]

    return {
        "schema_version": 1,
        "universe_name": cfg["universe_name"],
        "description": cfg.get("description"),
        "target_symbol_count": len(cfg["targets"]),
        "filter_tier": tier,
        "filter_missing_only": missing_only,
        "existing_cache_symbols": existing_cache,
        "configured_targets": [t["symbol"] for t in cfg["targets"]],
        "missing_symbols": sorted(missing),
        "parse_ok_symbols": sorted(parse_ok),
        "parse_fail_symbols": sorted(parse_fail),
        "rows": rows,
        "filtered_rows": filtered_rows,
        "next_gated_refresh_order": refresh_order,
        "tier_1_missing_refresh_order": tier_1_missing,
        "filtered_refresh_order": filtered_refresh,
        "observation_only": True,
        "live_http": False,
    }


def format_us_universe_expansion_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# US Universe Expansion Plan (read-only)",
        "",
        "Observation universe — not buy/sell advice.",
        "",
        f"- universe: {report.get('universe_name')}",
        f"- configured targets: {report.get('target_symbol_count')}",
        f"- missing cache: {len(report.get('missing_symbols') or [])}",
        f"- parse ok: {len(report.get('parse_ok_symbols') or [])}",
        f"- tier-1 missing: {len(report.get('tier_1_missing_refresh_order') or [])}",
        "",
        "## Tier-1 gated refresh readiness (read-only)",
        "- Live HTTP and cache write require explicit operator approval.",
        "- This report does not refresh cache files.",
        "",
        "## Tier-1 missing (gated refresh dry-run order)",
    ]
    for sym in report.get("tier_1_missing_refresh_order") or []:
        lines.append(f"- {sym}")
    lines.extend(["", "## Next gated refresh order (all missing, tier-sorted)"])
    for sym in report.get("next_gated_refresh_order") or []:
        lines.append(f"- {sym}")
    lines.extend(["", "## Targets"])
    for row in report.get("rows") or []:
        flag = "cache=ok" if row.get("has_cache_file") else "cache=missing"
        lines.append(
            f"- {row['symbol']} tier={row['tier']} theme={row['theme']} {flag} "
            f"watchlist={row.get('in_current_watchlist')}"
        )
    lines.append("")
    return "\n".join(lines)
