from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.ohlcv_provider_approval import (
    ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
    CACHE_WRITE_APPROVAL_PHRASE,
    ProviderExecutionAction,
    PUBLIC_OHLCV_APPROVAL_PHRASE,
)
from invis_alpha_os.data.ohlcv_provider_execution import (
    ProviderExecutionMode,
    ProviderExecutionVerdict,
    build_provider_safe_execution_harness,
)
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_ohlcv_provider_safe_execution_harness,
    build_provider_context_pack_block,
    write_ohlcv_provider_safe_execution_harness_outputs,
)


def test_default_mode_never_executes_live_cache_import() -> None:
    harness = build_provider_safe_execution_harness(report_date="2026-05-29")
    result = harness.to_dict()["result"]
    audit = result["audit_summary"]
    assert result["mode"] == "DRY_RUN_TRANSCRIPT"
    assert audit["live_http_executed"] is False
    assert audit["cache_write_executed"] is False
    assert audit["actual_refresh_import_executed"] is False
    assert audit["env_secret_displayed"] is False
    assert audit["raw_data_handled"] is False


def test_dangerous_gates_blocked_without_explicit_approval() -> None:
    harness = build_provider_safe_execution_harness(
        report_date="2026-05-29",
        requested_action=ProviderExecutionAction.ACTUAL_REFRESH,
    )
    result = harness.to_dict()["result"]
    assert {"LIVE_HTTP", "CACHE_WRITE", "ACTUAL_REFRESH"}.issubset(set(result["required_gates"]))
    assert result["approved_action"]["approved_gates"] == []
    assert result["transcript"]["verdict"] == ProviderExecutionVerdict.BLOCKED_MISSING_APPROVAL.value


def test_approval_decision_presence_changes_verdict_but_not_execution() -> None:
    harness = build_provider_safe_execution_harness(
        report_date="2026-05-29",
        mode=ProviderExecutionMode.APPROVED_EXECUTION_STUB,
        requested_action=ProviderExecutionAction.ACTUAL_REFRESH,
        approved_phrases=(
            PUBLIC_OHLCV_APPROVAL_PHRASE,
            CACHE_WRITE_APPROVAL_PHRASE,
            ACTUAL_REFRESH_IMPORT_APPROVAL_PHRASE,
        ),
    )
    result = harness.to_dict()["result"]
    assert result["transcript"]["verdict"] == ProviderExecutionVerdict.READY_FOR_EXPLICIT_USER_APPROVAL.value
    assert result["audit_summary"]["live_http_executed"] is False
    assert result["audit_summary"]["cache_write_executed"] is False
    assert result["audit_summary"]["actual_refresh_import_executed"] is False


def test_cache_write_preflight_is_transcript_only() -> None:
    harness = build_provider_safe_execution_harness(
        report_date="2026-05-29",
        requested_action=ProviderExecutionAction.CACHE_WRITE,
    )
    preflight = harness.to_dict()["result"]["cache_write_preflight"]
    assert preflight["would_write_cache"] is False
    assert preflight["status"] == "transcript_only"


def test_actual_import_preflight_is_transcript_only() -> None:
    harness = build_provider_safe_execution_harness(
        report_date="2026-05-29",
        requested_action=ProviderExecutionAction.ACTUAL_IMPORT,
    )
    preflight = harness.to_dict()["result"]["actual_import_preflight"]
    assert preflight["would_import"] is False
    assert preflight["status"] == "transcript_only"


def test_rollback_and_verification_checklists_present() -> None:
    _, payload = build_ohlcv_provider_safe_execution_harness(report_date="2026-05-29")
    result = payload["harness"]["result"]
    assert result["rollback_checklist"]["items"]
    assert result["verification_checklist"]["items"]
    assert result["stop_conditions"]


def test_report_contains_required_transcript_sections() -> None:
    markdown, payload = build_ohlcv_provider_safe_execution_harness(report_date="2026-05-29")
    assert "# OHLCV Provider Safe Execution Harness" in markdown
    for heading in (
        "## Requested Execution Scenario",
        "## Gate Evaluation",
        "## Preflight Result",
        "## Dry-Run Transcript",
        "## Expected Artifacts",
        "## Verification Checklist",
        "## Rollback Checklist",
        "## Stop Conditions",
        "## Safety Verdict",
    ):
        assert heading in markdown
    assert payload["harness"]["result"]["audit_summary"]["reports_private_touched"] is False


def test_write_safe_execution_harness_outputs(tmp_path: Path) -> None:
    markdown, payload = build_ohlcv_provider_safe_execution_harness(report_date="2026-05-29")
    paths = write_ohlcv_provider_safe_execution_harness_outputs(
        out_dir=tmp_path,
        report_date="2026-05-29",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_ohlcv_provider_safe_execution_harness_md"].is_file()
    assert paths["weekly_ohlcv_provider_safe_execution_harness_json"].is_file()


def test_cli_help_exposes_only_safe_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["weekly-candidate-brief-ohlcv-provider-safe-execution-harness", "--help"])
    assert result.exit_code == 0
    assert "--report-date" in result.output
    assert "--out-dir" in result.output
    assert "--format" in result.output
    assert "--live" not in result.output
    assert "--write-cache" not in result.output
    assert "--execute" not in result.output
    assert "--import" not in result.output


def test_cli_report_generation_is_dry_run_transcript_only(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-ohlcv-provider-safe-execution-harness",
            "--report-date",
            "2026-05-29",
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert "DRY_RUN_TRANSCRIPT" in result.output
    assert "dry_run_transcript_only=true" in result.stderr
    assert (tmp_path / "latest" / "ohlcv_provider_safe_execution_harness.json").is_file()
    assert "--live" not in result.output
    assert "--write-cache" not in result.output


def test_cli_rejects_unknown_format_without_writing(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-ohlcv-provider-safe-execution-harness",
            "--report-date",
            "2026-05-29",
            "--out-dir",
            str(tmp_path),
            "--format",
            "yaml",
        ],
    )
    assert result.exit_code == 2
    assert not (tmp_path / "latest" / "ohlcv_provider_safe_execution_harness.json").exists()


def test_context_pack_includes_harness_status() -> None:
    block = build_provider_context_pack_block(report_date="2026-05-29")
    status = block["provider_safe_execution_harness_status"]
    assert status["available"] is True
    assert status["mode"] == "DRY_RUN_TRANSCRIPT"
    assert status["dry_run_transcript_only"] is True
    assert status["current_verdict"] == ProviderExecutionVerdict.BLOCKED_MISSING_APPROVAL.value
    assert "LIVE_HTTP" in status["hard_gates_unapproved"]
