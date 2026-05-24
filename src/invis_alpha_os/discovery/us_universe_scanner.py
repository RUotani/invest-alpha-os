"""US universe discovery scanner MVP — cache-only; observation-only output."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from invis_alpha_os.config.loader import load_yaml
from invis_alpha_os.config.paths import CONFIG_DIR, OUTPUTS_DIR
from invis_alpha_os.config.us_watchlist import load_us_watchlist_tickers, normalize_us_symbol
from invis_alpha_os.data.us_daily_bars_cache import REL_US_CACHE_ROOT, load_us_daily_bars_cache
from invis_alpha_os.reports.symbol_display_names import display_symbol
from invis_alpha_os.discovery.cross_market_contract import (
    DISCOVERY_SCORE_DISCLAIMER,
    FORBIDDEN_OUTPUT_TERMS,
    MARKET_US,
    OBSERVATION_DISCLAIMER,
    RANKED_TABLE_HEADER as _RANKED_TABLE_HEADER,
    RANKED_TABLE_SEPARATOR as _RANKED_TABLE_SEPARATOR,
    DiscoveryScanEnvelope,
    build_discovery_json_payload,
    format_candidate_groups_markdown,
    format_insufficient_bullets_markdown,
    format_next_research_checklist,
    format_ranked_table_row,
    us_candidate_to_common,
)
from invis_alpha_os.signals.momentum import (
    DailyBar,
    calculate_returns,
    detect_high_breakout,
    high_distance_vs_prior_high_pct,
    volume_ratio_25d_prior_mean,
)

DISCOVERY_MIN_BARS = 80
R5_RAPID_THRESHOLD = 0.08
R20_RAPID_THRESHOLD = 0.20
VOLUME_SPIKE_RATIO_THRESHOLD = 2.0
NEAR_HIGH_DIST_THRESHOLD = -0.05
OVERHEAT_R20_THRESHOLD = 0.40
OVERHEAT_R60_THRESHOLD = 0.80
LOW_LIQUIDITY_AVG25_THRESHOLD = 200_000.0

@dataclass(frozen=True)
class UsDiscoveryCandidate:
    symbol: str
    symbol_name: str
    discovery_score: int
    latest_date: str
    close: float | None
    return_1d: float | None
    return_5d: float | None
    return_20d: float | None
    return_60d: float | None
    volume_ratio_25d: float | None
    high_distance_pct: float | None
    volume_status: str
    labels: tuple[str, ...]
    categories: tuple[str, ...]
    data_quality: str
    bar_count: int
    reason: str


@dataclass
class UsDiscoveryScanResult:
    universe_scope: str
    generated_at: str
    candidates: list[UsDiscoveryCandidate] = field(default_factory=list)
    symbol_count: int = 0
    insufficient: list[UsDiscoveryCandidate] = field(default_factory=list)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_us_universe_spec(universe_file: Path | None) -> tuple[str, list[str]]:
    if universe_file is None:
        return "", []
    data = load_yaml(universe_file)
    scope = str(data.get("universe_scope") or data.get("universe_name") or "curated_us_watchlist").strip()
    raw = data.get("symbols") or []
    if not isinstance(raw, list):
        raise ValueError("us universe file symbols must be a list")
    out: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            s = item.get("symbol") or item.get("ticker")
        else:
            s = item
        n = normalize_us_symbol(str(s)) if s is not None else None
        if n:
            out.append(n)
    # keep order first-wins
    seen: set[str] = set()
    dedup: list[str] = []
    for sym in out:
        if sym in seen:
            continue
        seen.add(sym)
        dedup.append(sym)
    return scope, dedup


def list_local_us_cache_symbols(cache_dir: Path) -> list[str]:
    if not cache_dir.is_dir():
        return []
    syms: list[str] = []
    for path in sorted(cache_dir.glob("*.json")):
        n = normalize_us_symbol(path.stem)
        if n:
            syms.append(n)
    return syms


def resolve_universe(*, universe_file: Path | None, cache_dir: Path) -> tuple[str, list[str]]:
    if universe_file is not None:
        scope, syms = load_us_universe_spec(universe_file)
        return (scope or "curated_us_watchlist"), syms
    watch = load_us_watchlist_tickers(CONFIG_DIR / "us_watchlist.yaml")
    if watch:
        return "us_watchlist", watch
    return "local_us_cache_available_symbols", list_local_us_cache_symbols(cache_dir)


def _volume_status(volumes: Sequence[float]) -> str:
    if len(volumes) < 6:
        return "unknown"
    last = float(volumes[-1])
    prior = [float(v) for v in volumes[:-1]]
    avg = sum(prior[-25:]) / min(25, len(prior))
    if avg <= 0:
        return "unknown"
    ratio = last / avg
    if ratio >= 2.0:
        return "high"
    if ratio < 0.5:
        return "low"
    return "normal"


def _discovery_overheat(r20: float | None, r60: float | None) -> bool:
    return (r20 is not None and r20 >= OVERHEAT_R20_THRESHOLD) or (r60 is not None and r60 >= OVERHEAT_R60_THRESHOLD)


def _score_and_labels(
    *,
    bar_count: int,
    breakout: bool,
    high_dist: float | None,
    vol_ratio: float | None,
    r5: float | None,
    r20: float | None,
    r60: float | None,
    vol_avg25: float | None,
) -> tuple[int, list[str], list[str], str, str]:
    if bar_count < DISCOVERY_MIN_BARS:
        return (
            0,
            [],
            ["insufficient_data"],
            "insufficient_history",
            f"bars {bar_count} < min {DISCOVERY_MIN_BARS}",
        )

    labels: list[str] = []
    categories: list[str] = []
    score = 0
    if breakout:
        labels.append("high_52w_breakout")
        categories.append("new_breakout_candidate")
        score += 2
    if high_dist is not None and high_dist >= NEAR_HIGH_DIST_THRESHOLD and not breakout:
        labels.append("near_high")
        categories.append("near_high_quality_trend")
        score += 1
    if vol_ratio is not None and vol_ratio >= VOLUME_SPIKE_RATIO_THRESHOLD:
        labels.append("volume_spike")
        categories.append("volume_spike")
        score += 2
    if r20 is not None and r20 >= R20_RAPID_THRESHOLD:
        labels.append("rapid_mover_20d")
        categories.append("rapid_mover")
        score += 2
    if r5 is not None and r5 >= R5_RAPID_THRESHOLD:
        labels.append("rapid_mover_5d")
        if "rapid_mover" not in categories:
            categories.append("rapid_mover")
        score += 1
    if _discovery_overheat(r20, r60):
        labels.append("overheat_caution")
        categories.append("overheated_caution")
        score -= 1
    if vol_avg25 is not None and vol_avg25 < LOW_LIQUIDITY_AVG25_THRESHOLD:
        labels.append("low_liquidity_caution")
    reason = "surfaced: " + ", ".join(labels) if labels else "no discovery labels (follow-up optional)"
    return score, labels, categories, "ok", reason


def analyze_symbol_for_discovery(symbol: str, bars: Sequence[DailyBar]) -> UsDiscoveryCandidate:
    sym = normalize_us_symbol(symbol) or symbol.strip().upper()
    if not bars:
        return UsDiscoveryCandidate(
            symbol=sym,
            symbol_name=display_symbol(sym, market="us"),
            discovery_score=0,
            latest_date="",
            close=None,
            return_1d=None,
            return_5d=None,
            return_20d=None,
            return_60d=None,
            volume_ratio_25d=None,
            high_distance_pct=None,
            volume_status="unknown",
            labels=(),
            categories=("insufficient_data",),
            data_quality="invalid_bars",
            bar_count=0,
            reason="empty bar series",
        )
    closes = [float(b["close"]) for b in bars]
    highs = [float(b["high"]) for b in bars]
    volumes = [float(b["volume"]) for b in bars]
    latest = bars[-1]
    latest_date = str(latest.get("date", "")).strip()
    close = float(latest["close"]) if latest.get("close") is not None else None
    rets = calculate_returns(closes, (1, 5, 20, 60))
    r1, r5, r20, r60 = rets.get(1), rets.get(5), rets.get(20), rets.get(60)
    vol_ratio = volume_ratio_25d_prior_mean(volumes)
    vol_avg25: float | None = None
    if len(volumes) >= 26:
        vol_avg25 = sum(volumes[-26:-1]) / 25.0
    breakout, _ = detect_high_breakout(highs, closes)
    high_dist = high_distance_vs_prior_high_pct(closes, highs)
    score, labels, categories, dq, reason = _score_and_labels(
        bar_count=len(bars),
        breakout=breakout,
        high_dist=high_dist,
        vol_ratio=vol_ratio,
        r5=r5,
        r20=r20,
        r60=r60,
        vol_avg25=vol_avg25,
    )
    return UsDiscoveryCandidate(
        symbol=sym,
        symbol_name=display_symbol(sym, market="us"),
        discovery_score=score,
        latest_date=latest_date,
        close=close,
        return_1d=r1,
        return_5d=r5,
        return_20d=r20,
        return_60d=r60,
        volume_ratio_25d=vol_ratio,
        high_distance_pct=high_dist,
        volume_status=_volume_status(volumes),
        labels=tuple(labels),
        categories=tuple(categories),
        data_quality=dq,
        bar_count=len(bars),
        reason=reason,
    )


def scan_us_universe(*, universe_file: Path | None = None, cache_dir: Path | None = None, limit: int = 20) -> UsDiscoveryScanResult:
    root = cache_dir or (OUTPUTS_DIR / REL_US_CACHE_ROOT)
    scope, symbols = resolve_universe(universe_file=universe_file, cache_dir=root)
    ranked: list[UsDiscoveryCandidate] = []
    insufficient: list[UsDiscoveryCandidate] = []
    for sym in symbols:
        loaded = load_us_daily_bars_cache(sym)
        if loaded is None:
            insufficient.append(
                UsDiscoveryCandidate(
                    symbol=sym,
                    symbol_name=display_symbol(sym, market="us"),
                    discovery_score=0,
                    latest_date="",
                    close=None,
                    return_1d=None,
                    return_5d=None,
                    return_20d=None,
                    return_60d=None,
                    volume_ratio_25d=None,
                    high_distance_pct=None,
                    volume_status="unknown",
                    labels=(),
                    categories=("insufficient_data",),
                    data_quality="invalid_bars",
                    bar_count=0,
                    reason="cache missing or invalid",
                )
            )
            continue
        bars, _meta = loaded
        row = analyze_symbol_for_discovery(sym, bars)
        if row.data_quality != "ok" or "insufficient_data" in row.categories:
            insufficient.append(row)
        else:
            ranked.append(row)

    def sort_key(c: UsDiscoveryCandidate) -> tuple[int, float, str]:
        r20v = float(c.return_20d) if c.return_20d is not None else -1e18
        return (-c.discovery_score, -r20v, c.symbol)

    ranked.sort(key=sort_key)
    if limit > 0:
        ranked = ranked[:limit]
    return UsDiscoveryScanResult(
        universe_scope=scope,
        generated_at=_utc_now_iso(),
        candidates=ranked,
        symbol_count=len(symbols),
        insufficient=insufficient,
    )


def candidate_to_dict(c: UsDiscoveryCandidate) -> dict[str, Any]:
    d = asdict(c)
    d["labels"] = list(c.labels)
    d["categories"] = list(c.categories)
    return d


def format_us_discovery_json(result: UsDiscoveryScanResult) -> dict[str, Any]:
    envelope = DiscoveryScanEnvelope(
        market=MARKET_US,
        universe_scope=result.universe_scope,
        generated_at=result.generated_at,
        symbol_count=result.symbol_count,
        ranked_candidate_count=len(result.candidates),
        insufficient_count=len(result.insufficient),
    )
    return build_discovery_json_payload(
        envelope=envelope,
        common_ranked=[us_candidate_to_common(c) for c in result.candidates],
        common_insufficient=[us_candidate_to_common(c) for c in result.insufficient],
        legacy_ranked=[candidate_to_dict(c) for c in result.candidates],
        legacy_insufficient=[candidate_to_dict(c) for c in result.insufficient],
    )


def format_us_discovery_markdown(result: UsDiscoveryScanResult) -> str:
    lines: list[str] = [
        "# US Universe Discovery Candidates",
        "",
        OBSERVATION_DISCLAIMER,
        "",
        DISCOVERY_SCORE_DISCLAIMER,
        "",
        "## Universe scope",
        f"- market: `{MARKET_US}`",
        f"- scope: `{result.universe_scope}`",
        f"- symbols scanned: {result.symbol_count}",
        f"- generated_at: {result.generated_at}",
        "- live_http: false",
        "",
        _RANKED_TABLE_HEADER,
        _RANKED_TABLE_SEPARATOR,
    ]
    for i, c in enumerate(result.candidates, start=1):
        lines.append(
            format_ranked_table_row(
                rank=i,
                display_name=c.symbol_name,
                row=c,
                close_digits=2,
                volume_status=c.volume_status,
            )
        )
    lines.extend(format_candidate_groups_markdown(result.candidates))
    lines.extend(format_insufficient_bullets_markdown(result.insufficient))
    lines.extend(format_next_research_checklist(market=MARKET_US))
    return "\n".join(lines)


def assert_no_forbidden_terms(text: str) -> None:
    lower = text.lower()
    for term in FORBIDDEN_OUTPUT_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", lower):
            raise ValueError(f"forbidden output term: {term}")
