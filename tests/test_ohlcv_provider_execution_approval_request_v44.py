from __future__ import annotations

import inspect
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.ohlcv_provider_approval_request import (
    DRAFT_HANDOFF_MARKER,
    build_provider_execution_approval_request,
)
from invis_alpha_os.data.ohlcv_provider_runbook import (
    NOT_EXECUTED_MARKER,
    ProviderApprovedExecutionScenario,
)
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_ohlcv_provider_execution_approval_request,
    build_provider_context_pack_block,
    write_ohlcv_provider_execution_approval_request_outputs,
)


def test_approval_request_generation_is_source_only_for_all_scenarios() -> None:
    for scenario in ProviderApprovedExecutionScenario:
        bundle = build_provider_execution_approval_request(report_date="2026-05-30", scenario=scenario)
        request = bundle.to_dict()["request"]
        risk = request["risk_summary"]
        assert risk["source_only"] is True
        assert risk["commands_executed"] is False
        assert all(value is False for value in risk["audit_flags"].values())


def test_each_scenario_has_exactly_one_primary_approval_phrase() -> None:
    phrases: dict[str, str] = {}
    for scenario in ProviderApprovedExecutionScenario:
        bundle = build_provider_execution_approval_request(report_date="2026-05-30", scenario=scenario)
        prompt = bundle.to_dict()["request"]["decision_prompt"]
        phrase = prompt["primary_approval_phrase"]
        assert isinstance(phrase, str)
        assert phrase.strip() == phrase
        assert phrase
        assert "\n" not in phrase
        phrases[scenario.value] = phrase
    assert set(phrases) == {"public_ohlcv", "jquants_refresh", "cache_write", "actual_import", "manual_import"}


def test_related_non_approved_actions_are_listed() -> None:
    bundle = build_provider_execution_approval_request(
        report_date="2026-05-30",
        scenario=ProviderApprovedExecutionScenario.PUBLIC_OHLCV,
    )
    scope = bundle.to_dict()["request"]["scope"]
    assert "cache_write" in scope["explicitly_not_approved"]
    assert "actual_refresh_import" in scope["explicitly_not_approved"]
    assert "manual_import" in scope["explicitly_not_approved"]


def test_cursor_handoff_is_draft_only_and_commands_not_executed() -> None:
    bundle = build_provider_execution_approval_request(
        report_date="2026-05-30",
        scenario=ProviderApprovedExecutionScenario.ACTUAL_IMPORT,
    )
    request = bundle.to_dict()["request"]
    assert DRAFT_HANDOFF_MARKER in request["cursor_execution_handoff_draft"]
    commands = request["commands_planned_but_not_executed"]
    assert commands
    assert all(command.startswith(NOT_EXECUTED_MARKER) for command in commands)


def test_report_contains_required_sections() -> None:
    markdown, payload = build_ohlcv_provider_execution_approval_request(
        report_date="2026-05-30",
        scenario=ProviderApprovedExecutionScenario.CACHE_WRITE,
    )
    for heading in (
        "## Executive Summary",
        "## Requested Scenario",
        "## Why This Is Needed",
        "## Scope",
        "## Required Human Approval Phrase",
        "## Explicitly Not Approved",
        "## Evidence From Approval Package",
        "## Evidence From Safe Execution Harness",
        "## Evidence From Operator Runbook",
        "## Commands Planned But Not Executed",
        "## Required Preconditions",
        "## Required Redaction Checks",
        "## Expected Artifacts",
        "## Rollback Plan",
        "## Verification Plan",
        "## Stop Conditions",
        "## Final Human Decision",
        "## Cursor Execution Handoff Draft",
        "## Machine-Readable Summary",
    ):
        assert heading in markdown
    request = payload["approval_request"]["request"]
    assert request["scope"]["scenario"] == "cache_write"
    assert request["risk_summary"]["audit_flags"]["cache_write_executed"] is False


def test_write_execution_approval_request_outputs(tmp_path: Path) -> None:
    markdown, payload = build_ohlcv_provider_execution_approval_request(report_date="2026-05-30")
    paths = write_ohlcv_provider_execution_approval_request_outputs(
        out_dir=tmp_path,
        report_date="2026-05-30",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_ohlcv_provider_execution_approval_request_md"].is_file()
    assert paths["weekly_ohlcv_provider_execution_approval_request_json"].is_file()


def test_cli_help_exposes_only_safe_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["weekly-candidate-brief-ohlcv-provider-execution-approval-request", "--help"])
    assert result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-ohlcv-provider-execution-approval-request"
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


def test_cli_scenario_generation_is_approval_request_only(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-ohlcv-provider-execution-approval-request",
            "--report-date",
            "2026-05-30",
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
    assert "approval_request_only=true" in result.stderr
    assert "commands_executed=false" in result.stderr
    assert (tmp_path / "latest" / "ohlcv_provider_execution_approval_request.json").is_file()


def test_cli_rejects_unknown_scenario_without_writing(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-ohlcv-provider-execution-approval-request",
            "--report-date",
            "2026-05-30",
            "--out-dir",
            str(tmp_path),
            "--scenario",
            "execute_now",
        ],
    )
    assert result.exit_code == 2
    assert "unknown scenario" in result.stderr
    assert not (tmp_path / "latest" / "ohlcv_provider_execution_approval_request.json").exists()


def test_context_pack_includes_approval_request_status() -> None:
    block = build_provider_context_pack_block(report_date="2026-05-30")
    status = block["provider_execution_approval_request_status"]
    assert status["available"] is True
    assert status["source_only"] is True
    assert status["current_phase"] == "no_live_no_cache_no_import"
    assert status["approval_package_exists"] is True
    assert status["safe_execution_harness_exists"] is True
    assert status["operator_runbook_exists"] is True
    assert status["execution_approval_request_exists"] is True
    assert set(status["next_human_approval_phrase_by_scenario"]) == {
        "public_ohlcv",
        "jquants_refresh",
        "cache_write",
        "actual_import",
        "manual_import",
    }
