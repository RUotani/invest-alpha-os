from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.weekly_workflow_post_merge_observation_plan import (
    build_weekly_workflow_post_merge_observation_plan,
    format_weekly_workflow_post_merge_observation_plan_markdown,
    write_weekly_workflow_post_merge_observation_plan_outputs,
)


def test_post_merge_observation_plan_verifies_v73_workflow_source() -> None:
    payload = build_weekly_workflow_post_merge_observation_plan(report_date="2026-06-01")
    assert payload["pack_version"] == "v73B"
    assert payload["next_run_target"]["next_run_date_jst"] == "2026-06-06"
    assert payload["next_run_target"]["next_run_local_time"] == "07:00"
    assert payload["next_run_target"]["github_actions_cron_utc"] == "0 22 * * 5"
    assert payload["workflow_source_status"]["workflow_exists"] is True
    assert payload["workflow_source_status"]["expected_cron_found"] is True
    assert payload["workflow_source_status"]["workflow_dispatch_found"] is True
    assert payload["workflow_source_status"]["artifact_paths_found"] is True
    assert payload["readiness_verdict"] == "ready_to_observe_next_scheduled_run_source_verified"


def test_observation_plan_links_artifact_triage_and_backfill_paths() -> None:
    payload = build_weekly_workflow_post_merge_observation_plan(report_date="2026-06-01")
    ui_steps = {row["step"]: row for row in payload["github_actions_ui_checks"]}
    assert "weekly_candidate_brief.yml" in ui_steps["open_actions_workflow"]["manual_url"]
    assert "do not press Run workflow" in ui_steps["confirm_no_manual_dispatch"]["expected"]
    artifact_items = {row["item"]: row for row in payload["artifact_verification_checklist"]}
    assert artifact_items["artifact_container"]["expected"] == "weekly-candidate-brief"
    assert artifact_items["operator_status"]["required"] is True
    assert payload["failure_triage_path"]["primary_pack"] == "v72C Scheduled Report Failure Triage Matrix"
    assert "scheduler_failure" in payload["failure_triage_path"]["classes"]
    assert payload["manual_backfill_decision_path"]["command_contract_pack"].startswith("v72B")
    assert payload["manual_backfill_decision_path"]["manual_backfill_execution_approved_by_this_pack"] is False
    assert payload["manual_backfill_decision_path"]["gmail_send_approved_by_this_pack"] is False


def test_markdown_writer_and_safety_flags(tmp_path: Path) -> None:
    payload = build_weekly_workflow_post_merge_observation_plan(report_date="2026-06-01")
    markdown = format_weekly_workflow_post_merge_observation_plan_markdown(payload)
    assert "# Weekly Workflow Post-Merge Observation Plan / Next Saturday Assurance Pack v73B" in markdown
    assert "ready_to_observe_next_scheduled_run_source_verified" in markdown
    assert "manual_workflow_dispatch_executed: false" in markdown
    assert "provider_live_access_executed: false" in markdown
    assert "cache_write_executed: false" in markdown
    paths = write_weekly_workflow_post_merge_observation_plan_outputs(
        out_dir=tmp_path / "out",
        report_date="2026-06-01",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_weekly_workflow_post_merge_observation_plan_md"].is_file()
    loaded = json.loads(paths["weekly_weekly_workflow_post_merge_observation_plan_json"].read_text(encoding="utf-8"))
    assert loaded["report_name"] == "weekly_workflow_post_merge_observation_plan"


def test_cli_and_context_pack_include_v73b(tmp_path: Path) -> None:
    runner = CliRunner()
    help_result = runner.invoke(app, ["weekly-candidate-brief-workflow-observation-plan", "--help"])
    assert help_result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-workflow-observation-plan"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-date", "--target-local-hour", "--out-dir", "--format"}.issubset(option_names)
    assert "--dispatch" not in option_names
    assert "--send" not in option_names
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-workflow-observation-plan",
            "--report-date",
            "2026-06-01",
            "--out-dir",
            str(tmp_path / "cli"),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "weekly_workflow_post_merge_observation_plan"' in result.output
    assert "manual_workflow_dispatch_executed=false" in result.stderr
    assert "workflow_files_modified=false" in result.stderr

    report_dir = tmp_path / "reports" / "2026-06-01"
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
    pack = build_chatgpt_context_pack(report_date="2026-06-01", report_dir=report_dir)
    status = pack.json_payload["weekly_workflow_post_merge_observation_plan_status"]
    assert status["plan_exists"] is True
    assert status["workflow_exists"] is True
    assert status["expected_cron_found"] is True
    assert status["manual_workflow_dispatch_executed"] is False
    assert "- weekly_workflow_post_merge_observation_plan_exists: true" in pack.markdown_text
