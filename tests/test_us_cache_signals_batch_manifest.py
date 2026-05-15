"""R6.12-C: explicit US cache signals batch manifest (no HTTP; no auto scan)."""

from __future__ import annotations

from pathlib import Path

import pytest

from invis_alpha_os.data.us_cache_signals_batch_manifest import (
    build_us_cache_signals_previews_from_batch_manifest,
    load_us_cache_signals_batch_manifest_json_file,
    parse_us_cache_signals_batch_manifest_payload,
)
from invis_alpha_os.reports.us_signals_dry_run import (
    render_us_cache_signals_multi_symbol_dry_run_section,
)

REPO = Path(__file__).resolve().parents[1]
FIX_MANIFEST = REPO / "tests" / "fixtures" / "us_equities" / "us_cache_signals_batch_minimal.json"


@pytest.fixture(autouse=True)
def _block_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("batch manifest tests must not use live HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)


def test_parse_manifest_minimal() -> None:
    loaded = load_us_cache_signals_batch_manifest_json_file(FIX_MANIFEST)
    assert loaded is not None
    assert loaded["entry_count"] == 2
    assert loaded["universe_path"] is not None


def test_build_previews_from_manifest_ok() -> None:
    out = build_us_cache_signals_previews_from_batch_manifest(FIX_MANIFEST, path_base=REPO)
    assert out["status"] == "ok"
    assert out["entry_count"] == 2
    previews = out["previews"]
    assert previews[0]["status"] == "ok"
    assert previews[0]["universe_status"] == "matched"
    assert previews[1]["status"] == "skipped_insufficient_bars"


def test_manifest_invalid_file() -> None:
    out = build_us_cache_signals_previews_from_batch_manifest(
        Path("/no/manifest.json"), path_base=REPO
    )
    assert out["status"] == "invalid"
    assert out["reason"] == "manifest_invalid"
    assert out["previews"] == []


def test_manifest_to_multi_symbol_dry_run_golden() -> None:
    out = build_us_cache_signals_previews_from_batch_manifest(FIX_MANIFEST, path_base=REPO)
    md = render_us_cache_signals_multi_symbol_dry_run_section(out["previews"])
    assert "## US Signals Dry Run" in md
    assert md.count("| MSFT |") == 2
    assert "| uptrend_aligned |" in md
    assert "| skipped |" in md


def test_parse_rejects_bad_entry() -> None:
    bad = {
        "schema_version": 1,
        "entries": [{"symbol": "MSFT"}],
    }
    assert parse_us_cache_signals_batch_manifest_payload(bad) is None
