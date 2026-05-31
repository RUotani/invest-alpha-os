from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.weekly_report_recovery_runbook import (
    build_weekly_report_recovery_runbook,
    format_weekly_report_recovery_runbook_markdown,
    write_weekly_report_recovery_runbook_outputs,
)


def test_recovery_runbook_does_not_approve_execution() -> None:
    payload = build_weekly_report_recovery_runbook(missed_report_date="2026-05-30")
    boundary = payload["backfill_approval_boundary"]
    assert payload["source_only"] is True
    assert boundary["this_pack_approves_backfill_execution"] is False
    assert boundary["manual_backfill_requires_human_choice"] is True
    assert boundary["gmail_send_approved"] is False
    assert boundary["workflow_change_approved"] is False
    assert boundary["provider_live_access_approved"] is False
    assert boundary["cache_write_approved"] is False
    assert boundary["actual_import_approved"] is False
    assert boundary["trading_action_approved"] is False


def test_recovery_commands_are_candidates_not_executed_by_pack() -> None:
    payload = build_weekly_report_recovery_runbook(missed_report_date="2026-05-30")
    commands = {row["command_id"]: row for row in payload["dry_run_commands"]}
    assert commands["CMD-01"]["executes_recovery"] is False
    assert commands["CMD-02"]["executes_recovery"] is False
    assert commands["CMD-03"]["executes_recovery"] is True
    assert "--report-date 2026-05-30" in commands["CMD-03"]["command"]
    assert "weekly-candidate-brief-email" in commands["CMD-05"]["command"]


def test_live_fetch_cache_import_and_trading_boundaries() -> None:
    payload = build_weekly_report_recovery_runbook(missed_report_date="2026-05-30")
    assert payload["live_fetch_boundary"]["provider_live_access_allowed"] is False
    assert payload["live_fetch_boundary"]["tiingo_api_call_allowed"] is False
    assert payload["cache_write_boundary"]["cache_write_allowed"] is False
    assert payload["cache_write_boundary"]["raw_ohlcv_persistence_allowed"] is False
    assert payload["actual_import_boundary"]["actual_refresh_import_allowed"] is False
    assert payload["actual_import_boundary"]["manual_actual_import_allowed"] is False
    assert payload["safety_summary"]["trading_action_executed"] is False


def test_markdown_writer_and_cli(tmp_path: Path) -> None:
    payload = build_weekly_report_recovery_runbook(missed_report_date="2026-05-30")
    markdown = format_weekly_report_recovery_runbook_markdown(payload)
    assert "## Safe Recovery Paths" in markdown
    assert "## Backfill Approval Boundary" in markdown
    assert "this_pack_approves_backfill_execution: false" in markdown
    paths = write_weekly_report_recovery_runbook_outputs(
        out_dir=tmp_path / "out",
        report_date="2026-05-30",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_weekly_report_recovery_runbook_md"].is_file()
    assert paths["weekly_weekly_report_recovery_runbook_json"].is_file()

    runner = CliRunner()
    help_result = runner.invoke(app, ["weekly-candidate-brief-recovery-runbook", "--help"])
    assert help_result.exit_code == 0
    command_info = next(
        command for command in app.registered_commands if command.name == "weekly-candidate-brief-recovery-runbook"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--missed-report-date", "--timezone", "--out-dir", "--format"}.issubset(option_names)
    assert "--execute" not in option_names
    assert "--send" not in option_names
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-recovery-runbook",
            "--missed-report-date",
            "2026-05-30",
            "--out-dir",
            str(tmp_path / "cli"),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "weekly_report_recovery_runbook"' in result.output
    assert "backfill_executed=false" in result.stderr


def test_chatgpt_context_pack_includes_v70f(tmp_path: Path) -> None:
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
    status = pack.json_payload["weekly_report_recovery_runbook_status"]
    assert status["runbook_exists"] is True
    assert status["missed_report_date"] == "2026-05-30"
    assert status["this_pack_approves_backfill_execution"] is False
    assert status["manual_backfill_requires_human_choice"] is True
    assert "- weekly_report_recovery_runbook_exists: true" in pack.markdown_text
