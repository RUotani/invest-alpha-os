"""R7.0-Ops-D: autonomous PR loop tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from invis_alpha_os.config.paths import CONFIG_DIR
from invis_alpha_os.operator.pr_loop import (
    FORBIDDEN_GH_SUBCOMMANDS,
    assert_gh_command_allowed,
    build_pr_body_draft,
    check_github_pr_create_gate,
    run_pr_loop,
)

GATED_TASK = CONFIG_DIR / "tasks" / "r7_0_jquants_ingest_gated_smoke.yaml"


def test_default_dry_run_draft_only(tmp_path: Path) -> None:
    result = run_pr_loop(
        branch="work/example",
        pr_title="Example PR",
        task_path=GATED_TASK,
        outputs_root=tmp_path,
        execute_checks=False,
        create_pr=False,
    )
    assert result.status == "completed"
    assert result.pr_create_mode == "draft_only"
    assert result.pr_url is None
    assert result.pytest_exit_code is None
    assert Path(result.pr_body_draft_path).is_file()
    ev = json.loads(Path(result.evidence_path).read_text(encoding="utf-8"))
    assert ev["forbidden_auto_merge"] is True


def test_create_pr_without_gate_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONFIRM_GITHUB_PR_CREATE", raising=False)

    def ok_pytest(cmd, **kwargs):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    def ok_git(cmd, **kwargs):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    def fail_if_gh(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd and cmd[0] == "gh":
            raise AssertionError("gh should not be called")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[0] == "gh":
            return fail_if_gh(cmd, **kwargs)
        if "status" in cmd:
            return ok_git(cmd, **kwargs)
        return ok_pytest(cmd, **kwargs)

    result = run_pr_loop(
        branch="work/example",
        pr_title="Example PR",
        pytest_cmd=f"{Path('.venv/bin/python')} -m pytest -q tests/test_operator_runner.py",
        outputs_root=tmp_path,
        execute_checks=True,
        create_pr=True,
        subprocess_run=route,
    )
    assert result.status == "blocked"
    assert result.pr_create_mode == "blocked"
    assert result.pr_url is None


def test_create_pr_with_gate_mock_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONFIRM_GITHUB_PR_CREATE", "YES")
    captured: list[list[str]] = []

    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[0] == "gh":
            captured.append(list(cmd))
            return subprocess.CompletedProcess(cmd, 0, stdout="https://github.com/org/repo/pull/99", stderr="")
        if "status" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout=" M docs/x.md", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_pr_loop(
        branch="work/example",
        pr_title="Example PR",
        pytest_cmd=f"{Path('.venv/bin/python')} -m pytest -q tests/test_operator_runner.py",
        outputs_root=tmp_path,
        execute_checks=True,
        create_pr=True,
        subprocess_run=route,
    )
    assert result.status == "completed"
    assert result.pr_create_mode == "create"
    assert result.pr_url == "https://github.com/org/repo/pull/99"
    assert captured
    assert "create" in captured[0]
    assert "merge" not in " ".join(captured[0])


def test_pytest_fail_stops_before_pr_create(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONFIRM_GITHUB_PR_CREATE", "YES")

    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[0] == "gh":
            raise AssertionError("gh should not run on pytest failure")
        return subprocess.CompletedProcess(cmd, 1, stdout="FAILED", stderr="")

    result = run_pr_loop(
        branch="work/example",
        pr_title="Example PR",
        pytest_cmd="pytest -q tests/nonexistent.py",
        outputs_root=tmp_path,
        execute_checks=True,
        create_pr=True,
        subprocess_run=route,
    )
    assert result.status == "stopped"
    assert result.pytest_exit_code == 1


def test_forbidden_gh_merge() -> None:
    with pytest.raises(ValueError, match="forbidden gh command"):
        assert_gh_command_allowed(["gh", "pr", "merge", "1"])


def test_pr_body_has_required_sections() -> None:
    body = build_pr_body_draft(
        pr_title="T",
        branch="b",
        task=None,
        runner_state=None,
        pytest_cmd="pytest -q",
        pytest_exit_code=0,
        git_status_lines=[],
        create_pr_requested=False,
        gate_ok=False,
    )
    assert "## Summary" in body
    assert "## Safety" in body
    assert "No auto-merge" in body


def test_gate_check_env() -> None:
    import os

    old = os.environ.get("CONFIRM_GITHUB_PR_CREATE")
    try:
        os.environ["CONFIRM_GITHUB_PR_CREATE"] = "YES"
        assert check_github_pr_create_gate().ok is True
    finally:
        if old is None:
            os.environ.pop("CONFIRM_GITHUB_PR_CREATE", None)
        else:
            os.environ["CONFIRM_GITHUB_PR_CREATE"] = old


def test_check_ci_success_readonly(tmp_path: Path) -> None:
    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["gh", "pr", "checks"]:
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout="test pass 50s https://example.test/run\n",
                stderr="",
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_pr_loop(
        branch="work/example",
        pr_title="Example PR",
        outputs_root=tmp_path,
        execute_checks=False,
        create_pr=False,
        check_ci=True,
        pr_number=123,
        subprocess_run=route,
    )
    assert result.status == "completed"
    assert result.ci_status == "success"


def test_check_ci_pending_stops(tmp_path: Path) -> None:
    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["gh", "pr", "checks"]:
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout="test pending 0 https://example.test/run\n",
                stderr="",
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_pr_loop(
        branch="work/example",
        pr_title="Example PR",
        outputs_root=tmp_path,
        execute_checks=False,
        create_pr=False,
        check_ci=True,
        pr_number=123,
        subprocess_run=route,
    )
    assert result.status == "stopped"
    assert result.ci_status == "pending"
    assert "ci_status=pending" in result.stop_reason


def test_check_ci_without_pr_number_blocked(tmp_path: Path) -> None:
    result = run_pr_loop(
        branch="work/example",
        pr_title="Example PR",
        outputs_root=tmp_path,
        execute_checks=False,
        create_pr=False,
        check_ci=True,
    )
    assert result.status == "blocked"
    assert result.ci_status == "unknown"


def test_check_ci_forbids_merge_command() -> None:
    with pytest.raises(ValueError, match="forbidden gh command"):
        assert_gh_command_allowed(["gh", "pr", "close", "1"])
