from __future__ import annotations

import json
from pathlib import Path

from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.position_aware_dca_decision_pack import (
    GenericPositionGuardInput,
    build_generic_position_guard,
)
from invis_alpha_os.reports.redacted_position_snapshot_input_pack import (
    build_redacted_position_snapshot_template,
    build_redacted_position_strategy_pack,
    validate_redacted_position_snapshot,
)


def _guard_input(**overrides: object) -> GenericPositionGuardInput:
    raw = {
        "symbol": "6501.T",
        "display_name": "Hitachi",
        "asset_class": "equity",
        "market": "JP",
        "sector_tag": "industrial",
        "theme_tag": "automation",
        "position_weight_pct": 2.0,
        "max_position_weight_pct": 5.0,
        "cash_buffer_status": "sufficient",
        "thesis_status": "intact",
        "business_value_status": "improving",
        "valuation_status": "cheap",
        "technical_status": "capitulation_seen",
        "portfolio_permission_status": "allowed",
        "dca_policy_mode": "review_only",
        "max_additional_buy_amount": 50000.0,
        "must_not_buy_if": (),
        "review_triggers": ("earnings guidance changes",),
        "operator_notes": "redacted note only",
    }
    raw.update(overrides)
    return GenericPositionGuardInput(**raw)


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


def test_generic_guard_allows_only_observation_label_without_symbol_branching() -> None:
    guard = build_generic_position_guard(_guard_input(symbol="AAPL", display_name="Apple"))
    assert guard["guard_label"] == "small_tranche_allowed"
    assert guard["observation_only_not_trade_instruction"] is True
    assert guard["symbol_specific_logic_used"] is False
    assert guard["cheap_price"] is True
    assert guard["improved_business_value"] is True
    assert guard["entry_trigger"] is True


def test_generic_guard_blocks_by_thesis_portfolio_and_cash() -> None:
    thesis = build_generic_position_guard(_guard_input(thesis_status="broken"))
    assert thesis["guard_label"] == "dca_blocked_by_thesis_damage"

    portfolio = build_generic_position_guard(_guard_input(position_weight_pct=5.0))
    assert portfolio["guard_label"] == "dca_blocked_by_portfolio_risk"

    cash = build_generic_position_guard(_guard_input(cash_buffer_status="insufficient"))
    assert cash["guard_label"] == "dca_blocked_by_cash_buffer"


def test_generic_guard_requires_latest_market_review_before_entry() -> None:
    guard = build_generic_position_guard(_guard_input(technical_status="needs_current_review"))
    assert guard["guard_label"] == "requires_latest_market_review"


def test_template_and_strategy_pack_accept_arbitrary_symbol_set() -> None:
    payload = build_redacted_position_snapshot_template(
        report_date="2026-06-01",
        symbols_csv="6501.T,7203.T,AAPL,NVDA,GLDM",
    )
    snapshot = payload["redacted_snapshot_template"]
    symbols = [row["symbol"] for row in snapshot["positions"]]
    assert symbols == ["6501.T", "7203.T", "AAPL", "NVDA", "GLDM"]
    assert all("dca_policy_mode" in row for row in snapshot["positions"])
    assert all("theme_tag" in row for row in snapshot["positions"])

    validation = validate_redacted_position_snapshot(snapshot)
    assert validation["validation_passed"] is True
    strategy = build_redacted_position_strategy_pack(report_date="2026-06-01", redacted_snapshot=snapshot)
    assert {row["symbol"] for row in strategy["rows"]} == set(symbols)
    assert all(row["generic_guard"]["symbol_specific_logic_used"] is False for row in strategy["rows"])


def test_chatgpt_context_pack_includes_generic_position_guard_status(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-06-01"
    _write_minimal_report(report_dir)
    pack = build_chatgpt_context_pack(report_date="2026-06-01", report_dir=report_dir)
    status = pack.json_payload["generic_position_aware_guard_status"]
    assert status["guard_exists"] is True
    assert status["pack_version"] == "v76"
    assert status["jfe_honda_scope"] == "starter_examples_and_fixtures_only"
    assert status["symbol_specific_guard_logic_allowed"] is False
    assert status["return_to_main_development_recommended"] is True
    assert status["provider_live_access_executed"] is False
    assert status["trading_action_executed"] is False
    assert "- generic_position_aware_guard_exists: true" in pack.markdown_text
