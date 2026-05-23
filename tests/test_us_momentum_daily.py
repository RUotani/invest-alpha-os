"""Main R: US momentum render skeleton (offline)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data import us_daily_bars_cache as usc
from invis_alpha_os.reports import momentum_daily as md
from invis_alpha_os.reports.momentum_daily import render_us_momentum_cache_only_section


@pytest.fixture(autouse=True)
def _reject_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    def _boom(*_a, **_k):
        raise AssertionError("live HTTP must not be used in US skeleton render tests")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)


@pytest.fixture(autouse=True)
def _patch_us_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(usc, "OUTPUTS_DIR", tmp_path)


def test_render_us_momentum_without_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(md, "load_us_watchlist_tickers", lambda: ["MSFT"])

    txt = render_us_momentum_cache_only_section()
    assert "## Momentum Signals — US Cache Only" in txt
    assert "No cached US watchlist tickers yet" in txt
    assert "No live data fetch" in txt
    assert "us_daily_bars" in txt


def test_render_us_momentum_with_one_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(md, "load_us_watchlist_tickers", lambda: ["MSFT", "QQQ"])

    bars: list[dict] = []
    start = date(2023, 1, 3)
    price = 100.0
    for i in range(140):
        d = (start + timedelta(days=i)).isoformat()
        o, h, l, c = price, price * 1.01, price * 0.99, price * 1.002
        vol = 2_500_000.0 + float(i % 101) * 10_000.0
        bars.append({"date": d, "open": o, "high": h, "low": l, "close": c, "volume": vol})
        price = c

    usc.save_us_daily_bars_cache(
        "MSFT",
        bars,
        asset_class="us_equity",
        fetched_at="2026-05-09T12:00:00+00:00",
        generated_at="2026-05-09T12:00:05+00:00",
    )

    txt = render_us_momentum_cache_only_section()
    assert "## Momentum Signals — US Cache Only" in txt
    assert "| MSFT |" in txt
    assert " cache " in txt.replace("|", " | ")
    assert "QQQ" in txt


def test_us_watchlist_preview_makefile_lists_target() -> None:
    from pathlib import Path

    makefile = Path(__file__).resolve().parents[1] / "Makefile"
    m = makefile.read_text(encoding="utf-8")
    assert "\nus-watchlist-preview:" in m or m.startswith("us-watchlist-preview:")
    assert ".PHONY" in m and "us-watchlist-preview" in m


def test_cli_us_watchlist_preview_runs() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["us-watchlist-preview"])
    assert result.exit_code == 0, result.stdout + result.stderr
    lines = result.stdout.strip().splitlines()
    assert lines[0] == "US watchlist symbols:"
    assert "MSFT" in lines


def test_daily_us_momentum_section_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import invis_alpha_os.cli.main as cli_main

    monkeypatch.setattr(cli_main, "OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(md, "load_us_watchlist_tickers", lambda: ["MSFT"])

    bars: list[dict] = []
    start = date(2023, 1, 3)
    price = 100.0
    for i in range(140):
        d = (start + timedelta(days=i)).isoformat()
        o, h, l, c = price, price * 1.01, price * 0.99, price * 1.002
        vol = 2_500_000.0 + float(i % 101) * 10_000.0
        bars.append({"date": d, "open": o, "high": h, "low": l, "close": c, "volume": vol})
        price = c

    usc.save_us_daily_bars_cache(
        "MSFT",
        bars,
        asset_class="us_equity",
        fetched_at="2026-05-09T12:00:00+00:00",
        generated_at="2026-05-09T12:00:05+00:00",
    )

    result = CliRunner().invoke(app, ["daily", "--us-momentum-section"])
    assert result.exit_code == 0, result.stdout + result.stderr
    report = (tmp_path / "reports" / "daily").glob("*.md")
    body = next(report).read_text(encoding="utf-8")
    assert "## Momentum Signals — US Cache Only" in body
    assert "| MSFT |" in body
