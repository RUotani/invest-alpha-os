from __future__ import annotations

import json

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.product.weekly_report_user_summary import (
    build_weekly_report_user_summary,
    format_weekly_report_user_summary_json,
)


def test_weekly_report_user_summary_reads_sample_file() -> None:
    summary = build_weekly_report_user_summary(source="sample")
    assert "ChatGPT One-Page Operator Summary" in summary.body_markdown
    assert "NO-GO" in summary.body_markdown


def test_weekly_report_user_summary_composed_fixture_mode() -> None:
    summary = build_weekly_report_user_summary(source="composed", report_date="2026-06-06")
    assert "# Weekly Report One-Page Summary" in summary.body_markdown
    assert "## 1. 今週の結論" in summary.body_markdown
    assert "## 2. 候補上位" in summary.body_markdown
    assert "## 3. ポートフォリオ制約" in summary.body_markdown
    assert "## 6. ChatGPTに聞きたい質問" in summary.body_markdown
    assert "285Aは過熱後でも深掘り価値がありますか？" in summary.body_markdown
    payload = json.loads(format_weekly_report_user_summary_json(summary))
    assert payload["source"] == "composed"


def test_weekly_report_user_summary_cli_stdout_markdown_and_json() -> None:
    md = CliRunner().invoke(app, ["weekly-report-user-summary", "--format", "markdown"])
    assert md.exit_code == 0
    assert "One-Page" in md.stdout or "Weekly Report User Summary" in md.stdout

    js = CliRunner().invoke(app, ["weekly-report-user-summary", "--format", "json", "--source", "composed"])
    assert js.exit_code == 0
    assert json.loads(js.stdout)["source"] == "composed"
