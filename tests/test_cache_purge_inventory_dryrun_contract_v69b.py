from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.cache_path_preflight_approval_package import DEFAULT_CANDIDATE_CACHE_PATH
from invis_alpha_os.data.cache_purge_inventory_dryrun_contract import (
    V69B_VERDICT,
    build_cache_purge_inventory_dryrun_contract,
)
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_cache_purge_inventory_dryrun_contract_report,
    build_provider_context_pack_block,
    write_cache_purge_inventory_dryrun_contract_outputs,
)


def test_contract_is_source_only_and_execution_not_approved() -> None:
    contract = build_cache_purge_inventory_dryrun_contract(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    ).to_dict()
    verdict = contract["readiness_verdict"]
    assert verdict["contract_verdict"] == V69B_VERDICT
    assert verdict["cache_write_approval_status"] == "not_approved"
    assert verdict["cache_write_execution_status"] == "not_executed"
    assert verdict["actual_import_approval_status"] == "not_approved"
    assert verdict["actual_import_execution_status"] == "not_executed"
    assert verdict["purge_execution_status"] == "not_executed"
    assert verdict["destructive_purge_approval_status"] == "not_approved"
    assert verdict["redacted_manifest_schema_status"] == "metadata_only_no_raw_rows"


def test_dryrun_semantics_do_not_read_delete_write_or_import() -> None:
    contract = build_cache_purge_inventory_dryrun_contract(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    ).to_dict()
    semantics = contract["dryrun_semantics"]
    assert semantics["no_file_deletion_executed"] is True
    assert semantics["no_raw_ohlcv_read"] is True
    assert semantics["no_provider_api_call"] is True
    assert semantics["no_cache_write"] is True
    assert semantics["no_actual_import"] is True
    assert semantics["candidate_cache_path_remains_candidate_only"] is True
    assert semantics["destructive_purge_requires_future_explicit_approval"] is True
    assert semantics["redacted_manifest_metadata_only"] is True


def test_redacted_manifest_allowed_fields_are_metadata_only() -> None:
    contract = build_cache_purge_inventory_dryrun_contract(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    ).to_dict()
    allowed = {row["field_name"] for row in contract["redacted_manifest_allowed_fields"]}
    assert "provider_name" in allowed
    assert "asset_scope_label" in allowed
    assert "symbol_count" in allowed
    assert "file_count" in allowed
    assert "date_range_label" in allowed
    assert "schema_version" in allowed
    assert "created_at_label" in allowed
    assert "hash_presence_boolean" in allowed
    assert "raw_rows_count_optional_aggregate" in allowed
    assert "no_raw_rows_embedded_boolean" in allowed
    assert all(row["allowed"] is True for row in contract["redacted_manifest_allowed_fields"])


def test_raw_ohlcv_and_secret_manifest_fields_are_forbidden() -> None:
    contract = build_cache_purge_inventory_dryrun_contract(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    ).to_dict()
    forbidden = {row["field_name"] for row in contract["redacted_manifest_forbidden_fields"]}
    assert {"open", "high", "low", "close", "adj_close", "volume"}.issubset(forbidden)
    assert "raw_api_response" in forbidden
    assert "per_row_ohlcv_data" in forbidden
    assert "secret_values" in forbidden
    assert "broker_manual_raw_data" in forbidden
    assert all(row["allowed"] is False for row in contract["redacted_manifest_forbidden_fields"])


def test_file_classification_and_purge_steps_are_contract_only() -> None:
    contract = build_cache_purge_inventory_dryrun_contract(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    ).to_dict()
    assert all(row["raw_read_allowed"] is False for row in contract["cache_file_classification"])
    assert all(row["delete_allowed"] is False for row in contract["cache_file_classification"])
    for section in (
        "purge_target_selection_semantics",
        "orphan_raw_file_check_semantics",
        "post_purge_verification_checklist",
        "rollback_checklist",
    ):
        assert contract[section]
        assert all(row["execution_mode"] == "contract_only_not_executed" for row in contract[section])
        assert all(row["destructive_action_allowed"] is False for row in contract[section])
        assert all(row["raw_ohlcv_read_allowed"] is False for row in contract[section])


