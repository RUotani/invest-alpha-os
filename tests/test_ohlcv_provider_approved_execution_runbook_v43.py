from __future__ import annotations

import inspect
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.ohlcv_provider_runbook import (
    NOT_EXECUTED_MARKER,
    ProviderApprovedExecutionScenario,
    build_provider_approved_execution_runbook,
)
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_ohlcv_provider_approved_execution_runbook,
    build_provider_context_pack_block,
    write_ohlcv_provider_approved_execution_runbook_outputs,
)


def test_runbook_generation_is_source_only_for_all_scenarios() -> None:
    for scenario in ProviderApprovedExecutionScenario:
        runbook = build_provider_approved_execution_runbook(
            report_date="2026-05-29",
            scenario=scenario,
        )
        record = runbook.to_dict()["decision_record"]
        assert record["source_only"] is True
        assert record["approved_in_this_runbook"] is False
        assert all(value is False for value in record["audit_flags"].values())


def test_all_scenarios_include_required_approval_phrase() -> None:
    phrases = {}
    for scenario in ProviderApprovedExecutionScenario:
        runbook = build_provider_approved_execution_runbook(
            report_date="2026-05-29",
            scenario=scenario,
        )
        requirement = runbook.to_dict()["approval_requirement"]
        phrases[scenario.value] = requirement["phrase"]
        assert requirement["approval_status"] == "not_approved_by_this_runbook"
        assert requirement["required_gates"]
    assert set(phrases) == {"public_ohlcv", "jquants_refresh", "cache_write", "actual_import", "manual_import"}
    assert all(phrase for phrase in phrases.values())


def test_commands_are_marked_not_executed() -> None:
    runbook = build_provider_approved_execution_runbook(
        report_date="2026-05-29",
        scenario=ProviderApprovedExecutionScenario.ACTUAL_IMPORT,
    )
    commands = runbook.to_dict()["command_plan"]["commands"]
    assert commands
    assert all(command.startswith(NOT_EXECUTED_MARKER) for command in commands)
    assert all("SECRET" not in command and "TOKEN" not in command and ".env" not in command for command in commands)


def test_report_contains_required_sections_and_machine_summary() -> None:
    markdown, payload = build_ohlcv_provider_approved_execution_runbook(
        report_date="2026-05-29",
        scenario=ProviderApprovedExecutionScenario.CACHE_WRITE,
    )
    for heading in (
        "## Executive Summary",
        "## Execution Scope",
        "## Required Approval Phrase",
        "## Explicitly Not Approved",
        "## Operator Preconditions",
        "## Commands To Run Later",
        "## Expected Artifacts",
        "## Preflight Checklist",
        "## Verification Checklist",
        "## Rollback Runbook",
        "## Stop Conditions",
        "## Audit Notes",
        "## Handoff To Cursor",
        "## Machine-Readable Summary",
    ):
        assert heading in markdown
    summary = payload["runbook"]["decision_record"]
    assert summary["audit_flags"]["cache_write_executed"] is False
    assert payload["runbook"]["scope"]["scenario"] == "cache_write"


def test_write_approved_execution_runbook_outputs(tmp_path: Path) -> None:
    markdown, payload = build_ohlcv_provider_approved_execution_runbook(report_date="2026-05-29")
    paths = write_ohlcv_provider_approved_execution_runbook_outputs(
        out_dir=tmp_path,
        report_date="2026-05-29",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_ohlcv_provider_approved_execution_runbook_md"].is_file()
    assert paths["weekly_ohlcv_provider_approved_execution_runbook_json"].is_file()


def test_cli_help_exposes_only_safe_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["weekly-candidate-brief-ohlcv-provider-approved-execution-runbook", "--help"])
    assert result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-ohlcv-provider-approved-execution-runbook"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-date", "--out-dir", "--format", "--scenario"}.issubset(option_names)
    assert "--live" not in option_names
    assert "--write-cache" not in option_names
    assert "--execute" not in option_names
    assert "--import" not in option_names


def test_cli_scenario_generation_is_source_only(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-ohlcv-provider-approved-execution-runbook",
            "--report-date",
            "2026-05-29",
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
            "--scenario",
            "manual_import",
        ],
    )
    assert result.exit_code == 0
    assert '"scenario": "manual_import"' in result.output
    assert "source_only=true" in result.stderr
    assert "commands_executed=false" in result.stderr
    assert (tmp_path / "latest" / "ohlcv_provider_approved_execution_runbook.json").is_file()


def test_cli_rejects_unknown_scenario_without_writing(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-ohlcv-provider-approved-execution-runbook",
            "--report-date",
            "2026-05-29",
            "--out-dir",
            str(tmp_path),
            "--scenario",
            "live_now",
        ],
    )
    assert result.exit_code == 2
    assert "unknown scenario" in result.stderr
    assert not (tmp_path / "latest" / "ohlcv_provider_approved_execution_runbook.json").exists()


def test_context_pack_includes_runbook_status() -> None:
    block = build_provider_context_pack_block(report_date="2026-05-29")
    status = block["provider_approved_execution_runbook_status"]
    assert status["available"] is True
    assert status["source_only"] is True
    assert status["current_phase"] == "no_live_no_cache_no_import"
    assert status["approval_package_exists"] is True
    assert status["safe_execution_harness_exists"] is True
    assert set(status["next_required_approval_phrase_by_scenario"]) == {
        "public_ohlcv",
        "jquants_refresh",
        "cache_write",
        "actual_import",
        "manual_import",
    }
