from __future__ import annotations

import json

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.product.operator_dashboard_summary import (
    build_operator_dashboard_summary,
    format_operator_dashboard_summary_json,
    render_operator_dashboard_summary_markdown,
)


def test_operator_dashboard_summary_covers_primary_queue_and_hard_gates() -> None:
    summary = build_operator_dashboard_summary()

    assert summary.schema_version == "operator_dashboard_summary.v1"
    by_key = {item.key: item for item in summary.queue_items}
    assert by_key["P1_scheduled_natural_run_observation"].status == "pending_not_yet_observable"
    assert by_key["P2_weekly_artifact_status_local_verification"].status == "ready"
    assert by_key["P3_weekly_monthly_golden_snapshots"].status == "ready"
    assert by_key["P4_operator_dashboard_cli_summary"].status == "ready"
    hard_gate_text = "\n".join(item.summary for item in summary.hard_gate_status)
    assert "provider/market-data live HTTPは未実行・未承認" in hard_gate_text
    assert "cache write / actual import / manual importは未実行・未承認" in hard_gate_text
    assert "workflow変更とmanual workflow_dispatchは未実行・未承認" in hard_gate_text


def test_operator_dashboard_summary_markdown_is_operator_readable() -> None:
    markdown = render_operator_dashboard_summary_markdown(build_operator_dashboard_summary())

    assert markdown.startswith("# Operator Dashboard Summary")
    assert "## Primary Queue" in markdown
    assert "## Hard Gate Status" in markdown
    assert "## Recommended Next Actions" in markdown
    assert "weekly-artifact-local-verify" in markdown
    assert "Actual Import Readinessは0%のまま" in markdown


def test_operator_dashboard_summary_json_is_machine_readable() -> None:
    payload = json.loads(format_operator_dashboard_summary_json(build_operator_dashboard_summary()))

    assert payload["schema_version"] == "operator_dashboard_summary.v1"
    assert payload["source_mode"] == "source_only_stdout_no_side_effects"
    assert payload["queue_items"][0]["key"] == "P1_scheduled_natural_run_observation"
    assert payload["hard_gate_status"]


def test_operator_dashboard_summary_cli_stdout_only_markdown_and_json() -> None:
    runner = CliRunner()

    markdown_result = runner.invoke(app, ["operator-dashboard-summary", "--format", "markdown"])
    assert markdown_result.exit_code == 0
    assert "Operator Dashboard Summary" in markdown_result.stdout
    assert "manual workflow_dispatch" in markdown_result.stdout

    json_result = runner.invoke(app, ["operator-dashboard-summary", "--format", "json"])
    assert json_result.exit_code == 0
    payload = json.loads(json_result.stdout)
    assert payload["source_mode"] == "source_only_stdout_no_side_effects"


def test_operator_dashboard_summary_cli_rejects_unsupported_format() -> None:
    result = CliRunner().invoke(app, ["operator-dashboard-summary", "--format", "html"])

    assert result.exit_code == 2
    assert "must be markdown or json" in result.stderr
