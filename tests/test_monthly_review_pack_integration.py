from __future__ import annotations

import json

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.product.monthly_review_pack_integration import (
    _missing_marker_issues,
    build_monthly_review_pack_integration_result,
    format_monthly_review_pack_integration_json,
    render_monthly_review_pack_integration_markdown,
)


def test_monthly_review_pack_integration_is_ready_for_redacted_fixture() -> None:
    result = build_monthly_review_pack_integration_result()

    assert result.schema_version == "monthly_review_pack_integration.v1"
    assert result.source_mode == "source_only_fixture_only_no_live_access"
    assert result.report_month == "2026-05"
    assert result.ready is True
    assert result.monthly_input_severity == "WARN"
    assert result.portfolio_data_quality_severity == "WARN"
    assert result.issues == ()
    assert set(result.checked_components) == {
        "monthly_decision_sheet_v84",
        "monthly_input_consistency_v95",
        "portfolio_data_quality_review_v109",
        "target_allocation_gap_v82",
    }


def test_monthly_review_pack_integration_markdown_contains_safety_and_components() -> None:
    markdown = render_monthly_review_pack_integration_markdown(build_monthly_review_pack_integration_result())

    assert markdown.startswith("# Monthly Review Pack Integration")
    assert "ready: true" in markdown
    assert "monthly_decision_sheet_v84" in markdown
    assert "portfolio_data_quality_review_v109" in markdown
    assert "no cache write / actual import / manual import" in markdown
    assert "no broker API / raw Excel direct parsing / env secret display" in markdown


def test_monthly_review_pack_integration_json_is_machine_readable() -> None:
    payload = json.loads(format_monthly_review_pack_integration_json(build_monthly_review_pack_integration_result()))

    assert payload["ready"] is True
    assert payload["report_month"] == "2026-05"
    assert payload["issues"] == []
    assert "target_allocation_gap_v82" in payload["checked_components"]


def test_monthly_review_pack_integration_missing_marker_detection() -> None:
    issues = _missing_marker_issues(
        component="fixture",
        text="hello",
        markers=("hello", "missing"),
    )

    assert len(issues) == 1
    assert issues[0].code == "missing_required_marker"
    assert issues[0].severity == "ERROR"
    assert issues[0].component == "fixture"


def test_monthly_review_pack_integration_cli_markdown_and_json() -> None:
    runner = CliRunner()

    markdown_result = runner.invoke(app, ["monthly-review-pack-integration", "--format", "markdown"])
    assert markdown_result.exit_code == 0
    assert "Monthly Review Pack Integration" in markdown_result.stdout
    assert "ready: true" in markdown_result.stdout

    json_result = runner.invoke(app, ["monthly-review-pack-integration", "--format", "json"])
    assert json_result.exit_code == 0
    payload = json.loads(json_result.stdout)
    assert payload["schema_version"] == "monthly_review_pack_integration.v1"


def test_monthly_review_pack_integration_cli_rejects_unsupported_format() -> None:
    result = CliRunner().invoke(app, ["monthly-review-pack-integration", "--format", "html"])

    assert result.exit_code == 2
    assert "must be markdown or json" in result.stderr
