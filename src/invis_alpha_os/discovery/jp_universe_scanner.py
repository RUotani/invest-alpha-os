"""JP universe discovery scanner MVP — cache/fixture input only; observation-only output."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from invis_alpha_os.config.loader import load_yaml
from invis_alpha_os.config.paths import CONFIG_DIR, OUTPUTS_DIR
from invis_alpha_os.data.jquants_daily_bars_cache import REL_CACHE_ROOT, load_jquants_daily_bars_cache
from invis_alpha_os.reports.symbol_display_names import display_symbol
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
LOW_LIQUIDITY_AVG25_THRESHOLD = 500.0

DISCOVERY_SCORE_DISCLAIMER = (
    "Discovery score is only a sorting aid for follow-up research, not trading advice."
)

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

_OBSERVATION_DISCLAIMER = (
    "Observation only — not trading advice. No automatic trading."
)


@dataclass(frozen=True)
class JpDiscoveryCandidate:
    code: str
    code_name: str
    discovery_score: int
    latest_date: str
    close: float | None
    return_1d: float | None
    return_5d: float | None
    return_20d: float | None
    return_60d: float | None
    volume_ratio_25d: float | None
    high_distance_pct: float | None
    labels: tuple[str, ...]
    categories: tuple[str, ...]
    data_quality: str
    bar_count: int
    reason: str


@dataclass
class JpDiscoveryScanResult:
    universe_scope: str
    generated_at: str
    candidates: list[JpDiscoveryCandidate] = field(default_factory=list)
    symbol_count: int = 0
    insufficient: list[JpDiscoveryCandidate] = field(default_factory=list)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt_pct(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{100.0 * x:.1f}%"


def _fmt_num(x: float | None, *, digits: int = 2) -> str:
    if x is None:
        return "—"
    return f"{x:,.{digits}f}"


def load_universe_spec(universe_file: Path | None) -> tuple[str, list[str]]:
    if universe_file is None:
        return "", []
    data = load_yaml(universe_file)
    scope = str(data.get("universe_scope") or "sample_jp_universe").strip()
    raw = data.get("symbols") or data.get("codes") or []
    if not isinstance(raw, list):
        raise ValueError("universe file symbols must be a list")
    codes = [str(x).strip().upper() for x in raw if str(x).strip()]
    return scope, codes


def list_local_jp_cache_codes(cache_dir: Path) -> list[str]:
    if not cache_dir.is_dir():
        return []
    codes: list[str] = []
    for path in sorted(cache_dir.glob("*.json")):
        stem = path.stem.strip().upper()
        if stem:
            codes.append(stem)
    return codes


def resolve_universe(
    *,
    universe_file: Path | None,
    cache_dir: Path,
) -> tuple[str, list[str]]:
    if universe_file is not None:
        scope, codes = load_universe_spec(universe_file)
        if not scope:
            scope = "sample_jp_universe"
        return scope, codes
    codes = list_local_jp_cache_codes(cache_dir)
    return "local_cache_available_symbols", codes


def _load_bars_for_code(code: str) -> tuple[list[DailyBar], str] | None:
    loaded = load_jquants_daily_bars_cache(code)
    if loaded is None:
        return None
    bars, _meta = loaded
    if not bars:
        return None
    return bars, "cache"


def _discovery_overheat(r20: float | None, r60: float | None) -> bool:
    if r20 is not None and r20 >= OVERHEAT_R20_THRESHOLD:
        return True
    if r60 is not None and r60 >= OVERHEAT_R60_THRESHOLD:
        return True
    return False


def _compute_discovery_score_and_labels(
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
        if "rapid_mover" not in categories:
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

    reason_parts: list[str] = []
    if labels:
        reason_parts.append("surfaced: " + ", ".join(labels))
    else:
        reason_parts.append("no discovery labels (follow-up optional)")
    if vol_avg25 is not None and vol_avg25 < LOW_LIQUIDITY_AVG25_THRESHOLD:
        reason_parts.append("liquidity check advised")

    return score, labels, categories, "ok", " ".join(reason_parts)


def analyze_code_for_discovery(code: str, bars: Sequence[DailyBar]) -> JpDiscoveryCandidate:
    code_u = code.strip().upper()
    if not bars:
        return JpDiscoveryCandidate(
            code=code_u,
            code_name=display_symbol(code_u, market="jp"),
            discovery_score=0,
            latest_date="",
            close=None,
            return_1d=None,
            return_5d=None,
            return_20d=None,
            return_60d=None,
            volume_ratio_25d=None,
            high_distance_pct=None,
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
        window = volumes[-26:-1]
        vol_avg25 = sum(window) / 25.0

    breakout, _ = detect_high_breakout(highs, closes)
    high_dist = high_distance_vs_prior_high_pct(closes, highs)

    score, labels, categories, dq, reason = _compute_discovery_score_and_labels(
        bar_count=len(bars),
        breakout=breakout,
        high_dist=high_dist,
        vol_ratio=vol_ratio,
        r5=r5,
        r20=r20,
        r60=r60,
        vol_avg25=vol_avg25,
    )

    return JpDiscoveryCandidate(
        code=code_u,
        code_name=display_symbol(code_u, market="jp"),
        discovery_score=score,
        latest_date=latest_date,
        close=close,
        return_1d=r1,
        return_5d=r5,
        return_20d=r20,
        return_60d=r60,
        volume_ratio_25d=vol_ratio,
        high_distance_pct=high_dist,
        labels=tuple(labels),
        categories=tuple(categories),
        data_quality=dq,
        bar_count=len(bars),
        reason=reason,
    )


def scan_jp_universe(
    *,
    universe_file: Path | None = None,
    cache_dir: Path | None = None,
    limit: int = 20,
) -> JpDiscoveryScanResult:
    root = cache_dir or (OUTPUTS_DIR / REL_CACHE_ROOT)
    scope, codes = resolve_universe(universe_file=universe_file, cache_dir=root)
    generated_at = _utc_now_iso()

    ranked: list[JpDiscoveryCandidate] = []
    insufficient: list[JpDiscoveryCandidate] = []

    for code in codes:
        loaded = _load_bars_for_code(code)
        if loaded is None:
            insufficient.append(
                JpDiscoveryCandidate(
                    code=code,
                    code_name=display_symbol(code, market="jp"),
                    discovery_score=0,
                    latest_date="",
                    close=None,
                    return_1d=None,
                    return_5d=None,
                    return_20d=None,
                    return_60d=None,
                    volume_ratio_25d=None,
                    high_distance_pct=None,
                    labels=(),
                    categories=("insufficient_data",),
                    data_quality="invalid_bars",
                    bar_count=0,
                    reason="cache missing or invalid",
                )
            )
            continue
        bars, _src = loaded
        row = analyze_code_for_discovery(code, bars)
        if row.data_quality != "ok" or "insufficient_data" in row.categories:
            insufficient.append(row)
        else:
            ranked.append(row)

    def sort_key(c: JpDiscoveryCandidate) -> tuple[int, float, str]:
        r20v = float(c.return_20d) if c.return_20d is not None else -1e18
        return (-c.discovery_score, -r20v, c.code)

    ranked.sort(key=sort_key)
    if limit > 0:
        ranked = ranked[:limit]

    return JpDiscoveryScanResult(
        universe_scope=scope,
        generated_at=generated_at,
        candidates=ranked,
        symbol_count=len(codes),
        insufficient=insufficient,
    )


def candidate_to_dict(c: JpDiscoveryCandidate) -> dict[str, Any]:
    d = asdict(c)
    d["labels"] = list(c.labels)
    d["categories"] = list(c.categories)
    return d


def format_jp_discovery_json(result: JpDiscoveryScanResult) -> dict[str, Any]:
    return {
        "universe_scope": result.universe_scope,
        "generated_at": result.generated_at,
        "safety": {
            "observation_only": True,
            "no_trading_advice": True,
            "discovery_score_disclaimer": DISCOVERY_SCORE_DISCLAIMER,
        },
        "summary": {
            "symbol_count": result.symbol_count,
            "ranked_candidate_count": len(result.candidates),
            "insufficient_count": len(result.insufficient),
        },
        "candidates": [candidate_to_dict(c) for c in result.candidates],
        "insufficient": [candidate_to_dict(c) for c in result.insufficient],
    }


def _group_candidates(
    candidates: Sequence[JpDiscoveryCandidate],
    category: str,
) -> list[JpDiscoveryCandidate]:
    return [c for c in candidates if category in c.categories]


def format_jp_discovery_markdown(result: JpDiscoveryScanResult) -> str:
    lines: list[str] = [
        "# JP Universe Discovery Candidates",
        "",
        _OBSERVATION_DISCLAIMER,
        "",
        DISCOVERY_SCORE_DISCLAIMER,
        "",
        "## Universe scope",
        f"- scope: `{result.universe_scope}`",
        f"- symbols scanned: {result.symbol_count}",
        f"- generated_at: {result.generated_at}",
        "",
        "| rank | code/name | discovery_score | latest_date | close | r5 | r20 | r60 | vol_ratio | high_dist | labels | data_quality |",
        "|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]

    for i, c in enumerate(result.candidates, start=1):
        lines.append(
            "| {rank} | {name} | {score} | {date} | {close} | {r5} | {r20} | {r60} | {vr} | {hd} | {labels} | {dq} |".format(
                rank=i,
                name=c.code_name,
                score=c.discovery_score,
                date=c.latest_date or "—",
                close=_fmt_num(c.close, digits=0),
                r5=_fmt_pct(c.return_5d),
                r20=_fmt_pct(c.return_20d),
                r60=_fmt_pct(c.return_60d),
                vr=_fmt_num(c.volume_ratio_25d),
                hd=_fmt_pct(c.high_distance_pct),
                labels=", ".join(c.labels) if c.labels else "—",
                dq=c.data_quality,
            )
        )

    def section(title: str, cat: str) -> None:
        rows = _group_candidates(result.candidates, cat)
        lines.extend(["", f"### {title}"])
        if not rows:
            lines.append("- (none in ranked set)")
            return
        for c in rows:
            lines.append(f"- **{c.code_name}** — {c.reason}")

    lines.extend(["", "## Candidate Groups"])
    section("Rapid movers", "rapid_mover")
    section("Volume spikes", "volume_spike")
    section("Near/new highs", "new_breakout_candidate")
    section("Near-high quality trend", "near_high_quality_trend")
    section("Overheat caution", "overheated_caution")
    section("Insufficient data", "insufficient_data")

    if result.insufficient:
        lines.extend(["", "### Insufficient data (not ranked)"])
        for c in result.insufficient[:15]:
            lines.append(f"- **{c.code_name}** — {c.data_quality}: {c.reason}")

    lines.extend(
        [
            "",
            "## Next Research Checklist",
            "- latest news / disclosure",
            "- earnings",
            "- valuation",
            "- liquidity",
            "- sector/theme",
            "- existing holdings",
            "",
        ]
    )
    return "\n".join(lines)


def assert_no_forbidden_terms(text: str) -> None:
    lower = text.lower()
    for term in FORBIDDEN_OUTPUT_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", lower):
            raise ValueError(f"forbidden output term: {term}")
