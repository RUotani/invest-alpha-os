from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.long_run_development_progress_snapshot import (
    build_long_run_development_progress_snapshot,
    format_long_run_development_progress_snapshot_markdown,
    write_long_run_development_progress_snapshot_outputs,
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


def test_progress_snapshot_uses_domain_percentages_only() -> None:
    payload = build_long_run_development_progress_snapshot(report_date="2026-06-01")
    assert payload["pack_version"] == "v72D"
    assert payload["progress_policy"]["single_overall_percent_allowed"] is False
    assert payload["progress_policy"]["domain_percentages_only"] is True
    domains = {row["domain"]: row for row in payload["domain_progress"]}
    assert {"cache_write", "weekly_report", "actual_import", "operator_runbook"}.issubset(domains)
    assert domains["weekly_report"]["progress_percent"] == 90
    assert "explicit .github/workflows approval" in domains["weekly_report"]["remaining_blockers"]


def test_hard_gate_status_and_markdown_writer(tmp_path: Path) -> None:
    payload = build_long_run_development_progress_snapshot(report_date="2026-06-01")
    assert payload["hard_gate_status"]["provider_live_access"] == "not_executed"
    assert payload["hard_gate_status"]["workflow_direct_change"] == "not_applied"
    assert payload["hard_gate_status"]["trading_action"] == "not_executed"
    markdown = format_long_run_development_progress_snapshot_markdown(payload)
    assert "single_overall_percent_allowed: false" in markdown
    assert "| weekly_report | 90 |" in markdown
    paths = write_long_run_development_progress_snapshot_outputs(
        out_dir=tmp_path / "out",
        report_date="2026-06-01",
        markdown_text=markdown,
        json_payload=payload,
    )
    loaded = json.loads(paths["weekly_long_run_development_progress_snapshot_json"].read_text(encoding="utf-8"))
    assert loaded["report_name"] == "long_run_development_progress_snapshot"


def test_cli_and_context_pack_include_v72d(tmp_path: Path) -> None:
    runner = CliRunner()
    help_result = runner.invoke(app, ["weekly-candidate-brief-long-run-progress-snapshot", "--help"])
    assert help_result.exit_code == 0
    command_info = next(
        command for command in app.registered_commands if command.name == "weekly-candidate-brief-long-run-progress-snapshot"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-date", "--out-dir", "--format"}.issubset(option_names)
    assert "--overall-percent" not in option_names
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-long-run-progress-snapshot",
            "--report-date",
            "2026-06-01",
            "--out-dir",
            str(tmp_path / "cli"),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "long_run_development_progress_snapshot"' in result.output
    assert "single_overall_percent_allowed=false" in result.stderr
    assert "workflow_files_modified=false" in result.stderr

    report_dir = tmp_path / "reports" / "2026-06-01"
    _write_minimal_report(report_dir)
    pack = build_chatgpt_context_pack(report_date="2026-06-01", report_dir=report_dir)
    status = pack.json_payload["long_run_development_progress_snapshot_status"]
    assert status["snapshot_exists"] is True
    assert status["single_overall_percent_allowed"] is False
    assert "weekly_report" in status["domains"]
    assert "- long_run_development_progress_snapshot_exists: true" in pack.markdown_text
