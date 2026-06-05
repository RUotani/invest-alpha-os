from __future__ import annotations

import json

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.portfolio.monthly_decision_sheet_v84 import build_monthly_decision_sheet_v84_markdown
from invis_alpha_os.product.report_ux_language_contract import (
    build_report_ux_language_contract,
    format_report_ux_language_contract_json,
    render_report_ux_language_contract_markdown,
    validate_report_ux_language_text,
)
from invis_alpha_os.product.weekly_candidate_brief_v0 import (
    WeeklyCandidateBriefV0,
    format_weekly_candidate_brief_v0_copy,
)


def _weekly_fixture_copy() -> str:
    return format_weekly_candidate_brief_v0_copy(
        WeeklyCandidateBriefV0(
            report_date="2026-06-06",
            generated_at_jp="fixture-jp",
            generated_at_us="fixture-us",
            jp_scope="fixture-jp-scope",
            us_scope="fixture-us-scope",
            macro_summary="fixture macro summary",
        )
    )


def test_report_ux_language_contract_contains_required_clarifications() -> None:
    contract = build_report_ux_language_contract()
    rules = {rule.key: rule for rule in contract.rules}

    assert contract.schema_version == "report_ux_language_contract.v1"
    assert rules["not_trade_instruction"].required_wording_ja.startswith("これは売買指示ではなく")
    assert "実行指示ではありません" in rules["high_priority_review_meaning"].required_wording_ja
    assert "ERRORは契約不一致" in rules["severity_meaning"].required_wording_ja
    assert "Gmail実送信ではありません" in rules["email_preview_not_delivery"].required_wording_ja
    assert "actual import" in rules["hard_gate_no_go"].required_wording_ja


def test_report_ux_language_contract_markdown_and_json() -> None:
    contract = build_report_ux_language_contract()
    markdown = render_report_ux_language_contract_markdown(contract)
    payload = json.loads(format_report_ux_language_contract_json(contract))

    assert markdown.startswith("# Report UX Language Contract")
    assert "HIGH_CONVICTION_REVIEW" in markdown
    assert "email preview artifact" in markdown
    assert payload["schema_version"] == "report_ux_language_contract.v1"
    assert payload["forbidden_wording"]


def test_report_ux_language_validator_blocks_direct_action_wording() -> None:
    issues = validate_report_ux_language_text("今すぐ発注してください。")

    assert "forbidden_wording:今すぐ発注" in issues


def test_report_ux_language_validator_accepts_weekly_and_monthly_fixtures() -> None:
    assert validate_report_ux_language_text(_weekly_fixture_copy()) == ()
    assert validate_report_ux_language_text(build_monthly_decision_sheet_v84_markdown()) == ()


def test_report_ux_language_contract_cli_markdown_and_json() -> None:
    runner = CliRunner()

    markdown_result = runner.invoke(app, ["report-ux-language-contract", "--format", "markdown"])
    assert markdown_result.exit_code == 0
    assert "Report UX Language Contract" in markdown_result.stdout
    assert "売買指示ではなく" in markdown_result.stdout

    json_result = runner.invoke(app, ["report-ux-language-contract", "--format", "json"])
    assert json_result.exit_code == 0
    payload = json.loads(json_result.stdout)
    assert payload["source_mode"] == "source_only_language_contract"


def test_report_ux_language_contract_cli_rejects_unsupported_format() -> None:
    result = CliRunner().invoke(app, ["report-ux-language-contract", "--format", "html"])

    assert result.exit_code == 2
    assert "must be markdown or json" in result.stderr
