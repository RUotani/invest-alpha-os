from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.cache_path_preflight_approval_package import DEFAULT_CANDIDATE_CACHE_PATH
from invis_alpha_os.data.cache_write_pilot_approval_packet import (
    V70_FIRST_SUBSET,
    V70_PACKET_VERDICT,
    build_cache_write_pilot_approval_packet,
)
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_cache_write_pilot_approval_packet_report,
    build_provider_context_pack_block,
    write_cache_write_pilot_approval_packet_outputs,
)


def test_future_pilot_identity_is_tiingo_subset_and_candidate_path_only() -> None:
    packet = build_cache_write_pilot_approval_packet(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    ).to_dict()
    identity = packet["future_pilot_identity"]
    assert identity["provider"] == "Tiingo"
    assert identity["operation"] == "tiingo_private_local_cache_write_pilot"
    assert identity["first_subset"] == list(V70_FIRST_SUBSET)
    assert identity["candidate_cache_path"] == DEFAULT_CANDIDATE_CACHE_PATH
    assert "EOD OHLCV" in identity["data_type"]
    assert "private/local" in identity["storage"]


def test_packet_is_not_execution_or_approval() -> None:
    packet = build_cache_write_pilot_approval_packet(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    ).to_dict()
    verdict = packet["readiness_verdict"]
    phrase = packet["approval_phrase_boundary"]
    assert verdict["packet_verdict"] == V70_PACKET_VERDICT
    assert verdict["cache_write_approval_status"] == "not_approved"
    assert verdict["cache_write_execution_status"] == "not_executed"
    assert verdict["actual_import_approval_status"] == "not_approved"
    assert verdict["actual_import_execution_status"] == "not_executed"
    assert verdict["approval_phrase_issued"] is False
    assert phrase["this_package_approves_cache_write"] is False
    assert phrase["cache_write_approval_phrase"] == "cache writeを実行してよい"
    assert phrase["cache_write_approval_phrase_issued"] is False
    assert phrase["actual_import_approval_phrase"] == "actual refresh/importを実行してよい"
    assert phrase["actual_import_approval_phrase_issued"] is False
    assert phrase["cache_write_does_not_approve_actual_import"] is True
    assert phrase["cache_write_does_not_approve_trading"] is True


def test_forbidden_operations_and_output_constraints_cover_raw_locations() -> None:
    packet = build_cache_write_pilot_approval_packet(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    ).to_dict()
    forbidden = {row["description"] for row in packet["forbidden_operations"]}
    assert "raw OHLCV in Git" in forbidden
    assert "raw OHLCV in reports-private" in forbidden
    assert "raw OHLCV in GitHub artifacts" in forbidden
    assert "raw OHLCV pasted to ChatGPT/Cursor" in forbidden
    assert "raw OHLCV in public outputs" in forbidden
    assert "raw API response persistence" in forbidden
    assert "broker/manual raw data handling" in forbidden
    constraints = packet["output_constraints"]
    assert "redacted summary" in constraints["allowed_outputs"]
    assert "metadata" in constraints["allowed_outputs"]
    assert "raw OHLCV" in constraints["forbidden_outputs"]
    assert "raw API response" in constraints["forbidden_outputs"]
    assert constraints["reports_private_raw_data_allowed"] is False
    assert constraints["git_tracked_raw_data_allowed"] is False
    assert constraints["chatgpt_cursor_raw_paste_allowed"] is False


def test_required_preconditions_and_operator_fields_exist() -> None:
    packet = build_cache_write_pilot_approval_packet(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    ).to_dict()
    preconditions = {row["description"] for row in packet["required_preconditions"]}
    operator_fields = {row["description"] for row in packet["required_operator_fields"]}
    assert "SIGNOFF-16 completed by human" in preconditions
    assert "v69 cache path preflight accepted" in preconditions
    assert "v69B purge/inventory dry-run contract accepted" in preconditions
    assert "future runtime contains exact cache-write approval phrase" in preconditions
    assert "operator name or handle recorded" in operator_fields
    assert "symbol subset SPY, QQQ, AAPL, NVDA confirmed" in operator_fields
    assert all(row["blocks_execution_if_unmet"] is True for row in packet["required_preconditions"])


def test_safety_flags_remain_false_for_hard_gates() -> None:
    packet = build_cache_write_pilot_approval_packet(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    ).to_dict()
    safety = packet["safety_flags"]
    assert safety["source_only"] is True
    assert safety["tiingo_api_call_executed"] is False
    assert safety["provider_live_access_executed"] is False
    assert safety["live_http_executed"] is False
    assert safety["cache_write_executed"] is False
    assert safety["actual_refresh_import_executed"] is False
    assert safety["manual_actual_import_executed"] is False
    assert safety["raw_ohlcv_read"] is False
    assert safety["raw_ohlcv_persisted"] is False
    assert safety["raw_api_response_persisted"] is False
    assert safety["reports_private_raw_data_written"] is False
    assert safety["git_tracked_raw_data_written"] is False
    assert safety["env_secret_displayed"] is False
    assert safety["workflow_dependency_pyproject_changed"] is False
    assert safety["trading_action_executed"] is False


