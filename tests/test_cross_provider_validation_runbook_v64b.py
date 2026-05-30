from __future__ import annotations

import inspect
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.cross_provider_validation_runbook import (
    CROSS_PROVIDER_RUNBOOK_VERDICT,
    build_cross_provider_validation_runbook_pack,
)
from invis_alpha_os.data.tiingo_live_fetch_result_review import (
    TIINGO_ACTUAL_IMPORT_READINESS_VERDICT,
    TIINGO_CACHE_WRITE_READINESS_VERDICT,
)
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_cross_provider_validation_runbook_report,
    build_provider_context_pack_block,
    write_cross_provider_validation_runbook_outputs,
)


def test_approval_package_is_draft_only_not_approved() -> None:
    pack = build_cross_provider_validation_runbook_pack(report_date="2026-05-30").to_dict()
    approval = pack["approval_package"]
    assert approval["package_status"] == "draft_only_not_approved"
    assert approval["operation"] == "no_write_cross_provider_data_quality_validation"
    assert approval["approval_phrase_issued"] is False
    assert approval["separate_explicit_approval_required"] is True
    assert approval["raw_data_persistence_allowed"] is False
    assert approval["cache_write_approved"] is False
    assert approval["actual_import_approved"] is False
    assert approval["manual_import_approved"] is False
    assert approval["trading_action_approved"] is False


def test_provider_scope_and_universe() -> None:
    pack = build_cross_provider_validation_runbook_pack(report_date="2026-05-30").to_dict()
    scope = pack["provider_scope"]
    universe = pack["universe"]
    assert scope["required_providers"] == ["Tiingo", "Stooq", "Yahoo Finance/yfinance"]
    assert scope["optional_providers"] == ["Polygon"]
    assert scope["provider_live_access_executed_by_this_pack"] is False
    assert len(universe["symbols"]) == 14
    assert universe["sample_groups"]["mega_cap_tech"] == ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
    assert universe["sample_groups"]["etf_samples"] == ["SPY", "QQQ"]


def test_validation_checks_cover_required_categories() -> None:
    pack = build_cross_provider_validation_runbook_pack(report_date="2026-05-30").to_dict()
    categories = {check["category"] for check in pack["validation_checks"]}
    assert "close_price_difference" in categories
    assert "adjusted_close_difference" in categories
    assert "row_count_comparison" in categories
    assert "date_min_date_max_comparison" in categories
    assert "trading_day_coverage_comparison" in categories
    assert "missing_day_comparison" in categories
    assert "volume_difference" in categories
    assert "split_sensitive_sample_checks" in categories
    assert "etf_sample_checks" in categories
    for check in pack["validation_checks"]:
        assert check["compute_now"] is False
        assert check["blocks_cache_import_on_major_disagreement"] is True


def test_tolerance_policy_is_conservative() -> None:
    pack = build_cross_provider_validation_runbook_pack(report_date="2026-05-30").to_dict()
    policy = pack["tolerance_policy"]
    assert policy["row_count_tolerance_days"] == 1
    assert policy["date_range_tolerance_days"] == 1
    assert policy["close_relative_tolerance_pct"] == 0.5
    assert policy["adjusted_close_relative_tolerance_pct"] == 0.5
    assert policy["volume_relative_tolerance_pct"] == 5.0
    assert policy["split_sensitive_requires_manual_review"] is True
    assert policy["missing_day_requires_investigation"] is True
    assert policy["provider_disagreement_requires_no_cache_import"] is True


def test_redacted_output_schema_forbids_raw_ohlcv() -> None:
    pack = build_cross_provider_validation_runbook_pack(report_date="2026-05-30").to_dict()
    schema = pack["redacted_output_schema"]
    assert "symbol_provider_pass_fail" in schema["allowed_fields"]
    assert "difference_summary_statistics" in schema["allowed_fields"]
    assert "raw_ohlcv_rows" in schema["forbidden_fields"]
    assert "raw_provider_responses" in schema["forbidden_fields"]
    assert "individual_daily_prices" in schema["forbidden_fields"]
    assert schema["reports_private_raw_data_forbidden"] is True
    assert schema["raw_ohlcv_rows_allowed"] is False
    assert schema["raw_provider_responses_allowed"] is False


