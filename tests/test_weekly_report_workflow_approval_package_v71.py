from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.weekly_report_workflow_approval_package import (
    build_weekly_report_workflow_approval_package,
    format_weekly_report_workflow_approval_package_markdown,
    write_weekly_report_workflow_approval_package_outputs,
)


def _write_minimal_repo(root: Path, *, workflow_text: str = "") -> None:
    workflow_dir = root / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    if workflow_text:
        (workflow_dir / "weekly_candidate_brief.yml").write_text(workflow_text, encoding="utf-8")
    launchd = root / "ops" / "launchd"
    launchd.mkdir(parents=True, exist_ok=True)
    (launchd / "com.invest-alpha-os.weekly-candidate-brief.plist.template").write_text(
        """<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict><key>StartCalendarInterval</key><dict><key>Weekday</key><integer>7</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict><key>EnvironmentVariables</key><dict><key>TZ</key><string>Asia/Tokyo</string></dict><key>ProgramArguments</key><array><string>scripts/run_weekly_candidate_brief.sh</string></array></dict></plist>""",
        encoding="utf-8",
    )
    scripts = root / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "run_weekly_candidate_brief.sh").write_text(
        "today_jst_iso\n--format markdown weekly_candidate_brief_v0_1.md\n--format copy weekly_candidate_brief_copy.md\nweekly-candidate-brief-email\nstatus.json\nCONFIRM_US_LIVE_HTTP=\n",
        encoding="utf-8",
    )


def test_missing_workflow_requires_human_approval(tmp_path: Path) -> None:
    _write_minimal_repo(tmp_path)
    payload = build_weekly_report_workflow_approval_package(report_date="2026-05-31", repo_root=tmp_path)
    assert payload["target_schedule"]["github_actions_cron_utc"] == "0 22 * * 5"
    assert payload["current_scheduler_assessment"]["workflow_patch_required"] is True
    assert payload["current_scheduler_assessment"]["tracked_weekly_workflow_schedule_sufficient"] is False
    assert payload["readiness_verdict"] == "workflow_patch_human_approval_required"
    assert payload["safety_summary"]["workflow_files_modified"] is False


def test_wrong_cron_detected(tmp_path: Path) -> None:
    _write_minimal_repo(
        tmp_path,
        workflow_text='on:\n  schedule:\n    - cron: "0 7 * * 6"\njobs:\n  x:\n    steps:\n      - run: scripts/run_weekly_candidate_brief.sh\n',
    )
    payload = build_weekly_report_workflow_approval_package(report_date="2026-05-31", repo_root=tmp_path)
    assert payload["current_scheduler_assessment"]["wrong_cron_detected"] is True
    assert payload["readiness_verdict"] == "workflow_patch_human_approval_required_wrong_cron_detected"


def test_correct_workflow_is_sufficient(tmp_path: Path) -> None:
    _write_minimal_repo(
        tmp_path,
        workflow_text='on:\n  schedule:\n    - cron: "0 22 * * 5"\njobs:\n  x:\n    steps:\n      - run: scripts/run_weekly_candidate_brief.sh\n',
    )
    payload = build_weekly_report_workflow_approval_package(report_date="2026-05-31", repo_root=tmp_path)
    assert payload["current_scheduler_assessment"]["workflow_patch_required"] is False
    assert payload["current_scheduler_assessment"]["tracked_weekly_workflow_schedule_sufficient"] is True
    assert payload["readiness_verdict"] == "tracked_workflow_schedule_sufficient"


def test_patch_rendering_and_writer(tmp_path: Path) -> None:
    _write_minimal_repo(tmp_path)
    payload = build_weekly_report_workflow_approval_package(report_date="2026-05-31", repo_root=tmp_path)
    markdown = format_weekly_report_workflow_approval_package_markdown(payload)
    assert "## Exact Proposed Workflow Patch" in markdown
    assert 'cron: "0 22 * * 5"' in markdown
    assert "workflow_files_modified: false" in markdown
    paths = write_weekly_report_workflow_approval_package_outputs(
        out_dir=tmp_path / "out",
        report_date="2026-05-31",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_weekly_report_workflow_approval_package_md"].is_file()
    assert paths["weekly_weekly_report_workflow_approval_package_json"].is_file()


def test_cli_and_context_pack_include_v71(tmp_path: Path) -> None:
    runner = CliRunner()
    help_result = runner.invoke(app, ["weekly-candidate-brief-workflow-approval-package", "--help"])
    assert help_result.exit_code == 0
    command_info = next(
        command for command in app.registered_commands if command.name == "weekly-candidate-brief-workflow-approval-package"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-date", "--target-timezone", "--target-weekday", "--target-local-hour", "--out-dir", "--format"}.issubset(
        option_names
    )
    assert "--apply" not in option_names
    assert "--edit-workflow" not in option_names
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-workflow-approval-package",
            "--report-date",
            "2026-05-31",
            "--out-dir",
            str(tmp_path / "cli"),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "weekly_report_workflow_approval_package"' in result.output
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
    status = pack.json_payload["weekly_report_workflow_approval_package_status"]
    assert status["package_exists"] is True
    assert status["github_actions_cron_utc"] == "0 22 * * 5"
    assert status["workflow_files_modified"] is False
    assert "- weekly_report_workflow_approval_package_exists: true" in pack.markdown_text
