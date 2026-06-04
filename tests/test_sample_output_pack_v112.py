from __future__ import annotations

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.product.sample_output_pack_v112 import render_sample_output_pack_markdown_v112


def test_v112_pack_includes_quality_quarantine_and_cross_review() -> None:
    markdown = render_sample_output_pack_markdown_v112()
    assert "Portfolio Data Quality Review" in markdown
    assert "Raw Input Quarantine Review" in markdown
    assert "Portfolio / Raw Input Quarantine Cross-Review" in markdown
    assert "Import Readiness: NO-GO" in markdown
    assert "fixture-only" in markdown


def test_v112_cli_stdout_only_markdown() -> None:
    result = CliRunner().invoke(app, ["sample-output-pack", "--format", "markdown"])
    assert result.exit_code == 0
    assert "Sample Output Pack" in result.stdout
    assert "cache write ではなく" in result.stdout
