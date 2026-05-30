from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.cache_write_operator_signoff_sheet import (
    V68_OPERATOR_SIGNOFF_STATUS,
    V68_OVERALL_READINESS,
    build_cache_write_operator_signoff_sheet,
)
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_cache_write_operator_signoff_sheet_report,
    build_provider_context_pack_block,
    write_cache_write_operator_signoff_sheet_outputs,
)


def test_default_status_is_human_review_required_and_not_approved() -> None:
    sheet = build_cache_write_operator_signoff_sheet(report_date="2026-05-30").to_dict()
    verdict = sheet["readiness_verdict"]
    assert sheet["sheet_status"] == V68_OPERATOR_SIGNOFF_STATUS
    assert verdict["operator_signoff_status"] == "human_review_required"
    assert verdict["cache_write_approval_status"] == "not_approved"
    assert verdict["cache_write_execution_status"] == "not_executed"
    assert verdict["actual_import_approval_status"] == "not_approved"
    assert verdict["actual_import_execution_status"] == "not_executed"
    assert verdict["overall_readiness"] == V68_OVERALL_READINESS
    assert sheet["readiness_phase"]["draft_only"] is True
    assert sheet["readiness_phase"]["ready_for_human_signoff"] is True
    assert sheet["readiness_phase"]["approved_by_human_phrase_present"] is False
    assert sheet["readiness_phase"]["execution_still_not_performed"] is True


def test_cache_path_unset_prevents_readiness() -> None:
    sheet = build_cache_write_operator_signoff_sheet(report_date="2026-05-30").to_dict()
    location = sheet["cache_location_checklist"]
    assert location["cache_path_proposed"] == "UNSET"
    assert location["cache_path_is_git_ignored"] == "unverified"
    assert location["cache_path_is_outside_source_git"] == "unverified"
    assert location["cache_path_is_outside_reports_private"] == "unverified"
    assert location["cache_path_is_local_or_private"] == "unverified"
    assert location["cache_path_unset_blocks_readiness"] is True
    assert sheet["readiness_verdict"]["cache_path_unset_blocks_readiness"] is True


def test_forbidden_locations_are_explicitly_listed() -> None:
    sheet = build_cache_write_operator_signoff_sheet(report_date="2026-05-30").to_dict()
    labels = {row["label"] for row in sheet["forbidden_raw_data_locations"]}
    assert "source Git: forbidden for raw OHLCV" in labels
    assert "reports-private: forbidden for raw OHLCV" in labels
    assert "GitHub artifacts: forbidden for raw OHLCV" in labels
    assert "ChatGPT pasted content: forbidden for raw OHLCV" in labels
    assert "Cursor pasted content: forbidden for raw OHLCV" in labels
    assert "public outputs: forbidden for raw OHLCV" in labels
    assert "broker/manual raw mix: forbidden" in labels
    assert all(row["current_status"] == "unreviewed" for row in sheet["forbidden_raw_data_locations"])


def test_approval_phrase_is_placeholder_and_false_by_default() -> None:
    sheet = build_cache_write_operator_signoff_sheet(report_date="2026-05-30").to_dict()
    phrase = sheet["approval_phrase_boundary"]
    assert phrase["cache_write_approval_phrase_required"] is True
    assert phrase["cache_write_approval_phrase"] == "cache writeを実行してよい"
    assert phrase["cache_write_approval_phrase_issued"] is False
    assert phrase["actual_import_approval_phrase_required"] is True
    assert phrase["actual_import_approval_phrase"] == "actual refresh/importを実行してよい"
    assert phrase["actual_import_approval_phrase_issued"] is False
    assert phrase["placeholder_phrase_is_not_runtime_approval"] is True


def test_actual_import_and_execution_boundaries_remain_blocked() -> None:
    sheet = build_cache_write_operator_signoff_sheet(report_date="2026-05-30").to_dict()
    boundary = sheet["execution_boundary"]
    assert boundary["cache_write_approval_status"] == "not_approved"
    assert boundary["cache_write_execution_status"] == "not_executed"
    assert boundary["actual_import_approval_status"] == "not_approved"
    assert boundary["actual_import_execution_status"] == "not_executed"
    assert boundary["trading_action_status"] == "not_approved_not_executed"
    assert boundary["raw_ohlcv_persistence_status"] == "not_approved_not_executed"
    assert boundary["provider_live_access_status"] == "not_approved_not_executed"


def test_retention_purge_and_data_quality_checklists_exist() -> None:
    sheet = build_cache_write_operator_signoff_sheet(report_date="2026-05-30").to_dict()
    retention = {row["label"] for row in sheet["retention_inventory_checklist"]}
    purge = {row["label"] for row in sheet["purge_rollback_checklist"]}
    data_quality = {row["label"] for row in sheet["data_quality_preconditions"]}
    assert "retention_policy is explicit" in retention
    assert "raw_inventory_required is accepted" in retention
    assert "redacted_metadata_index_allowed only without raw values" in retention
    assert "purge_command_or_manual_steps_required" in purge
    assert "purge_dry_run_required" in purge
    assert "rollback_checklist_required" in purge
    assert "provider_terms_reviewed" in data_quality
    assert "provider_rate_limit_reviewed" in data_quality
    assert "cross_provider_validation_reviewed" in data_quality
    assert "Stooq_adjustment_policy_reviewed" in data_quality


