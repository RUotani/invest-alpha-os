from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.scheduled_report_observability import (
    build_expected_occurrence,
    build_scheduled_report_observability,
    format_scheduled_report_observability_markdown,
    previous_expected_occurrence_date,
    write_scheduled_report_observability_outputs,
)


def test_expected_occurrence_model_for_saturday_jst() -> None:
    assert previous_expected_occurrence_date(as_of_date="2026-05-31", expected_weekday="Saturday") == "2026-05-30"
    occurrence = build_expected_occurrence(as_of_date="2026-05-31").to_dict()
    assert occurrence["expected_date"] == "2026-05-30"
    assert occurrence["expected_at_jst"] == "2026-05-30T07:00:00+09:00"
    assert occurrence["grace_deadline_jst"] == "2026-05-30T13:00:00+09:00"
    assert "reports/2026-05-30/weekly_candidate_brief_v0_1.md" in occurrence["report_paths"]


def test_invalid_lookback_fails_closed() -> None:
    try:
        previous_expected_occurrence_date(as_of_date="2026-05-31", lookback_days=0)
    except ValueError as exc:
        assert "lookback_days" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected lookback failure")


def test_missing_report_sentinel_detects_absent_artifacts(tmp_path: Path) -> None:
    payload = build_scheduled_report_observability(as_of_date="2026-05-31", repo_root=tmp_path)
    assert payload["missing_report_verdict"] == "missing_report_detected_source_artifact_absent"
    assert payload["expected_schedule"]["github_actions_cron_utc"] == "0 22 * * 5"
    assert payload["evidence_inputs"]["raw_market_data_read"] is False
    assert payload["evidence_inputs"]["raw_report_content_read"] is False
    assert payload["safety_summary"]["workflow_files_modified"] is False
    assert payload["safety_summary"]["gmail_send_executed"] is False


def test_present_report_without_status_warns(tmp_path: Path) -> None:
    report = tmp_path / "reports" / "2026-05-30" / "weekly_candidate_brief_v0_1.md"
    report.parent.mkdir(parents=True)
    report.write_text("# report\n", encoding="utf-8")
    payload = build_scheduled_report_observability(as_of_date="2026-05-31", repo_root=tmp_path)
    assert payload["missing_report_verdict"] == "warn_report_present_status_missing"


def test_report_and_status_present_passes(tmp_path: Path) -> None:
    report = tmp_path / "reports" / "2026-05-30" / "weekly_candidate_brief_v0_1.md"
    status = tmp_path / "outputs" / "operator" / "weekly_candidate_brief" / "2026-05-30" / "status.json"
    report.parent.mkdir(parents=True)
    status.parent.mkdir(parents=True)
    report.write_text("# report\n", encoding="utf-8")
    status.write_text('{"status":"weekly_candidate_brief_generated"}\n', encoding="utf-8")
    payload = build_scheduled_report_observability(as_of_date="2026-05-31", repo_root=tmp_path)
    assert payload["missing_report_verdict"] == "expected_report_present"


def test_markdown_writer_and_cli(tmp_path: Path) -> None:
    payload = build_scheduled_report_observability(as_of_date="2026-05-31", repo_root=tmp_path)
    markdown = format_scheduled_report_observability_markdown(payload)
    assert "## Expected Schedule" in markdown
    assert "## Missing Report Verdict" in markdown
    assert "missing_report_detected_source_artifact_absent" in markdown
    paths = write_scheduled_report_observability_outputs(
        out_dir=tmp_path / "out",
        report_date="2026-05-30",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_scheduled_report_observability_md"].is_file()
    assert paths["weekly_scheduled_report_observability_json"].is_file()

    runner = CliRunner()
    help_result = runner.invoke(app, ["weekly-candidate-brief-scheduled-report-observability", "--help"])
    assert help_result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-scheduled-report-observability"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-kind", "--as-of-date", "--timezone", "--expected-weekday", "--lookback-days"}.issubset(
        option_names
    )
    assert "--send" not in option_names
    assert "--write-workflow" not in option_names
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-scheduled-report-observability",
            "--as-of-date",
            "2026-05-31",
            "--out-dir",
            str(tmp_path / "cli"),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "scheduled_report_observability"' in result.output
    assert "workflow_files_modified=false" in result.stderr


def test_chatgpt_context_pack_includes_v70e(tmp_path: Path) -> None:
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
    status = pack.json_payload["scheduled_report_observability_status"]
    assert status["sentinel_exists"] is True
    assert status["expected_date"] == "2026-05-30"
    assert status["raw_market_data_read"] is False
    assert "- scheduled_report_observability_exists: true" in pack.markdown_text
