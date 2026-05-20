"""R7.0-Ops-E: overnight autonomous dev-loop tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from invis_alpha_os.operator.dev_loop import (
    default_pr_create_smoke_queue_path,
    resolve_branch_name,
    run_dev_loop,
)
from invis_alpha_os.operator.pr_loop import PrLoopResult


def _queue_file(tmp_path: Path, tasks: list[dict[str, str]]) -> Path:
    lines = ["version: ops_dev_queue.v1", "tasks:"]
    for task in tasks:
        lines.extend(
            [
                f"  - task_id: {task['task_id']}",
                f"    pr_title: \"{task['pr_title']}\"",
                f"    branch: \"{task['branch']}\"",
                f"    pytest_cmd: \"{task['pytest_cmd']}\"",
            ]
        )
    path = tmp_path / "queue.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _queue_file_raw(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "queue.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def _git_clean(cmd, **kwargs):  # type: ignore[no-untyped-def]
    if cmd[:3] == ["git", "status", "--short"]:
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    if cmd[:3] == ["git", "rev-parse", "--verify"]:
        return subprocess.CompletedProcess(cmd, 0, stdout="abc", stderr="")
    if cmd[:3] == ["git", "rev-parse", "--abbrev-ref"]:
        return subprocess.CompletedProcess(cmd, 0, stdout="main\n", stderr="")
    if cmd[:3] == ["git", "rev-list", "--count"]:
        return subprocess.CompletedProcess(cmd, 0, stdout="1\n", stderr="")
    if cmd[:3] == ["git", "ls-remote", "--heads"]:
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")


def test_default_dry_run_queue_plans_only(tmp_path: Path) -> None:
    queue = _queue_file(
        tmp_path,
        [
            {
                "task_id": "t1",
                "pr_title": "Task 1",
                "branch": "work/t1",
                "pytest_cmd": "pytest -q",
            }
        ],
    )
    result = run_dev_loop(task_queue_path=queue, outputs_root=tmp_path, subprocess_run=_git_clean)
    assert result.status == "completed"
    assert result.mode == "dry_run"
    assert result.tasks_executed == 1
    assert result.prs_created == 0
    assert result.task_results[0].status == "planned"


def test_execute_gate_missing_blocked(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("CONFIRM_OPERATOR_DEV_LOOP", raising=False)
    queue = _queue_file(
        tmp_path,
        [{"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"}],
    )
    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
    )
    assert result.status == "blocked"
    assert "CONFIRM_OPERATOR_DEV_LOOP" in result.stop_reason


def test_execute_gate_ok_runs_in_order_max_tasks(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file(
        tmp_path,
        [
            {"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"},
            {"task_id": "t2", "pr_title": "Task 2", "branch": "work/t2", "pytest_cmd": "pytest -q"},
        ],
    )
    seen: list[str] = []

    def pr_runner(**kwargs):  # type: ignore[no-untyped-def]
        seen.append(kwargs["branch"])
        return PrLoopResult(
            run_id="r",
            status="completed",
            pr_create_mode="draft_only",
            branch=kwargs["branch"],
            pr_title=kwargs["pr_title"],
            pytest_cmd=kwargs["pytest_cmd"],
            pytest_exit_code=0,
            git_status_lines=[],
            runner_status=None,
            runner_run_dir=None,
            pr_body_draft_path="x.md",
            evidence_path="e.json",
        )

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        pr_loop_runner=pr_runner,
        max_tasks=1,
    )
    assert seen == ["work/t1"]
    assert result.status == "stopped"
    assert "max_tasks reached: 1" in result.stop_reason


def test_max_runtime_stops(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file(
        tmp_path,
        [{"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"}],
    )
    ticks = {"v": 0.0}

    def mono() -> float:
        ticks["v"] += 61.0
        return ticks["v"]

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        monotonic_fn=mono,
        max_runtime_minutes=1,
        pr_loop_runner=lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not run")),  # type: ignore[no-untyped-def]
    )
    assert result.status == "stopped"
    assert "max_runtime reached" in result.stop_reason


def test_max_prs_stops(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file(
        tmp_path,
        [
            {"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"},
            {"task_id": "t2", "pr_title": "Task 2", "branch": "work/t2", "pytest_cmd": "pytest -q"},
        ],
    )

    def pr_runner(**kwargs):  # type: ignore[no-untyped-def]
        return PrLoopResult(
            run_id="r",
            status="completed",
            pr_create_mode="create",
            branch=kwargs["branch"],
            pr_title=kwargs["pr_title"],
            pytest_cmd=kwargs["pytest_cmd"],
            pytest_exit_code=0,
            git_status_lines=[],
            runner_status=None,
            runner_run_dir=None,
            pr_body_draft_path="x.md",
            evidence_path="e.json",
            pr_url="https://example/pull/1",
        )

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        create_pr=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        pr_loop_runner=pr_runner,
        max_prs=1,
    )
    assert result.status == "stopped"
    assert "max_prs reached: 1" in result.stop_reason


def test_stop_on_failure(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file(
        tmp_path,
        [
            {"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"},
            {"task_id": "t2", "pr_title": "Task 2", "branch": "work/t2", "pytest_cmd": "pytest -q"},
        ],
    )
    seen: list[str] = []

    def pr_runner(**kwargs):  # type: ignore[no-untyped-def]
        seen.append(kwargs["branch"])
        status = "stopped" if kwargs["branch"] == "work/t1" else "completed"
        return PrLoopResult(
            run_id="r",
            status=status,
            pr_create_mode="draft_only",
            branch=kwargs["branch"],
            pr_title=kwargs["pr_title"],
            pytest_cmd=kwargs["pytest_cmd"],
            pytest_exit_code=1 if status == "stopped" else 0,
            git_status_lines=[],
            runner_status=None,
            runner_run_dir=None,
            pr_body_draft_path="x.md",
            evidence_path="e.json",
            stop_reason="pytest exit 1" if status == "stopped" else "",
        )

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        pr_loop_runner=pr_runner,
        stop_on_failure=True,
    )
    assert seen == ["work/t1"]
    assert result.status == "stopped"
    assert "task_failed: t1" in result.stop_reason


def test_wait_ci_success_and_failure(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file(
        tmp_path,
        [{"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"}],
    )

    def ok_runner(**kwargs):  # type: ignore[no-untyped-def]
        return PrLoopResult(
            run_id="r",
            status="completed",
            pr_create_mode="draft_only",
            branch=kwargs["branch"],
            pr_title=kwargs["pr_title"],
            pytest_cmd=kwargs["pytest_cmd"],
            pytest_exit_code=0,
            git_status_lines=[],
            runner_status=None,
            runner_run_dir=None,
            pr_body_draft_path="x.md",
            evidence_path="e.json",
            ci_wait_status="success",
            ci_wait_poll_count=2,
        )

    ok = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        wait_ci=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        pr_loop_runner=ok_runner,
    )
    assert ok.status == "completed"
    assert ok.task_results[0].ci_wait_status == "success"

    def fail_runner(**kwargs):  # type: ignore[no-untyped-def]
        return PrLoopResult(
            run_id="r",
            status="stopped",
            pr_create_mode="draft_only",
            branch=kwargs["branch"],
            pr_title=kwargs["pr_title"],
            pytest_cmd=kwargs["pytest_cmd"],
            pytest_exit_code=0,
            git_status_lines=[],
            runner_status=None,
            runner_run_dir=None,
            pr_body_draft_path="x.md",
            evidence_path="e.json",
            ci_wait_status="timeout",
            ci_wait_poll_count=3,
            stop_reason="ci_wait_status=timeout",
        )

    bad = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        wait_ci=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        pr_loop_runner=fail_runner,
    )
    assert bad.status == "stopped"
    assert "task_failed: t1" in bad.stop_reason


def test_forbidden_dirty_paths_stop(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file(
        tmp_path,
        [{"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"}],
    )

    def dirty_outputs(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["git", "status", "--short"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=" M outputs/operator/x.json\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=dirty_outputs,
    )
    assert result.status == "stopped"
    assert "forbidden dirty path" in result.stop_reason


def test_allowed_paths_ok_docs_only(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file_raw(
        tmp_path,
        """version: ops_dev_queue.v1