def test_report_contains_mandatory_sections_and_json_fields() -> None:
    markdown, payload = build_cache_write_operator_signoff_sheet_report(report_date="2026-05-30")
    for heading in (
        "## Verdict",
        "## Operator Review Fields",
        "## Proposed Future Operation",
        "## Cache Location Checklist",
        "## Forbidden Raw Data Locations",
        "## Retention / Inventory Checklist",
        "## Purge / Rollback Checklist",
        "## Data Quality Preconditions",
        "## Approval Phrase Boundary",
        "## Execution Boundary",
        "## What Is Still Not Approved",
        "## Next Human Actions",
        "## Next Cursor Handoff Draft",
    ):
        assert heading in markdown
    assert "operator_signoff_status: human_review_required" in markdown
    assert "cache_write_approval_status: not_approved" in markdown
    assert "raw OHLCV persistence" in markdown
    assert payload["pack_version"] == "v68"
    data = payload["cache_write_operator_signoff_sheet"]
    assert data["operator_review"]["signoff_id"] == "SIGNOFF-16-2026-05-30"
    assert data["proposed_future_operation"]["symbols"] == ["SPY", "QQQ", "AAPL", "NVDA"]
    assert data["safety_flags"]["source_only"] is True


def test_write_outputs(tmp_path: Path) -> None:
    markdown, payload = build_cache_write_operator_signoff_sheet_report(report_date="2026-05-30")
    paths = write_cache_write_operator_signoff_sheet_outputs(
        out_dir=tmp_path,
        report_date="2026-05-30",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_cache_write_operator_signoff_sheet_md"].is_file()
    assert paths["latest_cache_write_operator_signoff_sheet_json"].is_file()
    assert paths["weekly_cache_write_operator_signoff_sheet_md"].is_file()
    assert paths["weekly_cache_write_operator_signoff_sheet_json"].is_file()


def test_cli_help_exposes_only_safe_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["weekly-candidate-brief-cache-write-operator-signoff-sheet", "--help"])
    assert result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-cache-write-operator-signoff-sheet"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-date", "--out-dir", "--format"}.issubset(option_names)
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
            "weekly-candidate-brief-cache-write-operator-signoff-sheet",
            "--report-date",
            "2026-05-30",
            "--out-dir",
            str(tmp_path),
            "--format",
            "markdown",
        ],
    )
    assert md_result.exit_code == 0
    assert "# v68 Cache-Write Operator Signoff Sheet" in md_result.output
    assert "source_only=true" in md_result.stderr
    assert "cache_write_executed=false" in md_result.stderr
    assert "actual_refresh_import_executed=false" in md_result.stderr
    assert "raw_ohlcv_persisted=false" in md_result.stderr

    json_result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-cache-write-operator-signoff-sheet",
            "--report-date",
            "2026-05-30",
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    assert json_result.exit_code == 0
    assert '"report_name": "cache_write_operator_signoff_sheet"' in json_result.output
    assert '"operator_signoff_status": "human_review_required"' in json_result.output
    assert (tmp_path / "latest" / "cache_write_operator_signoff_sheet.md").is_file()
    assert (tmp_path / "latest" / "cache_write_operator_signoff_sheet.json").is_file()


def test_context_pack_includes_v68_operator_signoff_sheet() -> None:
    block = build_provider_context_pack_block(report_date="2026-05-30")
    status = block["cache_write_operator_signoff_sheet_status"]
    assert status["sheet_exists"] is True
    assert status["source_only"] is True
    assert status["operator_signoff_status"] == "human_review_required"
    assert status["overall_readiness"] == V68_OVERALL_READINESS
    assert status["cache_write_approval_status"] == "not_approved"
    assert status["actual_import_approval_status"] == "not_approved"
    assert status["cache_path_proposed"] == "UNSET"
    assert status["cache_path_unset_blocks_readiness"] is True
    assert status["approval_phrase_issued"] is False


def _write_minimal_weekly_json(report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "sections": {
            "top_picks": [
                {
                    "ticker": "AAPL",
                    "name": "Apple",
                    "asset_class": "us_stock",
                    "score_total": 90,
                    "score": 90,
                }
            ],
            "avoid": [],
            "insufficient": [],
        }
    }
    (report_dir / "weekly_candidate_brief_v0_1.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_chatgpt_context_pack_includes_v68_summary(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-05-30"
    _write_minimal_weekly_json(report_dir)
    pack = build_chatgpt_context_pack(report_date="2026-05-30", report_dir=report_dir)
    status = pack.json_payload["cache_write_operator_signoff_sheet_status"]
    assert status["operator_signoff_status"] == "human_review_required"
    assert status["overall_readiness"] == V68_OVERALL_READINESS
    assert "- cache_write_operator_signoff_sheet_exists: true" in pack.markdown_text
    assert "- cache_write_operator_cache_write_approval_status: not_approved" in pack.markdown_text
