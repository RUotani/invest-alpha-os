from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.cache_path_preflight_approval_package import (
    DEFAULT_CANDIDATE_CACHE_PATH,
    V69_PREFLIGHT_VERDICT,
    build_cache_path_preflight_approval_package,
)
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_cache_path_preflight_approval_package_report,
    build_provider_context_pack_block,
    write_cache_path_preflight_approval_package_outputs,
)


def test_candidate_cache_path_preflight_passes_without_filesystem_access() -> None:
    package = build_cache_path_preflight_approval_package(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    ).to_dict()
    preflight = package["cache_path_preflight"]
    verdict = package["readiness_verdict"]
    assert preflight["candidate_cache_path"] == "$HOME/.local/share/invest-alpha-os/private-cache/tiingo-ohlcv"
    assert preflight["path_expansion_performed"] is False
    assert preflight["filesystem_probe_performed"] is False
    assert preflight["directory_created"] is False
    assert verdict["preflight_verdict"] == V69_PREFLIGHT_VERDICT
    assert verdict["all_structural_checks_pass"] is True
    assert all(row["status"] == "pass" for row in preflight["structural_checks"])


def test_candidate_path_classification_is_private_local_and_not_repo_or_reports_private() -> None:
    package = build_cache_path_preflight_approval_package(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    ).to_dict()
    classification = package["cache_path_preflight"]["path_classification"]
    assert classification["uses_home_variable_or_tilde"] is True
    assert classification["under_local_share"] is True
    assert classification["contains_private_cache_segment"] is True
    assert classification["provider_scoped_tiingo_ohlcv"] is True
    assert classification["appears_inside_source_git"] is False
    assert classification["appears_inside_reports_private"] is False
    assert classification["structurally_local_or_private"] is True
    assert classification["path_expansion_policy"] == "do_not_expand_or_print_real_home_in_source_only_report"


def test_invalid_repository_relative_path_fails_preflight() -> None:
    package = build_cache_path_preflight_approval_package(
        report_date="2026-05-31",
        candidate_cache_path="./data/raw/tiingo-ohlcv",
    ).to_dict()
    verdict = package["readiness_verdict"]
    statuses = {row["check_id"]: row["status"] for row in package["cache_path_preflight"]["structural_checks"]}
    assert verdict["preflight_verdict"] == "preflight_failed"
    assert verdict["all_structural_checks_pass"] is False
    assert statuses["PATH-02"] == "fail"
    assert statuses["PATH-05"] == "fail"


def test_pilot_approval_package_is_not_execution_approval() -> None:
    package = build_cache_path_preflight_approval_package(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    ).to_dict()
    pilot = package["pilot_approval_package"]
    phrase = pilot["approval_phrase_boundary"]
    verdict = package["readiness_verdict"]
    assert pilot["operation_name"] == "tiingo_private_local_cache_write_pilot"
    assert pilot["provider"] == "Tiingo"
    assert pilot["symbols"] == ["SPY", "QQQ", "AAPL", "NVDA"]
    assert pilot["cache_write_scope"] == "future private/local cache pilot only; not approved in v69"
    assert pilot["actual_import_scope"] == "not approved"
    assert pilot["trading_scope"] == "not approved"
    assert phrase["cache_write_approval_phrase"] == "cache writeを実行してよい"
    assert phrase["cache_write_approval_phrase_issued"] is False
    assert phrase["actual_import_approval_phrase"] == "actual refresh/importを実行してよい"
    assert phrase["actual_import_approval_phrase_issued"] is False
    assert verdict["cache_write_approval_status"] == "not_approved"
    assert verdict["actual_import_approval_status"] == "not_approved"
    assert verdict["approval_phrase_issued"] is False


def test_raw_data_and_execution_safety_flags_remain_false() -> None:
    package = build_cache_path_preflight_approval_package(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    ).to_dict()
    safety = package["safety_flags"]
    assert safety["source_only"] is True
    assert safety["live_http_executed"] is False
    assert safety["tiingo_api_call_executed"] is False
    assert safety["stooq_live_fetch_executed"] is False
    assert safety["yahoo_yfinance_live_fetch_executed"] is False
    assert safety["polygon_live_fetch_executed"] is False
    assert safety["provider_live_access_executed"] is False
    assert safety["cache_write_executed"] is False
    assert safety["actual_refresh_import_executed"] is False
    assert safety["manual_actual_import_executed"] is False
    assert safety["raw_ohlcv_persisted"] is False
    assert safety["raw_api_response_persisted"] is False
    assert safety["git_tracked_raw_data_written"] is False
    assert safety["filesystem_probe_performed"] is False
    assert safety["directory_created"] is False