tasks:
  - task_id: docs_task
    pr_title: "Docs task"
    branch: "work/docs-task"
    pytest_cmd: "pytest -q"
    allowed_paths:
      - "docs/"
""",
    )

    def dirty_docs(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["git", "status", "--short"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=" M docs/01_development_status.md\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=dirty_docs,
        stop_on_dirty_tree=False,
        pr_loop_runner=lambda **kwargs: PrLoopResult(  # type: ignore[no-untyped-def]
            run_id="r",
            status="completed",
            pr_create_mode="draft_only",
            branch=kwargs["branch"],
            pr_title=kwargs["pr_title"],
            pytest_cmd=kwargs["pytest_cmd"],
            pytest_exit_code=0,
            git_status_lines=[],
            runner_status=None,
            runner_run_dir=None,
            pr_body_draft_path="x.md",
            evidence_path="e.json",
        ),
    )
    assert result.status == "completed"
    assert result.scope_violations == []


def test_allowed_paths_violation_docs_task_src_changed(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file_raw(
        tmp_path,
        """version: ops_dev_queue.v1
tasks:
  - task_id: docs_task
    pr_title: "Docs task"
    branch: "work/docs-task"
    pytest_cmd: "pytest -q"
    allowed_paths:
      - "docs/"
""",
    )

    def dirty_src(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["git", "status", "--short"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=" M src/invis_alpha_os/operator/dev_loop.py\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=dirty_src,
        stop_on_dirty_tree=False,
    )
    assert result.status == "stopped"
    assert result.scope_violations
    assert "scope violation" in result.stop_reason


def test_forbidden_paths_violation(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file_raw(
        tmp_path,
        """version: ops_dev_queue.v1
