from __future__ import annotations

import json

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.product.sample_output_regeneration_contract import (
    build_sample_output_regeneration_contract,
    format_sample_output_regeneration_contract_json,
    render_sample_output_regeneration_contract_markdown,
)


def test_sample_output_regeneration_contract_lists_stdout_only_commands() -> None:
    contract = build_sample_output_regeneration_contract()

    assert contract.schema_version == "sample_output_regeneration_contract.v1"
    assert contract.source_mode == "source_only_stdout_contract"
    by_id = {command.id: command for command in contract.commands}
    assert by_id["sample_output_pack_markdown"].output_mode == "stdout_only"
    assert by_id["operator_dashboard_summary_markdown"].output_mode == "stdout_only"
    assert by_id["progress_dashboard_check_markdown"].output_mode == "stdout_only_read_only"
    assert by_id["state_consistency_check_markdown"].output_mode == "stdout_only_read_only"
    assert all(">" not in command.command for command in contract.commands)


def test_sample_output_regeneration_contract_records_hard_boundaries() -> None:
    contract = build_sample_output_regeneration_contract()
    forbidden = "\n".join(contract.forbidden_actions)

    assert "workflow change" in forbidden
    assert "manual workflow_dispatch" in forbidden
    assert "live HTTP / market-data live fetch" in forbidden
    assert "cache write" in forbidden
    assert "actual import / manual import" in forbidden
    assert "broker API / raw Excel direct parsing" in forbidden
    assert "env/secret display" in forbidden
    assert "trading action / order placement" in forbidden
    assert "real email send" in forbidden


def test_sample_output_regeneration_contract_markdown_and_json() -> None:
    contract = build_sample_output_regeneration_contract()
    markdown = render_sample_output_regeneration_contract_markdown(contract)
    payload = json.loads(format_sample_output_regeneration_contract_json(contract))

    assert markdown.startswith("# Sample Output Regeneration Contract")
    assert "sample-output-pack --format markdown" in markdown
    assert "progress-dashboard-check --format markdown" in markdown
    assert payload["schema_version"] == "sample_output_regeneration_contract.v1"
    assert payload["commands"][0]["expected_markers"]


def test_sample_output_regeneration_contract_cli_stdout_only_markdown_and_json() -> None:
    runner = CliRunner()

    markdown_result = runner.invoke(app, ["sample-output-regeneration-contract", "--format", "markdown"])
    assert markdown_result.exit_code == 0
    assert "Sample Output Regeneration Contract" in markdown_result.stdout
    assert "This contract lists allowed regeneration commands; it does not execute them." in markdown_result.stdout

    json_result = runner.invoke(app, ["sample-output-regeneration-contract", "--format", "json"])
    assert json_result.exit_code == 0
    payload = json.loads(json_result.stdout)
    assert payload["source_mode"] == "source_only_stdout_contract"


def test_sample_output_regeneration_contract_cli_rejects_unsupported_format() -> None:
    result = CliRunner().invoke(app, ["sample-output-regeneration-contract", "--format", "html"])

    assert result.exit_code == 2
    assert "must be markdown or json" in result.stderr
