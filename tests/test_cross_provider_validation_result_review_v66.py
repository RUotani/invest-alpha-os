from __future__ import annotations

import inspect
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.cross_provider_validation_result_review import (
    STOOQ_ADJUSTED_SUITABILITY,
    STOOQ_BASE_SUITABILITY,
    V65_RECLASSIFIED_VERDICT,
    V65_RESULT_REVIEW_VERDICT,
    build_cross_provider_validation_result_review,
)
from invis_alpha_os.data.tiingo_live_fetch_result_review import (
    TIINGO_ACTUAL_IMPORT_READINESS_VERDICT,
    TIINGO_CACHE_WRITE_READINESS_VERDICT,
)
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_cross_provider_validation_result_review_report,
    build_provider_context_pack_block,
    write_cross_provider_validation_result_review_outputs,
)


def test_v65_result_review_states_warn_manual_review_required() -> None:
    review = build_cross_provider_validation_result_review(report_date="2026-05-30").to_dict()
    summary = review["result_summary"]
    assert summary["verdict"] == V65_RESULT_REVIEW_VERDICT
    assert summary["required_providers_available"] is True
    assert summary["required_provider_symbols_success"] == "14/14"
    assert summary["row_count_per_symbol"] == 604
    assert summary["row_count_consistent"] is True
    assert summary["date_range_consistent"] is True
    assert summary["polygon_status"] == "skipped_missing_token"


def test_tiingo_yahoo_adjusted_comparison_is_pass() -> None:
    review = build_cross_provider_validation_result_review(report_date="2026-05-30").to_dict()
    summary = review["result_summary"]
    assert summary["tiingo_yahoo_adjusted_close_consistency"] == "pass"
    assert summary["adjusted_close_tiingo_yahoo_max_deviation_approx_pct"] == 0.009
    readiness = review["cache_write_readiness"]
    assert readiness["tiingo_adjusted_series_confidence"] == "medium_high_after_yahoo_agreement"


def test_stooq_adjusted_comparison_is_not_suitable_and_base_only() -> None:
    review = build_cross_provider_validation_result_review(report_date="2026-05-30").to_dict()
    summary = review["result_summary"]
    stooq = review["stooq_adjustment_policy"]
    assert summary["stooq_adjusted_comparison_suitability"] == STOOQ_ADJUSTED_SUITABILITY
    assert summary["stooq_base_close_comparison_suitability"] == STOOQ_BASE_SUITABILITY
    assert stooq["has_adjusted_close"] is False
    assert stooq["adjusted_series_oracle"] is False
    assert stooq["disable_adjusted_comparison_unless_adjusted_series_available"] is True
    assert "fallback" in stooq["fallback_role"]


def test_provider_pair_policy_classifies_stooq_as_fallback_base_coverage_only() -> None:
    review = build_cross_provider_validation_result_review(report_date="2026-05-30").to_dict()
    policies = {row["pair"]: row for row in review["provider_pair_policy"]}
    assert policies["Tiingo vs Yahoo adjusted close"]["status_after_v65"] == "passed_strong_signal"
    assert policies["Tiingo vs Yahoo adjusted close"]["suitability"] == "primary_adjusted_series_sanity_check"
    assert policies["Tiingo vs Stooq close"]["suitability"] == "base_close_coverage_fallback_only"
    assert policies["Tiingo vs Stooq close"]["status_after_v65"] == "warning_due_series_definition_mismatch"
    assert policies["Yahoo vs Stooq close"]["role"] == "secondary base close / coverage check only"
    assert policies["Polygon"]["status_after_v65"] == "skipped_missing_token"


def test_nvda_avgo_warning_is_likely_series_definition_mismatch() -> None:
    review = build_cross_provider_validation_result_review(report_date="2026-05-30").to_dict()
    interpretations = {row["symbol"]: row for row in review["breach_interpretations"]}
    for symbol in ("NVDA", "AVGO"):
        row = interpretations[symbol]
        assert row["interpretation"] == (
            "likely Stooq non-adjusted/base series compared with adjusted or differently adjusted series"
        )
        assert row["treat_as_tiingo_failure_by_default"] is False
        assert row["requires_manual_review"] is True


def test_cache_write_and_actual_import_remain_not_ready() -> None:
    review = build_cross_provider_validation_result_review(report_date="2026-05-30").to_dict()
    readiness = review["cache_write_readiness"]
    assert readiness["cross_provider_validation_result"] == V65_RECLASSIFIED_VERDICT
    assert readiness["cache_write_readiness"] == TIINGO_CACHE_WRITE_READINESS_VERDICT
    assert readiness["actual_import_readiness"] == TIINGO_ACTUAL_IMPORT_READINESS_VERDICT
    assert readiness["cache_write_approved"] is False
    assert readiness["actual_import_approved"] is False
    prerequisites = {row["prerequisite_id"]: row for row in readiness["prerequisites"]}
    assert prerequisites["SIGNOFF-16"]["blocks_cache_write"] is True
    assert prerequisites["CACHE-APPROVAL-PHRASE"]["status"] == "not_issued"


