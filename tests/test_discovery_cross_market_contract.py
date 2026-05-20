"""R7.0-C1: JP/US discovery cross-market output contract."""

from __future__ import annotations

import json
import re

from invis_alpha_os.discovery.cross_market_contract import (
    COMMON_CANDIDATE_KEYS,
    FORBIDDEN_OUTPUT_TERMS,
    MARKET_JP,
    MARKET_US,
    SCHEMA_VERSION,
    jp_candidate_to_common,
    merge_cross_market_json_payloads,
    us_candidate_to_common,
)
from invis_alpha_os.discovery.jp_universe_scanner import (
    JpDiscoveryCandidate,
    JpDiscoveryScanResult,
    format_jp_discovery_json,
    format_jp_discovery_markdown,
)
from invis_alpha_os.discovery.us_universe_scanner import (
    UsDiscoveryCandidate,
    UsDiscoveryScanResult,
    format_us_discovery_json,
    format_us_discovery_markdown,
)


def _jp_row() -> JpDiscoveryCandidate:
    return JpDiscoveryCandidate(
        code="7011",
        code_name="7011",
        discovery_score=3,
        latest_date="2026-05-01",
        close=100.0,
        return_1d=0.01,
        return_5d=0.05,
        return_20d=0.12,
        return_60d=0.20,
        volume_ratio_25d=1.5,
        high_distance_pct=-0.02,
        labels=("near_high",),
        categories=("near_high_quality_trend",),
        data_quality="ok",
        bar_count=90,
        reason="surfaced: near_high",
    )


def _us_row() -> UsDiscoveryCandidate:
    return UsDiscoveryCandidate(
        symbol="MSFT",
        symbol_name="MSFT",
        discovery_score=4,
        latest_date="2026-05-01",
        close=400.0,
        return_1d=0.01,
        return_5d=0.06,
        return_20d=0.15,
        return_60d=0.25,
        volume_ratio_25d=2.1,
        high_distance_pct=-0.01,
        volume_status="normal",
        labels=("volume_spike",),
        categories=("volume_spike",),
        data_quality="ok",
        bar_count=90,
        reason="surfaced: volume_spike",
    )


def test_common_candidate_keys_aligned() -> None:
    jp_common = jp_candidate_to_common(_jp_row())
    us_common = us_candidate_to_common(_us_row())
    assert set(jp_common) == set(COMMON_CANDIDATE_KEYS)
    assert set(us_common) == set(COMMON_CANDIDATE_KEYS)
    assert jp_common["market"] == MARKET_JP
    assert us_common["market"] == MARKET_US
    assert jp_common["volume_status"] is None
    assert us_common["volume_status"] == "normal"


def test_json_envelope_has_schema_and_legacy_arrays() -> None:
    jp_payload = format_jp_discovery_json(
        JpDiscoveryScanResult(
            universe_scope="sample_jp_universe",
            generated_at="2026-05-20T00:00:00Z",
            candidates=[_jp_row()],
            symbol_count=1,
        )
    )
    us_payload = format_us_discovery_json(
        UsDiscoveryScanResult(
            universe_scope="curated_us_watchlist",
            generated_at="2026-05-20T00:00:00Z",
            candidates=[_us_row()],
            symbol_count=1,
        )
    )
    assert jp_payload["schema_version"] == SCHEMA_VERSION
    assert us_payload["schema_version"] == SCHEMA_VERSION
    assert jp_payload["candidates"][0]["code"] == "7011"
    assert us_payload["candidates"][0]["symbol"] == "MSFT"
    assert jp_payload["common_candidates"][0]["instrument_id"] == "7011"
    assert us_payload["common_candidates"][0]["instrument_id"] == "MSFT"


def test_merge_cross_market_payload_for_runner() -> None:
    jp_payload = format_jp_discovery_json(
        JpDiscoveryScanResult(
            universe_scope="sample_jp_universe",
            generated_at="2026-05-20T00:00:00Z",
            candidates=[_jp_row()],
            symbol_count=1,
        )
    )
    us_payload = format_us_discovery_json(
        UsDiscoveryScanResult(
            universe_scope="curated_us_watchlist",
            generated_at="2026-05-20T00:00:00Z",
            candidates=[_us_row()],
            symbol_count=1,
        )
    )
    merged = merge_cross_market_json_payloads(jp_payload, us_payload)
    assert merged["schema_version"] == SCHEMA_VERSION
    assert merged["markets"]["jp"]["summary"]["ranked_candidate_count"] == 1
    assert merged["markets"]["us"]["common_candidates"][0]["instrument_id"] == "MSFT"
    blob = json.dumps(merged).lower()
    for term in FORBIDDEN_OUTPUT_TERMS:
        assert not re.search(rf"\b{re.escape(term)}\b", blob)


def test_markdown_tables_share_header() -> None:
    jp_md = format_jp_discovery_markdown(
        JpDiscoveryScanResult(
            universe_scope="sample_jp_universe",
            generated_at="2026-05-20T00:00:00Z",
            candidates=[_jp_row()],
            symbol_count=1,
        )
    )
    us_md = format_us_discovery_markdown(
        UsDiscoveryScanResult(
            universe_scope="curated_us_watchlist",
            generated_at="2026-05-20T00:00:00Z",
            candidates=[_us_row()],
            symbol_count=1,
        )
    )
    assert "| rank | instrument | discovery_score |" in jp_md
    assert "| rank | instrument | discovery_score |" in us_md
    assert "## Candidate Groups" in jp_md
    assert "## Candidate Groups" in us_md
