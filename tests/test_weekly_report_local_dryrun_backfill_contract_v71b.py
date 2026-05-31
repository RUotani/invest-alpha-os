from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.weekly_report_local_dryrun_backfill_contract import (
    build_weekly_report_local_dryrun_backfill_contract,
    format_weekly_report_local_dryrun_backfill_contract_markdown,
    write_weekly_report_local_dryrun_backfill_contract_outputs,
)


def test_contract_defines_safe_command_inventory_without_approving_backfill() -> None:
    payload = build_weekly_report_local_dryrun_backfill_contract(
        report_date="2026-05-31",
        missed_report_date="2026-05-30",
    )
    commands = {row["id"]: row["command"] for row in payload["command_inventory"]}
    assert payload["pack_version"] == "v71B"
    assert payload["readiness_verdict"] == "local_dryrun_backfill_contract_ready_execution_not_approved"
    assert payload["scope"]["local_dryrun_execution_approved_by_this_pack"] is False
    assert payload["scope"]["manual_backfill_execution_approved_by_this_pack"] is False
    assert "weekly-candidate-brief --report-date 2026-05-30 --format markdown" in commands["generate_markdown_report"]
    assert "weekly-candidate-brief-email --report-date 2026-05-30" in commands["build_email_draft_preview"]
    all_commands = "\n".join(commands.values())
    assert "--write-cache" not in all_commands
    assert "--send-test" not in all_commands
    assert "cache-refresh-execute" not in all_commands
    assert "manual-csv-import-execute" not in all_commands


def test_output_contract_forbids_raw_data_locations() -> None:
    payload = build_weekly_report_local_dryrun_backfill_contract(report_date="2026-05-31")
    contract = payload["output_contract"]
    allowed = "\n".join(contract["allowed_redacted_or_generated_outputs"])
    forbidden = "\n".join(contract["forbidden_locations"])
    assert "reports/2026-05-30/weekly_candidate_brief_v0_1.md" in allowed
    assert "outputs/operator/weekly_candidate_brief/2026-05-30/status.json" in allowed
    assert "raw OHLCV files" in forbidden
    assert "reports-private raw market data" in forbidden
    assert payload["safety_summary"]["raw_ohlcv_persistence_executed"] is False
    assert payload["safety_summary"]["git_tracked_raw_data_written"] is False


def test_failure_mode_matrix_covers_required_cases_and_markdown() -> None:
    payload = build_weekly_report_local_dryrun_backfill_contract(report_date="2026-05-31")
    failure_ids = {row["id"] for row in payload["failure_mode_matrix"]}
    assert {
        "CLI_MISSING",
        "DATE_MISMATCH",
        "TIMEZONE_MISMATCH",
        "OUTPUT_MISSING",
        "EMPTY_REPORT",
        "NOTIFICATION_EXPORT_MISSING",
        "WORKFLOW_NOT_APPROVED",
    }.issubset(failure_ids)
    markdown = format_weekly_report_local_dryrun_backfill_contract_markdown(payload)
    assert "## Failure Mode Matrix" in markdown
    assert "provider_live_access_executed: false" in markdown
    assert "workflow_files_modified: false" in markdown


def test_writer_outputs_markdown_and_json(tmp_path: Path) -> None:
    payload = build_weekly_report_local_dryrun_backfill_contract(report_date="2026-05-31")
    markdown = format_weekly_report_local_dryrun_backfill_contract_markdown(payload)
    paths = write_weekly_report_local_dryrun_backfill_contract_outputs(
        out_dir=tmp_path / "out",
        report_date="2026-05-31",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_weekly_report_local_dryrun_backfill_contract_md"].is_file()
    assert paths["latest_weekly_report_local_dryrun_backfill_contract_json"].is_file()
    assert paths["weekly_weekly_report_local_dryrun_backfill_contract_md"].is_file()
    loaded = json.loads(paths["weekly_weekly_report_local_dryrun_backfill_contract_json"].read_text(encoding="utf-8"))
    assert loaded["report_name"] == "weekly_report_local_dryrun_backfill_contract"


def test_cli_and_context_pack_include_v71b(tmp_path: Path) -> None:
    runner = CliRunner()
    help_result = runner.invoke(app, ["weekly-candidate-brief-local-dryrun-backfill-contract", "--help"])
    assert help_result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-local-dryrun-backfill-contract"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-date", "--missed-report-date", "--out-dir", "--format"}.issubset(option_names)
    assert "--execute" not in option_names
    assert "--send" not in option_names
    assert "--write-cache" not in option_names
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-local-dryrun-backfill-contract",
            "--report-date",
            "2026-05-31",
            "--missed-report-date",
            "2026-05-30",
            "--out-dir",
            str(tmp_path / "cli"),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "weekly_report_local_dryrun_backfill_contract"' in result.output
    assert "local_dryrun_executed=false" in result.stderr
    assert "workflow_files_modified=false" in result.stderr

    report_dir = tmp_path / "reports" / "2026-05-31"
    report_dir.mkdir(parents=True, exist_ok=True)
    weekly_payload = {
        "sections": {
            "top_picks": [
                {"ticker": "AAPL", "name": "Apple", "asset_class": "us_stock", "score_total": 90, "score": 90}
            ],
            "avoid": [],
            "insufficient": [],
        }
    }
    (report_dir / "weekly_candidate_brief_v0_1.json").write_text(
        json.dumps(weekly_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    pack = build_chatgpt_context_pack(report_date="2026-05-31", report_dir=report_dir)
    status = pack.json_payload["weekly_report_local_dryrun_backfill_contract_status"]
    assert status["contract_exists"] is True
    assert status["local_dryrun_execution_approved_by_this_pack"] is False
    assert status["manual_backfill_execution_approved_by_this_pack"] is False
    assert status["workflow_files_modified"] is False
    assert "- weekly_report_local_dryrun_backfill_contract_exists: true" in pack.markdown_text
