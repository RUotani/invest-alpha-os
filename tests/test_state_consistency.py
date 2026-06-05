from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.product.state_consistency import (
    check_state_consistency,
    format_state_consistency_json,
    render_state_consistency_markdown,
)

REPO = Path(__file__).resolve().parents[1]


def test_state_consistency_current_file_keeps_required_safety_markers() -> None:
    result = check_state_consistency(REPO / "STATE.md")

    assert result.ok is True
    assert result.latest_verified_main is not None
    assert result.issues == ()


def test_state_consistency_warns_on_latest_main_mismatch_without_strict_mode() -> None:
    result = check_state_consistency(
        REPO / "STATE.md",
        expected_main="0000000000000000000000000000000000000000",
        strict_latest_main=False,
    )

    assert result.ok is True
    assert any(issue.code == "latest_verified_main_mismatch" and issue.severity == "WARN" for issue in result.issues)
    assert "latest_verified_main_mismatch" in render_state_consistency_markdown(result)


def test_state_consistency_strict_mode_blocks_latest_main_mismatch() -> None:
    result = check_state_consistency(
        REPO / "STATE.md",
        expected_main="0000000000000000000000000000000000000000",
        strict_latest_main=True,
    )

    assert result.ok is False
    assert any(issue.code == "latest_verified_main_mismatch" and issue.severity == "ERROR" for issue in result.issues)


def test_state_consistency_reports_missing_hard_gate_marker(tmp_path: Path) -> None:
    source = (REPO / "STATE.md").read_text(encoding="utf-8")
    broken = source.replace("cache write: **NO-GO**", "cache write: pending")
    path = tmp_path / "STATE.md"
    path.write_text(broken, encoding="utf-8")

    result = check_state_consistency(path)

    assert result.ok is False
    assert any(issue.code == "missing_cache_write_no_go" for issue in result.issues)


def test_state_consistency_json_renderer_is_machine_readable() -> None:
    result = check_state_consistency(REPO / "STATE.md")
    payload = json.loads(format_state_consistency_json(result))

    assert payload["ok"] is True
    assert payload["latest_verified_main"]
    assert payload["safety_notes"][0] == "read-only STATE.md consistency check"


def test_state_consistency_cli_json_warn_mode_and_strict_failure() -> None:
    runner = CliRunner()
    warn_result = runner.invoke(
        app,
        [
            "state-consistency-check",
            "--path",
            str(REPO / "STATE.md"),
            "--expected-main",
            "0000000000000000000000000000000000000000",
            "--format",
            "json",
        ],
    )

    assert warn_result.exit_code == 0
    warn_payload = json.loads(warn_result.stdout)
    assert warn_payload["ok"] is True
    assert warn_payload["issues"][0]["severity"] == "WARN"

    strict_result = runner.invoke(
        app,
        [
            "state-consistency-check",
            "--path",
            str(REPO / "STATE.md"),
            "--expected-main",
            "0000000000000000000000000000000000000000",
            "--strict-latest-main",
            "--format",
            "markdown",
        ],
    )

    assert strict_result.exit_code == 1
    assert "latest_verified_main_mismatch" in strict_result.stdout