def test_safety_flags_remain_false_for_hard_gates() -> None:
    contract = build_cache_purge_inventory_dryrun_contract(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    ).to_dict()
    safety = contract["safety_flags"]
    assert safety["source_only"] is True
    assert safety["live_http_executed"] is False
    assert safety["tiingo_api_call_executed"] is False
    assert safety["provider_live_access_executed"] is False
    assert safety["cache_write_executed"] is False
    assert safety["actual_refresh_import_executed"] is False
    assert safety["manual_actual_import_executed"] is False
    assert safety["raw_ohlcv_read"] is False
    assert safety["raw_ohlcv_persisted"] is False
    assert safety["raw_api_response_persisted"] is False
    assert safety["reports_private_raw_data_written"] is False
    assert safety["git_tracked_raw_data_written"] is False
    assert safety["filesystem_scan_executed"] is False
    assert safety["file_deletion_executed"] is False
    assert safety["env_secret_displayed"] is False
    assert safety["workflow_dependency_pyproject_changed"] is False
    assert safety["trading_action_executed"] is False


def test_markdown_report_and_json_payload_contain_required_sections() -> None:
    markdown, payload = build_cache_purge_inventory_dryrun_contract_report(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    )
    for heading in (
        "## Verdict",
        "## Candidate Cache Path",
        "## Dry-Run Semantics",
        "## Allowed Redacted Manifest Fields",
        "## Forbidden Manifest Fields",
        "## Cache File Classification Contract",
        "## Purge Target Selection Semantics",
        "## Orphan Raw File Check Semantics",
        "## Post-Purge Verification Checklist",
        "## Rollback Checklist",
        "## What Is Still Not Approved",
        "## Next Source-Only Handoff",
    ):
        assert heading in markdown
    assert "purge_inventory_dryrun_contract_ready_execution_not_approved" in markdown
    assert "no_file_deletion_executed: true" in markdown
    assert payload["pack_version"] == "v69B"


def test_write_outputs(tmp_path: Path) -> None:
    markdown, payload = build_cache_purge_inventory_dryrun_contract_report(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    )
    paths = write_cache_purge_inventory_dryrun_contract_outputs(
        out_dir=tmp_path,
        report_date="2026-05-31",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_cache_purge_inventory_dryrun_contract_md"].is_file()
    assert paths["latest_cache_purge_inventory_dryrun_contract_json"].is_file()
    assert paths["weekly_cache_purge_inventory_dryrun_contract_md"].is_file()
    assert paths["weekly_cache_purge_inventory_dryrun_contract_json"].is_file()


def test_cli_help_exposes_safe_options_only() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["weekly-candidate-brief-cache-purge-inventory-dryrun-contract", "--help"])
    assert result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-cache-purge-inventory-dryrun-contract"
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
    assert "--delete" not in option_names
    assert "--import" not in option_names
    assert "--secret" not in option_names


def test_cli_generation_markdown_and_json_are_source_only(tmp_path: Path) -> None:
    runner = CliRunner()
    md_result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-cache-purge-inventory-dryrun-contract",
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
    assert "# v69B Cache Purge / Inventory Dry-Run Contract" in md_result.output
    assert "source_only=true" in md_result.stderr
    assert "file_deletion_executed=false" in md_result.stderr
    assert "raw_ohlcv_read=false" in md_result.stderr
    json_result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-cache-purge-inventory-dryrun-contract",
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
    assert '"report_name": "cache_purge_inventory_dryrun_contract"' in json_result.output
    assert '"contract_verdict": "purge_inventory_dryrun_contract_ready_execution_not_approved"' in json_result.output
    assert (tmp_path / "latest" / "cache_purge_inventory_dryrun_contract.md").is_file()
    assert (tmp_path / "latest" / "cache_purge_inventory_dryrun_contract.json").is_file()


def test_context_pack_includes_v69b_contract_status() -> None:
    block = build_provider_context_pack_block(report_date="2026-05-31")
    status = block["cache_purge_inventory_dryrun_contract_status"]
    assert status["contract_exists"] is True
    assert status["source_only"] is True
    assert status["contract_verdict"] == V69B_VERDICT
    assert status["candidate_cache_path"] == DEFAULT_CANDIDATE_CACHE_PATH
    assert status["redacted_manifest_schema_status"] == "metadata_only_no_raw_rows"
    assert status["purge_execution_status"] == "not_executed"
    assert status["cache_write_approval_status"] == "not_approved"
    assert status["actual_import_approval_status"] == "not_approved"
    assert status["file_deletion_executed"] is False
    assert status["raw_ohlcv_read"] is False


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


def test_chatgpt_context_pack_includes_v69b_summary(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-05-31"
    _write_minimal_weekly_json(report_dir)
    pack = build_chatgpt_context_pack(report_date="2026-05-31", report_dir=report_dir)
    status = pack.json_payload["cache_purge_inventory_dryrun_contract_status"]
    assert status["contract_verdict"] == V69B_VERDICT
    assert status["file_deletion_executed"] is False
    assert "- cache_purge_inventory_dryrun_contract_exists: true" in pack.markdown_text
    assert "- cache_purge_inventory_file_deletion_executed: false" in pack.markdown_text
