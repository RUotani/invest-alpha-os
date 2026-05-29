from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data.ohlcv_provider_approval import (
    ProviderExecutionGate,
    build_default_provider_approval_package,
)
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import (
    build_ohlcv_provider_approval_package,
    build_provider_context_pack_block,
    write_ohlcv_provider_approval_package_outputs,
)


REQUIRED_GATES = {
    "LIVE_HTTP",
    "PUBLIC_OHLCV_SOURCE_LIVE_FETCH",
    "JQUANTS_GATED_REFRESH",
    "CACHE_WRITE",
    "ACTUAL_REFRESH",
    "ACTUAL_IMPORT",
    "MANUAL_ACTUAL_IMPORT",
    "BROKER_OR_MANUAL_RAW_DATA_HANDLING",
    "ENV_OR_SECRET_REQUIRED",
    "WORKFLOW_DEPENDENCY_OR_PYPROJECT_CHANGE",
    "TRADING_ACTION",
}


def test_default_plan_requires_no_gated_execution() -> None:
    package = build_default_provider_approval_package(report_date="2026-05-29")
    payload = package.to_dict()
    assert payload["execution_plan"]["dry_run_only"] is True
    assert payload["safety_summary"]["live_http_executed"] is False
    assert payload["safety_summary"]["cache_write_executed"] is False
    assert payload["safety_summary"]["actual_refresh_import_executed"] is False
    assert payload["safety_summary"]["manual_actual_import_executed"] is False


def test_all_dangerous_actions_require_explicit_approval() -> None:
    package = build_default_provider_approval_package(report_date="2026-05-29")
    requirements = package.to_dict()["requirements"]
    gates = {row["gate"] for row in requirements}
    assert REQUIRED_GATES.issubset(gates)
    for row in requirements:
        assert row["default_status"] == "blocked_until_explicit_approval"
        assert row["explicit_user_approval_required"] is True
        assert row["safe_by_default_behavior"] == "preview_only_no_execution"


def test_approval_package_contains_gate_labels_and_phrases() -> None:
    markdown, payload = build_ohlcv_provider_approval_package(report_date="2026-05-29")
    assert "OHLCV Provider Approval Package" in markdown
    for gate in REQUIRED_GATES:
        assert gate in markdown
    assert "public OHLCV source live fetchを実行してよい" in markdown
    assert "J-Quants gated refreshを実行してよい" in markdown
    assert "cache writeを実行してよい" in markdown
    assert "actual refresh/importを実行してよい" in markdown
    assert "manual JP bars actual importを実行してよい" in markdown
    assert payload["dry_run_only"] is True


def test_provider_execution_plan_contains_rollback_and_verification_sections() -> None:
    markdown, payload = build_ohlcv_provider_approval_package(report_date="2026-05-29")
    assert "## Verification Plan" in markdown
    assert "## Rollback Plan" in markdown
    assert "## Stop Conditions" in markdown
    plan = payload["package"]["execution_plan"]
    assert plan["rollback_plan"]["notes"]
    assert plan["verification"]["checks"]
    assert any(ProviderExecutionGate.CACHE_WRITE.value in step["required_gates"] for step in plan["steps"])


def test_write_approval_package_outputs(tmp_path: Path) -> None:
    markdown, payload = build_ohlcv_provider_approval_package(report_date="2026-05-29")
    paths = write_ohlcv_provider_approval_package_outputs(
        out_dir=tmp_path,
        report_date="2026-05-29",
        markdown_text=markdown,
        json_payload=payload,
    )
    assert paths["latest_ohlcv_provider_approval_package_md"].is_file()
    assert paths["weekly_ohlcv_provider_approval_package_json"].is_file()


def test_cli_preview_does_not_run_live_cache_import(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-ohlcv-provider-approval-package",
            "--report-date",
            "2026-05-29",
            "--out-dir",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert "live_http_executed" in result.output
    assert "actual_refresh_import_executed" in result.stderr
    assert (tmp_path / "latest" / "ohlcv_provider_approval_package.json").is_file()
    assert "--live" not in result.output
    assert "--write-cache" not in result.output


def test_cli_rejects_unknown_format_without_execution(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "weekly-candidate-brief-ohlcv-provider-approval-package",
            "--report-date",
            "2026-05-29",
            "--out-dir",
            str(tmp_path),
            "--format",
            "yaml",
        ],
    )
    assert result.exit_code == 2
    assert not (tmp_path / "latest" / "ohlcv_provider_approval_package.json").exists()


def test_context_pack_integration_remains_safe() -> None:
    block = build_provider_context_pack_block(report_date="2026-05-29")
    status = block["provider_approval_package_status"]
    assert status["available"] is True
    assert status["dry_run_only"] is True
    assert REQUIRED_GATES.issubset(set(status["gates_covered"]))
    assert block["approval_gate_status"]["allow_live_http"] is False
    assert block["approval_gate_status"]["allow_cache_write"] is False
