"""JP/US discovery output contract — shared fields and format helpers (observation-only)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

SCHEMA_VERSION = "discovery.cross_market.v1"
MARKET_JP = "jp"
MARKET_US = "us"

DISCOVERY_SCORE_DISCLAIMER = (
    "Discovery score is only a sorting aid for follow-up research, not trading advice."
)
OBSERVATION_DISCLAIMER = "Observation only — not trading advice. No automatic trading."

FORBIDDEN_OUTPUT_TERMS: tuple[str, ...] = (
    "buy",
    "sell",
    "recommendation",
    "allocation",
    "target price",
    "entry instruction",
    "exit instruction",
    "position size",
    "order",
)


def assert_no_forbidden_terms(text: str) -> None:
    lower = text.lower()
    for term in FORBIDDEN_OUTPUT_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", lower):
            raise ValueError(f"forbidden output term: {term}")

COMMON_CANDIDATE_KEYS: tuple[str, ...] = (
    "market",
    "instrument_id",
    "display_name",
    "discovery_score",
    "latest_date",
    "close",
    "return_1d",
    "return_5d",
    "return_20d",
    "return_60d",
    "volume_ratio_25d",
    "high_distance_pct",
    "volume_status",
    "labels",
    "categories",
    "data_quality",
    "bar_count",
    "reason",
)

CATEGORY_GROUP_TITLES: tuple[tuple[str, str], ...] = (
    ("Rapid movers", "rapid_mover"),
    ("Volume spikes", "volume_spike"),
    ("Near/new highs", "new_breakout_candidate"),
    ("Near-high quality trend", "near_high_quality_trend"),
    ("Overheat caution", "overheated_caution"),
    ("Insufficient data", "insufficient_data"),
)

RANKED_TABLE_HEADER = (
    "| rank | instrument | discovery_score | latest_date | close | r5 | r20 | r60 | "
    "vol_ratio | volume_status | high_dist | labels | data_quality |"
)
RANKED_TABLE_SEPARATOR = (
    "|---:|---|---:|---|---:|---:|---:|---:|---:|---|---:|---|---|"
)


class _DiscoveryRow(Protocol):
    discovery_score: int
    latest_date: str
    close: float | None
    return_5d: float | None
    return_20d: float | None
    return_60d: float | None
    volume_ratio_25d: float | None
    high_distance_pct: float | None
    labels: tuple[str, ...]
    categories: tuple[str, ...]
    data_quality: str
    reason: str


@dataclass(frozen=True)
class DiscoveryScanEnvelope:
    """Top-level scan metadata shared by JP/US JSON envelopes."""

    market: str
    universe_scope: str
    generated_at: str
    symbol_count: int
    ranked_candidate_count: int
    insufficient_count: int


def format_pct(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{100.0 * x:.1f}%"


def format_num(x: float | None, *, digits: int = 2) -> str:
    if x is None:
        return "—"
    return f"{x:,.{digits}f}"


def discovery_safety_block(*, market: str, cache_read_only: bool = True, live_http: bool = False) -> dict[str, Any]:
    return {
        "observation_only": True,
        "no_trading_advice": True,
        "discovery_score_disclaimer": DISCOVERY_SCORE_DISCLAIMER,
        "cache_read_only": cache_read_only,
        "live_http": live_http,
        "market": market,
    }


def discovery_summary_block(
    *,
    symbol_count: int,
    ranked_candidate_count: int,
    insufficient_count: int,
) -> dict[str, int]:
    return {
        "symbol_count": symbol_count,
        "ranked_candidate_count": ranked_candidate_count,
        "insufficient_count": insufficient_count,
    }


def jp_candidate_to_common(row: Any) -> dict[str, Any]:
    return {
        "market": MARKET_JP,
        "instrument_id": row.code,
        "display_name": row.code_name,
        "discovery_score": row.discovery_score,
        "latest_date": row.latest_date,
        "close": row.close,
        "return_1d": row.return_1d,
        "return_5d": row.return_5d,
        "return_20d": row.return_20d,
        "return_60d": row.return_60d,
        "volume_ratio_25d": row.volume_ratio_25d,
        "high_distance_pct": row.high_distance_pct,
        "volume_status": None,
        "labels": list(row.labels),
        "categories": list(row.categories),
        "data_quality": row.data_quality,
        "bar_count": row.bar_count,
        "reason": row.reason,
    }


def us_candidate_to_common(row: Any) -> dict[str, Any]:
    return {
        "market": MARKET_US,
        "instrument_id": row.symbol,
        "display_name": row.symbol_name,
        "discovery_score": row.discovery_score,
        "latest_date": row.latest_date,
        "close": row.close,
        "return_1d": row.return_1d,
        "return_5d": row.return_5d,
        "return_20d": row.return_20d,
        "return_60d": row.return_60d,
        "volume_ratio_25d": row.volume_ratio_25d,
        "high_distance_pct": row.high_distance_pct,
        "volume_status": row.volume_status,
        "labels": list(row.labels),
        "categories": list(row.categories),
        "data_quality": row.data_quality,
        "bar_count": row.bar_count,
        "reason": row.reason,
    }


def build_discovery_json_payload(
    *,
    envelope: DiscoveryScanEnvelope,
    common_ranked: Sequence[Mapping[str, Any]],
    common_insufficient: Sequence[Mapping[str, Any]],
    legacy_ranked: Sequence[Mapping[str, Any]],
    legacy_insufficient: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "market": envelope.market,
        "universe_scope": envelope.universe_scope,
        "generated_at": envelope.generated_at,
        "safety": discovery_safety_block(market=envelope.market),
        "summary": discovery_summary_block(
            symbol_count=envelope.symbol_count,
            ranked_candidate_count=envelope.ranked_candidate_count,
            insufficient_count=envelope.insufficient_count,
        ),
        "common_candidates": list(common_ranked),
        "common_insufficient": list(common_insufficient),
        "candidates": list(legacy_ranked),
        "insufficient": list(legacy_insufficient),
    }


def merge_cross_market_json_payloads(
    jp_payload: Mapping[str, Any],
    us_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Combine JP/US discovery JSON for operator-runner / integrated reports (read-only)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_jp": jp_payload.get("generated_at"),
        "generated_at_us": us_payload.get("generated_at"),
        "safety": {
            "observation_only": True,
            "no_trading_advice": True,
            "discovery_score_disclaimer": DISCOVERY_SCORE_DISCLAIMER,
            "cache_read_only": True,
            "live_http": False,
        },
        "markets": {
            MARKET_JP: {
                "universe_scope": jp_payload.get("universe_scope"),
                "summary": jp_payload.get("summary"),
                "common_candidates": jp_payload.get("common_candidates", []),
                "common_insufficient": jp_payload.get("common_insufficient", []),
            },
            MARKET_US: {
                "universe_scope": us_payload.get("universe_scope"),
                "summary": us_payload.get("summary"),
                "common_candidates": us_payload.get("common_candidates", []),
                "common_insufficient": us_payload.get("common_insufficient", []),
            },
        },
    }


def _group_by_category(candidates: Sequence[_DiscoveryRow], category: str) -> list[_DiscoveryRow]:
    return [c for c in candidates if category in c.categories]


def format_ranked_table_row(
    *,
    rank: int,
    display_name: str,
    row: _DiscoveryRow,
    close_digits: int,
    volume_status: str | None,
) -> str:
    vs = volume_status if volume_status else "—"
    return (
        "| {rank} | {name} | {score} | {date} | {close} | {r5} | {r20} | {r60} | {vr} | {vs} | {hd} | {labels} | {dq} |"
    ).format(
        rank=rank,
        name=display_name,
        score=row.discovery_score,
        date=row.latest_date or "—",
        close=format_num(row.close, digits=close_digits),
        r5=format_pct(row.return_5d),
        r20=format_pct(row.return_20d),
        r60=format_pct(row.return_60d),
        vr=format_num(row.volume_ratio_25d),
        vs=vs,
        hd=format_pct(row.high_distance_pct),
        labels=", ".join(row.labels) if row.labels else "—",
        dq=row.data_quality,
    )


def format_candidate_groups_markdown(candidates: Sequence[_DiscoveryRow]) -> list[str]:
    lines: list[str] = ["", "## Candidate Groups"]
    for title, cat in CATEGORY_GROUP_TITLES:
        rows = _group_by_category(candidates, cat)
        lines.append("")
        lines.append(f"### {title}")
        if not rows:
            lines.append("- (none in ranked set)")
            continue
        for c in rows:
            name = getattr(c, "code_name", None) or getattr(c, "symbol_name", "")
            lines.append(f"- **{name}** — {c.reason}")
    return lines


def format_insufficient_bullets_markdown(
    insufficient: Sequence[_DiscoveryRow],
    *,
    limit: int = 15,
) -> list[str]:
    if not insufficient:
        return []
    lines = ["", "### Insufficient data (not ranked)"]
    for c in insufficient[:limit]:
        name = getattr(c, "code_name", None) or getattr(c, "symbol_name", "")
        lines.append(f"- **{name}** — {c.data_quality}: {c.reason}")
    return lines


def format_next_research_checklist(*, market: str) -> list[str]:
    if market == MARKET_US:
        bullets = (
            "- recent filings/news",
            "- earnings trend",
            "- liquidity / spread",
            "- index/sector context",
            "- existing holdings overlap",
        )
    else:
        bullets = (
            "- latest news / disclosure",
            "- earnings",
            "- valuation",
            "- liquidity",
            "- sector/theme",
            "- existing holdings",
        )
    return ["", "## Next Research Checklist", *bullets, ""]
