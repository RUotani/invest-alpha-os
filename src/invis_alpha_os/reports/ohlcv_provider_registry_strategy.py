"""OHLCV provider registry strategy report (design; no live HTTP)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

CONTRACT_DATA_TO = "2026-03-06"
MANUAL_IMPORT_PHRASE = "manual JP bars actual importを実行してよい"
PUBLIC_LIVE_PHRASE = "public OHLCV source live fetchを実行してよい"

CANONICAL_EXTENDED_COLUMNS = (
    "ticker",
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "provider",
    "adjustment",
    "source_timestamp",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_ohlcv_provider_registry_strategy(*, report_date: str) -> tuple[str, dict[str, Any]]:
    providers: list[dict[str, Any]] = [
        {
            "id": "jquants",
            "market": "JP",
            "role": "primary",
            "live_http": True,
            "approval_gate": "J-Quants gated refreshを実行してよい",
            "manual_fallback": False,
            "notes": "Contract cap; cache-first",
        },
        {
            "id": "stooq",
            "market": "JP,US,global",
            "role": "fallback",
            "live_http": True,
            "approval_gate": PUBLIC_LIVE_PHRASE,
            "manual_fallback": True,
            "notes": "Stooq CSV dropzone ingest (v34); gated live fetch",
        },
        {
            "id": "yahoo_manual",
            "market": "JP",
            "role": "manual_fallback",
            "live_http": False,
            "approval_gate": MANUAL_IMPORT_PHRASE,
            "manual_fallback": True,
            "notes": "OHLCV-only CSV export",
        },
        {
            "id": "alpha_vantage",
            "market": "US,global",
            "role": "fallback_candidate",
            "live_http": True,
            "approval_gate": PUBLIC_LIVE_PHRASE,
            "manual_fallback": False,
            "notes": "Quota/cost monitoring required",
        },
        {
            "id": "tiingo",
            "market": "US",
            "role": "fallback_candidate",
            "live_http": True,
            "approval_gate": PUBLIC_LIVE_PHRASE,
            "manual_fallback": False,
            "notes": "EOD US",
        },
        {
            "id": "polygon",
            "market": "US",
            "role": "primary_candidate",
            "live_http": True,
            "approval_gate": PUBLIC_LIVE_PHRASE,
            "manual_fallback": False,
            "notes": "Paid primary candidate",
        },
        {
            "id": "eodhd",
            "market": "global",
            "role": "paid_fallback_candidate",
            "live_http": True,
            "approval_gate": PUBLIC_LIVE_PHRASE,
            "manual_fallback": False,
            "notes": "License/cost risk",
        },
    ]
    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "pack_version": "v34",
        "design_principles": [
            "manual_csv_is_emergency_fallback_not_primary",
            "jp_primary_jquants",
            "jp_fallback_stooq_then_yahoo_manual",
            "us_fallback_alpha_vantage_tiingo_polygon",
            "all_providers_normalize_to_canonical_ohlcv",
            "live_http_requires_explicit_approval_phrase",
        ],
        "canonical_columns": list(CANONICAL_EXTENDED_COLUMNS),
        "contract_data_available_to": CONTRACT_DATA_TO,
        "providers": providers,
        "priority_jp": ["jquants", "stooq", "yahoo_manual"],
        "priority_us": ["polygon", "tiingo", "alpha_vantage", "stooq"],
        "evaluation_dimensions": [
            "coverage",
            "freshness",
            "quota",
            "cost",
            "license_risk",
        ],
        "secrets_printed": False,
    }
    lines = [
        "# OHLCV Provider Registry Strategy",
        "",
        "## Design principles",
        "",
    ]
    for p in payload["design_principles"]:
        lines.append(f"- {p}")
    lines.extend(
        [
            "",
            "## JP priority",
            "",
            f"- {' > '.join(payload['priority_jp'])}",
            "",
            "## Canonical columns",
            "",
            f"- {', '.join(CANONICAL_EXTENDED_COLUMNS)}",
            "",
            "## Providers",
            "",
            "| id | market | role | live_http | approval_gate |",
            "|---|---|---|---|---|",
        ]
    )
    for prov in providers:
        gate = prov.get("approval_gate", "")
        if len(gate) > 40:
            gate = gate[:37] + "..."
        lines.append(
            f"| {prov['id']} | {prov['market']} | {prov['role']} | "
            f"{str(prov['live_http']).lower()} | {gate} |"
        )
    return "\n".join(lines), payload


def build_ohlcv_provider_coverage_matrix(*, report_date: str) -> tuple[str, dict[str, Any]]:
    rows = [
        {
            "provider": "jquants",
            "market": "JP",
            "role": "primary",
            "live_http": True,
            "cost_quota": "plan contract",
            "freshness": f"capped_to_{CONTRACT_DATA_TO}",
            "recommendation": "refresh_when_approved",
        },
        {
            "provider": "stooq",
            "market": "JP/US",
            "role": "fallback",
            "live_http": True,
            "cost_quota": "free_tier_manual_csv",
            "freshness": "dropzone_csv_or_gated_live",
            "recommendation": "manual_csv_now_live_fetch_deferred",
        },
        {
            "provider": "yahoo_manual",
            "market": "JP",
            "role": "manual_fallback",
            "live_http": False,
            "cost_quota": "user_export",
            "freshness": "user_dependent",
            "recommendation": "secondary_to_stooq_csv",
        },
        {
            "provider": "alpha_vantage",
            "market": "US",
            "role": "fallback",
            "live_http": True,
            "cost_quota": "api_key_quota",
            "freshness": "eod",
            "recommendation": "evaluate_for_us_watchlist",
        },
        {
            "provider": "tiingo",
            "market": "US",
            "role": "fallback",
            "live_http": True,
            "cost_quota": "paid_tier",
            "freshness": "eod",
            "recommendation": "candidate",
        },
        {
            "provider": "polygon",
            "market": "US",
            "role": "primary_candidate",
            "live_http": True,
            "cost_quota": "paid",
            "freshness": "intraday_eod",
            "recommendation": "long_term_us_primary",
        },
    ]
    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "pack_version": "v34",
        "matrix": rows,
        "secrets_printed": False,
    }
    lines = [
        "# OHLCV Provider Coverage Matrix",
        "",
        "| provider | market | role | live_http | cost/quota | recommendation |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['provider']} | {r['market']} | {r['role']} | "
            f"{str(r['live_http']).lower()} | {r['cost_quota']} | {r['recommendation']} |"
        )
    return "\n".join(lines), payload
