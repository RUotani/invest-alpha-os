"""R6.12-A: US signals report dry-run section (no HTTP; not wired to daily report)."""

from __future__ import annotations

from pathlib import Path

import pytest

from invis_alpha_os.data.us_cache_signals import (
    attach_us_asset_universe_metadata_to_signals_preview,
    build_us_cache_signals_preview,
)
from invis_alpha_os.reports.us_signals_dry_run import render_us_cache_signals_dry_run_section

REPO = Path(__file__).resolve().parents[1]
FIX_25 = REPO / "tests" / "fixtures" / "us_equities" / "msft_25bars_metrics_envelope.json"
FIX_MINIMAL = REPO / "tests" / "fixtures" / "us_equities" / "minimal_msft_envelope.json"
FIX_UNIVERSE = REPO / "tests" / "fixtures" / "us_equities" / "us_asset_universe_minimal.json"


@pytest.fixture(autouse=True)
def _block_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("US signals dry-run tests must not use live HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)


def test_dry_run_section_ok_matched_golden() -> None:
    preview = build_us_cache_signals_preview(FIX_25)
    preview = attach_us_asset_universe_metadata_to_signals_preview(preview, FIX_UNIVERSE)
    md = render_us_cache_signals_dry_run_section(preview)
    assert "## US Signals Dry Run" in md
    assert "dry-run" in md.lower()
    assert "not buy/sell" in md.lower()
    assert "| MSFT | us_equity | single_stock | uptrend_aligned |" in md
    assert "| matched |" in md or "| matched |" in md.split("\n")[-3]
    assert "**display_name**: Microsoft Corporation" in md
    assert "recommend" not in md.lower() or "not buy/sell" in md.lower()


def test_dry_run_section_skipped_with_universe() -> None:
    preview = build_us_cache_signals_preview(FIX_MINIMAL)
    preview = attach_us_asset_universe_metadata_to_signals_preview(preview, FIX_UNIVERSE)
    md = render_us_cache_signals_dry_run_section(preview)
    assert "| MSFT |" in md
    assert "| skipped |" in md
    assert "**status**: skipped_insufficient_bars" in md
    assert "| matched |" in md


def test_dry_run_section_invalid_universe() -> None:
    preview = build_us_cache_signals_preview(FIX_25)
    preview = attach_us_asset_universe_metadata_to_signals_preview(
        preview, Path("/no/universe.json")
    )
    md = render_us_cache_signals_dry_run_section(preview)
    assert "| universe_invalid |" in md
    assert "**status**: invalid" in md


def test_dry_run_section_without_universe_defaults() -> None:
    preview = build_us_cache_signals_preview(FIX_25)
    md = render_us_cache_signals_dry_run_section(preview)
    assert "| MSFT | — | — | uptrend_aligned |" in md
    assert "| — |" in md