def test_markdown_report_and_json_payload_contain_required_sections() -> None:
    markdown, payload = build_cache_path_preflight_approval_package_report(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    )
    for heading in (
        "## Verdict",
        "## Candidate Cache Path",
        "## Structural Preflight Checks",
        "## Path Classification",
        "## Future Pilot Approval Package",
        "## Raw Data Handling Boundary",
        "## Required Operator Confirmations",
        "## Approval Phrase Boundary",
        "## Stop Conditions",
        "## What Is Still Not Approved",
        "## Next Source-Only Handoff",
    ):
        assert heading in markdown
    assert "preflight_package_ready_but_execution_not_approved" in markdown
    assert "cache_write_approval_status: not_approved" in markdown
    assert payload["pack_version"] == "v69"
    assert payload["cache_path_preflight_approval_package"]["readiness_verdict"]["preflight_verdict"] == (
        V69_PREFLIGHT_VERDICT
    )


def test_write_outputs(tmp_path: Path) -> None:
    markdown, payload = build_cache_path_preflight_approval_package_report(
        report_date="2026-05-31",
        candidate_cache_path=DEFAULT_CANDIDATE_CACHE_PATH,
    )
    paths = write_cache_path_preflight_approval_package_outputs(
        out_dir=tmp_path,
        report_date="2026-05-31",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_cache_path_preflight_approval_package_md"].is_file()
    assert paths["latest_cache_path_preflight_approval_package_json"].is_file()
    assert paths["weekly_cache_path_preflight_approval_package_md"].is_file()
    assert paths["weekly_cache_path_preflight_approval_package_json"].is_file()


def test_cli_help_exposes_safe_options_only() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["weekly-candidate-brief-cache-path-preflight-approval-package", "--help"])
    assert result.exit_code == 0
    command_info = next(
        command
        for command in app.registered_commands
        if command.name == "weekly-candidate-brief-cache-path-preflight-approval-package"
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
    assert "--import" not in option_names
    assert "--secret" not in option_names


def test_cli_generation_markdown_and_json_are_source_only(tmp_path: Path) -> None:
    runner = CliRunner()
    md_result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-cache-path-preflight-approval-package",
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
    assert "# v69 Cache Path Preflight / Cache-Write Pilot Approval Package" in md_result.output
    assert "source_only=true" in md_result.stderr
    assert "filesystem_probe_performed=false" in md_result.stderr
    assert "directory_created=false" in md_result.stderr
    assert "cache_write_executed=false" in md_result.stderr
    json_result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-cache-path-preflight-approval-package",
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
    assert '"report_name": "cache_path_preflight_approval_package"' in json_result.output
    assert '"preflight_verdict": "preflight_package_ready_but_execution_not_approved"' in json_result.output
    assert (tmp_path / "latest" / "cache_path_preflight_approval_package.md").is_file()
    assert (tmp_path / "latest" / "cache_path_preflight_approval_package.json").is_file()


def test_context_pack_includes_v69_preflight_status() -> None:
    block = build_provider_context_pack_block(report_date="2026-05-31")
    status = block["cache_path_preflight_approval_package_status"]
    assert status["package_exists"] is True
    assert status["source_only"] is True
    assert status["preflight_verdict"] == V69_PREFLIGHT_VERDICT
    assert status["all_structural_checks_pass"] is True
    assert status["candidate_cache_path"] == DEFAULT_CANDIDATE_CACHE_PATH
    assert status["path_expansion_performed"] is False
    assert status["filesystem_probe_performed"] is False
    assert status["directory_created"] is False
    assert status["cache_write_approval_status"] == "not_approved"
    assert status["actual_import_approval_status"] == "not_approved"
    assert status["approval_phrase_issued"] is False


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


def test_chatgpt_context_pack_includes_v69_summary(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-05-31"
    _write_minimal_weekly_json(report_dir)
    pack = build_chatgpt_context_pack(report_date="2026-05-31", report_dir=report_dir)
    status = pack.json_payload["cache_path_preflight_approval_package_status"]
    assert status["preflight_verdict"] == V69_PREFLIGHT_VERDICT
    assert status["cache_write_approval_status"] == "not_approved"
    assert "- cache_path_preflight_package_exists: true" in pack.markdown_text
    assert "- cache_path_preflight_cache_write_approval_status: not_approved" in pack.markdown_text
