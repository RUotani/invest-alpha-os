from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.redacted_position_snapshot_input_pack import (
    build_redacted_position_human_input_checklist,
    build_redacted_position_snapshot_template,
    build_redacted_position_strategy_pack,
    detect_forbidden_fields,
    detect_forbidden_values,
    format_redacted_position_human_input_checklist_markdown,
    format_redacted_position_snapshot_template_markdown,
    format_redacted_position_snapshot_validation_markdown,
    format_redacted_position_strategy_pack_markdown,
    load_redacted_position_snapshot_json,
    validate_redacted_position_snapshot,
    write_redacted_position_outputs,
)


def _valid_snapshot() -> dict[str, object]:
    return {
        "report_date": "2026-06-01",
        "portfolio_snapshot_date": "2026-06-01",
        "currency": "JPY",
        "cash_buffer_status": "sufficient",
        "household_risk_budget_note": "redacted household allocation note",
        "positions": [
            {
                "symbol": "5411.T",
                "display_name": "JFE Holdings",
                "account_alias": "taxable_alias_1",
                "account_type": "taxable",
                "shares": 100,
                "average_cost": 2300,
                "manual_current_price": 1900,
                "market_value": 190000,
                "unrealized_pl": -40000,
                "unrealized_pl_pct": -17.3913,
                "portfolio_weight_pct": 2.4,
                "sector_tag": "steel",
                "thesis_status": "watch",
                "dca_intent": "review_only",
                "max_additional_buy_amount": 50000,
                "max_position_weight_pct": 5,
                "must_not_buy_if": ["thesis_status is broken", "cash buffer becomes insufficient"],
                "review_triggers": ["guidance changes", "dividend policy changes"],
                "operator_notes": "redacted note only",
            },
            {
                "symbol": "7267.T",
                "display_name": "Honda Motor",
                "account_alias": "taxable_alias_1",
                "account_type": "taxable",
                "shares": 100,
                "average_cost": 1700,
                "manual_current_price": 1500,
                "market_value": 150000,
                "unrealized_pl": -20000,
                "unrealized_pl_pct": -11.7647,
                "portfolio_weight_pct": 2.0,
                "sector_tag": "auto",
                "thesis_status": "watch",
                "dca_intent": "review_only",
                "max_additional_buy_amount": 50000,
                "max_position_weight_pct": 5,
                "must_not_buy_if": ["thesis_status is broken", "cash buffer becomes insufficient"],
                "review_triggers": ["EV losses worsen", "margin pressure worsens"],
                "operator_notes": "redacted note only",
            },
        ],
    }


def test_template_contains_jfe_honda_json_skeleton_and_safety() -> None:
    payload = build_redacted_position_snapshot_template(report_date="2026-06-01", symbols_csv="5411.T,7267.T")
    template = payload["redacted_snapshot_template"]
    assert template["cash_buffer_status"] == "unknown"
    assert [row["symbol"] for row in template["positions"]] == ["5411.T", "7267.T"]
    markdown = format_redacted_position_snapshot_template_markdown(payload)
    assert "Redacted Position Snapshot Template v75" in markdown
    assert "broker account numbers" in markdown
    assert "Copy-ready ChatGPT Prompt" in markdown
    assert "broker_api_access_executed: false" in markdown


def test_validator_passes_valid_redacted_snapshot() -> None:
    payload = validate_redacted_position_snapshot(_valid_snapshot())
    assert payload["validation_passed"] is True
    assert payload["chatgpt_paste_ready"] is True
    assert payload["forbidden_fields_detected"] == ()
    assert payload["dca_readiness_blockers"] == ()
    assert all(row["valid"] for row in payload["position_results"])


def test_validator_detects_missing_fields_and_numeric_mismatch() -> None:
    snapshot = _valid_snapshot()
    first = snapshot["positions"][0]
    assert isinstance(first, dict)
    first.pop("shares")
    second = snapshot["positions"][1]
    assert isinstance(second, dict)
    second["market_value"] = 123
    payload = validate_redacted_position_snapshot(snapshot)
    assert payload["validation_passed"] is False
    assert "shares" in payload["position_results"][0]["missing_fields"]
    failed_checks = [
        row
        for row in payload["position_results"][1]["numerical_consistency"]
        if row["check"] == "market_value_equals_shares_times_manual_current_price"
    ]
    assert failed_checks and failed_checks[0]["pass"] is False
    markdown = format_redacted_position_snapshot_validation_markdown(payload)
    assert "validation_passed: false" in markdown


