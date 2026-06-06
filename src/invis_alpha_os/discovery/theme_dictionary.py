"""Static theme dictionary and fixture ticker mappings (v1.4 cache-only)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from invis_alpha_os.discovery.candidate_roles import CandidateRole


class ThemeId(str, Enum):
    NAND_MEMORY = "nand_memory"
    SEMICONDUCTOR_EQUIPMENT = "semiconductor_equipment"
    AI_INFRASTRUCTURE = "ai_infrastructure"
    DATA_CENTER_POWER = "data_center_power"
    NUCLEAR_ENERGY = "nuclear_energy"
    DEFENSE = "defense"
    HEALTHCARE = "healthcare"
    GOLD_PRECIOUS_METALS = "gold_precious_metals"
    CRYPTO_RELATED = "crypto_related"
    JP_VALUE_FINANCIALS = "jp_value_financials"
    US_EQUITY = "us_equity"
    US_ETF = "us_etf"


THEME_LABEL_JA: dict[ThemeId, str] = {
    ThemeId.NAND_MEMORY: "NAND / Memory",
    ThemeId.SEMICONDUCTOR_EQUIPMENT: "Semiconductor Equipment",
    ThemeId.AI_INFRASTRUCTURE: "AI Infrastructure",
    ThemeId.DATA_CENTER_POWER: "Data Center Power",
    ThemeId.NUCLEAR_ENERGY: "Nuclear / Energy",
    ThemeId.DEFENSE: "Defense",
    ThemeId.HEALTHCARE: "Healthcare",
    ThemeId.GOLD_PRECIOUS_METALS: "Gold / Precious Metals",
    ThemeId.CRYPTO_RELATED: "Crypto Related",
    ThemeId.JP_VALUE_FINANCIALS: "Japanese Value / Financials",
    ThemeId.US_EQUITY: "US Equity",
    ThemeId.US_ETF: "US ETF / Index",
}


@dataclass(frozen=True)
class TickerThemeEntry:
    ticker: str
    themes: tuple[ThemeId, ...]
    role_hint: CandidateRole | None = None
    display_name: str | None = None


FIXTURE_TICKER_THEMES: dict[str, TickerThemeEntry] = {
    "285A": TickerThemeEntry(
        ticker="285A",
        themes=(ThemeId.NAND_MEMORY,),
        role_hint=CandidateRole.THEME_PROXY,
        display_name="キオクシア",
    ),
    "AAPL": TickerThemeEntry(
        ticker="AAPL",
        themes=(ThemeId.AI_INFRASTRUCTURE, ThemeId.US_EQUITY),
        role_hint=CandidateRole.DEEP_DIVE,
        display_name="Apple",
    ),
    "QQQ": TickerThemeEntry(
        ticker="QQQ",
        themes=(ThemeId.AI_INFRASTRUCTURE, ThemeId.US_ETF),
        role_hint=CandidateRole.WATCH,
        display_name="Nasdaq 100 ETF",
    ),
    "NVDA": TickerThemeEntry(
        ticker="NVDA",
        themes=(ThemeId.AI_INFRASTRUCTURE, ThemeId.US_EQUITY),
        role_hint=CandidateRole.WATCH,
    ),
    "MSFT": TickerThemeEntry(
        ticker="MSFT",
        themes=(ThemeId.AI_INFRASTRUCTURE, ThemeId.US_EQUITY),
        role_hint=CandidateRole.DEEP_DIVE,
    ),
}


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def lookup_ticker_entry(ticker: str) -> TickerThemeEntry | None:
    return FIXTURE_TICKER_THEMES.get(normalize_ticker(ticker))


def lookup_ticker_themes(ticker: str) -> tuple[ThemeId, ...]:
    entry = lookup_ticker_entry(ticker)
    if entry is None:
        return ()
    return entry.themes


def lookup_theme_labels(theme_ids: tuple[ThemeId, ...]) -> tuple[str, ...]:
    return tuple(THEME_LABEL_JA[t] for t in theme_ids if t in THEME_LABEL_JA)


def role_hint_for_ticker(ticker: str) -> CandidateRole | None:
    entry = lookup_ticker_entry(ticker)
    return entry.role_hint if entry else None


def is_theme_proxy_ticker(ticker: str) -> bool:
    hint = role_hint_for_ticker(ticker)
    return hint in {CandidateRole.THEME_PROXY, CandidateRole.DO_NOT_CHASE}
