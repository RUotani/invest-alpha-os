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
    wait_for_ci_runs,
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
        if cmd[:3] == ["git", "rev-parse", "--verify"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="abc123", stderr="")
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


def test_pr_create_failure_stops_without_traceback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONFIRM_GITHUB_PR_CREATE", "YES")

    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["gh", "pr", "create"]:
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="pull request create failed\n")
        if cmd[:3] == ["git", "rev-parse", "--verify"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="abc123", stderr="")
        if "status" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
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
    assert result.status == "stopped"
    assert result.stop_reason == "pr_create_failed"
    assert result.pr_create_exit_code == 1
    assert result.pr_url is None
    ev = json.loads(Path(result.evidence_path).read_text(encoding="utf-8"))
    assert ev["pr_create_exit_code"] == 1
    assert "pull request create failed" in ev["pr_create_detail"]


def test_pr_create_preflight_missing_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONFIRM_GITHUB_PR_CREATE", "YES")

    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["git", "rev-parse", "--verify"]:
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")
        if cmd[0] == "gh":
            raise AssertionError("gh should not run when preflight fails")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_pr_loop(
        branch="work/missing-branch",
        pr_title="Example PR",
        pytest_cmd=f"{Path('.venv/bin/python')} -m pytest -q tests/test_operator_runner.py",
        outputs_root=tmp_path,
        execute_checks=True,
        create_pr=True,
        subprocess_run=route,
    )
    assert result.status == "stopped"
    assert result.stop_reason.startswith("preflight:")
    assert result.pr_url is None


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


def _run_list_response(runs: list[dict[str, str]]) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        ["gh", "run", "list"],
        0,
        stdout=json.dumps(runs),
        stderr="",
    )


def test_default_no_ci_wait(tmp_path: Path) -> None:
    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["gh", "run", "list"]:
            raise AssertionError("gh run list should not run without --wait-ci")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_pr_loop(
        branch="work/example",
        pr_title="Example PR",
        outputs_root=tmp_path,
        execute_checks=False,
        subprocess_run=route,
    )
    assert result.status == "completed"
    assert result.ci_wait_status is None
    assert result.ci_wait_poll_count == 0


def test_wait_ci_success(tmp_path: Path) -> None:
    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["gh", "run", "list"]:
            return _run_list_response(
                [{"status": "completed", "conclusion": "success", "workflowName": "test"}]
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_pr_loop(
        branch="work/example",
        pr_title="Example PR",
        outputs_root=tmp_path,
        execute_checks=False,
        wait_ci=True,
        subprocess_run=route,
    )
    assert result.status == "completed"
    assert result.ci_wait_status == "success"
    assert result.ci_wait_poll_count == 1


def test_wait_ci_pending_then_success(tmp_path: Path) -> None:
    calls = {"n": 0}

    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["gh", "run", "list"]:
            calls["n"] += 1
            if calls["n"] == 1:
                return _run_list_response([{"status": "in_progress", "conclusion": ""}])
            return _run_list_response(
                [{"status": "completed", "conclusion": "success", "workflowName": "test"}]
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_pr_loop(
        branch="work/example",
        pr_title="Example PR",
        outputs_root=tmp_path,
        execute_checks=False,
        wait_ci=True,
        ci_poll_seconds=1,
        subprocess_run=route,
        sleep_fn=lambda _s: None,
    )
    assert result.status == "completed"
    assert result.ci_wait_status == "success"
    assert result.ci_wait_poll_count == 2


def test_wait_ci_failure_stops(tmp_path: Path) -> None:
    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["gh", "run", "list"]:
            return _run_list_response(
                [{"status": "completed", "conclusion": "failure", "workflowName": "test"}]
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_pr_loop(
        branch="work/example",
        pr_title="Example PR",
        outputs_root=tmp_path,
        execute_checks=False,
        wait_ci=True,
        subprocess_run=route,
    )
    assert result.status == "stopped"
    assert result.ci_wait_status == "failing"
    assert "ci_wait_status=failing" in result.stop_reason


def test_wait_ci_cancelled_stops(tmp_path: Path) -> None:
    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["gh", "run", "list"]:
            return _run_list_response(
                [{"status": "completed", "conclusion": "cancelled", "workflowName": "test"}]
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_pr_loop(
        branch="work/example",
        pr_title="Example PR",
        outputs_root=tmp_path,
        execute_checks=False,
        wait_ci=True,
        subprocess_run=route,
    )
    assert result.status == "stopped"
    assert result.ci_wait_status == "cancelled"


def test_wait_ci_timeout(tmp_path: Path) -> None:
    clock = {"t": 0.0}

    def mono() -> float:
        return clock["t"]

    def advance(_s: float) -> None:
        clock["t"] += 15.0

    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["gh", "run", "list"]:
            return _run_list_response([{"status": "queued", "conclusion": ""}])
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_pr_loop(
        branch="work/example",
        pr_title="Example PR",
        outputs_root=tmp_path,
        execute_checks=False,
        wait_ci=True,
        ci_timeout_seconds=30,
        ci_poll_seconds=10,
        subprocess_run=route,
        monotonic_fn=mono,
        sleep_fn=advance,
    )
    assert result.status == "stopped"
    assert result.ci_wait_status == "timeout"
    assert result.ci_wait_poll_count >= 2


def test_wait_ci_and_check_ci_combo(tmp_path: Path) -> None:
    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["gh", "run", "list"]:
            return _run_list_response(
                [{"status": "completed", "conclusion": "success", "workflowName": "test"}]
            )
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
        wait_ci=True,
        check_ci=True,
        pr_number=42,
        subprocess_run=route,
    )
    assert result.status == "completed"
    assert result.ci_wait_status == "success"
    assert result.ci_status == "success"


def test_wait_for_ci_runs_unit() -> None:
    clock = {"t": 0.0}

    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        return _run_list_response([{"status": "queued", "conclusion": ""}])

    status, detail, polls = wait_for_ci_runs(
        branch="work/example",
        repo_root=Path("."),
        timeout_seconds=20,
        poll_seconds=5,
        subprocess_run=route,
        monotonic_fn=lambda: clock["t"],
        sleep_fn=lambda s: clock.__setitem__("t", clock["t"] + s),
    )
    assert status == "timeout"
    assert polls >= 2
    assert "timeout=20s" in detail
# dev-loop smoke marker: 20260522T142443Z (2026-05-22T14:28:04Z)
