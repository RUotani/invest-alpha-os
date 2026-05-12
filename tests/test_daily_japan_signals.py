from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.config.paths import OUTPUTS_DIR
from invis_alpha_os.utils.date_utils import today_jst_iso


runner = CliRunner()


def test_daily_report_has_japan_signals_section():
    result = runner.invoke(app, ["daily"])
    assert result.exit_code == 0
    today = today_jst_iso()
    path = OUTPUTS_DIR / "reports" / "daily" / f"{today}.md"
    body = path.read_text(encoding="utf-8")
    assert "## Japan Signals" in body
    assert "Watchlist count:" in body
    assert "## Momentum Signals" in body
    assert "Observation only" in body
    assert "**Bars source:**" in body
    assert "synthetic" in body.lower() or "cache" in body.lower()
    assert "not actionable" in body.lower()
