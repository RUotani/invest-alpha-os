"""Symbol display names (config-only)."""

from __future__ import annotations

from invis_alpha_os.reports.symbol_display_names import (
    display_name,
    display_symbol,
    format_us_preview_symbol_cell,
)


def test_jp_display_names() -> None:
    assert display_name("5802", market="jp") == "住友電工"
    assert display_name("6506", market="jp") == "安川電機"
    assert display_name("285A", market="jp") == "キオクシア"
    assert display_symbol("5802", market="jp") == "5802 住友電工"


def test_us_display_names() -> None:
    assert display_name("MSFT", market="us") == "Microsoft"
    assert display_name("NVDA", market="us") == "NVIDIA"
    assert format_us_preview_symbol_cell("MSFT") == "MSFT Microsoft"


def test_unknown_falls_back_to_code() -> None:
    assert display_name("ZZZZ", market="us") == "ZZZZ"
    assert display_symbol("ZZZZ", market="us") == "ZZZZ"
