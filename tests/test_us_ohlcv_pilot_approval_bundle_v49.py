from __future__ import annotations

import inspect
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.ohlcv_provider_registry import PUBLIC_OHLCV_APPROVAL_PHRASE
from invis_alpha_os.data.ohlcv_provider_runbook import NOT_EXECUTED_MARKER
from invis_alpha_os.data.us_ohlcv_provider_selection import DEFAULT_US_PILOT_UNIVERSE
from invis_alpha_os.data.us_ohlcv_pilot_approval_bundle import (
    DEFAULT_US_OHLCV_PILOT_DATE_RANGE,
    build_us_ohlcv_pilot_approval_bundle,
    validate_single_primary_approval_phrase,
)
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_provider_context_pack_block,
    build_us_ohlcv_pilot_approval_bundle_report,
    write_us_ohlcv_pilot_approval_bundle_outputs,
)


def test_pilot_approval_bundle_generation_is_source_only() -> None:
    bundle = build_us_ohlcv_pilot_approval_bundle(report_date="2026-05-30").to_dict()
    safety = bundle["safety"]
    assert safety["source_only"] is True
    assert safety["commands_executed"] is False
    assert safety["live_http_executed"] is False
    assert safety["public_ohlcv_source_live_fetch_executed"] is False
    assert safety["provider_live_access_executed"] is False
    assert safety["jquants_refresh_executed"] is False
    assert safety["cache_write_executed"] is False
    assert safety["actual_refresh_import_executed"] is False
    assert safety["manual_actual_import_executed"] is False
    assert safety["env_secret_displayed"] is False
    assert safety["broker_manual_raw_data_handled"] is False
    assert safety["workflow_dependency_pyproject_changed"] is False
    assert safety["trading_action_executed"] is False


def test_tiingo_defaults_and_pilot_scope_are_fixed() -> None:
    bundle = build_us_ohlcv_pilot_approval_bundle(report_date="2026-05-30")
    payload = bundle.to_dict()
    candidate = payload["candidate"]
    assert candidate["provider"] == "Tiingo"
    assert candidate["scenario"] == "public_ohlcv"
    assert candidate["operation"] == "future live fetch only - not executed by this bundle"
    assert tuple(candidate["universe"]) == DEFAULT_US_PILOT_UNIVERSE
    assert "AAPL" in candidate["universe"]
    assert "SPY" in candidate["universe"]
    assert candidate["date_range"] == DEFAULT_US_OHLCV_PILOT_DATE_RANGE
    assert validate_single_primary_approval_phrase(bundle) is True


def test_exactly_one_primary_approval_phrase_is_present() -> None:
    payload = build_us_ohlcv_pilot_approval_bundle(report_date="2026-05-30").to_dict()
    assert payload["candidate"]["primary_approval_phrase"] == PUBLIC_OHLCV_APPROVAL_PHRASE
    assert payload["candidate"]["approval_phrase_status"] == (
        "required_but_not_provided_in_this_source_only_bundle"
    )


def test_not_approved_actions_and_hard_gates_remain_unapproved() -> None:
    payload = build_us_ohlcv_pilot_approval_bundle(report_date="2026-05-30").to_dict()
    not_approved = set(payload["safety"]["explicitly_not_approved"])
    assert "cache_write" in not_approved
    assert "actual_refresh_import" in not_approved
    assert "manual_actual_import" in not_approved
    assert "jquants_refresh" in not_approved
    assert "broker_manual_raw_data_handling" in not_approved
    assert "trading_action" in not_approved


def test_commands_and_cursor_handoff_are_non_executing() -> None:
    payload = build_us_ohlcv_pilot_approval_bundle(report_date="2026-05-30").to_dict()
    assert payload["commands_planned_but_not_executed"]
    assert all(
        command.startswith(NOT_EXECUTED_MARKER)
        for command in payload["commands_planned_but_not_executed"]
    )
    assert "DRAFT ONLY - DO NOT RUN UNTIL HUMAN APPROVAL PHRASE IS PROVIDED" in payload[
        "cursor_handoff_draft"
    ]
    assert "cache write" in payload["cursor_handoff_draft"]
    assert "actual refresh/import" in payload["cursor_handoff_draft"]
    assert "secret display" in payload["cursor_handoff_draft"]


