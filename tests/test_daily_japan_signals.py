from datetime import date

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.config.paths import OUTPUTS_DIR

runner = CliRunner()


def test_daily_report_has_japan_signals_section():
    result = runner.invoke(app, ["daily"])
    assert result.exit_code == 0
    today = date.today().isoformat()
    path = OUTPUTS_DIR / "reports" / "daily" / f"{today}.md"
    body = path.read_text(encoding="utf-8")
    assert "## Japan Signals" in body
    assert "Watchlist count:" in body
