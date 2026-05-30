from __future__ import annotations

import inspect
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.cache_write_readiness_gate import (
    CACHE_WRITE_GATE_STATUS,
    SIGNOFF_16_STATUS,
    build_cache_write_readiness_gate,
)
from invis_alpha_os.data.tiingo_live_fetch_result_review import (
    TIINGO_ACTUAL_IMPORT_READINESS_VERDICT,
    TIINGO_CACHE_WRITE_READINESS_VERDICT,
)
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_cache_write_readiness_gate_report,
    build_provider_context_pack_block,
    write_cache_write_readiness_gate_outputs,
)


def test_signoff16_is_unresolved_and_required() -> None:
    gate = build_cache_write_readiness_gate(report_date="2026-05-30").to_dict()
    assert gate["gate_status"] == CACHE_WRITE_GATE_STATUS
    requirements = gate["signoff16_requirements"]
    assert len(requirements) >= 10
    assert all(row["status"] == SIGNOFF_16_STATUS for row in requirements)
    assert all(row["required_before_cache_write"] is True for row in requirements)
    descriptions = {row["description"] for row in requirements}
    assert "Tiingo terms/cache suitability acknowledgement" in descriptions
    assert "raw data must not be committed to reports-private" in descriptions
    assert "actual import remains separate" in descriptions


def test_cache_actual_import_trading_and_approval_flags_remain_false() -> None:
    gate = build_cache_write_readiness_gate(report_date="2026-05-30").to_dict()
    verdict = gate["readiness_verdict"]
    boundary = gate["cache_write_approval_boundary"]
    actual_import = gate["actual_import_boundary"]
    assert verdict["cache_write_approved"] is False
    assert verdict["actual_import_approved"] is False
    assert verdict["trading_action_approved"] is False
    assert verdict["approval_phrase_issued"] is False
    assert boundary["cache_write_approved"] is False
    assert boundary["approval_phrase_issued"] is False
    assert actual_import["actual_import_approved"] is False
    assert actual_import["approval_phrase_issued"] is False
    assert actual_import["remains_separate_from_cache_write"] is True


def test_raw_data_forbidden_locations_include_required_boundaries() -> None:
    gate = build_cache_write_readiness_gate(report_date="2026-05-30").to_dict()
    forbidden = {row["location_id"] for row in gate["storage_policy"]["forbidden_locations"]}
    assert "reports_private_raw_ohlcv" in forbidden
    assert "source_git_raw_ohlcv" in forbidden
    assert "github_artifacts_raw_ohlcv" in forbidden
    assert "chatgpt_pasted_raw_data" in forbidden
    assert "public_outputs" in forbidden
    assert "broker_manual_raw_mix" in forbidden


def test_allowed_storage_is_future_private_local_only_after_approval() -> None:
    gate = build_cache_write_readiness_gate(report_date="2026-05-30").to_dict()
    storage = gate["storage_policy"]
    assert storage["policy_status"] == "draft_only_not_approved"
    assert storage["cache_location"] == "to be explicitly configured"
    assert storage["raw_data_git_allowed"] is False
    assert storage["raw_data_reports_private_allowed"] is False
    assert storage["redacted_summary_reports_private_allowed"] is True
    assert all(row["allowed_only_after_future_approval"] is True for row in storage["allowed_candidates"])


def test_retention_purge_and_rollback_policy_exists() -> None:
    gate = build_cache_write_readiness_gate(report_date="2026-05-30").to_dict()
    retention = gate["retention_policy"]
    purge = gate["purge_rollback_policy"]
    assert retention["retention_period_initial_pilot"] == "short_lived_or_operator_defined"
    assert retention["raw_file_inventory_required"] is True
    assert retention["redacted_summary_required"] is True
    assert retention["no_orphan_raw_files_required"] is True
    assert purge["cache_purge_command_required"] is True
    assert purge["rollback_checklist_required"] is True
    assert purge["purge_dry_run_required"] is True
    assert purge["post_purge_verification_required"] is True
    assert purge["future_checklist"]


def test_cache_write_pilot_is_draft_only_not_approved() -> None:
    gate = build_cache_write_readiness_gate(report_date="2026-05-30").to_dict()
    pilot = gate["future_cache_write_pilot"]
    assert pilot["package_status"] == "draft_only_not_approved"
    assert pilot["operation"] == "tiingo_private_local_cache_write_pilot"
    assert pilot["provider"] == "Tiingo"
    assert pilot["recommended_first_subset"] == ["SPY", "QQQ", "AAPL", "NVDA"]
    assert pilot["cache_location"] == "to be explicitly configured"
    assert pilot["raw_data_git_allowed"] is False
    assert pilot["raw_data_reports_private_allowed"] is False
    assert pilot["redacted_summary_reports_private_allowed"] is True
    assert pilot["approval_phrase_issued"] is False
    assert pilot["separate_explicit_approval_required"] is True


