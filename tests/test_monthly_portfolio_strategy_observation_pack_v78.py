from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.monthly_portfolio_strategy_observation_pack import (
    build_monthly_chatgpt_portfolio_review_pack,
    build_monthly_portfolio_allocation_guardrails,
    build_monthly_portfolio_snapshot_template,
    build_portfolio_cleanup_candidate_matrix,
    detect_monthly_snapshot_forbidden_values,
    format_monthly_portfolio_strategy_markdown,
    load_monthly_portfolio_snapshot_json,
    validate_monthly_portfolio_snapshot,
    write_monthly_portfolio_strategy_outputs,
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


def _valid_snapshot() -> dict[str, object]:
    return build_monthly_portfolio_snapshot_template(report_month="2026-05")["monthly_portfolio_snapshot"]


def test_v78a_monthly_snapshot_template_uses_corrected_may_values() -> None:
    payload = build_monthly_portfolio_snapshot_template(report_month="2026-05")
    snapshot = payload["monthly_portfolio_snapshot"]
    assert payload["pack_version"] == "v78"
    assert snapshot["total_assets"] == 4327.9
    assert snapshot["liabilities_or_mortgage"] == 3432.0
    assert snapshot["net_worth"] == 895.9
    assert snapshot["cash"] == 508.2
    assert snapshot["index_funds"] == 2088.2
    assert snapshot["individual_stocks"] == 846.3
    assert snapshot["bonds"] == 582.7
    assert snapshot["gold"] == 234.5
    assert snapshot["crypto_or_high_beta"] == 57.5
    assert snapshot["leveraged"] == 10.5
    correction = snapshot["data_corrections"][0]
    assert correction["field"] == "OLC"
    assert correction["incorrect_value"] == 224.0
    assert correction["corrected_value"] == 22.4
    markdown = format_monthly_portfolio_strategy_markdown(payload)
    assert "Monthly Portfolio Snapshot Template v78" in markdown
    assert "22.4" in markdown
    assert "raw_excel_direct_parsed: false" in markdown


def test_v78a_snapshot_validation_passes_and_derives_percentages() -> None:
    payload = validate_monthly_portfolio_snapshot(_valid_snapshot())
    assert payload["validation_passed"] is True
    assert payload["chatgpt_paste_ready"] is True
    assert payload["correction_notes_present"] is True
    assert payload["derived_allocation_pct"]["cash"] == 11.7
    assert payload["derived_allocation_pct"]["index_funds"] == 48.2
    assert payload["derived_allocation_pct"]["individual_stocks"] == 19.6
    assert all(row["pass"] is True for row in payload["total_consistency_checks"])
    assert all(row["pass"] is True for row in payload["percent_consistency_checks"])


def test_v78a_snapshot_validation_detects_mismatch_and_forbidden_values() -> None:
    snapshot = _valid_snapshot()
    snapshot["total_assets"] = 4400.0
    snapshot["notes"] = "please place order after reading raw broker export"
    assert "notes" in detect_monthly_snapshot_forbidden_values(snapshot)
    payload = validate_monthly_portfolio_snapshot(snapshot)
    assert payload["validation_passed"] is False
    assert "notes" in payload["forbidden_values_detected"]
    failed = [row for row in payload["total_consistency_checks"] if row["pass"] is False]
    assert failed and failed[0]["check"] == "total_assets_matches_asset_buckets"


def test_v78a_json_loader_accepts_only_object(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(_valid_snapshot(), ensure_ascii=False), encoding="utf-8")
    loaded = load_monthly_portfolio_snapshot_json(path)
    assert loaded["report_month"] == "2026-05"
    bad = tmp_path / "bad.json"
    bad.write_text("[]", encoding="utf-8")
    try:
        load_monthly_portfolio_snapshot_json(bad)
    except ValueError as exc:
        assert "must be an object" in str(exc)
    else:
        raise AssertionError("expected object validation failure")


def test_v78b_core_satellite_guardrails_classify_current_allocation() -> None:
    payload = build_monthly_portfolio_allocation_guardrails(report_month="2026-05")
    rows = {row["bucket"]: row for row in payload["guardrail_rows"]}
    assert rows["cash"]["band_status"] == "underweight"
    assert rows["cash"]["observation_action"] == "rebuild_cash_buffer"
    assert rows["index_funds"]["band_status"] == "underweight"
    assert rows["individual_stocks"]["band_status"] == "overweight"
    assert rows["individual_stocks"]["observation_action"] == "review_sell_candidates"
    assert rows["leveraged"]["band_status"] == "watch"
    assert payload["portfolio_guardrail_summary"]["overall_classification"] == "action_required_observation_only"
    assert payload["safety_summary"]["trading_action_executed"] is False


def test_v78c_cleanup_candidate_matrix_uses_generic_fixture_examples_only() -> None:
    payload = build_portfolio_cleanup_candidate_matrix(report_month="2026-05")
    rows = {row["symbol_or_label"]: row for row in payload["matrix_rows"]}
    assert rows["TMF"]["label"] == "exit_rule_required"
    assert rows["TMF"]["criteria_matrix"]["leveraged_decay_or_path_dependency"] is True
    assert rows["theme_stock_example"]["label"] == "cleanup_candidate"
    assert rows["long_term_core_example"]["label"] == "hold_core"
    assert payload["source_boundary"]["uses_fixture_examples_only"] is True
    assert payload["source_boundary"]["live_prices_fetched"] is False
    assert payload["safety_summary"]["provider_live_access_executed"] is False


def test_v78d_monthly_chatgpt_review_pack_combines_snapshot_guardrails_and_handoff() -> None:
    payload = build_monthly_chatgpt_portfolio_review_pack(report_month="2026-05")
    assert payload["snapshot_validation_status"]["validation_passed"] is True
    assert payload["cash_buffer_warning"] is True
    assert payload["individual_stock_exposure_note"] == "overweight"
    assert payload["generic_position_aware_guard_note"]["dca_guard_is_sub_tool"] is True
    assert "OLC must be 22.4万円" in payload["main_development_handoff_update"]["olc_correction_example"]
    assert "observe 2026-06-06 weekly scheduled run" in payload["main_development_handoff_update"][
        "next_main_development_priorities"
    ]
    markdown = format_monthly_portfolio_strategy_markdown(payload)
    assert "Monthly Chatgpt Portfolio Review Pack v78" in markdown
    assert "Observation-only Caveat" in markdown
    assert "trading_action_executed: false" in markdown


def test_v78_writer_and_cli_commands(tmp_path: Path) -> None:
    payload = build_monthly_chatgpt_portfolio_review_pack(report_month="2026-05")
    markdown = format_monthly_portfolio_strategy_markdown(payload)
    paths = write_monthly_portfolio_strategy_outputs(
        out_dir=tmp_path / "out",
        report_month="2026-05",
        stem="monthly_chatgpt_portfolio_review_pack",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_monthly_chatgpt_portfolio_review_pack_md"].is_file()
    loaded = json.loads(
        paths["monthly_monthly_chatgpt_portfolio_review_pack_json"].read_text(encoding="utf-8")
    )
    assert loaded["report_name"] == "monthly_chatgpt_portfolio_review_pack"

    runner = CliRunner()
    commands = (
        "monthly-portfolio-snapshot-template",
        "monthly-portfolio-snapshot-validate",
        "monthly-portfolio-allocation-guardrails",
        "portfolio-cleanup-candidate-matrix",
        "monthly-chatgpt-portfolio-review-pack",
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
        assert {"--report-month", "--out-dir", "--format"}.issubset(option_names)
        assert "--broker" not in option_names
        assert "--trade" not in option_names
        assert "--execute" not in option_names
        assert "--dispatch" not in option_names

    result = runner.invoke(
        app,
        [
            "monthly-chatgpt-portfolio-review-pack",
            "--report-month",
            "2026-05",
            "--out-dir",
            str(tmp_path / "cli"),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"report_name": "monthly_chatgpt_portfolio_review_pack"' in result.output
    assert "broker_api_access_executed=false" in result.stderr
    assert "raw_broker_export_parsed=false" in result.stderr
    assert "raw_excel_direct_parsed=false" in result.stderr
    assert "trading_action_executed=false" in result.stderr


def test_v78e_chatgpt_context_pack_includes_monthly_portfolio_status(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-06-02"
    _write_minimal_weekly_json(report_dir)
    pack = build_chatgpt_context_pack(report_date="2026-06-02", report_dir=report_dir)
    status = pack.json_payload["v78_monthly_portfolio_strategy_status"]
    assert status["pack_exists"] is True
    assert status["report_month"] == "2026-05"
    assert status["monthly_snapshot_validation_passed"] is True
    assert status["correction_notes_present"] is True
    assert "22.4万円" in status["olc_correction_example"]
    assert status["raw_excel_direct_parsed"] is False
    assert status["trading_action_executed"] is False
    assert "- v78_monthly_portfolio_strategy_pack_exists: true" in pack.markdown_text
