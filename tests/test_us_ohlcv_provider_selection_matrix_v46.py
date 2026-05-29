from __future__ import annotations

import inspect
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.us_ohlcv_provider_selection import (
    DEFAULT_US_PILOT_UNIVERSE,
    REQUIRED_US_PROVIDER_DIMENSIONS,
    build_us_ohlcv_provider_selection_matrix,
)
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_provider_context_pack_block,
    build_us_ohlcv_provider_selection_matrix_report,
    write_us_ohlcv_provider_selection_matrix_outputs,
)


REQUIRED_PROVIDERS = {
    "Stooq",
    "Alpha Vantage",
    "Yahoo Finance / yfinance",
    "Polygon.io",
    "Tiingo",
    "EODHD",
}


def test_provider_matrix_generation_is_source_only() -> None:
    matrix = build_us_ohlcv_provider_selection_matrix(report_date="2026-05-30").to_dict()
    safety = matrix["safety"]
    assert safety["source_only"] is True
    assert safety["live_http_executed"] is False
    assert safety["public_ohlcv_source_live_fetch_executed"] is False
    assert safety["cache_write_executed"] is False
    assert safety["actual_refresh_import_executed"] is False
    assert safety["env_secret_displayed"] is False
    assert safety["reports_private_touched"] is False


def test_all_required_providers_are_included() -> None:
    matrix = build_us_ohlcv_provider_selection_matrix(report_date="2026-05-30").to_dict()
    providers = {row["provider"] for row in matrix["providers"]}
    assert REQUIRED_PROVIDERS.issubset(providers)


def test_all_required_evaluation_dimensions_are_present() -> None:
    matrix = build_us_ohlcv_provider_selection_matrix(report_date="2026-05-30").to_dict()
    assert set(REQUIRED_US_PROVIDER_DIMENSIONS).issubset(set(matrix["evaluation_dimensions"]))
    for provider in matrix["providers"]:
        for dimension in REQUIRED_US_PROVIDER_DIMENSIONS:
            assert dimension in provider


def test_recommended_first_pilot_and_free_paid_distinction_exist() -> None:
    matrix = build_us_ohlcv_provider_selection_matrix(report_date="2026-05-30").to_dict()
    ranking = matrix["ranking"]
    assert ranking["best_first_pilot_provider"]
    assert ranking["best_production_candidate"]
    assert ranking["best_free_fallback"]
    cost_tiers = {row["cost_tier"] for row in matrix["providers"]}
    assert {"free", "free_limited"}.intersection(cost_tiers)
    assert {"paid_low", "paid_mid", "paid_high"}.intersection(cost_tiers)


def test_pilot_universe_and_hard_gates_remain_unapproved() -> None:
    matrix = build_us_ohlcv_provider_selection_matrix(report_date="2026-05-30").to_dict()
    pilot = matrix["pilot_design"]
    safety = matrix["safety"]
    assert tuple(pilot["pilot_universe"]) == DEFAULT_US_PILOT_UNIVERSE
    assert "AAPL" in pilot["pilot_universe"]
    assert "SPY" in pilot["pilot_universe"]
    assert "QQQ" in pilot["pilot_universe"]
    assert pilot["cache_write_approved"] is False
    assert pilot["actual_import_approved"] is False
    assert "public OHLCV source live fetchを実行してよい" in safety["hard_gates_required_for_live_test"]
    assert "cache_write" in safety["explicitly_not_approved"]
    assert "actual_refresh_import" in safety["explicitly_not_approved"]


def test_report_contains_required_sections_and_summary() -> None:
    markdown, payload = build_us_ohlcv_provider_selection_matrix_report(report_date="2026-05-30")
    for heading in (
        "## Executive Summary",
        "## Why This Matters For Stock Recommendations",
        "## Provider Candidates",
        "## Evaluation Criteria",
        "## Provider Matrix",
        "## Free / Low-Cost Options",
        "## Paid / Production Candidates",
        "## Recommended First Pilot",
        "## Pilot Universe",
        "## Pilot Date Range",
        "## Success Criteria",
        "## Failure Criteria",
        "## Data Quality Checks",
        "## Hard Gates Required For Live Testing",
        "## Explicitly Not Approved",
        "## Missing Evidence",
        "## Recommended Next Approval Request",
        "## Machine-Readable Summary",
    ):
        assert heading in markdown
    assert payload["selection_matrix"]["ranking"]["best_first_pilot_provider"] == "Tiingo"


def test_write_us_selection_matrix_outputs(tmp_path: Path) -> None:
    markdown, payload = build_us_ohlcv_provider_selection_matrix_report(report_date="2026-05-30")
    paths = write_us_ohlcv_provider_selection_matrix_outputs(
        out_dir=tmp_path,
        report_date="2026-05-30",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_us_ohlcv_provider_selection_matrix_md"].is_file()
    assert paths["weekly_us_ohlcv_provider_selection_matrix_json"].is_file()


def test_cli_help_exposes_only_safe_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["weekly-candidate-brief-us-ohlcv-provider-selection-matrix", "--help"])
    assert result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-us-ohlcv-provider-selection-matrix"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-date", "--out-dir", "--format"}.issubset(option_names)
    assert "--live" not in option_names
    assert "--write-cache" not in option_names
    assert "--execute" not in option_names
    assert "--import" not in option_names


def test_cli_matrix_generation_is_source_only(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-us-ohlcv-provider-selection-matrix",
            "--report-date",
            "2026-05-30",
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "us_ohlcv_provider_selection_matrix"' in result.output
    assert "source_only=true" in result.stderr
    assert "matrix_only=true" in result.stderr
    assert (tmp_path / "latest" / "us_ohlcv_provider_selection_matrix.json").is_file()


def test_context_pack_includes_us_provider_selection_status() -> None:
    block = build_provider_context_pack_block(report_date="2026-05-30")
    status = block["us_ohlcv_provider_selection_status"]
    assert status["provider_selected"] is False
    assert status["selection_matrix_exists"] is True
    assert status["recommended_first_pilot_provider"] == "Tiingo"
    assert status["recommended_free_fallback"] == "Stooq"
    assert "AAPL" in status["pilot_universe"]
    assert status["cache_write_approved"] is False
    assert status["actual_import_approved"] is False
