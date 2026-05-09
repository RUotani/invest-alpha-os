from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.config.paths import OUTPUTS_DIR

runner = CliRunner()


def test_log_outcome_creates_jsonl():
    out_path = OUTPUTS_DIR / "outcome_log" / "outcome_log.jsonl"
    if out_path.exists():
        out_path.unlink()
    result = runner.invoke(app, ["log", "outcome", "--symbol", "7011", "--result", "neutral"])
    assert result.exit_code == 0
    assert out_path.exists()
    assert out_path.read_text(encoding="utf-8").strip()

