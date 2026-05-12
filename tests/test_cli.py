from typer.testing import CliRunner

from invis_alpha_os.cli.main import app

runner = CliRunner()


def test_daily_output_path_uses_jst_date_label(monkeypatch):
    monkeypatch.setattr("invis_alpha_os.cli.main.today_jst_iso", lambda: "2031-07-15")
    r = runner.invoke(app, ["daily"])
    assert r.exit_code == 0
    assert "daily" in r.stdout
    assert "2031-07-15.md" in r.stdout


def test_pack_output_path_uses_jst_date_label(monkeypatch):
    monkeypatch.setattr("invis_alpha_os.cli.main.today_jst_iso", lambda: "2031-07-15")
    r = runner.invoke(app, ["pack", "--ticker", "7011"])
    assert r.exit_code == 0
    assert "7011_2031-07-15.md" in r.stdout


def test_status_command():
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Observation Only" in result.stdout


def test_config_check_command():
    result = runner.invoke(app, ["config-check"])
    assert result.exit_code == 0
    assert "OK" in result.stdout

