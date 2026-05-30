from __future__ import annotations

import inspect
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.tiingo_current_docs_recheck import (
    REQUIRED_TIINGO_RECHECK_CATEGORIES,
    TIINGO_RECHECK_VERDICT,
    build_tiingo_current_docs_recheck_pack,
)
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_provider_context_pack_block,
    build_tiingo_current_docs_recheck_pack_report,
    write_tiingo_current_docs_recheck_pack_outputs,
)


def test_tiingo_recheck_pack_generation_is_source_only() -> None:
    pack = build_tiingo_current_docs_recheck_pack(report_date="2026-05-30").to_dict()
    safety = pack["safety"]
    assert safety["source_only"] is True
    assert safety["live_http_executed"] is False
    assert safety["tiingo_api_called"] is False
    assert safety["provider_live_access_executed"] is False
    assert safety["public_ohlcv_source_live_fetch_executed"] is False
    assert safety["cache_write_executed"] is False
    assert safety["actual_refresh_import_executed"] is False
    assert safety["manual_actual_import_executed"] is False
    assert safety["env_secret_displayed"] is False
    assert safety["broker_manual_raw_data_handled"] is False
    assert safety["workflow_dependency_pyproject_changed"] is False
    assert safety["trading_action_executed"] is False


def test_all_required_recheck_categories_exist() -> None:
    pack = build_tiingo_current_docs_recheck_pack(report_date="2026-05-30").to_dict()
    categories = {item["category"] for item in pack["checklist_items"]}
    assert set(REQUIRED_TIINGO_RECHECK_CATEGORIES).issubset(categories)


def test_all_evidence_items_require_manual_recheck_and_no_execution() -> None:
    pack = build_tiingo_current_docs_recheck_pack(report_date="2026-05-30").to_dict()
    for item in pack["checklist_items"]:
        assert item["needs_manual_recheck"] is True
        assert item["source_accessed_live"] is False
        assert item["api_called"] is False
        assert item["cache_written"] is False
        assert item["operator_signoff_required"] is True
        assert item["official_source_label"]
        assert item["official_source_url_or_reference"]
        assert item["evidence_date"] == "2026-05-30"


def test_pilot_remains_not_approved_and_verdict_is_conservative() -> None:
    pack = build_tiingo_current_docs_recheck_pack(report_date="2026-05-30").to_dict()
    assert pack["provider"] == "Tiingo"
    assert pack["scenario"] == "public_ohlcv"
    assert pack["readiness_verdict"] == TIINGO_RECHECK_VERDICT
    assert "tiingo_api_call" in pack["safety"]["explicitly_not_approved"]
    assert "cache_write" in pack["safety"]["explicitly_not_approved"]
    assert "actual_refresh_import" in pack["safety"]["explicitly_not_approved"]


def test_manual_signoff_checklist_exists() -> None:
    pack = build_tiingo_current_docs_recheck_pack(report_date="2026-05-30").to_dict()
    signoffs = set(pack["manual_signoff_checklist"])
    assert "pricing_plan_signoff" in signoffs
    assert "terms_redistribution_attribution_signoff" in signoffs
    assert "api_limits_throughput_signoff" in signoffs
    assert "adjusted_price_method_signoff" in signoffs
    assert "cache_suitability_signoff_before_any_cache_write" in signoffs


def test_report_contains_required_sections_and_summary() -> None:
    markdown, payload = build_tiingo_current_docs_recheck_pack_report(report_date="2026-05-30")
    for heading in (
        "## Executive Summary",
        "## Why This Pack Exists",
        "## Current Pilot Candidate",
        "## Official Source References",
        "## Pricing / Plan Recheck",
        "## API Limits / Throughput Recheck",
        "## Terms / Redistribution / Attribution Recheck",
        "## Cache Suitability Recheck",
        "## EOD Coverage Recheck",
        "## Adjusted Price Method Recheck",
        "## Split / Dividend / Corporate Action Recheck",
        "## ETF / ADR / Mutual Fund / Delisted Coverage Recheck",
        "## Python Implementation Notes",
        "## Pilot Universe Compatibility",
        "## Manual Sign-off Checklist",
        "## Blocking Questions Before Live Fetch",
        "## Explicitly Not Approved",
        "## Next Approval Decision",
        "## Machine-Readable Summary",
    ):
        assert heading in markdown
    assert payload["pack_version"] == "v52"
    assert payload["tiingo_current_docs_recheck_pack"]["readiness_verdict"] == TIINGO_RECHECK_VERDICT


def test_write_tiingo_recheck_pack_outputs(tmp_path: Path) -> None:
    markdown, payload = build_tiingo_current_docs_recheck_pack_report(report_date="2026-05-30")
    paths = write_tiingo_current_docs_recheck_pack_outputs(
        out_dir=tmp_path,
        report_date="2026-05-30",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_tiingo_current_docs_recheck_pack_md"].is_file()
    assert paths["weekly_tiingo_current_docs_recheck_pack_json"].is_file()


def test_cli_help_exposes_only_safe_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["weekly-candidate-brief-tiingo-current-docs-recheck-pack", "--help"])
    assert result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-tiingo-current-docs-recheck-pack"
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
            "weekly-candidate-brief-tiingo-current-docs-recheck-pack",
            "--report-date",
            "2026-05-30",
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "tiingo_current_docs_recheck_pack"' in result.output
    assert "source_only=true" in result.stderr
    assert "tiingo_api_called=false" in result.stderr
    assert "cache_write_executed=false" in result.stderr
    assert (tmp_path / "latest" / "tiingo_current_docs_recheck_pack.json").is_file()


def test_context_pack_includes_tiingo_recheck_status() -> None:
    block = build_provider_context_pack_block(report_date="2026-05-30")
    status = block["tiingo_current_docs_recheck_status"]
    assert status["recheck_pack_exists"] is True
    assert status["source_only"] is True
    assert status["manual_recheck_required_before_live_fetch"] is True
    assert status["pricing_terms_cache_adjustment_rate_limit_signoff_required"] is True
    assert status["pilot_approved"] is False
    assert status["cache_write_approved"] is False
    assert status["actual_import_approved"] is False
    assert status["readiness_verdict"] == TIINGO_RECHECK_VERDICT
