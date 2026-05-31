from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.scheduled_report_failure_triage_matrix import (
    build_scheduled_report_failure_triage_matrix,
    format_scheduled_report_failure_triage_matrix_markdown,
    write_scheduled_report_failure_triage_matrix_outputs,
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


def test_triage_matrix_contains_required_failure_classes() -> None:
    payload = build_scheduled_report_failure_triage_matrix(report_date="2026-06-01")
    failure_classes = {row["failure_class"] for row in payload["triage_matrix"]}
    assert {
        "scheduler_failure",
        "cli_failure",
        "report_generation_failure",
        "delivery_export_failure",
        "timezone_mismatch",
        "missing_secret",
        "permission_failure",
        "silent_failure",
    }.issubset(failure_classes)
    assert payload["expected_schedule"]["utc_cron_expression"] == "0 22 * * 5"
    assert payload["expected_schedule"]["corresponding_jst_schedule"] == "Saturday 07:00 Asia/Tokyo"


def test_evidence_boundaries_do_not_expose_secrets_or_raw_data() -> None:
    payload = build_scheduled_report_failure_triage_matrix(report_date="2026-06-01")
    boundaries = payload["evidence_boundaries"]
    assert boundaries["secret_values_may_be_displayed"] is False
    assert boundaries["raw_market_data_may_be_read"] is False
    assert boundaries["raw_market_data_may_be_written"] is False
    assert boundaries["live_http_may_be_used"] is False
    assert boundaries["workflow_files_may_be_modified"] is False
    assert payload["safety_summary"]["env_secret_displayed"] is False
    assert payload["safety_summary"]["workflow_files_modified"] is False


def test_markdown_writer_and_cli_context(tmp_path: Path) -> None:
    payload = build_scheduled_report_failure_triage_matrix(report_date="2026-06-01")
    markdown = format_scheduled_report_failure_triage_matrix_markdown(payload)
    assert "scheduler_failure" in markdown
    assert "missing_secret" in markdown
    assert "secret_values_may_be_displayed: false" in markdown
    paths = write_scheduled_report_failure_triage_matrix_outputs(
        out_dir=tmp_path / "out",
        report_date="2026-06-01",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_scheduled_report_failure_triage_matrix_md"].is_file()
    loaded = json.loads(paths["weekly_scheduled_report_failure_triage_matrix_json"].read_text(encoding="utf-8"))
    assert loaded["report_name"] == "scheduled_report_failure_triage_matrix"

    runner = CliRunner()
    help_result = runner.invoke(app, ["weekly-candidate-brief-scheduled-report-failure-triage", "--help"])
    assert help_result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-scheduled-report-failure-triage"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-date", "--expected-cron-utc", "--out-dir", "--format"}.issubset(option_names)
    assert "--show-secret" not in option_names
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-scheduled-report-failure-triage",
            "--report-date",
            "2026-06-01",
            "--out-dir",
            str(tmp_path / "cli"),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "scheduled_report_failure_triage_matrix"' in result.output
    assert "env_secret_displayed=false" in result.stderr

    report_dir = tmp_path / "reports" / "2026-06-01"
    _write_minimal_report(report_dir)
    pack = build_chatgpt_context_pack(report_date="2026-06-01", report_dir=report_dir)
    status = pack.json_payload["scheduled_report_failure_triage_matrix_status"]
    assert status["matrix_exists"] is True
    assert "scheduler_failure" in status["failure_classes"]
    assert status["secret_values_may_be_displayed"] is False
    assert "- scheduled_report_failure_triage_matrix_exists: true" in pack.markdown_text
