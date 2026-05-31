from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.weekly_report_manual_backfill_command_pack import (
    build_weekly_report_manual_backfill_command_pack,
    format_weekly_report_manual_backfill_command_pack_markdown,
    write_weekly_report_manual_backfill_command_pack_outputs,
)


def _write_minimal_report(report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "sections": {
            "top_picks": [
                {"ticker": "AAPL", "name": "Apple", "asset_class": "us_stock", "score_total": 90, "score": 90}
            ],
            "avoid": [],
            "insufficient": [],
        }
    }
    (report_dir / "weekly_candidate_brief_v0_1.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_manual_backfill_command_pack_is_source_only() -> None:
    payload = build_weekly_report_manual_backfill_command_pack(report_date="2026-06-01")
    assert payload["pack_version"] == "v72B"
    assert payload["timezone"] == "Asia/Tokyo"
    assert payload["dry_run_boundary"]["manual_backfill_execution_approved_by_this_pack"] is False
    assert payload["dry_run_boundary"]["provider_live_access_allowed"] is False
    assert payload["dry_run_boundary"]["actual_refresh_import_allowed"] is False
    assert payload["dry_run_boundary"]["gmail_send_allowed"] is False
    assert payload["safety_summary"]["workflow_files_modified"] is False


def test_command_pack_and_output_schema_are_explicit() -> None:
    payload = build_weekly_report_manual_backfill_command_pack(report_date="2026-06-01")
    commands = {row["id"]: row["command"] for row in payload["command_pack"]}
    all_commands = "\n".join(commands.values())
    assert "--report-date 2026-05-30 --format markdown" in commands["generate_markdown"]
    assert "--report-date 2026-05-30 --format json" in commands["generate_json"]
    assert "--report-date 2026-05-30 --format copy" in commands["generate_copy"]
    assert "weekly-candidate-brief-email --report-date 2026-05-30" in commands["build_email_preview_no_send"]
    assert "--send-test" not in all_commands
    assert "cache-refresh-execute" not in all_commands
    assert "manual-csv-import-execute" not in all_commands
    schema = payload["expected_output_schema"]
    assert schema["markdown_report"] == "reports/2026-05-30/weekly_candidate_brief_v0_1.md"
    assert schema["json_report"] == "reports/2026-05-30/weekly_candidate_brief_v0_1.json"
    assert schema["raw_data_outputs_allowed"] is False


def test_markdown_and_writer(tmp_path: Path) -> None:
    payload = build_weekly_report_manual_backfill_command_pack(report_date="2026-06-01")
    markdown = format_weekly_report_manual_backfill_command_pack_markdown(payload)
    assert "manual_backfill_execution_approved_by_this_pack: false" in markdown
    assert "raw_data_outputs_allowed: false" in markdown
    paths = write_weekly_report_manual_backfill_command_pack_outputs(
        out_dir=tmp_path / "out",
        report_date="2026-06-01",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_weekly_report_manual_backfill_command_pack_md"].is_file()
    loaded = json.loads(paths["weekly_weekly_report_manual_backfill_command_pack_json"].read_text(encoding="utf-8"))
    assert loaded["report_name"] == "weekly_report_manual_backfill_command_pack"


def test_cli_and_context_pack_include_v72b(tmp_path: Path) -> None:
    runner = CliRunner()
    help_result = runner.invoke(app, ["weekly-candidate-brief-manual-backfill-command-pack", "--help"])
    assert help_result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-manual-backfill-command-pack"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-date", "--missed-report-date", "--target-timezone", "--backfill-out-dir", "--out-dir", "--format"}.issubset(
        option_names
    )
    assert "--execute" not in option_names
    assert "--send" not in option_names
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-manual-backfill-command-pack",
            "--report-date",
            "2026-06-01",
            "--out-dir",
            str(tmp_path / "cli"),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "weekly_report_manual_backfill_command_pack"' in result.output
    assert "manual_backfill_executed=false" in result.stderr
    assert "gmail_send_executed=false" in result.stderr

    report_dir = tmp_path / "reports" / "2026-06-01"
    _write_minimal_report(report_dir)
    pack = build_chatgpt_context_pack(report_date="2026-06-01", report_dir=report_dir)
    status = pack.json_payload["weekly_report_manual_backfill_command_pack_status"]
    assert status["pack_exists"] is True
    assert status["manual_backfill_execution_approved_by_this_pack"] is False
    assert status["raw_data_outputs_allowed"] is False
    assert status["workflow_files_modified"] is False
    assert "- weekly_report_manual_backfill_command_pack_exists: true" in pack.markdown_text
