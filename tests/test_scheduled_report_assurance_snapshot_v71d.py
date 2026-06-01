from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.scheduled_report_assurance_snapshot import (
    build_scheduled_report_assurance_snapshot,
    format_scheduled_report_assurance_snapshot_markdown,
    write_scheduled_report_assurance_snapshot_outputs,
)


def test_assurance_snapshot_combines_v70d_to_v71c_components() -> None:
    payload = build_scheduled_report_assurance_snapshot(report_date="2026-05-31")
    assert payload["pack_version"] == "v71D"
    assert payload["next_run_target"]["next_run_date_jst"] == "2026-06-06"
    assert payload["next_run_target"]["next_run_local_time"] == "07:00"
    assert payload["next_run_target"]["github_actions_cron_utc"] == "0 22 * * 5"
    assert payload["component_status"]["scheduled_report_observability_exists"] is True
    assert payload["component_status"]["weekly_report_recovery_runbook_exists"] is True
    assert payload["component_status"]["weekly_report_workflow_approval_package_exists"] is True
    assert payload["component_status"]["weekly_report_local_dryrun_backfill_contract_exists"] is True
    assert payload["component_status"]["long_run_operator_preflight_sleep_guard_exists"] is True


def test_readiness_matrix_and_remaining_manual_approvals() -> None:
    payload = build_scheduled_report_assurance_snapshot(report_date="2026-05-31")
    rows = {row["item"]: row for row in payload["readiness_matrix"]}
    assert rows["next_saturday_morning_jst_target"]["status"] == "ready"
    assert rows["local_dryrun_backfill_contract_exists"]["status"] == "ready"
    assert rows["missing_report_sentinel_exists"]["status"] == "ready"
    assert rows["recovery_runbook_exists"]["status"] == "ready"
    assert rows["workflow_patch_required"]["status"] == "ready"
    assert rows["sleep_prevention_instruction_present"]["evidence"] == "caffeinate -dimsu -t 43200"
    assert rows["manual_approvals_remaining"]["status"] == "not_ready"
    assert "workflow patch applied" in rows["manual_approvals_remaining"]["evidence"]
    approvals = "\n".join(payload["remaining_manual_approvals"])
    assert "observe the next Saturday 07:00 JST scheduled workflow run" in approvals
    assert "local dry-run/backfill execution approval" in approvals
    assert "Gmail send approval" in approvals


def test_markdown_writer_and_safety_flags(tmp_path: Path) -> None:
    payload = build_scheduled_report_assurance_snapshot(report_date="2026-05-31")
    markdown = format_scheduled_report_assurance_snapshot_markdown(payload)
    assert "# Scheduled Report Assurance Snapshot / Next-Run Readiness Matrix v71D" in markdown
    assert "scheduled_report_ready_for_next_run_observation" in markdown
    assert "workflow_files_modified: false" in markdown
    assert "gmail_send_executed: false" in markdown
    paths = write_scheduled_report_assurance_snapshot_outputs(
        out_dir=tmp_path / "out",
        report_date="2026-05-31",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_scheduled_report_assurance_snapshot_md"].is_file()
    loaded = json.loads(paths["weekly_scheduled_report_assurance_snapshot_json"].read_text(encoding="utf-8"))
    assert loaded["report_name"] == "scheduled_report_assurance_snapshot"


def test_cli_and_context_pack_include_v71d(tmp_path: Path) -> None:
    runner = CliRunner()
    help_result = runner.invoke(app, ["weekly-candidate-brief-scheduled-report-assurance-snapshot", "--help"])
    assert help_result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-scheduled-report-assurance-snapshot"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-date", "--missed-report-date", "--target-local-hour", "--out-dir", "--format"}.issubset(option_names)
    assert "--apply-workflow" not in option_names
    assert "--send" not in option_names
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-scheduled-report-assurance-snapshot",
            "--report-date",
            "2026-05-31",
            "--out-dir",
            str(tmp_path / "cli"),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "scheduled_report_assurance_snapshot"' in result.output
    assert "workflow_files_modified=false" in result.stderr
    assert "gmail_send_executed=false" in result.stderr

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
    status = pack.json_payload["scheduled_report_assurance_snapshot_status"]
    assert status["snapshot_exists"] is True
    assert status["next_run_date_jst"] == "2026-06-06"
    assert status["workflow_files_modified"] is False
    assert status["gmail_send_executed"] is False
    assert "- scheduled_report_assurance_snapshot_exists: true" in pack.markdown_text
