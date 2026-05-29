from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.ohlcv_provider_registry import (
    ProviderPriorityPolicy,
    build_default_ohlcv_provider_registry,
)
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_ohlcv_provider_automation_core,
    build_ohlcv_provider_coverage_matrix,
    build_ohlcv_provider_selection_planner,
    write_ohlcv_provider_automation_core_outputs,
)


def test_provider_registry_registration_includes_required_specs() -> None:
    registry = build_default_ohlcv_provider_registry()
    provider_ids = {spec.provider_id for spec in registry.list()}
    assert {
        "jquants",
        "stooq_manual",
        "yahoo_manual",
        "stooq_live_gated",
        "alpha_vantage_gated",
        "tiingo_gated",
        "polygon_gated",
        "eodhd_gated",
    }.issubset(provider_ids)
    assert registry.get("jquants").supports_market("JP")


def test_provider_priority_selection_jp_requires_jquants_approval_when_live_disabled() -> None:
    policy = ProviderPriorityPolicy(build_default_ohlcv_provider_registry())
    selection = policy.select(
        market="JP",
        ticker="285A",
        required_date_from="2026-03-06",
        required_date_to="2026-05-29",
        freshness_required=True,
        allow_live_http=False,
        allow_cache_write=False,
    )
    assert selection.selected_provider == "jquants"
    assert selection.requires_approval is True
    assert selection.reason == "live_http_disabled"
    assert "J-Quants" in str(selection.approval_phrase)


def test_provider_priority_selection_us_falls_back_to_manual_when_live_disabled() -> None:
    policy = ProviderPriorityPolicy(build_default_ohlcv_provider_registry())
    selection = policy.select(
        market="US",
        ticker="NVDA",
        required_date_from="2026-03-06",
        required_date_to="2026-05-29",
        freshness_required=True,
        allow_live_http=False,
        allow_cache_write=True,
    )
    assert selection.selected_provider == "stooq_manual"
    assert selection.requires_approval is False
    assert selection.reason == "freshness_requires_human_supplied_csv_or_approval"


def test_coverage_matrix_report_contains_285a_and_no_live_execution() -> None:
    markdown, payload = build_ohlcv_provider_coverage_matrix(report_date="2026-05-29")
    assert "285A" in payload["sample_tickers"]["JP"]
    assert payload["live_http_executed"] is False
    assert payload["cache_write_executed"] is False
    assert "stooq_live_gated" in markdown


def test_selection_planner_report_generation_blocks_live_provider() -> None:
    markdown, payload = build_ohlcv_provider_selection_planner(report_date="2026-05-29")
    assert "OHLCV Provider Selection Planner" in markdown
    rows = payload["selections"]
    jp = next(row for row in rows if row["ticker"] == "285A")
    assert jp["requires_approval"] is True
    assert jp["reason"] == "live_http_disabled"


def test_automation_core_writes_latest_outputs(tmp_path: Path) -> None:
    result = build_ohlcv_provider_automation_core(report_date="2026-05-29")
    paths = write_ohlcv_provider_automation_core_outputs(
        out_dir=tmp_path,
        report_date="2026-05-29",
        result=result,
    )
    assert paths["latest_ohlcv_provider_registry_strategy_md"].is_file()
    assert paths["latest_cache_refresh_readiness_json"].is_file()


def test_cli_ohlcv_provider_automation_core_writes_reports(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-ohlcv-provider-automation-core",
            "--report-date",
            "2026-05-29",
            "--out-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "dry_run_only=true" in result.output
    assert (tmp_path / "latest" / "ohlcv_provider_selection_planner.json").is_file()