tasks:
  - task_id: code_task
    pr_title: "Code task"
    branch: "work/code-task"
    pytest_cmd: "pytest -q"
    forbidden_paths:
      - "pyproject.toml"
""",
    )

    def dirty_forbidden(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["git", "status", "--short"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=" M pyproject.toml\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=dirty_forbidden,
        stop_on_dirty_tree=False,
    )
    assert result.status == "stopped"
    assert result.scope_violations
    assert "forbidden path" in result.stop_reason


def test_dirty_tree_token_credentials_cache_detected(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file(
        tmp_path,
        [{"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"}],
    )

    def dirty_sensitive(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["git", "status", "--short"]:
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout=" M secrets/token_notes.md\n M config/credentials.txt\n M data/cache_dump.json\n",
                stderr="",
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=dirty_sensitive,
    )
    assert result.status == "stopped"
    assert result.dirty_tree_violations


def test_forbidden_command_detected(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file_raw(
        tmp_path,
        """version: ops_dev_queue.v1
tasks:
  - task_id: bad_cmd
    pr_title: "Bad command task"
    branch: "work/bad-cmd"
    pytest_cmd: "gh pr merge 123"
""",
    )
    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
    )
    assert result.status == "stopped"
    assert result.forbidden_command_violations
    assert "forbidden command" in result.stop_reason


def test_forbidden_text_detected(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file_raw(
        tmp_path,
        """version: ops_dev_queue.v1
tasks:
  - task_id: bad_text
    pr_title: "Buy signal task"
    branch: "work/bad-text"
    pytest_cmd: "pytest -q"
""",
    )
    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
    )
    assert result.status == "stopped"
    assert result.forbidden_text_violations
    assert "forbidden text" in result.stop_reason


def test_profile_load_smoke_20min(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file(
        tmp_path,
        [{"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"}],
    )
    profile = tmp_path / "profiles.yaml"
    profile.write_text(
        """version: ops_dev_loop_profiles.v1
profiles:
  smoke_20min:
    max_runtime_minutes: 20
    max_tasks: 2
    max_prs: 1
    wait_ci: false
    ci_timeout_seconds: 700
    ci_poll_seconds: 11
    stop_on_failure: true
    stop_on_dirty_tree: true
""",
        encoding="utf-8",
    )
    result = run_dev_loop(
        task_queue_path=queue,
        profile_name="smoke_20min",
        profile_path=profile,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
    )
    payload = (Path(result.evidence_path)).read_text(encoding="utf-8")
    assert '"profile_name": "smoke_20min"' in payload
    assert '"max_runtime_minutes": 20' in payload
    assert '"ci_poll_seconds": 11' in payload


def test_profile_override_priority(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file(
        tmp_path,
        [{"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"}],
    )
    profile = tmp_path / "profiles.yaml"
    profile.write_text(
        """version: ops_dev_loop_profiles.v1
