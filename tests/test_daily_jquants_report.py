"""Task 7–8: J-Quants daily report section (no HTTP)."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app, JQuantsClient
from invis_alpha_os.config.jp_watchlist import jquants_daily_bars_ticker_kind, load_jp_watchlist_tickers
from invis_alpha_os.config.paths import OUTPUTS_DIR
from invis_alpha_os.reports.jquants_watchlist_daily import (
    JQuantsDryRunFacts,
    classify_jquants_daily_readiness,
    render_jquants_watchlist_bars_check_section,
)

runner = CliRunner()

_FAKE_KEY = "SUPER_SECRET_JQUANTS_KEY_NEVER_PRINT_99999"


@pytest.fixture
def jq_data_guard_env(monkeypatch):
    """Bounds both set and parse so readiness can be Green in CI/tests."""
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_FROM", "2024-01-01")
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_TO", "2025-12-31")


def test_daily_report_readiness_green(jq_data_guard_env):
    tickers = load_jp_watchlist_tickers()
    target_n = len(tickers)
    unsupported_n = sum(1 for t in tickers if jquants_daily_bars_ticker_kind(t) != "ok")
    supported_n = target_n - unsupported_n

    result = runner.invoke(app, ["daily"])
    assert result.exit_code == 0
    today = date.today().isoformat()
    path = OUTPUTS_DIR / "reports" / "daily" / f"{today}.md"
    body = path.read_text(encoding="utf-8")
    assert "## J-Quants Watchlist Bars Check" in body
    assert "- Readiness: Green" in body
    assert "Mode: dry_run" in body
    assert f"Unsupported code count: {unsupported_n}" in body
    assert f"Supported code count: {supported_n}" in body
    assert f"Target count: {target_n}" in body
    assert "- Unsupported codes skipped: 285A" in body
    assert "### Local smoke test record" in body
    assert "Task 7 spec-style field examples" in body
    assert "7974 / 2024-02-16" in body
    assert "7011, 6501, 6506" in body
    assert "documented reference" in body.lower()
    assert "Raw response included: false" in body
    assert "api key displayed: false" in body.lower()


def test_daily_report_readiness_yellow_without_guard(monkeypatch):
    monkeypatch.delenv("JQUANTS_DATA_AVAILABLE_FROM", raising=False)
    monkeypatch.delenv("JQUANTS_DATA_AVAILABLE_TO", raising=False)

    result = runner.invoke(app, ["daily"])
    assert result.exit_code == 0
    today = date.today().isoformat()
    body = (OUTPUTS_DIR / "reports" / "daily" / f"{today}.md").read_text(encoding="utf-8")
    assert "- Readiness: Yellow" in body
    assert "- Data availability guard: not enabled" in body


def test_daily_report_no_http_and_no_secrets(monkeypatch, jq_data_guard_env):
    monkeypatch.setenv("JQUANTS_API_KEY", _FAKE_KEY)

    def _boom(*_a, **_k):
        raise AssertionError("daily must not open HTTP connections")

    with patch("urllib.request.urlopen", side_effect=_boom):
        r = runner.invoke(app, ["daily"])
    assert r.exit_code == 0
    today = date.today().isoformat()
    body = (OUTPUTS_DIR / "reports" / "daily" / f"{today}.md").read_text(encoding="utf-8")
    assert _FAKE_KEY not in body
    low = body.lower()
    assert "x-api-key:" not in low


def test_render_section_omit_smoke_when_disabled(jq_data_guard_env):
    md = render_jquants_watchlist_bars_check_section(
        {
            "include_local_smoke_record": False,
            "readiness_green_requires_smoke_record": False,
        }
    )
    assert "### Local smoke test record" not in md
    assert "## J-Quants Watchlist Bars Check" in md


def test_daily_does_not_call_jquants_client_get_daily_quotes(jq_data_guard_env):
    m = MagicMock()
    with patch.object(JQuantsClient, "get_daily_quotes", m):
        r = runner.invoke(app, ["daily"])
    assert r.exit_code == 0
    m.assert_not_called()


def test_classify_readiness_green():
    assert (
        classify_jquants_daily_readiness(
            supported=10,
            watchlist_load_error=None,
            guard_enabled=True,
            include_smoke_record=True,
            raw_response_included=False,
            api_key_displayed=False,
            live_http_in_daily="disabled",
            readiness_green_requires_data_guard=True,
            readiness_green_requires_smoke_record=True,
        )
        == "green"
    )


def test_classify_readiness_yellow_when_guard_missing():
    assert (
        classify_jquants_daily_readiness(
            supported=10,
            watchlist_load_error=None,
            guard_enabled=False,
            include_smoke_record=True,
            raw_response_included=False,
            api_key_displayed=False,
            live_http_in_daily="disabled",
            readiness_green_requires_data_guard=True,
            readiness_green_requires_smoke_record=True,
        )
        == "yellow"
    )


def test_classify_readiness_red_supported_zero():
    assert (
        classify_jquants_daily_readiness(
            supported=0,
            watchlist_load_error=None,
            guard_enabled=True,
            include_smoke_record=True,
            raw_response_included=False,
            api_key_displayed=False,
            live_http_in_daily="disabled",
            readiness_green_requires_data_guard=True,
            readiness_green_requires_smoke_record=True,
        )
        == "red"
    )


def test_classify_readiness_red_live_http_enabled():
    assert (
        classify_jquants_daily_readiness(
            supported=10,
            watchlist_load_error=None,
            guard_enabled=True,
            include_smoke_record=True,
            raw_response_included=False,
            api_key_displayed=False,
            live_http_in_daily="enabled",
            readiness_green_requires_data_guard=True,
            readiness_green_requires_smoke_record=True,
        )
        == "red"
    )


def test_render_readiness_red_watchlist_load_error(monkeypatch):
    bad = JQuantsDryRunFacts(
        watchlist_load_error="watchlist_load_failed",
        tickers=(),
        unsupported_codes=(),
        supported=0,
        target_count=0,
        guard_enabled=False,
    )
    monkeypatch.setattr(
        "invis_alpha_os.reports.jquants_watchlist_daily.collect_jquants_dry_run_facts",
        lambda: bad,
    )

    md = render_jquants_watchlist_bars_check_section({"readiness_green_requires_smoke_record": False})
    assert "- Readiness: Red" in md
    assert "unavailable (watchlist load failed)" in md.lower()
