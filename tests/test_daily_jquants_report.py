"""Task 7: J-Quants section in daily report (no HTTP)."""

from datetime import date
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app, JQuantsClient
from invis_alpha_os.config.jp_watchlist import jquants_daily_bars_ticker_kind, load_jp_watchlist_tickers
from invis_alpha_os.config.paths import OUTPUTS_DIR
from invis_alpha_os.reports.jquants_watchlist_daily import render_jquants_watchlist_bars_check_section

runner = CliRunner()

_FAKE_KEY = "SUPER_SECRET_JQUANTS_KEY_NEVER_PRINT_99999"


def test_daily_report_contains_jquants_watchlist_section():
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
    assert "Mode: dry_run" in body
    assert f"Unsupported code count: {unsupported_n}" in body
    assert f"Supported code count: {supported_n}" in body
    assert f"Target count: {target_n}" in body
    assert "### Local smoke test record" in body
    assert "Task 7 spec-style field examples" in body
    assert "7974 / 2024-02-16" in body
    assert "7011, 6501, 6506" in body
    assert "Raw response included: false" in body
    assert "api key displayed: false" in body.lower()


def test_daily_report_no_http_and_no_secrets(monkeypatch):
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


def test_render_section_omit_smoke_when_disabled():
    md = render_jquants_watchlist_bars_check_section({"include_local_smoke_record": False})
    assert "### Local smoke test record" not in md
    assert "## J-Quants Watchlist Bars Check" in md


def test_daily_does_not_call_jquants_client_get_daily_quotes():
    m = MagicMock()
    with patch.object(JQuantsClient, "get_daily_quotes", m):
        r = runner.invoke(app, ["daily"])
    assert r.exit_code == 0
    m.assert_not_called()