def test_no_live_cache_import_flags_are_enabled() -> None:
    gate = build_cache_write_readiness_gate(report_date="2026-05-30").to_dict()
    safety = gate["safety_flags"]
    assert safety["source_only"] is True
    assert safety["tiingo_api_call_executed"] is False
    assert safety["stooq_live_fetch_executed"] is False
    assert safety["yahoo_yfinance_live_fetch_executed"] is False
    assert safety["polygon_live_fetch_executed"] is False
    assert safety["provider_live_access_executed"] is False
    assert safety["public_ohlcv_source_live_fetch_executed"] is False
    assert safety["cache_write_executed"] is False
    assert safety["actual_refresh_import_executed"] is False
    assert safety["manual_actual_import_executed"] is False
    assert safety["env_secret_displayed"] is False
    assert safety["broker_manual_raw_data_handled"] is False
    assert safety["workflow_dependency_pyproject_changed"] is False
    assert safety["reports_private_touched"] is False
    assert safety["trading_action_executed"] is False
    assert safety["raw_ohlcv_persisted"] is False
    assert safety["raw_api_response_persisted"] is False


def test_readiness_verdict_remains_not_ready() -> None:
    gate = build_cache_write_readiness_gate(report_date="2026-05-30").to_dict()
    verdict = gate["readiness_verdict"]
    assert verdict["signoff16_status"] == SIGNOFF_16_STATUS
    assert verdict["cache_write_readiness"] == TIINGO_CACHE_WRITE_READINESS_VERDICT
    assert verdict["actual_import_readiness"] == TIINGO_ACTUAL_IMPORT_READINESS_VERDICT


def test_report_contains_required_sections() -> None:
    markdown, payload = build_cache_write_readiness_gate_report(report_date="2026-05-30")
    for heading in (
        "## Executive Summary",
        "## Current State After v63B/v65/v66",
        "## SIGNOFF-16 Requirements",
        "## Private/Local Cache Storage Policy",
        "## Forbidden Raw Data Locations",
        "## Retention Policy Draft",
        "## Purge / Rollback Policy Draft",
        "## Terms / Cache Acknowledgement",
        "## Cache-Write Approval Boundary",
        "## Actual Import Boundary",
        "## Future Cache-Write Pilot Draft",
        "## Readiness Verdict",
        "## Explicitly Not Approved",
        "## Machine-Readable Summary",
    ):
        assert heading in markdown
    assert "approval_phrase_issued: false" in markdown
    assert "reports-private raw OHLCV" in markdown
    assert payload["pack_version"] == "v67"


def test_write_cache_write_readiness_gate_outputs(tmp_path: Path) -> None:
    markdown, payload = build_cache_write_readiness_gate_report(report_date="2026-05-30")
    paths = write_cache_write_readiness_gate_outputs(
        out_dir=tmp_path,
        report_date="2026-05-30",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_cache_write_readiness_gate_md"].is_file()
    assert paths["weekly_cache_write_readiness_gate_json"].is_file()


def test_cli_help_exposes_only_safe_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["weekly-candidate-brief-cache-write-readiness-gate", "--help"])
    assert result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-cache-write-readiness-gate"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-date", "--out-dir", "--format"}.issubset(option_names)
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
            "weekly-candidate-brief-cache-write-readiness-gate",
            "--report-date",
            "2026-05-30",
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "cache_write_readiness_gate"' in result.output
    assert '"gate_status": "draft_only_not_approved"' in result.output
    assert "source_only=true" in result.stderr
    assert "tiingo_api_call_executed=false" in result.stderr
    assert "cache_write_executed=false" in result.stderr
    assert "actual_refresh_import_executed=false" in result.stderr
    assert (tmp_path / "latest" / "cache_write_readiness_gate.json").is_file()


def test_context_pack_includes_v67_cache_write_readiness_gate() -> None:
    block = build_provider_context_pack_block(report_date="2026-05-30")
    status = block["cache_write_readiness_gate_status"]
    assert status["gate_exists"] is True
    assert status["source_only"] is True
    assert status["gate_status"] == CACHE_WRITE_GATE_STATUS
    assert status["signoff16_status"] == SIGNOFF_16_STATUS
    assert status["cache_write_approved"] is False
    assert status["actual_import_approved"] is False
    assert status["trading_action_approved"] is False
    assert status["approval_phrase_issued"] is False
    assert status["cache_location"] == "to be explicitly configured"
    assert status["raw_data_git_allowed"] is False
    assert status["raw_data_reports_private_allowed"] is False
    assert status["redacted_summary_reports_private_allowed"] is True
    assert status["future_cache_write_pilot_status"] == "draft_only_not_approved"
    assert status["future_cache_write_pilot_subset"] == ["SPY", "QQQ", "AAPL", "NVDA"]