profiles:
  smoke_20min:
    max_runtime_minutes: 20
    max_tasks: 5
    max_prs: 5
    wait_ci: false
    ci_timeout_seconds: 600
    ci_poll_seconds: 30
    stop_on_failure: true
    stop_on_dirty_tree: true
""",
        encoding="utf-8",
    )
    result = run_dev_loop(
        task_queue_path=queue,
        profile_name="smoke_20min",
        profile_path=profile,
        max_tasks=1,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
    )
    payload = (Path(result.evidence_path)).read_text(encoding="utf-8")
    assert '"max_tasks": 1' in payload


def test_default_compat_without_profile(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file(
        tmp_path,
        [
            {"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"},
            {"task_id": "t2", "pr_title": "Task 2", "branch": "work/t2", "pytest_cmd": "pytest -q"},
        ],
    )
    result = run_dev_loop(
        task_queue_path=queue,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        max_tasks=1,
    )
    assert result.mode == "dry_run"
    assert result.tasks_executed == 1


def test_pr_create_gate_missing_no_pr(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    monkeypatch.delenv("CONFIRM_GITHUB_PR_CREATE", raising=False)
    queue = _queue_file(
        tmp_path,
        [{"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"}],
    )
    called = {"n": 0}

    def pr_runner(**kwargs):  # type: ignore[no-untyped-def]
        called["n"] += 1
        return PrLoopResult(
            run_id="r",
            status="blocked",
            pr_create_mode="blocked",
            branch=kwargs["branch"],
            pr_title=kwargs["pr_title"],
            pytest_cmd=kwargs["pytest_cmd"],
            pytest_exit_code=0,
            git_status_lines=[],
            runner_status=None,
            runner_run_dir=None,
            pr_body_draft_path="x.md",
            evidence_path="e.json",
            stop_reason="missing gate CONFIRM_GITHUB_PR_CREATE=YES",
        )

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        create_pr=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        pr_loop_runner=pr_runner,
    )
    assert called["n"] == 1
    assert result.prs_created == 0


def test_pr_create_gate_ok_mock_pr_created(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    monkeypatch.setenv("CONFIRM_GITHUB_PR_CREATE", "YES")
    queue = _queue_file(
        tmp_path,
        [{"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"}],
    )

    def pr_runner(**kwargs):  # type: ignore[no-untyped-def]
        assert kwargs["create_pr"] is True
        return PrLoopResult(
            run_id="r",
            status="completed",
            pr_create_mode="create",
            branch=kwargs["branch"],
            pr_title=kwargs["pr_title"],
            pytest_cmd=kwargs["pytest_cmd"],
            pytest_exit_code=0,
            git_status_lines=[],
            runner_status=None,
            runner_run_dir=None,
            pr_body_draft_path="x.md",
            evidence_path="e.json",
            pr_url="https://example/pull/7",
        )

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        create_pr=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        pr_loop_runner=pr_runner,
    )
    assert result.prs_created == 1
    payload = Path(result.evidence_path).read_text(encoding="utf-8")
    assert '"ok": true' in payload


def test_profile_name_not_found(tmp_path: Path) -> None:
    queue = _queue_file(
        tmp_path,
        [{"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"}],
    )
    profile = tmp_path / "profiles.yaml"
    profile.write_text("version: ops_dev_loop_profiles.v1\nprofiles: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="profile not found"):
        run_dev_loop(task_queue_path=queue, profile_name="missing", profile_path=profile, outputs_root=tmp_path)


def test_dev_loop_pr_create_failure_stops_queue(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    monkeypatch.setenv("CONFIRM_GITHUB_PR_CREATE", "YES")
    queue = _queue_file(
        tmp_path,
        [
            {"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"},
            {"task_id": "t2", "pr_title": "Task 2", "branch": "work/t2", "pytest_cmd": "pytest -q"},
        ],
    )
    gh_calls = {"n": 0}

    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["gh", "pr", "create"]:
            gh_calls["n"] += 1
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="create failed\n")
        if cmd[:3] == ["git", "rev-parse", "--verify"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="abc", stderr="")
        if cmd[:3] == ["git", "rev-list", "--count"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="1\n", stderr="")
        if cmd[:3] == ["git", "status", "--short"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        create_pr=True,
        outputs_root=tmp_path,
        subprocess_run=route,
        stop_on_failure=True,
    )
    assert gh_calls["n"] == 1
    assert result.tasks_executed == 1
    assert result.status == "stopped"
    assert result.task_results[0].stop_reason == "pr_create_failed"
    assert "task_failed: t1" in result.stop_reason
    payload = Path(result.evidence_path).read_text(encoding="utf-8")
    assert "pr_create_failed" in payload


def test_smoke_queue_dry_run_planned(tmp_path: Path) -> None:
    queue = tmp_path / "smoke.yaml"
    queue.write_text(
        (default_pr_create_smoke_queue_path()).read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    result = run_dev_loop(
        task_queue_path=queue,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        max_tasks=1,
    )
    assert result.status == "completed"
    assert result.task_results[0].preparation_status == "planned"
    assert Path(result.evidence_path).is_file()
    assert (tmp_path / "operator/dev_loop").exists()


def test_no_commits_ahead_stops_with_evidence(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file_raw(
        tmp_path,
        """version: ops_dev_queue.v1
