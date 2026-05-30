from __future__ import annotations

import inspect
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.tiingo_live_fetch_result_review import (
    TIINGO_ACTUAL_IMPORT_READINESS_VERDICT,
    TIINGO_CACHE_WRITE_READINESS_VERDICT,
    TIINGO_NEXT_EXECUTION_TASK,
    TIINGO_V63B_RESULT_VERDICT,
    build_tiingo_live_fetch_result_review_pack,
)
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_provider_context_pack_block,
    build_tiingo_live_fetch_result_review_report,
    write_tiingo_live_fetch_result_review_outputs,
)


def test_v63b_result_review_states_14_of_14_pass() -> None:
    pack = build_tiingo_live_fetch_result_review_pack(report_date="2026-05-30").to_dict()
    result = pack["pilot_result"]
    assert result["result_status"] == "pass"
    assert result["symbols_total"] == 14
    assert result["symbols_success"] == 14
    assert result["symbols_failed"] == 0
    assert result["row_count_per_symbol"] == 604
    assert pack["verdict"]["live_fetch_provider_viability"] == TIINGO_V63B_RESULT_VERDICT


def test_base_and_adjusted_fields_are_present_but_not_accuracy_proven() -> None:
    pack = build_tiingo_live_fetch_result_review_pack(report_date="2026-05-30").to_dict()
    fields = pack["pilot_result"]["field_summary"]
    assert fields["base_fields_all_present"] is True
    assert fields["adjusted_fields_all_present"] is True
    assert fields["base_fields"] == ["date", "open", "high", "low", "close", "volume"]
    assert fields["adjusted_fields"] == ["adjOpen", "adjHigh", "adjLow", "adjClose", "adjVolume"]
    assert fields["raw_price_accuracy_proven"] is False
    assert fields["adjusted_calculation_correctness_proven"] is False


def test_no_write_no_import_no_trading_flags_remain_false() -> None:
    pack = build_tiingo_live_fetch_result_review_pack(report_date="2026-05-30").to_dict()
    safety = pack["pilot_result"]["safety"]
    assert safety["source_only"] is True
    assert safety["live_http_executed_by_this_pack"] is False
    assert safety["tiingo_api_called_by_this_pack"] is False
    assert safety["provider_live_access_executed_by_this_pack"] is False
    assert safety["public_ohlcv_source_live_fetch_executed_by_this_pack"] is False
    assert safety["stooq_yahoo_polygon_live_fetch_executed_by_this_pack"] is False
    assert safety["raw_data_persisted"] is False
    assert safety["reports_private_raw_data_written"] is False
    assert safety["cache_write_executed"] is False
    assert safety["actual_import_executed"] is False
    assert safety["manual_actual_import_executed"] is False
    assert safety["env_secret_displayed"] is False
    assert safety["broker_manual_raw_data_handled"] is False
    assert safety["workflow_dependency_pyproject_changed"] is False
    assert safety["reports_private_touched"] is False
    assert safety["trading_action_executed"] is False


def test_report_clearly_lists_unproven_items() -> None:
    markdown, payload = build_tiingo_live_fetch_result_review_report(report_date="2026-05-30")
    for heading in (
        "## Executive Summary",
        "## v63B Pilot Result",
        "## What The Pilot Proved",
        "## What The Pilot Did Not Prove",
        "## Symbol-Level Summary",
        "## Field Availability Summary",
        "## Adjusted Field Presence Summary",
        "## No-Write / No-Import Verification",
        "## Data Quality Validation Plan",
        "## Cross-Provider Validation Matrix",
        "## Cache-Write Readiness Assessment",
        "## Actual Import Readiness Assessment",
        "## Risk Register",
        "## Recommended Next Task",
        "## Explicitly Not Approved",
        "## Machine-Readable Summary",
    ):
        assert heading in markdown
    assert "raw price accuracy not proven" in markdown
    assert "cross-provider consistency not proven" in markdown
    assert "cache/database legal suitability not resolved" in markdown
    assert payload["pack_version"] == "v64"


