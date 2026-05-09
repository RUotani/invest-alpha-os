from typer.testing import CliRunner

from invis_alpha_os.cli.main import app

runner = CliRunner()


def test_status_command():
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Observation Only" in result.stdout


def test_config_check_command():
    result = runner.invoke(app, ["config-check"])
    assert result.exit_code == 0
    assert "OK" in result.stdout

