from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.return_to_main_development_pack import (
    build_actual_import_quarantine_followthrough_matrix,
    build_cache_write_pilot_preexecution_readiness_snapshot,
    build_chatgpt_main_development_handoff_summary,
    build_portfolio_strategy_observation_report,
    build_weekly_scheduled_run_observation_pack,
    format_return_to_main_pack_markdown,
    write_return_to_main_pack_outputs,
)


def _write_minimal_weekly_json(report_dir: Path) -> None:
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


def test_v77a_weekly_scheduled_run_pack_is_observation_only() -> None:
    payload = build_weekly_scheduled_run_observation_pack(report_date="2026-06-02")
    status = payload["weekly_report_status"]
    workflow = status["workflow_source_status"]
    assert payload["pack_version"] == "v77"
    assert workflow["expected_cron_utc"] == "0 22 * * 5"
    assert workflow["corresponding_jst_schedule"] == "Saturday 07:00 JST"
    assert workflow["workflow_dispatch_expected"] is True
    assert workflow["artifact_name_expected"] == "weekly-candidate-brief"
    assert payload["manual_backfill_path"]["manual_backfill_execution_approved_by_this_pack"] is False
    assert payload["safety_summary"]["manual_workflow_dispatch_executed"] is False
    assert payload["safety_summary"]["workflow_files_modified"] is False


def test_v77b_cache_snapshot_consolidates_prior_gates_without_execution() -> None:
    payload = build_cache_write_pilot_preexecution_readiness_snapshot(report_date="2026-06-02")
    assert {"v67", "v68", "v69", "v69B", "v70", "v70B", "v70C"}.issubset(payload["consolidated_inputs"])
    summary = payload["readiness_summary"]
    assert summary["cache_write_approved"] is False
    assert summary["actual_import_approved"] is False
    assert summary["provider_live_access_approved"] is False
    assert payload["safety_summary"]["cache_directory_created"] is False
    assert payload["safety_summary"]["cache_write_executed"] is False


def test_v77c_actual_import_quarantine_matrix_blocks_import() -> None:
    payload = build_actual_import_quarantine_followthrough_matrix(report_date="2026-06-02")
    gates = {row["gate"]: row for row in payload["followthrough_matrix"]}
    assert gates["actual_import_approval_phrase"]["current_status"] == "not_issued"
    assert all(row["execution_allowed_now"] is False for row in payload["followthrough_matrix"])
    assert payload["readiness_verdict"]["actual_import_execution_allowed_now"] is False
    assert payload["safety_summary"]["actual_refresh_import_executed"] is False
    assert payload["safety_summary"]["raw_broker_export_parsed"] is False


def test_v77d_portfolio_strategy_report_uses_generic_guard_only() -> None:
    payload = build_portfolio_strategy_observation_report(report_date="2026-06-02", symbols_csv="6501.T,AAPL,NVDA")
    status = payload["portfolio_strategy_status"]
    assert status["observation_only"] is True
    assert status["uses_generic_position_guard"] is True
    assert status["dca_feature_deepening"] is False
    assert status["buy_sell_execution_recommendation_allowed"] is False
    rows = payload["generic_position_guard"]["rows"]
    assert {row["symbol"] for row in rows} == {"6501.T", "AAPL", "NVDA"}
    assert all(row["generic_guard"]["symbol_specific_logic_used"] is False for row in rows)
    assert payload["safety_summary"]["trading_action_executed"] is False


def test_v77e_handoff_summary_closes_dca_and_returns_to_main_line() -> None:
    payload = build_chatgpt_main_development_handoff_summary(report_date="2026-06-02")
    summary = payload["summary"]
    assert summary["v73_workflow_merged_next_run_observation_required"] is True
    assert summary["v76_dca_line_closed_generic_guard_only"] is True
    assert summary["cache_write_pilot_approved"] is False
    assert summary["actual_import_approved"] is False
    assert "Weekly report scheduled-run observation".lower() in payload["copy_ready_chatgpt_summary"].lower()
    assert payload["safety_summary"]["provider_live_access_executed"] is False


def test_markdown_writer_and_output_writer(tmp_path: Path) -> None:
    payload = build_chatgpt_main_development_handoff_summary(report_date="2026-06-02")
    markdown = format_return_to_main_pack_markdown(payload)
    assert "# Chatgpt Main Development Handoff Summary v77" in markdown
    assert "## Short Summary to Paste to ChatGPT" in markdown
    assert "provider_live_access_executed: false" in markdown
    paths = write_return_to_main_pack_outputs(
        out_dir=tmp_path / "out",
        report_date="2026-06-02",
        stem="chatgpt_main_development_handoff_summary",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_chatgpt_main_development_handoff_summary_md"].is_file()
    loaded = json.loads(paths["weekly_chatgpt_main_development_handoff_summary_json"].read_text(encoding="utf-8"))
    assert loaded["report_name"] == "chatgpt_main_development_handoff_summary"


def test_cli_commands_have_safe_contract_and_no_execution_options(tmp_path: Path) -> None:
    runner = CliRunner()
    commands = (
        "weekly-candidate-brief-scheduled-run-observation-pack",
        "cache-write-pilot-preexecution-readiness-snapshot",
        "actual-import-quarantine-followthrough-matrix",
        "portfolio-strategy-observation-report",
        "chatgpt-main-development-handoff-summary",
    )
    for command in commands:
        help_result = runner.invoke(app, [command, "--help"])
        assert help_result.exit_code == 0
        command_info = next(item for item in app.registered_commands if item.name == command)
        option_names = {
            option
            for parameter in inspect.signature(command_info.callback).parameters.values()
            for option in parameter.default.param_decls
        }
        assert {"--report-date", "--out-dir", "--format"}.issubset(option_names)
        assert "--execute" not in option_names
        assert "--dispatch" not in option_names
        assert "--trade" not in option_names
        assert "--broker" not in option_names

    result = runner.invoke(
        app,
        [
            "chatgpt-main-development-handoff-summary",
            "--report-date",
            "2026-06-02",
            "--out-dir",
            str(tmp_path / "cli"),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "chatgpt_main_development_handoff_summary"' in result.output
    assert "provider_live_access_executed=false" in result.stderr
    assert "cache_write_executed=false" in result.stderr
    assert "trading_action_executed=false" in result.stderr


def test_chatgpt_context_pack_includes_v77_status(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-06-02"
    _write_minimal_weekly_json(report_dir)
    pack = build_chatgpt_context_pack(report_date="2026-06-02", report_dir=report_dir)
    status = pack.json_payload["v77_return_to_main_development_status"]
    assert status["pack_exists"] is True
    assert status["cache_write_approved"] is False
    assert status["actual_import_approved"] is False
    assert status["portfolio_observation_only"] is True
    assert status["v76_dca_line_closed_generic_guard_only"] is True
    assert status["workflow_files_modified"] is False
    assert "- v77_return_to_main_development_pack_exists: true" in pack.markdown_text
