"""R6.17: Opt-in US cache preview on daily report (read-only)."""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli import main as cli_main
from invis_alpha_os.cli.main import app
from invis_alpha_os.config.paths import OUTPUTS_DIR
from invis_alpha_os.reports.us_cache_preview_opt_in import (
    _OPT_IN_HEADER,
    build_us_cache_opt_in_preview,
    build_us_cache_opt_in_preview_row,
    preview_note_for_freshness,
    render_us_cache_opt_in_preview_markdown,
)

runner = CliRunner()
REPO = Path(__file__).resolve().parents[1]
FIX_MINIMAL = REPO / "tests" / "fixtures" / "us_equities" / "minimal_msft_envelope.json"
FIX_25 = REPO / "tests" / "fixtures" / "us_equities" / "msft_25bars_metrics_envelope.json"
_FORBIDDEN = (
    "recommendation",
    "allocation",
    "portfolio",
    "buy",
    "sell",
    "veto",
    "macro",
    "production",
)


def _preview_section_text(body: str) -> str:
    """Isolate opt-in preview markdown (exclude JP header / other sections)."""

    if _OPT_IN_HEADER not in body:
        return ""
    return body[body.index(_OPT_IN_HEADER) :]


def _assert_preview_forbidden_terms(text: str) -> None:
    lowered = text.lower()
    for word in _FORBIDDEN:
        assert word not in lowered, f"forbidden term in preview section: {word!r}"


def _daily_body(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *extra_args: str) -> str:
    monkeypatch.setattr(cli_main, "_jquants_report_settings", lambda: {"include_watchlist_bars_check": False})
    monkeypatch.setattr(
        "invis_alpha_os.cli.main._daily_report_momentum_sections_flags",
        lambda: (False, False, False),
    )
    monkeypatch.setattr("invis_alpha_os.reports.jquants_watchlist_daily.ROOT_DIR", tmp_path)
    out_root = tmp_path / "outputs"
    monkeypatch.setattr("invis_alpha_os.cli.main.OUTPUTS_DIR", out_root)
    monkeypatch.setattr("invis_alpha_os.reports.us_cache_preview_opt_in.OUTPUTS_DIR", out_root)
    r = runner.invoke(app, ["daily", *extra_args])
    assert r.exit_code == 0, r.stdout + r.stderr
    return (out_root / "reports" / "daily" / f"{cli_main.today_jst_iso()}.md").read_text(encoding="utf-8")


def test_preview_note_stale_and_unknown() -> None:
    assert preview_note_for_freshness("stale") == "stale — returns not used"
    assert preview_note_for_freshness("freshness_unknown") == "freshness unknown — returns not used"
    assert preview_note_for_freshness("fresh_enough") == ""


def test_stale_inventory_row_gets_stale_note() -> None:
    inv_row = {
        "symbol": "MSFT",
        "status": "ok",
        "freshness_status": "stale",
        "latest_date": "2024-01-26",
        "last_date": "2024-01-26",
        "path": str(FIX_25.resolve()),
        "live_http": False,
    }
    row = build_us_cache_opt_in_preview_row(inv_row)
    assert row["freshness_status"] == "stale"
    assert row["note"] == "stale — returns not used"
    assert row["return_1d"] is not None


def test_render_includes_allowed_columns_only() -> None:
    preview = {
        "status": "ok",
        "rows": [
            {
                "symbol": "SPY",
                "latest_date": "2024-01-03",
                "freshness_status": "fresh_enough",
                "close": 100.0,
                "return_1d": 0.01,
                "return_5d": 0.02,
                "return_20d": 0.03,
                "volume_status": "normal",
                "note": "",
            }
        ],
        "stale_count": 0,
        "benchmark_warnings": [],
        "missing_symbols": [],
    }
    md = render_us_cache_opt_in_preview_markdown(preview)
    assert "| symbol | latest_date | freshness_status | close | return_1d |" in md
    assert "SPY" in md
    _assert_preview_forbidden_terms(md)


def test_daily_default_excludes_us_cache_preview(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    body = _daily_body(monkeypatch, tmp_path)
    assert _OPT_IN_HEADER not in body


def test_daily_opt_in_includes_us_cache_preview(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cache_dir = tmp_path / "outputs" / "market_data" / "us_daily_bars"
    cache_dir.mkdir(parents=True)
    shutil.copy(FIX_MINIMAL, cache_dir / "msft.json")
    body = _daily_body(monkeypatch, tmp_path, "--us-cache-preview")
    assert _OPT_IN_HEADER in body
    assert "MSFT" in body
    assert "**live_http**: false" in body
    _assert_preview_forbidden_terms(_preview_section_text(body))


def test_daily_opt_in_no_cache_write_guard(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("daily --us-cache-preview must not write cache")

    monkeypatch.setattr(
        "invis_alpha_os.data.us_daily_bars_cache.save_us_daily_bars_cache",
        _boom,
    )
    _daily_body(monkeypatch, tmp_path, "--us-cache-preview")


def test_daily_opt_in_no_live_http_guard(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import urllib.request

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("daily --us-cache-preview must not use live HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    _daily_body(monkeypatch, tmp_path, "--us-cache-preview")