def test_bundle_integrates_v46_v48_v44_v43_v41_v39_evidence() -> None:
    payload = build_us_ohlcv_pilot_approval_bundle(report_date="2026-05-30").to_dict()
    evidence = payload["evidence_summary"]
    assert evidence["provider_selection_matrix"]["exists"] is True
    assert evidence["provider_selection_matrix"]["recommended_first_pilot_provider"] == "Tiingo"
    assert evidence["current_evidence_pack"]["exists"] is True
    assert evidence["current_evidence_pack"]["needs_current_recheck"] is True
    assert evidence["execution_approval_request"]["exists"] is True
    assert evidence["approved_execution_runbook"]["exists"] is True
    assert evidence["approved_execution_runbook"]["commands_marked_not_executed"] is True
    assert evidence["safe_execution_harness"]["exists"] is True
    assert evidence["approval_package"]["exists"] is True
    assert evidence["approval_package"]["dry_run_only"] is True


def test_evidence_gap_closure_checklist_is_manual_only() -> None:
    payload = build_us_ohlcv_pilot_approval_bundle(report_date="2026-05-30").to_dict()
    checklist = payload["evidence_gap_closure_checklist"]
    gaps = {item["gap"] for item in checklist}
    assert {
        "pricing_terms",
        "adjusted_price_methodology",
        "cache_suitability",
        "bulk_throughput",
        "adr_delisted_coverage",
    }.issubset(gaps)
    assert all(item["operator_signoff"] == "pending" for item in checklist)
    assert all("manual" in item["manual_recheck"].lower() or "confirm" in item["manual_recheck"].lower() for item in checklist)


def test_report_contains_required_sections_and_summary() -> None:
    markdown, payload = build_us_ohlcv_pilot_approval_bundle_report(report_date="2026-05-30")
    for heading in (
        "## Executive Summary",
        "## First Pilot Candidate",
        "## Why Tiingo Is The First Pilot Candidate",
        "## Evidence From Provider Selection Matrix",
        "## Evidence From Current Evidence Pack",
        "## Pilot Universe",
        "## Pilot Date Range",
        "## Required Human Approval Phrase",
        "## Explicitly Not Approved",
        "## Commands Planned But Not Executed",
        "## Preflight Checklist",
        "## Redaction / Secret Handling Checklist",
        "## Expected Outputs",
        "## Verification Plan",
        "## Rollback / No-Write Discipline",
        "## Stop Conditions",
        "## Risk Register",
        "## Evidence Gap Closure Checklist",
        "## Cursor Handoff Draft",
        "## Final Readiness Verdict",
        "## Machine-Readable Summary",
    ):
        assert heading in markdown
    assert payload["pack_version"] == "v49"
    assert payload["pilot_approval_bundle"]["candidate"]["provider"] == "Tiingo"


def test_write_pilot_approval_bundle_outputs(tmp_path: Path) -> None:
    markdown, payload = build_us_ohlcv_pilot_approval_bundle_report(report_date="2026-05-30")
    paths = write_us_ohlcv_pilot_approval_bundle_outputs(
        out_dir=tmp_path,
        report_date="2026-05-30",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_us_ohlcv_pilot_approval_bundle_md"].is_file()
    assert paths["weekly_us_ohlcv_pilot_approval_bundle_json"].is_file()


def test_cli_help_exposes_only_safe_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["weekly-candidate-brief-us-ohlcv-pilot-approval-bundle", "--help"])
    assert result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-us-ohlcv-pilot-approval-bundle"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-date", "--out-dir", "--format", "--provider", "--scenario"}.issubset(
        option_names
    )
    assert "--live" not in option_names
    assert "--fetch" not in option_names
    assert "--execute" not in option_names
    assert "--write-cache" not in option_names
    assert "--import" not in option_names
    assert "--secret" not in option_names


def test_cli_generation_is_source_only(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-us-ohlcv-pilot-approval-bundle",
            "--report-date",
            "2026-05-30",
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
            "--provider",
            "tiingo",
            "--scenario",
            "public_ohlcv",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "us_ohlcv_pilot_approval_bundle"' in result.output
    assert "source_only=true" in result.stderr
    assert "commands_executed=false" in result.stderr
    assert "cache_write_executed=false" in result.stderr
    assert (tmp_path / "latest" / "us_ohlcv_pilot_approval_bundle.json").is_file()


def test_context_pack_includes_pilot_approval_bundle_status() -> None:
    block = build_provider_context_pack_block(report_date="2026-05-30")
    status = block["us_ohlcv_pilot_approval_bundle_status"]
    assert status["pilot_approval_bundle_exists"] is True
    assert status["source_only"] is True
    assert status["commands_executed"] is False
    assert status["recommended_first_pilot_provider"] == "Tiingo"
    assert status["scenario"] == "public_ohlcv"
    assert status["approval_phrase_required"] == PUBLIC_OHLCV_APPROVAL_PHRASE
    assert status["cache_write_approved"] is False
    assert status["actual_import_approved"] is False
    assert status["next_step_requires_explicit_human_approval"] is True
