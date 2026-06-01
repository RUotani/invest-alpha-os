from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.position_aware_dca_decision_pack import (
    THESIS_BROKEN,
    THESIS_INTACT,
    build_dca_decision_matrix,
    build_position_aware_dca_decision_pack,
    fixture_position_snapshots,
    format_position_aware_dca_decision_pack_markdown,
    jfe_honda_starter_profiles,
    validate_position_snapshot,
    write_position_aware_dca_decision_pack_outputs,
)


def _base_snapshot() -> dict[str, object]:
    return {
        "symbol": "5411.T",
        "display_name": "JFE Holdings",
        "account_label": "manual_redacted_taxable",
        "shares": 100,
        "average_cost": 2300,
        "last_price": 1900,
        "market_value": 190000,
        "unrealized_pnl": -40000,
        "unrealized_pnl_pct": -17.39,
        "portfolio_weight_pct": 2.0,
        "sector_weight_pct": 4.0,
        "intended_role": "cyclical recovery",
        "max_position_weight_pct": 5.0,
        "planned_dca_budget": 50000,
        "remaining_cash_buffer": 500000,
    }


def test_valid_position_snapshot_accepts_jp_alphanumeric_symbol() -> None:
    raw = _base_snapshot()
    raw["symbol"] = "285A.T"
    snapshot = validate_position_snapshot(raw)
    assert snapshot.symbol == "285A.T"
    assert snapshot.portfolio_weight_pct == 2.0


def test_invalid_position_snapshot_rejects_missing_and_negative_fields() -> None:
    raw = _base_snapshot()
    raw.pop("shares")
    try:
        validate_position_snapshot(raw)
    except ValueError as exc:
        assert "missing position snapshot fields: shares" in str(exc)
    else:
        raise AssertionError("expected missing field failure")

    raw = _base_snapshot()
    raw["portfolio_weight_pct"] = -1
    try:
        validate_position_snapshot(raw)
    except ValueError as exc:
        assert "portfolio_weight_pct must be non-negative" in str(exc)
    else:
        raise AssertionError("expected negative field failure")


def test_over_position_limit_blocks_dca() -> None:
    raw = _base_snapshot()
    raw["portfolio_weight_pct"] = 5.0
    snapshot = validate_position_snapshot(raw)
    matrix = build_dca_decision_matrix(
        snapshot=snapshot,
        valuation_tags=("business_value_improving",),
        thesis_integrity_status=THESIS_INTACT,
    )
    assert matrix["decision_label"] == "monitor_only"
    assert "over_position_limit" in matrix["blockers"]
    assert matrix["portfolio_risk_permits_additional_exposure"] is False


def test_broken_thesis_blocks_dca_even_if_price_is_lower() -> None:
    snapshot = validate_position_snapshot(_base_snapshot())
    matrix = build_dca_decision_matrix(
        snapshot=snapshot,
        valuation_tags=("business_value_improving",),
        thesis_integrity_status=THESIS_BROKEN,
    )
    assert matrix["price_is_cheaper"] is True
    assert matrix["decision_label"] == "reduce_or_stop_loss_review"
    assert "thesis_broken" in matrix["blockers"]


def test_cash_buffer_insufficient_blocks_dca() -> None:
    raw = _base_snapshot()
    raw["remaining_cash_buffer"] = 10000
    snapshot = validate_position_snapshot(raw)
    matrix = build_dca_decision_matrix(
        snapshot=snapshot,
        valuation_tags=("business_value_improving",),
        thesis_integrity_status=THESIS_INTACT,
    )
    assert matrix["decision_label"] == "monitor_only"
    assert "cash_buffer_insufficient" in matrix["blockers"]


def test_dividend_attractiveness_alone_is_insufficient() -> None:
    snapshot = validate_position_snapshot(_base_snapshot())
    matrix = build_dca_decision_matrix(
        snapshot=snapshot,
        dividend_tags=("dividend_floor_vs_payout_sustainability",),
        thesis_integrity_status=THESIS_INTACT,
    )
    assert matrix["decision_label"] == "monitor_only"
    assert "dividend_or_yield_attractiveness_alone_is_insufficient" in matrix["warnings"]
    assert matrix["business_value_is_better"] is False


def test_jfe_honda_starter_profiles_render_without_live_data() -> None:
    profiles = jfe_honda_starter_profiles()
    assert "steel_cycle" in profiles["5411.T"]["starter_tags"]["business_risk"]
    assert "auto_margin_pressure" in profiles["7267.T"]["starter_tags"]["business_risk"]
    assert fixture_position_snapshots()["5411.T"].symbol == "5411.T"
    payload = build_position_aware_dca_decision_pack(report_date="2026-06-01", symbols_csv="5411.T,7267.T")
    markdown = format_position_aware_dca_decision_pack_markdown(payload)
    assert "JFE Holdings" in markdown
    assert "Honda Motor" in markdown
    assert "Copy-ready ChatGPT Prompt" in markdown
    assert "trading_action_executed: false" in markdown
    assert payload["safety_summary"]["broker_api_access_executed"] is False


def test_write_outputs_and_cli_contract(tmp_path: Path) -> None:
    payload = build_position_aware_dca_decision_pack(report_date="2026-06-01", symbols_csv="5411.T,7267.T")
    markdown = format_position_aware_dca_decision_pack_markdown(payload)
    paths = write_position_aware_dca_decision_pack_outputs(
        out_dir=tmp_path / "position_aware_dca",
        report_date="2026-06-01",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_position_aware_dca_decision_pack_md"].is_file()
    loaded = json.loads(paths["dated_position_aware_dca_decision_pack_json"].read_text(encoding="utf-8"))
    assert loaded["report_name"] == "position_aware_dca_decision_pack"

    runner = CliRunner()
    help_result = runner.invoke(app, ["position-aware-dca-decision-pack", "--help"])
    assert help_result.exit_code == 0
    command_info = next(command for command in app.registered_commands if command.name == "position-aware-dca-decision-pack")
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-date", "--symbols", "--out-dir", "--format"}.issubset(option_names)
    assert "--broker" not in option_names
    assert "--trade" not in option_names

    result = runner.invoke(
        app,
        [
            "position-aware-dca-decision-pack",
            "--report-date",
            "2026-06-01",
            "--symbols",
            "5411.T,7267.T",
            "--out-dir",
            str(tmp_path / "cli"),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "position_aware_dca_decision_pack"' in result.output
    assert "broker_api_access_executed=false" in result.stderr
    assert "trading_action_executed=false" in result.stderr