def test_validator_detects_forbidden_fields_and_values() -> None:
    snapshot = _valid_snapshot()
    snapshot["broker_account_number"] = "123-456"
    first = snapshot["positions"][0]
    assert isinstance(first, dict)
    first["operator_notes"] = "please place order tomorrow"
    assert "broker_account_number" in detect_forbidden_fields(snapshot)
    assert "positions[0].operator_notes" in detect_forbidden_values(snapshot)
    payload = validate_redacted_position_snapshot(snapshot)
    assert payload["validation_passed"] is False
    assert "broker_account_number" in payload["forbidden_fields_detected"]
    assert "positions[0].operator_notes" in payload["forbidden_values_detected"]


def test_strategy_pack_integrates_valid_redacted_snapshot() -> None:
    payload = build_redacted_position_strategy_pack(report_date="2026-06-01", redacted_snapshot=_valid_snapshot())
    assert payload["validation"]["validation_passed"] is True
    rows = {row["symbol"]: row for row in payload["rows"]}
    assert rows["5411.T"]["placeholder_label"] == "wait_for_capitulation"
    assert rows["5411.T"]["redacted_position_label"] in {"monitor_only", "wait_for_capitulation"}
    assert rows["7267.T"]["placeholder_label"] == "monitor_only"
    markdown = format_redacted_position_strategy_pack_markdown(payload)
    assert "JFE/Honda Side-by-Side" in markdown
    assert "not a trading recommendation" in markdown
    assert "trading_action_executed: false" in markdown


def test_json_loader_accepts_only_redacted_json_object(tmp_path: Path) -> None:
    path = tmp_path / "redacted_snapshot.json"
    path.write_text(json.dumps(_valid_snapshot(), ensure_ascii=False), encoding="utf-8")
    loaded = load_redacted_position_snapshot_json(path)
    assert loaded["currency"] == "JPY"
    bad = tmp_path / "bad.json"
    bad.write_text("[]", encoding="utf-8")
    try:
        load_redacted_position_snapshot_json(bad)
    except ValueError as exc:
        assert "must be an object" in str(exc)
    else:
        raise AssertionError("expected object validation failure")


def test_output_writer_and_cli_commands(tmp_path: Path) -> None:
    payload = validate_redacted_position_snapshot(_valid_snapshot())
    markdown = format_redacted_position_snapshot_validation_markdown(payload)
    paths = write_redacted_position_outputs(
        out_dir=tmp_path / "out",
        report_date="2026-06-01",
        stem="redacted_position_snapshot_validation",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_redacted_position_snapshot_validation_md"].is_file()
    runner = CliRunner()
    for command in (
        "position-snapshot-template",
        "position-snapshot-validate",
        "position-aware-dca-strategy-pack",
        "position-snapshot-human-input-checklist",
    ):
        help_result = runner.invoke(app, [command, "--help"])
        assert help_result.exit_code == 0
        command_info = next(item for item in app.registered_commands if item.name == command)
        option_names = {
            option
            for parameter in inspect.signature(command_info.callback).parameters.values()
            for option in parameter.default.param_decls
        }
        assert {"--report-date", "--out-dir", "--format"}.issubset(option_names)
        assert "--broker" not in option_names
        assert "--trade" not in option_names

    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(json.dumps(_valid_snapshot(), ensure_ascii=False), encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "position-aware-dca-strategy-pack",
            "--snapshot-path",
            str(snapshot_path),
            "--report-date",
            "2026-06-01",
            "--out-dir",
            str(tmp_path / "cli"),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "redacted_position_strategy_pack"' in result.output
    assert "broker_api_access_executed=false" in result.stderr
    assert "raw_broker_export_parsed=false" in result.stderr
    assert "trading_action_executed=false" in result.stderr


def test_human_input_checklist_documents_safe_next_inputs() -> None:
    payload = build_redacted_position_human_input_checklist(report_date="2026-06-01", symbols_csv="5411.T,7267.T")
    assert payload["pack_version"] == "v75E"
    assert "shares" in payload["required_inputs"]
    assert "raw broker CSV/export rows" in payload["do_not_include"]
    markdown = format_redacted_position_human_input_checklist_markdown(payload)
    assert "Redacted Position Human Input Checklist v75E" in markdown
    assert "position-snapshot-template" in markdown
    assert "trading_action_executed: false" in markdown
