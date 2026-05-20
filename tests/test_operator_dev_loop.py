"""R7.0-Ops-E: overnight autonomous dev-loop tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

from invis_alpha_os.operator.dev_loop import run_dev_loop
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


def _git_clean(cmd, **kwargs):  # type: ignore[no-untyped-def]
    if cmd[:3] == ["git", "status", "--short"]:
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
