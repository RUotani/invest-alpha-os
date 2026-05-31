from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.weekly_report_schedule_diagnostic import (
    build_weekly_report_schedule_diagnostic,
    format_weekly_report_schedule_diagnostic_markdown,
    github_actions_cron_for_jst,
    write_weekly_report_schedule_diagnostic_outputs,
)


def test_saturday_0700_jst_maps_to_friday_2200_utc_cron() -> None:
    mapping = github_actions_cron_for_jst(
        expected_weekday="Saturday",
        expected_hour_jst=7,
        timezone_name="Asia/Tokyo",
    ).to_dict()
    assert mapping["github_actions_cron_utc"] == "0 22 * * 5"
    assert mapping["utc_weekday"] == "Friday"
    assert mapping["utc_hour"] == 22
    assert mapping["utc_minute"] == 0


def test_invalid_timezone_and_weekday_fail_closed() -> None:
    try:
        github_actions_cron_for_jst(timezone_name="UTC")
    except ValueError as exc:
        assert "Asia/Tokyo" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected timezone failure")
    try:
        github_actions_cron_for_jst(expected_weekday="Funday")
    except ValueError as exc:
        assert "unsupported weekday" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected weekday failure")


def test_source_diagnostic_identifies_missing_github_weekly_schedule() -> None:
    payload = build_weekly_report_schedule_diagnostic(observed_missing_date="2026-05-30")
    wiring = payload["detected_scheduler_wiring"]
    assert payload["user_observed_issue"] == "Saturday morning JST weekly report did not appear"
    assert "no_tracked_github_weekly_schedule" in payload["root_cause_found"]
    assert wiring["weekly_script"]["exists"] is True
    assert wiring["weekly_script"]["writes_markdown_report"] is True
    assert wiring["weekly_script"]["writes_copy_report"] is True
    assert wiring["weekly_script"]["writes_email_preview"] is True
    assert wiring["launchd_template"]["exists"] is True
    assert wiring["launchd_template"]["template_only_not_installation_evidence"] is True
    assert wiring["github_actions"]["github_weekly_schedule_found"] is False


def test_workflow_patch_is_proposed_not_applied() -> None:
    payload = build_weekly_report_schedule_diagnostic(observed_missing_date="2026-05-30")
    patch = payload["proposed_workflow_patch"]
    assert "weekly_candidate_brief.yml" in patch
    assert 'cron: "0 22 * * 5"' in patch
    assert "scripts/run_weekly_candidate_brief.sh" in patch
    assert payload["safety_summary"]["workflow_files_modified"] is False
    assert "RULES.md forbids .github/workflows changes" in payload["why_workflow_change_requires_human_approval"]


def test_markdown_and_output_writer(tmp_path: Path) -> None:
    payload = build_weekly_report_schedule_diagnostic(observed_missing_date="2026-05-30")
    markdown = format_weekly_report_schedule_diagnostic_markdown(payload)
    assert "## User-Observed Issue" in markdown
    assert "## Root Cause Candidates" in markdown
    assert "## Proposed Workflow Patch If Required" in markdown
    assert "workflow_files_modified: false" in markdown
    paths = write_weekly_report_schedule_diagnostic_outputs(
        out_dir=tmp_path,
        report_date="2026-05-30",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_weekly_report_schedule_diagnostic_md"].is_file()
    assert paths["weekly_weekly_report_schedule_diagnostic_json"].is_file()


def test_cli_and_context_pack_include_v70d(tmp_path: Path) -> None:
    runner = CliRunner()
    help_result = runner.invoke(app, ["weekly-candidate-brief-schedule-diagnostic", "--help"])
    assert help_result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-schedule-diagnostic"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {
        "--observed-missing-date",
        "--timezone",
        "--expected-weekday",
        "--expected-hour-jst",
        "--out-dir",
        "--format",
    }.issubset(option_names)
    assert "--send" not in option_names
    assert "--edit-workflow" not in option_names
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-schedule-diagnostic",
            "--observed-missing-date",
            "2026-05-30",
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "weekly_report_schedule_diagnostic"' in result.output
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
    status = pack.json_payload["weekly_report_schedule_diagnostic_status"]
    assert status["diagnostic_exists"] is True
    assert status["github_weekly_schedule_found"] is False
    assert status["workflow_files_modified"] is False
    assert "- weekly_report_schedule_diagnostic_exists: true" in pack.markdown_text