tasks:
  - task_id: smoke
    pr_title: "Smoke"
    branch: "work/smoke"
    pytest_cmd: "git diff --check"
    smoke_file: "docs/smoke.md"
    prepare_for_pr: true
    allowed_paths:
      - "docs/"
""",
    )

    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["git", "ls-remote", "--heads"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:3] == ["git", "checkout", "-B"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:2] == ["git", "add"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:2] == ["git", "commit"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:2] == ["git", "push"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:3] == ["git", "rev-parse", "--verify"]:
            if "origin/" in " ".join(cmd):
                return subprocess.CompletedProcess(cmd, 0, stdout="abc", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="abc", stderr="")
        if cmd[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="main\n", stderr="")
        if cmd[:3] == ["git", "rev-list", "--count"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="0\n", stderr="")
        if cmd[:3] == ["git", "status", "--short"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=" M docs/smoke.md", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        create_pr=True,
        outputs_root=tmp_path,
        subprocess_run=route,
        stop_on_dirty_tree=False,
    )
    assert result.status == "stopped"
    assert "no commits ahead" in result.stop_reason
    assert Path(result.evidence_path).is_file()
    assert (Path(result.evidence_path).parent / "dev_loop_result.json").is_file()


def test_mock_prepare_and_pr_create_success(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    monkeypatch.setenv("CONFIRM_GITHUB_PR_CREATE", "YES")
    repo = tmp_path / "repo"
    repo.mkdir()
    queue = _queue_file_raw(
        tmp_path,
        """version: ops_dev_queue.v1
tasks:
  - task_id: smoke
    pr_title: "Smoke PR"
    branch: "work/smoke"
    pytest_cmd: "git diff --check"
    smoke_file: "docs/smoke.md"
    commit_message: "smoke commit"
    prepare_for_pr: true
    allowed_paths:
      - "docs/"
