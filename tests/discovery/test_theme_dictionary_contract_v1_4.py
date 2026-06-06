from __future__ import annotations

from invis_alpha_os.discovery.candidate_roles import CandidateRole, is_early_discovery_role
from invis_alpha_os.discovery.theme_dictionary import (
    ThemeId,
    lookup_theme_labels,
    lookup_ticker_themes,
    role_hint_for_ticker,
    is_theme_proxy_ticker,
)


def test_285a_maps_to_nand_memory_theme() -> None:
    themes = lookup_ticker_themes("285A")
    labels = lookup_theme_labels(themes)
    assert ThemeId.NAND_MEMORY in themes
    assert "NAND / Memory" in labels


def test_285a_role_hint_is_theme_proxy_not_early_discovery() -> None:
    hint = role_hint_for_ticker("285A")
    assert hint == CandidateRole.THEME_PROXY
    assert is_theme_proxy_ticker("285A")
    assert not is_early_discovery_role(hint)


def test_aapl_and_qqq_fixture_mappings() -> None:
    assert ThemeId.AI_INFRASTRUCTURE in lookup_ticker_themes("AAPL")
    assert ThemeId.US_ETF in lookup_ticker_themes("QQQ")
    assert role_hint_for_ticker("AAPL") == CandidateRole.DEEP_DIVE
    assert role_hint_for_ticker("QQQ") == CandidateRole.WATCH