def test_stop_conditions_include_hard_safety_boundaries() -> None:
    pack = build_cross_provider_validation_runbook_pack(report_date="2026-05-30").to_dict()
    labels = {condition["label"] for condition in pack["stop_conditions"]}
    assert "secret_displayed" in labels
    assert "raw_ohlcv_persisted" in labels
    assert "cache_write_attempted" in labels
    assert "actual_import_attempted" in labels
    assert "reports_private_raw_data_risk" in labels
    assert all(condition["stop_immediately"] is True for condition in pack["stop_conditions"])


def test_no_live_cache_import_flags_are_enabled() -> None:
    pack = build_cross_provider_validation_runbook_pack(report_date="2026-05-30").to_dict()
    safety = pack["safety_controls"]
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


def test_readiness_remains_no_write_only() -> None:
    pack = build_cross_provider_validation_runbook_pack(report_date="2026-05-30").to_dict()
    verdict = pack["readiness_verdict"]
    assert verdict["cross_provider_validation_execution_readiness"] == CROSS_PROVIDER_RUNBOOK_VERDICT
    assert verdict["cache_write_readiness"] == TIINGO_CACHE_WRITE_READINESS_VERDICT
    assert verdict["actual_import_readiness"] == TIINGO_ACTUAL_IMPORT_READINESS_VERDICT


def test_report_contains_required_sections() -> None:
    markdown, payload = build_cross_provider_validation_runbook_report(report_date="2026-05-30")
    for heading in (
        "## Executive Summary",
        "## Why This Pack Exists",
        "## Current State After v63B/v64",
        "## Provider Scope",
        "## Universe",
        "## Future Date Range",
        "## Validation Checks",
        "## Tolerance Policy",
        "## Redacted Output Schema",
        "## No-Write / No-Import Safety Controls",
        "## Stop Conditions",
        "## Approval Package Draft",
        "## Operator Runbook",
        "## Readiness Verdict",
        "## Explicitly Not Approved",
        "## Next Cursor Handoff",
        "## Machine-Readable Summary",
    ):
        assert heading in markdown
    assert "approval_phrase_issued: false" in markdown
    assert "raw_ohlcv_rows" in markdown
    assert payload["pack_version"] == "v64B"


def test_write_cross_provider_validation_runbook_outputs(tmp_path: Path) -> None:
    markdown, payload = build_cross_provider_validation_runbook_report(report_date="2026-05-30")
    paths = write_cross_provider_validation_runbook_outputs(
        out_dir=tmp_path,
        report_date="2026-05-30",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_cross_provider_validation_runbook_md"].is_file()
    assert paths["weekly_cross_provider_validation_runbook_json"].is_file()


def test_cli_help_exposes_only_safe_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["weekly-candidate-brief-cross-provider-validation-runbook", "--help"])
    assert result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-cross-provider-validation-runbook"
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
            "weekly-candidate-brief-cross-provider-validation-runbook",
            "--report-date",
            "2026-05-30",
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "cross_provider_validation_runbook"' in result.output
    assert '"package_status": "draft_only_not_approved"' in result.output
    assert "source_only=true" in result.stderr
    assert "tiingo_api_call_executed=false" in result.stderr
    assert "stooq_live_fetch_executed=false" in result.stderr
    assert "yahoo_yfinance_live_fetch_executed=false" in result.stderr
    assert "polygon_live_fetch_executed=false" in result.stderr
    assert "cache_write_executed=false" in result.stderr
    assert (tmp_path / "latest" / "cross_provider_validation_runbook.json").is_file()


def test_context_pack_includes_next_cross_provider_validation_task() -> None:
    block = build_provider_context_pack_block(report_date="2026-05-30")
    status = block["cross_provider_validation_runbook_status"]
    assert status["runbook_pack_exists"] is True
    assert status["source_only"] is True
    assert status["package_status"] == "draft_only_not_approved"
    assert status["operation"] == "no_write_cross_provider_data_quality_validation"
    assert status["providers"] == ["Tiingo", "Stooq", "Yahoo Finance/yfinance"]
    assert status["optional_providers"] == ["Polygon"]
    assert status["universe_count"] == 14
    assert status["approval_phrase_issued"] is False
    assert status["separate_explicit_approval_required"] is True
    assert status["raw_data_persistence_allowed"] is False
    assert status["cache_write_approved"] is False
    assert status["actual_import_approved"] is False
    assert status["readiness_verdict"] == CROSS_PROVIDER_RUNBOOK_VERDICT
