"""Infer JP ticker codes from Stooq/manual CSV filenames (metadata only)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from invis_alpha_os.config.jp_watchlist import normalize_jquants_equity_code

STOOQ_CSV_EXCLUDE_NAMES: frozenset[str] = frozenset(
    {
        "manual_jp_bars.csv",
        "manual_jp_bars.tsv",
        "manual_jp_bars_template.csv",
        "manual_data_intermediate_2026-05-29.csv",
        "paste_ohlcv_here.tsv",
    }
)

_TICKER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"stooq[_-]?(\d{3,4}[0-9A-Za-z]?)", re.I),
    re.compile(r"^(\d{3,4}[0-9A-Za-z]?)\.jp", re.I),
    re.compile(r"^(\d{3,4}[0-9A-Za-z]?)[_.-]", re.I),
    re.compile(r"^(\d{3,4}[0-9A-Za-z]?)$", re.I),
)


@dataclass(frozen=True)
class TickerInferenceResult:
    ticker: str | None
    confidence: str
    reason: str


def _stem_token(path: Path) -> str:
    return path.stem.strip()


def infer_ticker_from_filename(path: Path) -> TickerInferenceResult:
    stem = _stem_token(path)
    if not stem:
        return TickerInferenceResult(None, "none", "empty_stem")
    for pattern in _TICKER_PATTERNS:
        match = pattern.search(stem)
        if not match:
            continue
        raw = match.group(1).upper()
        wire = normalize_jquants_equity_code(raw)
        if wire:
            conf = "high" if stem.upper() in {wire, f"{wire}.JP", f"{wire}_JP"} else "medium"
            return TickerInferenceResult(wire, conf, f"pattern:{pattern.pattern[:24]}")
    return TickerInferenceResult(None, "none", "no_pattern_match")


def is_stooq_candidate_filename(name: str) -> bool:
    lowered = name.lower()
    if lowered in {n.lower() for n in STOOQ_CSV_EXCLUDE_NAMES}:
        return False
    if lowered.startswith("readme"):
        return False
    if lowered.endswith("_template.csv"):
        return False
    return lowered.endswith((".csv", ".tsv", ".txt"))