def test_cache_write_and_actual_import_readiness_remain_not_ready() -> None:
    pack = build_tiingo_live_fetch_result_review_pack(report_date="2026-05-30").to_dict()
    readiness = pack["cache_write_readiness_assessment"]
    assert readiness["cache_write_readiness"] == TIINGO_CACHE_WRITE_READINESS_VERDICT
    assert readiness["actual_import_readiness"] == TIINGO_ACTUAL_IMPORT_READINESS_VERDICT
    assert readiness["cache_write_approved"] is False
    assert readiness["actual_import_approved"] is False
    prerequisites = {row["prerequisite_id"]: row for row in readiness["prerequisites"]}
    assert prerequisites["SIGNOFF-16"]["blocks_cache_write"] is True
    assert prerequisites["DATA-QUALITY-VALIDATION"]["status"] == "not_completed"


def test_cross_provider_validation_plan_exists_and_is_draft_only() -> None:
    pack = build_tiingo_live_fetch_result_review_pack(report_date="2026-05-30").to_dict()
    plan = pack["data_quality_validation_plan"]
    assert plan["package_status"] == "draft_only_not_approved"
    assert plan["operation"] == TIINGO_NEXT_EXECUTION_TASK
    assert plan["providers"] == ["Tiingo", "Stooq", "Yahoo Finance/yfinance", "optional Polygon"]
    assert len(plan["universe"]) == 14
    assert plan["raw_data_persistence_allowed"] is False
    assert plan["cache_write_approved"] is False
    assert plan["actual_import_approved"] is False
    assert plan["trading_action_approved"] is False
    categories = {row["category"] for row in plan["checks"]}
    assert "close_adjusted_close_comparison" in categories
    assert "split_sensitive_adjustment_sample" in categories
    assert "etf_sample_comparison" in categories


def test_write_tiingo_live_fetch_result_review_outputs(tmp_path: Path) -> None:
    markdown, payload = build_tiingo_live_fetch_result_review_report(report_date="2026-05-30")
    paths = write_tiingo_live_fetch_result_review_outputs(
        out_dir=tmp_path,
        report_date="2026-05-30",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_tiingo_live_fetch_result_review_md"].is_file()
    assert paths["weekly_tiingo_live_fetch_result_review_json"].is_file()


def test_cli_help_exposes_only_safe_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["weekly-candidate-brief-tiingo-live-fetch-result-review", "--help"])
    assert result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-tiingo-live-fetch-result-review"
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
            "weekly-candidate-brief-tiingo-live-fetch-result-review",
            "--report-date",
            "2026-05-30",
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "tiingo_live_fetch_result_review"' in result.output
    assert '"symbols_success": 14' in result.output
    assert "source_only=true" in result.stderr
    assert "tiingo_api_called_by_this_pack=false" in result.stderr
    assert "stooq_yahoo_polygon_live_fetch_executed_by_this_pack=false" in result.stderr
    assert "cache_write_executed=false" in result.stderr
    assert (tmp_path / "latest" / "tiingo_live_fetch_result_review.json").is_file()


def test_context_pack_includes_v63b_result_and_next_step() -> None:
    block = build_provider_context_pack_block(report_date="2026-05-30")
    status = block["tiingo_live_fetch_result_review_status"]
    assert status["result_review_pack_exists"] is True
    assert status["source_only"] is True
    assert status["v63b_result_status"] == "pass"
    assert status["symbols_total"] == 14
    assert status["symbols_success"] == 14
    assert status["symbols_failed"] == 0
    assert status["base_fields_all_present"] is True
    assert status["adjusted_fields_all_present"] is True
    assert status["raw_data_persisted"] is False
    assert status["cache_write_approved"] is False
    assert status["actual_import_approved"] is False
    assert status["next_recommended_task"] == TIINGO_NEXT_EXECUTION_TASK
    assert status["cache_write_readiness"] == TIINGO_CACHE_WRITE_READINESS_VERDICT