""",
    )
    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["git", "ls-remote", "--heads"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:3] == ["git", "rev-parse", "--verify"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="abc", stderr="")
        if cmd[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="main\n", stderr="")
        if cmd[:3] == ["git", "rev-list", "--count"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="1\n", stderr="")
        if cmd[:3] == ["git", "checkout", "-B"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:2] == ["git", "add"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:2] == ["git", "commit"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:2] == ["git", "push"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:2] == ["git", "diff", "--check"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:3] == ["git", "status", "--short"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=" M docs/smoke.md", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        create_pr=True,
        repo_root=repo,
        outputs_root=tmp_path,
        subprocess_run=route,
        pr_loop_runner=lambda **kwargs: PrLoopResult(
            run_id="r",
            status="completed",
            pr_create_mode="create",
            branch=kwargs["branch"],
            pr_title=kwargs["pr_title"],
            pytest_cmd=kwargs["pytest_cmd"],
            pytest_exit_code=0,
            git_status_lines=[],
            runner_status=None,
            runner_run_dir=None,
            pr_body_draft_path="x.md",
            evidence_path="e.json",
            pr_url="https://example/pull/99",
        ),
        stop_on_dirty_tree=False,
    )
    assert result.status == "completed"
    assert result.prs_created == 1
    assert result.task_results[0].preparation_status == "prepared"
    assert (repo / "docs/smoke.md").is_file()


def test_evidence_written_when_execute_gate_blocked(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("CONFIRM_OPERATOR_DEV_LOOP", raising=False)
    queue = _queue_file(
        tmp_path,
        [{"task_id": "t1", "pr_title": "T", "branch": "work/t", "pytest_cmd": "pytest -q"}],
    )
    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
    )
    assert result.status == "blocked"
    out_dir = Path(result.evidence_path).parent
    assert (out_dir / "evidence_summary.json").is_file()
    assert (out_dir / "dev_loop_result.json").is_file()


def test_resolve_branch_name_template() -> None:
    assert resolve_branch_name("work/dev-loop-smoke/{run_id}", "20260520T101501Z") == (
        "work/dev-loop-smoke/20260520t101501z"
    )
    assert resolve_branch_name("work/fixed", "20260520T101501Z") == "work/fixed"


def test_smoke_queue_uses_branch_template(tmp_path: Path) -> None:
    text = default_pr_create_smoke_queue_path().read_text(encoding="utf-8")
    assert "{run_id}" in text
    assert "work/dev-loop-smoke/{run_id}" in text


def test_smoke_dry_run_expands_unique_branch(tmp_path: Path) -> None:
    queue = tmp_path / "smoke.yaml"
    queue.write_text(
        (default_pr_create_smoke_queue_path()).read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    result = run_dev_loop(
        task_queue_path=queue,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        max_tasks=1,
    )
    preflight = result.task_results[0].preparation_preflight
    assert "{run_id}" not in preflight.get("intended_branch", "")
    assert preflight.get("branch_template", "").endswith("{run_id}")
    assert "work/dev-loop-smoke/" in preflight.get("intended_branch", "")


def test_remote_branch_exists_stops_before_push(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    repo = tmp_path / "repo"
    repo.mkdir()
    queue = _queue_file_raw(
        tmp_path,
        """version: ops_dev_queue.v1
tasks:
  - task_id: smoke
    pr_title: "Smoke"
    branch: "work/smoke-fixed"
    pytest_cmd: "git diff --check"
    smoke_file: "docs/smoke.md"
    prepare_for_pr: true
    allowed_paths:
      - "docs/"
""",
    )

    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["git", "ls-remote", "--heads"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="deadbeef\trefs/heads/work/smoke-fixed\n", stderr="")
        if cmd[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="main\n", stderr="")
        if cmd[:3] == ["git", "status", "--short"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        repo_root=repo,
        outputs_root=tmp_path,
        subprocess_run=route,
        stop_on_dirty_tree=False,
    )
    assert result.status == "stopped"
    assert "remote_branch_exists" in result.stop_reason
    assert result.task_results[0].preparation_preflight.get("remote_branch_exists") is True
    assert Path(result.evidence_path).is_file()


def test_push_non_fast_forward_controlled_stop(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    repo = tmp_path / "repo"
    repo.mkdir()
    queue = _queue_file_raw(
        tmp_path,
        """version: ops_dev_queue.v1
tasks:
  - task_id: smoke
    pr_title: "Smoke"
    branch: "work/smoke-{run_id}"
    pytest_cmd: "git diff --check"
    smoke_file: "docs/smoke.md"
    prepare_for_pr: true
    allowed_paths:
      - "docs/"
""",
    )

    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["git", "ls-remote", "--heads"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:3] == ["git", "checkout", "-B"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:2] == ["git", "add"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:2] == ["git", "commit"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:2] == ["git", "push"]:
            return subprocess.CompletedProcess(
                cmd,
                1,
                stdout="",
                stderr="! [rejected] non-fast-forward\n",
            )
        if cmd[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="main\n", stderr="")
        if cmd[:3] == ["git", "status", "--short"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        repo_root=repo,
        outputs_root=tmp_path,
        subprocess_run=route,
        stop_on_dirty_tree=False,
    )
    assert result.status == "stopped"
    assert "push_rejected_non_ff" in result.stop_reason
    payload = Path(result.evidence_path).read_text(encoding="utf-8")
    assert "push_rejected_non_ff" in payload
    assert "non-fast-forward" not in payload or "[rejected]" in payload
