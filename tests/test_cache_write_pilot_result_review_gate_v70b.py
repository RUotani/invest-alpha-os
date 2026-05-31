from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.cache_path_preflight_approval_package import DEFAULT_CANDIDATE_CACHE_PATH
from invis_alpha_os.data.cache_write_pilot_result_review_gate import (
    V70B_ALLOWED_VERDICTS,
    V70B_CURRENT_VERDICT,
    build_cache_write_pilot_result_review_gate,
)
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_cache_write_pilot_result_review_gate_report,
    build_provider_context_pack_block,
    write_cache_write_pilot_result_review_gate_outputs,
)


def test_current_state_is_not_run_and_actual_import_not_ready() -> None:
    gate = build_cache_write_pilot_result_review_gate(report_date="2026-05-31").to_dict()
    verdict = gate["readiness_verdict"]
    assert gate["review_status"] == "source_only_result_review_gate_ready_pilot_not_run"
    assert verdict["result_review_verdict"] == V70B_CURRENT_VERDICT
    assert verdict["pilot_has_run"] is False
    assert verdict["cache_write_pilot_review_ready"] is True
    assert verdict["actual_import_readiness"] == "not_ready_result_review_not_run_and_separate_approval_required"
    assert verdict["trading_readiness"] == "not_approved"
    assert verdict["raw_ohlcv_fields_emitted"] is False


def test_allowed_and_forbidden_result_fields_are_metadata_only() -> None:
    gate = build_cache_write_pilot_result_review_gate(report_date="2026-05-31").to_dict()
    allowed = set(gate["allowed_result_fields"])
    forbidden = set(gate["forbidden_result_fields"])
    assert "row_count_aggregate" in allowed
    assert "field_presence_booleans" in allowed
    assert "redacted_manifest_status" in allowed
    assert "raw_leakage_status" in allowed
    assert {"open", "high", "low", "close", "adj_close", "volume"}.issubset(forbidden)
    assert "raw_api_response" in forbidden
    assert "per_row_ohlcv_data" in forbidden
    assert "secret_values" in forbidden
    assert "broker_manual_raw_data" in forbidden


def test_acceptance_criteria_do_not_allow_raw_values() -> None:
    gate = build_cache_write_pilot_result_review_gate(report_date="2026-05-31").to_dict()
    descriptions = {row["description"] for row in gate["acceptance_criteria"]}
    assert "symbol coverage summary" in descriptions
    assert "row count summary" in descriptions
    assert "base/adjusted field presence summary" in descriptions
    assert "raw leakage check" in descriptions
    assert "cache path policy check" in descriptions
    assert all(row["raw_values_allowed"] is False for row in gate["acceptance_criteria"])


def test_verdict_policy_blocks_import_and_trading_inference() -> None:
    gate = build_cache_write_pilot_result_review_gate(report_date="2026-05-31").to_dict()
    policy = gate["verdict_policy"]
    assert set(policy["allowed_verdicts"]) == set(V70B_ALLOWED_VERDICTS)
    assert policy["current_verdict"] == "not_run"
    assert policy["pass_requires_no_raw_leakage"] is True
    assert policy["pass_requires_cache_path_policy_pass"] is True
    assert policy["pass_requires_redacted_manifest"] is True
    assert policy["pass_requires_purge_contract"] is True
    assert policy["pass_does_not_approve_actual_import"] is True
    assert policy["pass_does_not_approve_trading"] is True


def test_safety_flags_remain_false_for_hard_gates() -> None:
    gate = build_cache_write_pilot_result_review_gate(report_date="2026-05-31").to_dict()
    safety = gate["safety_flags"]
    assert safety["source_only"] is True
    assert safety["provider_live_access_executed"] is False
    assert safety["live_http_executed"] is False
    assert safety["tiingo_api_call_executed"] is False
    assert safety["cache_write_executed"] is False
    assert safety["actual_refresh_import_executed"] is False
    assert safety["manual_actual_import_executed"] is False
    assert safety["raw_ohlcv_emitted"] is False
    assert safety["raw_ohlcv_persisted"] is False
    assert safety["raw_api_response_persisted"] is False
    assert safety["reports_private_raw_data_written"] is False
    assert safety["git_tracked_raw_data_written"] is False
    assert safety["env_secret_displayed"] is False
    assert safety["trading_action_executed"] is False


def test_report_and_write_outputs(tmp_path: Path) -> None:
    markdown, payload = build_cache_write_pilot_result_review_gate_report(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    )
    assert "## Acceptance Criteria" in markdown
    assert "## Allowed Result Fields" in markdown
    assert "## Forbidden Result Fields" in markdown
    assert "result_review_verdict: not_run" in markdown
    assert payload["pack_version"] == "v70B"
    paths = write_cache_write_pilot_result_review_gate_outputs(
        out_dir=tmp_path,
        report_date="2026-05-31",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_cache_write_pilot_result_review_gate_md"].is_file()
    assert paths["weekly_cache_write_pilot_result_review_gate_json"].is_file()


def test_cli_and_context_pack_include_v70b(tmp_path: Path) -> None:
    runner = CliRunner()
    help_result = runner.invoke(app, ["weekly-candidate-brief-cache-write-pilot-result-review-gate", "--help"])
    assert help_result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-cache-write-pilot-result-review-gate"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-date", "--candidate-cache-path", "--out-dir", "--format"}.issubset(option_names)
    assert "--execute" not in option_names
    assert "--write-cache" not in option_names
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-cache-write-pilot-result-review-gate",
            "--report-date",
            "2026-05-31",
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "cache_write_pilot_result_review_gate"' in result.output
    assert "pilot_has_run=false" in result.stderr
    block = build_provider_context_pack_block(report_date="2026-05-31")
    status = block["cache_write_pilot_result_review_gate_status"]
    assert status["gate_exists"] is True
    assert status["current_verdict"] == "not_run"
    assert status["actual_import_readiness"].startswith("not_ready")
    assert status["raw_ohlcv_emitted"] is False


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


def test_chatgpt_context_pack_includes_v70b_summary(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-05-31"
    _write_minimal_weekly_json(report_dir)
    pack = build_chatgpt_context_pack(report_date="2026-05-31", report_dir=report_dir)
    status = pack.json_payload["cache_write_pilot_result_review_gate_status"]
    assert status["current_verdict"] == "not_run"
    assert "- cache_write_pilot_result_review_gate_exists: true" in pack.markdown_text
    assert "- cache_write_pilot_result_review_raw_ohlcv_emitted: false" in pack.markdown_text
