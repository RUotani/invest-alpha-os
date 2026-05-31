from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.actual_import_readiness_boundary import (
    V70C_ACTUAL_IMPORT_READINESS,
    build_actual_import_readiness_boundary,
)
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_actual_import_readiness_boundary_report,
    build_provider_context_pack_block,
    write_actual_import_readiness_boundary_outputs,
)


def test_actual_import_remains_not_ready() -> None:
    boundary = build_actual_import_readiness_boundary(report_date="2026-05-31").to_dict()
    verdict = boundary["readiness_verdict"]
    assert boundary["boundary_status"] == "source_only_actual_import_boundary_ready_import_not_approved"
    assert verdict["cache_write_pilot_readiness"] == "future_approval_required"
    assert verdict["cache_write_pilot_result_review_readiness"] == "not_run"
    assert verdict["actual_import_readiness"] == V70C_ACTUAL_IMPORT_READINESS
    assert verdict["actual_import_execution_allowed_now"] is False
    assert verdict["manual_actual_import_execution_allowed_now"] is False


def test_cache_write_approval_does_not_imply_actual_import() -> None:
    boundary = build_actual_import_readiness_boundary(report_date="2026-05-31").to_dict()
    phrase = boundary["approval_phrase_boundary"]
    assert phrase["cache_write_approval_phrase"] == "cache writeを実行してよい"
    assert phrase["cache_write_approval_phrase_issued"] is False
    assert phrase["cache_write_approval_does_not_imply_actual_import"] is True
    assert phrase["actual_import_approval_phrase"] == "actual refresh/importを実行してよい"
    assert phrase["actual_import_approval_phrase_required_separately"] is True
    assert phrase["actual_import_approval_phrase_issued"] is False


def test_result_review_pass_required_but_not_sufficient() -> None:
    boundary = build_actual_import_readiness_boundary(report_date="2026-05-31").to_dict()
    phrase = boundary["approval_phrase_boundary"]
    prereq_notes = {row["notes"] for row in boundary["actual_import_prerequisites"]}
    assert phrase["result_review_pass_required_for_actual_import_discussion"] is True
    assert phrase["result_review_pass_not_sufficient_for_actual_import"] is True
    assert "cache-write pilot result review gate passed or explicitly reviewed" in prereq_notes
    assert "actual import approval package created separately" in prereq_notes
    assert "explicit future actual import approval phrase issued separately" in prereq_notes


def test_trading_action_remains_forbidden_and_quarantined() -> None:
    boundary = build_actual_import_readiness_boundary(report_date="2026-05-31").to_dict()
    quarantine = boundary["quarantine_boundary"]
    verdict = boundary["readiness_verdict"]
    assert quarantine["pilot_cache_is_quarantined_from_actual_import"] is True
    assert quarantine["automatic_promotion_from_cache_to_actual_import_allowed"] is False
    assert quarantine["trading_action_separate_and_not_approved"] is True
    assert verdict["trading_readiness"] == "not_approved"
    assert verdict["trading_action_allowed_now"] is False


def test_safety_flags_remain_false_for_hard_gates() -> None:
    boundary = build_actual_import_readiness_boundary(report_date="2026-05-31").to_dict()
    safety = boundary["safety_flags"]
    assert safety["source_only"] is True
    assert safety["provider_live_access_executed"] is False
    assert safety["live_http_executed"] is False
    assert safety["tiingo_api_call_executed"] is False
    assert safety["cache_write_executed"] is False
    assert safety["actual_refresh_import_executed"] is False
    assert safety["manual_actual_import_executed"] is False
    assert safety["raw_ohlcv_persisted"] is False
    assert safety["raw_api_response_persisted"] is False
    assert safety["reports_private_raw_data_written"] is False
    assert safety["git_tracked_raw_data_written"] is False
    assert safety["env_secret_displayed"] is False
    assert safety["trading_action_executed"] is False


def test_report_and_write_outputs(tmp_path: Path) -> None:
    markdown, payload = build_actual_import_readiness_boundary_report(
        report_date="2026-05-31",
        candidate_cache_path="$HOME/.local/share/invest-alpha-os/private-cache/tiingo-ohlcv",
    )
    assert "## Readiness Matrix" in markdown
    assert "## Actual Import Prerequisites" in markdown
    assert "actual_import_readiness: not_ready_separate_actual_import_approval_required" in markdown
    assert payload["pack_version"] == "v70C"
    paths = write_actual_import_readiness_boundary_outputs(
        out_dir=tmp_path,
        report_date="2026-05-31",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_actual_import_readiness_boundary_md"].is_file()
    assert paths["weekly_actual_import_readiness_boundary_json"].is_file()


def test_cli_and_context_pack_include_v70c(tmp_path: Path) -> None:
    runner = CliRunner()
    help_result = runner.invoke(app, ["weekly-candidate-brief-actual-import-readiness-boundary", "--help"])
    assert help_result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-actual-import-readiness-boundary"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-date", "--candidate-cache-path", "--out-dir", "--format"}.issubset(option_names)
    assert "--execute" not in option_names
    assert "--actual-import" not in option_names
    assert "--trade" not in option_names
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-actual-import-readiness-boundary",
            "--report-date",
            "2026-05-31",
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "actual_import_readiness_boundary"' in result.output
    assert "actual_refresh_import_executed=false" in result.stderr
    block = build_provider_context_pack_block(report_date="2026-05-31")
    status = block["actual_import_readiness_boundary_status"]
    assert status["boundary_exists"] is True
    assert status["actual_import_readiness"] == V70C_ACTUAL_IMPORT_READINESS
    assert status["actual_import_execution_allowed_now"] is False
    assert status["trading_readiness"] == "not_approved"


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


def test_chatgpt_context_pack_includes_v70c_summary(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-05-31"
    _write_minimal_weekly_json(report_dir)
    pack = build_chatgpt_context_pack(report_date="2026-05-31", report_dir=report_dir)
    status = pack.json_payload["actual_import_readiness_boundary_status"]
    assert status["actual_import_readiness"] == V70C_ACTUAL_IMPORT_READINESS
    assert "- actual_import_readiness_boundary_exists: true" in pack.markdown_text
    assert "- actual_import_boundary_execution_allowed_now: false" in pack.markdown_text
