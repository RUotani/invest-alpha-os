from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.long_run_operator_preflight import (
    SLEEP_GUARD_COMMAND,
    build_long_run_operator_preflight_pack,
    format_long_run_operator_preflight_pack_markdown,
    write_long_run_operator_preflight_pack_outputs,
)


def test_sleep_guard_block_contains_required_operator_steps() -> None:
    payload = build_long_run_operator_preflight_pack(report_date="2026-05-31")
    sleep = payload["sleep_prevention"]
    assert sleep["recommended_command"] == SLEEP_GUARD_COMMAND
    assert sleep["separate_terminal_required"] is True
    assert sleep["ac_power_required"] is True
    assert sleep["lid_open_required"] is True
    assert sleep["keep_terminal_running"] is True
    assert sleep["display_sleep_alone_sufficient"] is False
    assert sleep["agent_macos_settings_change_allowed"] is False
    assert "caffeinate -dimsu -t 43200" in sleep["markdown_block"]
    assert "Keep the MacBook connected to AC power." in sleep["markdown_block"]
    assert "Keep the lid open." in sleep["markdown_block"]


def test_handoff_contract_and_hard_gate_block_are_included() -> None:
    payload = build_long_run_operator_preflight_pack(report_date="2026-05-31")
    handoff = payload["handoff_inclusion_contract"]
    hard_gate = payload["hard_gate_reminder"]["markdown_block"]
    assert handoff["future_long_run_max_instructions_include_sleep_guard"] is True
    assert handoff["future_cursor_handoffs_include_sleep_guard"] is True
    assert handoff["future_operator_runbooks_include_sleep_guard"] is True
    assert "- live HTTP" in hard_gate
    assert "- cache write" in hard_gate
    assert "- `.github/workflows` direct changes" in hard_gate
    assert payload["safety_summary"]["workflow_files_modified"] is False
    assert payload["safety_summary"]["macos_system_settings_changed"] is False


def test_markdown_and_writer_outputs(tmp_path: Path) -> None:
    payload = build_long_run_operator_preflight_pack(report_date="2026-05-31")
    markdown = format_long_run_operator_preflight_pack_markdown(payload)
    assert "# Long-Run Operator Preflight / Sleep-Guard Pack v71C" in markdown
    assert "```bash\ncaffeinate -dimsu -t 43200\n```" in markdown
    assert "macos_system_settings_changed: false" in markdown
    paths = write_long_run_operator_preflight_pack_outputs(
        out_dir=tmp_path / "out",
        report_date="2026-05-31",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_long_run_operator_preflight_sleep_guard_pack_md"].is_file()
    loaded = json.loads(paths["weekly_long_run_operator_preflight_sleep_guard_pack_json"].read_text(encoding="utf-8"))
    assert loaded["report_name"] == "long_run_operator_preflight_sleep_guard_pack"


def test_cli_and_context_pack_include_v71c(tmp_path: Path) -> None:
    runner = CliRunner()
    help_result = runner.invoke(app, ["weekly-candidate-brief-long-run-operator-preflight", "--help"])
    assert help_result.exit_code == 0
    command_info = next(
        command for command in app.registered_commands if command.name == "weekly-candidate-brief-long-run-operator-preflight"
    )
    option_names = {
        option
        for parameter in inspect.signature(command_info.callback).parameters.values()
        for option in parameter.default.param_decls
    }
    assert {"--report-date", "--out-dir", "--format"}.issubset(option_names)
    assert "--set-macos-settings" not in option_names
    assert "--edit-workflow" not in option_names
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-long-run-operator-preflight",
            "--report-date",
            "2026-05-31",
            "--out-dir",
            str(tmp_path / "cli"),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"recommended_command": "caffeinate -dimsu -t 43200"' in result.output
    assert "macos_system_settings_changed=false" in result.stderr
    assert "workflow_files_modified=false" in result.stderr

    report_dir = tmp_path / "reports" / "2026-05-31"
    report_dir.mkdir(parents=True, exist_ok=True)
    weekly_payload = {
        "sections": {
            "top_picks": [
                {"ticker": "AAPL", "name": "Apple", "asset_class": "us_stock", "score_total": 90, "score": 90}
            ],
            "avoid": [],
            "insufficient": [],
        }
    }
    (report_dir / "weekly_candidate_brief_v0_1.json").write_text(
        json.dumps(weekly_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    pack = build_chatgpt_context_pack(report_date="2026-05-31", report_dir=report_dir)
    status = pack.json_payload["long_run_operator_preflight_sleep_guard_status"]
    assert status["pack_exists"] is True
    assert status["recommended_command"] == "caffeinate -dimsu -t 43200"
    assert status["future_long_run_max_instructions_include_sleep_guard"] is True
    assert status["macos_system_settings_changed"] is False
    assert "- long_run_operator_preflight_sleep_guard_exists: true" in pack.markdown_text
