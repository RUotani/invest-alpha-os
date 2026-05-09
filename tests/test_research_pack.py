from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.config.paths import OUTPUTS_DIR

runner = CliRunner()


def test_pack_generates_markdown():
    result = runner.invoke(app, ["pack", "--ticker", "7011"])
    assert result.exit_code == 0
    paths = list((OUTPUTS_DIR / "research_packs").glob("7011_*.md"))
    assert paths
    assert Path(paths[-1]).read_text(encoding="utf-8").startswith("# Research Pack")