def test_no_live_cache_import_flags_are_enabled() -> None:
    review = build_cross_provider_validation_result_review(report_date="2026-05-30").to_dict()
    summary = review["result_summary"]
    next_step = review["next_step"]
    assert summary["raw_data_persisted"] is False
    assert summary["cache_write_executed"] is False
    assert summary["actual_import_executed"] is False
    assert summary["manual_import_executed"] is False
    assert summary["trading_action_executed"] is False
    assert summary["secret_displayed"] is False
    assert next_step["approval_phrase_issued"] is False
    assert "tiingo_api_call" in next_step["explicitly_not_approved"]
    assert "stooq_live_fetch" in next_step["explicitly_not_approved"]
    assert "yahoo_yfinance_live_fetch" in next_step["explicitly_not_approved"]
    assert "polygon_live_fetch" in next_step["explicitly_not_approved"]
    assert "cache_write" in next_step["explicitly_not_approved"]


def test_report_contains_required_sections() -> None:
    markdown, payload = build_cross_provider_validation_result_review_report(report_date="2026-05-30")
    for heading in (
        "## Executive Summary",
        "## v65 Result Summary",
        "## Warning Interpretation",
        "## Provider-Pair Comparison Policy",
        "## Stooq Adjustment Policy",
        "## Tolerance Policy Refinement",
        "## Tiingo/Yahoo Agreement Assessment",
        "## Impact on Tiingo Provider Viability",
        "## Cache-Write Readiness Assessment",
        "## Actual Import Readiness Assessment",
        "## Risk Register",
        "## Recommended Next Step",
        "## Explicitly Not Approved",
        "## Machine-Readable Summary",
    ):
        assert heading in markdown
    assert "Stooq should not be used as adjusted-close oracle" in markdown
    assert "NVDA/AVGO" in markdown
    assert payload["pack_version"] == "v66"


def test_write_cross_provider_validation_result_review_outputs(tmp_path: Path) -> None:
    markdown, payload = build_cross_provider_validation_result_review_report(report_date="2026-05-30")
    paths = write_cross_provider_validation_result_review_outputs(
        out_dir=tmp_path,
        report_date="2026-05-30",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_cross_provider_validation_result_review_md"].is_file()
    assert paths["weekly_cross_provider_validation_result_review_json"].is_file()


def test_cli_help_exposes_only_safe_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["weekly-candidate-brief-cross-provider-validation-result-review", "--help"])
    assert result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-cross-provider-validation-result-review"
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
            "weekly-candidate-brief-cross-provider-validation-result-review",
            "--report-date",
            "2026-05-30",
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "cross_provider_validation_result_review"' in result.output
    assert '"verdict": "warn_manual_review_required"' in result.output
    assert "source_only=true" in result.stderr
    assert "tiingo_api_call_executed=false" in result.stderr
    assert "stooq_live_fetch_executed=false" in result.stderr
    assert "yahoo_yfinance_live_fetch_executed=false" in result.stderr
    assert "polygon_live_fetch_executed=false" in result.stderr
    assert "cache_write_executed=false" in result.stderr
    assert (tmp_path / "latest" / "cross_provider_validation_result_review.json").is_file()


def test_context_pack_includes_v65_warning_interpretation_and_stooq_policy() -> None:
    block = build_provider_context_pack_block(report_date="2026-05-30")
    status = block["cross_provider_validation_result_review_status"]
    assert status["result_review_pack_exists"] is True
    assert status["source_only"] is True
    assert status["v65_verdict"] == V65_RESULT_REVIEW_VERDICT
    assert status["required_providers_available"] is True
    assert status["required_provider_symbols_success"] == "14/14"
    assert status["tiingo_yahoo_adjusted_close_consistency"] == "pass"
    assert status["stooq_adjusted_comparison_suitability"] == STOOQ_ADJUSTED_SUITABILITY
    assert status["stooq_base_close_comparison_suitability"] == STOOQ_BASE_SUITABILITY
    assert status["nvda_avgo_warning_interpretation"] == (
        "likely_stooq_series_definition_mismatch_not_tiingo_failure_by_default"
    )
    assert status["cache_write_readiness"] == TIINGO_CACHE_WRITE_READINESS_VERDICT
    assert status["actual_import_readiness"] == TIINGO_ACTUAL_IMPORT_READINESS_VERDICT