def test_report_and_payload_are_deterministic() -> None:
    markdown, payload = build_cache_write_pilot_approval_packet_report(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    )
    for heading in (
        "## Verdict",
        "## Future Pilot Identity",
        "## Required Preconditions",
        "## Required Operator Fields",
        "## Forbidden Operations",
        "## Execution Runbook",
        "## Output Constraints",
        "## Approval Phrase Boundary",
        "## What Is Still Not Approved",
    ):
        assert heading in markdown
    assert "approval_packet_ready_future_phrase_required" in markdown
    assert "cache_write_approval_status: not_approved" in markdown
    assert payload["pack_version"] == "v70"
    assert payload["cache_write_pilot_approval_packet"]["readiness_verdict"]["packet_verdict"] == V70_PACKET_VERDICT


def test_write_outputs(tmp_path: Path) -> None:
    markdown, payload = build_cache_write_pilot_approval_packet_report(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    )
    paths = write_cache_write_pilot_approval_packet_outputs(
        out_dir=tmp_path,
        report_date="2026-05-31",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_cache_write_pilot_approval_packet_md"].is_file()
    assert paths["latest_cache_write_pilot_approval_packet_json"].is_file()
    assert paths["weekly_cache_write_pilot_approval_packet_md"].is_file()
    assert paths["weekly_cache_write_pilot_approval_packet_json"].is_file()


def test_cli_help_exposes_safe_options_only() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["weekly-candidate-brief-cache-write-pilot-approval-packet", "--help"])
    assert result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-cache-write-pilot-approval-packet"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-date", "--candidate-cache-path", "--out-dir", "--format"}.issubset(option_names)
    assert "--live" not in option_names
    assert "--fetch" not in option_names
    assert "--execute" not in option_names
    assert "--write-cache" not in option_names
    assert "--import" not in option_names
    assert "--secret" not in option_names


def test_cli_generation_markdown_and_json_are_source_only(tmp_path: Path) -> None:
    runner = CliRunner()
    md_result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-cache-write-pilot-approval-packet",
            "--report-date",
            "2026-05-31",
            "--candidate-cache-path",
            DEFAULT_CANDIDATE_CACHE_PATH,
            "--out-dir",
            str(tmp_path),
            "--format",
            "markdown",
        ],
    )
    assert md_result.exit_code == 0
    assert "# v70 Cache-Write Pilot Execution Runbook" in md_result.output
    assert "source_only=true" in md_result.stderr
    assert "cache_write_executed=false" in md_result.stderr
    json_result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-cache-write-pilot-approval-packet",
            "--report-date",
            "2026-05-31",
            "--candidate-cache-path",
            DEFAULT_CANDIDATE_CACHE_PATH,
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    assert json_result.exit_code == 0
    assert '"report_name": "cache_write_pilot_approval_packet"' in json_result.output
    assert '"packet_verdict": "approval_packet_ready_future_phrase_required"' in json_result.output
    assert (tmp_path / "latest" / "cache_write_pilot_approval_packet.md").is_file()
    assert (tmp_path / "latest" / "cache_write_pilot_approval_packet.json").is_file()


def test_context_pack_includes_v70_status() -> None:
    block = build_provider_context_pack_block(report_date="2026-05-31")
    status = block["cache_write_pilot_approval_packet_status"]
    assert status["packet_exists"] is True
    assert status["source_only"] is True
    assert status["packet_verdict"] == V70_PACKET_VERDICT
    assert status["provider"] == "Tiingo"
    assert status["first_subset"] == list(V70_FIRST_SUBSET)
    assert status["candidate_cache_path"] == DEFAULT_CANDIDATE_CACHE_PATH
    assert status["cache_write_approval_status"] == "not_approved"
    assert status["actual_import_approval_status"] == "not_approved"
    assert status["approval_phrase_issued"] is False
    assert status["raw_ohlcv_persisted"] is False


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


def test_chatgpt_context_pack_includes_v70_summary(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-05-31"
    _write_minimal_weekly_json(report_dir)
    pack = build_chatgpt_context_pack(report_date="2026-05-31", report_dir=report_dir)
    status = pack.json_payload["cache_write_pilot_approval_packet_status"]
    assert status["packet_verdict"] == V70_PACKET_VERDICT
    assert "- cache_write_pilot_approval_packet_exists: true" in pack.markdown_text
    assert "- cache_write_pilot_cache_write_approval_status: not_approved" in pack.markdown_text
