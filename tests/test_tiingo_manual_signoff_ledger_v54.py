from __future__ import annotations

import inspect
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.tiingo_manual_signoff_ledger import (
    REQUIRED_TIINGO_SIGNOFF_SECTIONS,
    TIINGO_MANUAL_SIGNOFF_VERDICT,
    TiingoManualReviewStatus,
    build_tiingo_manual_signoff_ledger,
)
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_provider_context_pack_block,
    build_tiingo_manual_signoff_ledger_report,
    write_tiingo_manual_signoff_ledger_outputs,
)


REQUIRED_FIELDS = {
    "item_id",
    "section",
    "question",
    "why_it_matters",
    "official_source_reference",
    "required_evidence",
    "operator_answer_placeholder",
    "operator_signoff_status",
    "blocking_if_unanswered",
    "blocks_live_fetch",
    "blocks_cache_write",
    "blocks_actual_import",
    "requires_secret_or_token",
    "source_accessed_live",
    "api_called",
    "cache_written",
    "actual_import_executed",
    "trading_action_executed",
    "needs_manual_current_recheck",
}


def test_manual_signoff_ledger_generation_is_source_only() -> None:
    ledger = build_tiingo_manual_signoff_ledger(report_date="2026-05-30").to_dict()
    safety = ledger["safety"]
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


def test_all_required_signoff_sections_exist() -> None:
    ledger = build_tiingo_manual_signoff_ledger(report_date="2026-05-30").to_dict()
    sections = {item["section"] for item in ledger["signoff_items"]}
    assert set(REQUIRED_TIINGO_SIGNOFF_SECTIONS).issubset(sections)


def test_all_required_fields_exist_and_default_to_unreviewed() -> None:
    ledger = build_tiingo_manual_signoff_ledger(report_date="2026-05-30").to_dict()
    for item in ledger["signoff_items"]:
        assert REQUIRED_FIELDS.issubset(item)
        assert item["operator_signoff_status"] == TiingoManualReviewStatus.UNREVIEWED.value
        assert item["blocking_if_unanswered"] is True
        assert item["source_accessed_live"] is False
        assert item["api_called"] is False
        assert item["cache_written"] is False
        assert item["actual_import_executed"] is False
        assert item["trading_action_executed"] is False
        assert item["needs_manual_current_recheck"] is True


def test_approval_statuses_remain_false_and_blocked() -> None:
    ledger = build_tiingo_manual_signoff_ledger(report_date="2026-05-30").to_dict()
    summary = ledger["evidence_summary"]
    assert summary["default_status"] == "unreviewed"
    assert summary["live_fetch_approved"] is False
    assert summary["cache_write_approved"] is False
    assert summary["actual_import_approved"] is False
    assert summary["primary_blocker"] == "manual_signoff_incomplete"
    assert ledger["final_verdict"] == TIINGO_MANUAL_SIGNOFF_VERDICT


def test_report_contains_required_sections_and_conservative_verdict() -> None:
    markdown, payload = build_tiingo_manual_signoff_ledger_report(report_date="2026-05-30")
    for heading in (
        "## Executive Summary",
        "## Current Pilot Candidate",
        "## Current Approval Status",
        "## How To Use This Review Sheet",
        "## Signoff Status Summary",
        "## Blocking Items Before Live Fetch",
        "## Pricing / Plan Signoff",
        "## Terms / Redistribution / Attribution Signoff",
        "## API Limits / Throughput Signoff",
        "## EOD Historical OHLCV Signoff",
        "## Adjusted Price Method Signoff",
        "## Split / Dividend / Corporate Action Signoff",
        "## Coverage Signoff",
        "## Cache Suitability Signoff",
        "## Pilot Scope Signoff",
        "## Secret / Redaction / No-Write Discipline",
        "## Verification Criteria",
        "## Operator Signoff Fields",
        "## Explicitly Not Approved",
        "## Final Readiness Verdict",
        "## Machine-Readable Summary",
    ):
        assert heading in markdown
    assert payload["pack_version"] == "v54"
    assert payload["tiingo_manual_signoff_ledger"]["final_verdict"] == TIINGO_MANUAL_SIGNOFF_VERDICT


def test_write_tiingo_manual_signoff_ledger_outputs(tmp_path: Path) -> None:
    markdown, payload = build_tiingo_manual_signoff_ledger_report(report_date="2026-05-30")
    paths = write_tiingo_manual_signoff_ledger_outputs(
        out_dir=tmp_path,
        report_date="2026-05-30",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_tiingo_manual_signoff_ledger_md"].is_file()
    assert paths["weekly_tiingo_manual_signoff_ledger_json"].is_file()


def test_cli_help_exposes_only_safe_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["weekly-candidate-brief-tiingo-manual-signoff-ledger", "--help"])
    assert result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-tiingo-manual-signoff-ledger"
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
            "weekly-candidate-brief-tiingo-manual-signoff-ledger",
            "--report-date",
            "2026-05-30",
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "tiingo_manual_signoff_ledger"' in result.output
    assert "source_only=true" in result.stderr
    assert "tiingo_api_called=false" in result.stderr
    assert "cache_write_executed=false" in result.stderr
    assert (tmp_path / "latest" / "tiingo_manual_signoff_ledger.json").is_file()


def test_context_pack_includes_manual_signoff_status() -> None:
    block = build_provider_context_pack_block(report_date="2026-05-30")
    status = block["tiingo_manual_signoff_ledger_status"]
    assert status["manual_signoff_ledger_exists"] is True
    assert status["all_items_default_unreviewed"] is True
    assert status["source_only"] is True
    assert status["live_fetch_approved"] is False
    assert status["cache_write_approved"] is False
    assert status["actual_import_approved"] is False
    assert status["primary_blocker"] == "manual_signoff_incomplete"
    assert status["final_verdict"] == TIINGO_MANUAL_SIGNOFF_VERDICT
