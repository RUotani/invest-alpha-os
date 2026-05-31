from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.weekly_report_workflow_patch_review_gate import (
    build_weekly_report_workflow_patch_review_gate,
    format_weekly_report_workflow_patch_review_gate_markdown,
    write_weekly_report_workflow_patch_review_gate_outputs,
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


def test_workflow_patch_review_gate_freezes_schedule_and_approval_boundary(tmp_path: Path) -> None:
    payload = build_weekly_report_workflow_patch_review_gate(report_date="2026-06-01", repo_root=tmp_path)
    assert payload["pack_version"] == "v72"
    assert payload["schedule"]["utc_cron_expression"] == "0 22 * * 5"
    assert payload["schedule"]["corresponding_jst_schedule"] == "Saturday 07:00 Asia/Tokyo"
    assert payload["approval_gate"]["workflow_patch_required"] is True
    assert payload["approval_gate"]["workflow_patch_applied_by_this_pack"] is False
    assert payload["approval_gate"]["human_approval_required"] is True
    assert payload["safety_summary"]["workflow_files_modified"] is False


def test_patch_contains_manual_dispatch_and_expected_artifacts(tmp_path: Path) -> None:
    payload = build_weekly_report_workflow_patch_review_gate(report_date="2026-06-01", repo_root=tmp_path)
    patch = payload["exact_proposed_workflow_patch"]
    assert "workflow_dispatch:" in patch
    assert 'cron: "0 22 * * 5"' in patch
    assert "scripts/run_weekly_candidate_brief.sh" in patch
    assert "reports/*/weekly_candidate_brief_v0_1.md" in patch
    assert "outputs/operator/weekly_candidate_brief/*/status.json" in patch
    markdown = format_weekly_report_workflow_patch_review_gate_markdown(payload)
    assert "## Failure Detection" in markdown
    assert "scheduler_failure" in markdown
    assert "workflow_files_modified: false" in markdown


def test_writer_outputs_markdown_and_json(tmp_path: Path) -> None:
    payload = build_weekly_report_workflow_patch_review_gate(report_date="2026-06-01", repo_root=tmp_path)
    markdown = format_weekly_report_workflow_patch_review_gate_markdown(payload)
    paths = write_weekly_report_workflow_patch_review_gate_outputs(
        out_dir=tmp_path / "out",
        report_date="2026-06-01",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_weekly_report_workflow_patch_review_gate_md"].is_file()
    loaded = json.loads(paths["weekly_weekly_report_workflow_patch_review_gate_json"].read_text(encoding="utf-8"))
    assert loaded["report_name"] == "weekly_report_workflow_patch_review_gate"


def test_cli_and_context_pack_include_v72(tmp_path: Path) -> None:
    runner = CliRunner()
    help_result = runner.invoke(app, ["weekly-candidate-brief-workflow-patch-review-gate", "--help"])
    assert help_result.exit_code == 0
    command_info = next(
        command for command in app.registered_commands if command.name == "weekly-candidate-brief-workflow-patch-review-gate"
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
            "weekly-candidate-brief-workflow-patch-review-gate",
            "--report-date",
            "2026-06-01",
            "--out-dir",
            str(tmp_path / "cli"),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "weekly_report_workflow_patch_review_gate"' in result.output
    assert "workflow_files_modified=false" in result.stderr

    report_dir = tmp_path / "reports" / "2026-06-01"
    _write_minimal_report(report_dir)
    pack = build_chatgpt_context_pack(report_date="2026-06-01", report_dir=report_dir)
    status = pack.json_payload["weekly_report_workflow_patch_review_gate_status"]
    assert status["gate_exists"] is True
    assert status["utc_cron_expression"] == "0 22 * * 5"
    assert status["human_approval_required"] is True
    assert status["workflow_files_modified"] is False
    assert "- weekly_report_workflow_patch_review_gate_exists: true" in pack.markdown_text
