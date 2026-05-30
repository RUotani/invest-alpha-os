from __future__ import annotations

import inspect
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.us_provider_current_evidence import (
    REQUIRED_CURRENT_EVIDENCE_DIMENSIONS,
    US_PROVIDER_CURRENT_EVIDENCE_PROVIDERS,
    build_us_provider_current_evidence_pack,
)
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_provider_context_pack_block,
    build_us_provider_current_evidence_pack_report,
    write_us_provider_current_evidence_pack_outputs,
)


def test_current_evidence_pack_is_source_only() -> None:
    pack = build_us_provider_current_evidence_pack(report_date="2026-05-30").to_dict()
    safety = pack["safety"]
    assert safety["source_only"] is True
    assert safety["live_http_executed"] is False
    assert safety["provider_live_access_executed"] is False
    assert safety["cache_write_executed"] is False
    assert safety["actual_refresh_import_executed"] is False
    assert safety["env_secret_displayed"] is False
    assert safety["broker_manual_raw_data_handled"] is False
    assert safety["workflow_dependency_pyproject_changed"] is False
    assert safety["trading_action_executed"] is False


def test_all_required_providers_and_dimensions_are_present() -> None:
    pack = build_us_provider_current_evidence_pack(report_date="2026-05-30").to_dict()
    providers = {row["provider"] for row in pack["providers"]}
    assert set(US_PROVIDER_CURRENT_EVIDENCE_PROVIDERS).issubset(providers)
    assert set(REQUIRED_CURRENT_EVIDENCE_DIMENSIONS).issubset(set(pack["evidence_dimensions"]))
    for provider in pack["providers"]:
        for dimension in REQUIRED_CURRENT_EVIDENCE_DIMENSIONS:
            assert dimension in provider


def test_all_current_evidence_requires_manual_recheck() -> None:
    pack = build_us_provider_current_evidence_pack(report_date="2026-05-30").to_dict()
    for provider in pack["providers"]:
        assert provider["needs_current_recheck"] is True
        assert provider["evidence_confidence"] == "seed_only / manual_recheck_required"
        assert provider["source_accessed_live"] is False


def test_v46_provider_roles_remain_unapproved() -> None:
    pack = build_us_provider_current_evidence_pack(report_date="2026-05-30").to_dict()
    rec = pack["current_v46_recommendation"]
    roles = {row["provider"]: row["recommended_role"] for row in pack["providers"]}
    assert rec["first_pilot_candidate"] == "Tiingo"
    assert rec["production_candidate"] == "Polygon.io"
    assert rec["free_fallback"] == "Stooq"
    assert rec["provider_selected"] == "false"
    assert rec["live_testing_approved"] == "false"
    assert roles["Tiingo"] == "first_pilot_candidate_not_approved"
    assert roles["Polygon.io"] == "production_candidate_not_approved"
    assert roles["Stooq"] == "free_fallback_not_primary"


def test_current_evidence_report_contains_required_sections() -> None:
    markdown, payload = build_us_provider_current_evidence_pack_report(report_date="2026-05-30")
    for heading in (
        "## Executive Summary",
        "## Evidence Date",
        "## Why This Evidence Pack Exists",
        "## Current v46 Recommendation",
        "## Provider Evidence Table",
        "## Pricing / Plan Evidence",
        "## Historical OHLCV Evidence",
        "## Adjusted Price / Corporate Action Evidence",
        "## Coverage / Universe Evidence",
        "## Bulk / Rate Limit Evidence",
        "## Terms / Cache Suitability Evidence",
        "## Evidence Gaps",
        "## Pilot Readiness Verdict",
        "## Recommended First Pilot Recheck",
        "## Hard Gates Required For Live Testing",
        "## Explicitly Not Approved",
        "## Next Approval Request Draft",
        "## Machine-Readable Summary",
    ):
        assert heading in markdown
    assert payload["pack_version"] == "v48"
    assert payload["current_evidence_pack"]["current_v46_recommendation"]["first_pilot_candidate"] == "Tiingo"


def test_write_current_evidence_pack_outputs(tmp_path: Path) -> None:
    markdown, payload = build_us_provider_current_evidence_pack_report(report_date="2026-05-30")
    paths = write_us_provider_current_evidence_pack_outputs(
        out_dir=tmp_path,
        report_date="2026-05-30",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_us_provider_current_evidence_pack_md"].is_file()
    assert paths["weekly_us_provider_current_evidence_pack_json"].is_file()


def test_cli_help_exposes_only_safe_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["weekly-candidate-brief-us-provider-current-evidence-pack", "--help"])
    assert result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-us-provider-current-evidence-pack"
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


def test_cli_current_evidence_generation_is_source_only(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-us-provider-current-evidence-pack",
            "--report-date",
            "2026-05-30",
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "us_provider_current_evidence_pack"' in result.output
    assert "source_only=true" in result.stderr
    assert "provider_live_access_executed=false" in result.stderr
    assert (tmp_path / "latest" / "us_provider_current_evidence_pack.json").is_file()


def test_context_pack_includes_current_evidence_status() -> None:
    block = build_provider_context_pack_block(report_date="2026-05-30")
    status = block["us_provider_current_evidence_status"]
    assert status["current_evidence_pack_exists"] is True
    assert status["source_only"] is True
    assert status["source_accessed_live"] is False
    assert status["evidence_confidence"] == "seed_only / manual_recheck_required"
    assert status["needs_current_recheck"] is True
    assert "Tiingo" in status["providers"]
    assert "current_pricing_terms" in status["evidence_gaps"]
