"""R7.0-Ops-E: overnight autonomous dev-loop tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from invis_alpha_os.config.paths import ROOT_DIR
from invis_alpha_os.operator.dev_loop import (
    DevLoopProfile,
    _load_profile,
    _load_queue,
    _native_longrun_enabled,
    apply_profile_longrun_defaults,
    default_longrun_task_queue_path,
    default_pr_create_smoke_queue_path,
    default_productive_8h_task_queue_path,
    default_profile_path,
    default_task_queue_path,
    dev_loop_should_exit_nonzero,
    format_longrun_heartbeat_line,
    format_productive_longrun_preflight_notice,
    longrun_profile_runtime_warnings,
    resolve_branch_name,
    normalize_failure_category,
    run_dev_loop,
    task_is_critical,
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
    tmp_path.mkdir(parents=True, exist_ok=True)
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
    assert resolve_branch_name(
        "work/dev-loop/autonomous/{task_id}/{run_id}",
        "20260520T102654Z",
        task_id="docs_status_microfix",
    ) == "work/dev-loop/autonomous/docs-status-microfix/20260520t102654z"


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


def test_autonomous_queue_has_branch_templates() -> None:
    text = default_task_queue_path().read_text(encoding="utf-8")
    assert "{task_id}" in text
    assert "{run_id}" in text
    assert "prepare_for_pr: true" in text
    assert "docs/01_development_status.md" in text


def test_autonomous_docs_microfix_prepare_and_pr_mock(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    monkeypatch.setenv("CONFIRM_GITHUB_PR_CREATE", "YES")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "docs").mkdir()
    (repo / "docs/01_development_status.md").write_text("# Status\n", encoding="utf-8")

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
            return subprocess.CompletedProcess(cmd, 0, stdout=" M docs/01_development_status.md", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_dev_loop(
        task_queue_path=default_task_queue_path(),
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
            pr_url="https://example/pull/42",
        ),
        max_tasks=1,
        max_prs=1,
        stop_on_dirty_tree=False,
    )
    assert result.status == "stopped"
    assert "max_tasks reached" in result.stop_reason
    assert result.prs_created == 1
    preflight = result.task_results[0].preparation_preflight
    assert preflight.get("task_id") == "docs_status_microfix"
    assert "docs-status-microfix" in preflight.get("intended_branch", "")
    assert result.task_results[0].preparation_status == "prepared"
    body = (repo / "docs/01_development_status.md").read_text(encoding="utf-8")
    assert "dev-loop smoke marker" in body


def test_branch_not_pushed_without_prepare_stops(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file_raw(
        tmp_path,
        """version: ops_dev_queue.v1
tasks:
  - task_id: no_prep
    pr_title: "No prep"
    branch: "work/fixed-branch"
    pytest_cmd: "git diff --check"
    allowed_paths:
      - "docs/"
""",
    )
    called = {"n": 0}

    def pr_runner(**kwargs):  # type: ignore[no-untyped-def]
        called["n"] += 1
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

    def route(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["git", "rev-parse", "--verify"] and "refs/remotes/origin/" in " ".join(cmd):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")
        return _git_clean(cmd, **kwargs)

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        create_pr=True,
        outputs_root=tmp_path,
        subprocess_run=route,
        pr_loop_runner=pr_runner,
        max_tasks=1,
    )
    assert result.status == "stopped"
    assert "branch not pushed" in result.stop_reason
    assert called["n"] == 0
    assert Path(result.evidence_path).is_file()


def test_overnight_profile_autonomous_first_task_dry_run(tmp_path: Path) -> None:
    result = run_dev_loop(
        task_queue_path=default_task_queue_path(),
        profile_name="overnight_safe_3h",
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        max_tasks=1,
        max_prs=1,
    )
    assert result.status == "stopped"
    assert "max_tasks reached" in result.stop_reason
    assert result.profile_name == "overnight_safe_3h"
    assert result.task_results[0].task_id == "docs_status_microfix"
    assert result.task_results[0].preparation_status == "planned"
    preflight = result.task_results[0].preparation_preflight
    assert preflight.get("prepare_for_pr") is True
    assert "docs-status-microfix" in preflight.get("intended_branch", "")


def test_longrun_queue_has_six_prepare_tasks() -> None:
    tasks = _load_queue(default_longrun_task_queue_path())
    assert len(tasks) >= 6
    assert all(t.prepare_for_pr for t in tasks)
    task_ids = {t.task_id for t in tasks}
    assert "docs_status_microfix" not in task_ids
    assert "longrun_runbook_anchor" in task_ids


def test_longrun_runbook_forbids_smoke_only_caps() -> None:
    runbook = default_longrun_task_queue_path().parents[2] / "docs/112_r7_0_ops_longrun_autonomous_runbook.md"
    text = runbook.read_text(encoding="utf-8")
    assert "--max-tasks 6" in text
    assert "--max-prs 3" in text
    assert "max-tasks 1" in text
    assert "smoke" in text.lower()


def test_longrun_dry_run_plans_multiple_tasks(tmp_path: Path) -> None:
    result = run_dev_loop(
        task_queue_path=default_longrun_task_queue_path(),
        profile_name="overnight_safe_3h",
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        max_tasks=3,
        max_prs=2,
    )
    assert result.status == "stopped"
    assert "max_tasks reached: 3" in result.stop_reason
    assert len(result.task_results) == 3
    assert result.task_results[0].task_id == "longrun_runbook_anchor"


class _AdvancingClock:
    def __init__(self) -> None:
        self.t = 0.0

    def monotonic(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += float(seconds)


def test_smoke_max_tasks_exits_nonzero_without_longrun(tmp_path: Path) -> None:
    result = run_dev_loop(
        task_queue_path=default_task_queue_path(),
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        max_tasks=1,
    )
    assert "max_tasks reached: 1" in result.stop_reason
    assert dev_loop_should_exit_nonzero(result)


def test_longrun_task_cap_heartbeats_until_min_runtime(tmp_path: Path) -> None:
    clock = _AdvancingClock()
    result = run_dev_loop(
        task_queue_path=default_task_queue_path(),
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        max_tasks=1,
        min_runtime_minutes=2,
        no_early_success_exit=True,
        continue_after_task_limit="heartbeat",
        heartbeat_interval_minutes=1,
        monotonic_fn=clock.monotonic,
        sleep_fn=clock.sleep,
    )
    assert result.longrun_exit_success
    assert result.stop_reason == "min_runtime reached: 2"
    assert not dev_loop_should_exit_nonzero(result)
    payload = json.loads(Path(result.evidence_path).read_text(encoding="utf-8"))
    assert payload["longrun"]["cap_reached"]["tasks"] is True
    assert payload["longrun"]["longrun_state"] == "min_runtime_reached"


def test_longrun_pr_cap_heartbeats_until_min_runtime(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    monkeypatch.setenv("CONFIRM_GITHUB_PR_CREATE", "YES")
    clock = _AdvancingClock()
    queue = _queue_file(
        tmp_path,
        [
            {"task_id": "t1", "pr_title": "T1", "branch": "work/t1", "pytest_cmd": "pytest -q"},
            {"task_id": "t2", "pr_title": "T2", "branch": "work/t2", "pytest_cmd": "pytest -q"},
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
        min_runtime_minutes=2,
        no_early_success_exit=True,
        continue_after_pr_limit="heartbeat",
        heartbeat_interval_minutes=1,
        monotonic_fn=clock.monotonic,
        sleep_fn=clock.sleep,
    )
    assert result.longrun_exit_success
    assert result.stop_reason == "min_runtime reached: 2"
    assert result.prs_created == 1
    payload = json.loads(Path(result.evidence_path).read_text(encoding="utf-8"))
    assert payload["longrun"]["cap_reached"]["prs"] is True


def test_longrun_real_failure_still_nonzero(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    clock = _AdvancingClock()
    queue = _queue_file(
        tmp_path,
        [{"task_id": "t1", "pr_title": "T", "branch": "work/t1", "pytest_cmd": "pytest -q"}],
    )

    def dirty_status(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["git", "status", "--short"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=" M outputs/x.txt", stderr="")
        return _git_clean(cmd, **kwargs)

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=dirty_status,
        min_runtime_minutes=10,
        no_early_success_exit=True,
        continue_after_task_limit="heartbeat",
        monotonic_fn=clock.monotonic,
        sleep_fn=clock.sleep,
    )
    assert result.safety_validator_status == "failed"
    assert dev_loop_should_exit_nonzero(result)
    assert not result.longrun_exit_success


def test_true_longrun_3h_profile_resolves_native_flags() -> None:
    profile = _load_profile("true_longrun_3h", profile_path=default_profile_path())
    mr, ne, hb, cpr, ctk = apply_profile_longrun_defaults(
        profile,
        min_runtime_minutes=None,
        no_early_success_exit=False,
        heartbeat_interval_minutes=10,
        continue_after_pr_limit=None,
        continue_after_task_limit=None,
    )
    assert mr == 180
    assert ne is True
    assert hb == 10
    assert cpr == "heartbeat"
    assert ctk == "heartbeat"
    assert _native_longrun_enabled(min_runtime_minutes=mr, no_early_success_exit=ne)


def test_smoke_profile_has_no_min_runtime() -> None:
    profile = _load_profile("smoke_20min", profile_path=default_profile_path())
    mr, ne, _, _, _ = apply_profile_longrun_defaults(
        profile,
        min_runtime_minutes=None,
        no_early_success_exit=False,
        heartbeat_interval_minutes=10,
        continue_after_pr_limit=None,
        continue_after_task_limit=None,
    )
    assert mr is None
    assert ne is False


def test_run_true_longrun_script_includes_required_flags() -> None:
    text = (ROOT_DIR / "scripts/run_true_longrun_3h.sh").read_text(encoding="utf-8")
    assert "true_longrun_3h" in text
    assert "autonomous_dev_queue_longrun.yaml" in text
    assert "CONFIRM_OPERATOR_DEV_LOOP" in text
    assert "CONFIRM_GITHUB_PR_CREATE" in text
    assert "--min-runtime-minutes 180" in text
    assert "--no-early-success-exit" in text
    assert "--continue-after-pr-limit heartbeat" in text
    assert "gh pr list" in text
    assert "gh pr merge" not in text


def test_profile_true_longrun_3h_heartbeats_until_min_runtime(tmp_path: Path) -> None:
    clock = _AdvancingClock()
    result = run_dev_loop(
        task_queue_path=default_task_queue_path(),
        profile_name="true_longrun_3h",
        profile_path=default_profile_path(),
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        max_tasks=1,
        monotonic_fn=clock.monotonic,
        sleep_fn=clock.sleep,
    )
    assert result.longrun_exit_success
    assert result.stop_reason == "min_runtime reached: 180"
    assert not dev_loop_should_exit_nonzero(result)


def test_true_longrun_8h_profile_resolves_native_flags() -> None:
    profile = _load_profile("true_longrun_8h", profile_path=default_profile_path())
    assert profile.max_runtime_minutes >= 480
    assert profile.min_runtime_minutes == 480
    mr, ne, hb, cpr, ctk = apply_profile_longrun_defaults(
        profile,
        min_runtime_minutes=None,
        no_early_success_exit=False,
        heartbeat_interval_minutes=10,
        continue_after_pr_limit=None,
        continue_after_task_limit=None,
    )
    assert mr == 480
    assert ne is True
    assert hb == 10
    assert cpr == "heartbeat"
    assert profile.max_tasks == 100
    assert profile.max_prs == 10


def test_true_longrun_6h_max_runtime_unchanged() -> None:
    profile = _load_profile("true_longrun_6h", profile_path=default_profile_path())
    assert profile.max_runtime_minutes == 360
    assert profile.min_runtime_minutes == 360


def test_run_true_longrun_8h_script_includes_required_flags() -> None:
    text = (ROOT_DIR / "scripts/run_true_longrun_8h.sh").read_text(encoding="utf-8")
    assert "true_longrun_8h" in text
    assert "caffeinate" in text
    assert "--min-runtime-minutes 480" in text
    assert "--max-tasks 100" in text
    assert "--max-prs 10" in text
    assert "CONFIRM_OPERATOR_DEV_LOOP" in text
    assert "gh pr merge" not in text


def test_visible_heartbeat_line_emitted_during_longrun(tmp_path: Path) -> None:
    clock = _AdvancingClock()
    lines: list[str] = []

    result = run_dev_loop(
        task_queue_path=default_task_queue_path(),
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        max_tasks=1,
        min_runtime_minutes=2,
        no_early_success_exit=True,
        continue_after_task_limit="heartbeat",
        heartbeat_interval_minutes=1,
        monotonic_fn=clock.monotonic,
        sleep_fn=clock.sleep,
        heartbeat_emit_fn=lines.append,
    )
    assert result.longrun_exit_success
    assert lines
    assert any("true-longrun heartbeat:" in line for line in lines)
    assert any("elapsed=" in line and "remaining=" in line for line in lines)
    hb = format_longrun_heartbeat_line(
        result,
        start_mono=0.0,
        min_runtime_minutes=2,
        now_fn=lambda: 60.0,
    )
    assert "state=" in hb
    assert "evidence=" in hb


def test_productive_queue_has_at_least_twelve_tasks() -> None:
    tasks = _load_queue(default_productive_8h_task_queue_path())
    assert len(tasks) >= 12
    assert all(t.prepare_for_pr for t in tasks)


def test_productive_queue_avoids_forbidden_actions() -> None:
    text = default_productive_8h_task_queue_path().read_text(encoding="utf-8").lower()
    for forbidden in (
        "cache write",
        "gmail send",
        "trading recommendation",
        "target price",
        "auto-merge",
        "gh pr merge",
        "confirm_gmail",
    ):
        assert forbidden not in text
    assert "no live http" in text or "without live" in text


def test_productive_preflight_notice_format() -> None:
    tasks = _load_queue(default_productive_8h_task_queue_path())
    line = format_productive_longrun_preflight_notice(
        tasks,
        max_tasks=100,
        max_prs=10,
        min_runtime_minutes=480,
    )
    assert "productive-longrun preflight:" in line
    assert "tasks=16" in line
    assert "may exhaust before min_runtime" in line


def test_productive_script_includes_gates_and_queue() -> None:
    text = (ROOT_DIR / "scripts/run_productive_true_longrun_8h.sh").read_text(encoding="utf-8")
    assert "autonomous_dev_queue_productive_8h.yaml" in text
    assert "true_longrun_8h" in text
    assert "CONFIRM_OPERATOR_DEV_LOOP" in text
    assert "CONFIRM_GITHUB_PR_CREATE" in text
    assert "--min-runtime-minutes 480" in text
    assert "caffeinate" in text
    assert "gh pr merge" not in text


def test_productive_script_i2_failfast_preflight() -> None:
    text = (ROOT_DIR / "scripts/run_productive_true_longrun_8h.sh").read_text(encoding="utf-8")
    assert 'export PATH="${REPO_ROOT}/.venv/bin:${PATH}"' in text
    assert "PRODUCTIVE-LONGRUN-8H PREFLIGHT FAILED" in text
    assert "PRODUCTIVE-LONGRUN-8H FAILED: dev_loop_rc=" in text
    assert "PRODUCTIVE-LONGRUN-8H SUCCEEDED" in text
    assert ".venv/bin/pytest" in text
    assert "python -m pytest" in text
    assert "tail -n 80" in text
    assert "evidence_summary.json" in text or "latest_evidence" in text
    assert "operator_dev_loop_profiles.yaml" in text
    assert "gh --version" in text


def test_task_is_critical_from_risk_level(tmp_path: Path) -> None:
    low = _load_queue(
        _queue_file_raw(
            tmp_path / "low",
            "version: ops_dev_queue.v1\ntasks:\n  - task_id: t\n    pr_title: T\n    branch: b\n    pytest_cmd: pytest\n    risk_level: low\n",
        )
    )[0]
    high = _load_queue(
        _queue_file_raw(
            tmp_path / "high",
            "version: ops_dev_queue.v1\ntasks:\n  - task_id: t\n    pr_title: T\n    branch: b\n    pytest_cmd: pytest\n    risk_level: critical\n",
        )
    )[0]
    assert not task_is_critical(low)
    assert task_is_critical(high)


def test_continue_on_task_failure_records_and_continues(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
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
            evidence_path=str(tmp_path / "e1.json"),
            stop_reason="pytest exit 1" if status == "stopped" else "",
        )

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        pr_loop_runner=pr_runner,
        continue_on_task_failure=True,
        max_task_failures=3,
    )
    assert seen == ["work/t1", "work/t2"]
    assert result.status == "completed_with_failures"
    assert len(result.failed_tasks) == 1
    assert result.failed_tasks[0]["task_id"] == "t1"
    assert not dev_loop_should_exit_nonzero(result)
    evidence = json.loads(Path(result.evidence_path).read_text(encoding="utf-8"))
    assert evidence["failure_policy"]["continue_on_task_failure"] is True
    assert len(evidence["failed_tasks"]) == 1


def test_max_task_failures_stops_queue(tmp_path: Path, monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file(
        tmp_path,
        [
            {"task_id": "t1", "pr_title": "T1", "branch": "work/t1", "pytest_cmd": "pytest -q"},
            {"task_id": "t2", "pr_title": "T2", "branch": "work/t2", "pytest_cmd": "pytest -q"},
            {"task_id": "t3", "pr_title": "T3", "branch": "work/t3", "pytest_cmd": "pytest -q"},
            {"task_id": "t4", "pr_title": "T4", "branch": "work/t4", "pytest_cmd": "pytest -q"},
        ],
    )

    def pr_runner(**kwargs):  # type: ignore[no-untyped-def]
        return PrLoopResult(
            run_id="r",
            status="stopped",
            pr_create_mode="draft_only",
            branch=kwargs["branch"],
            pr_title=kwargs["pr_title"],
            pytest_cmd=kwargs["pytest_cmd"],
            pytest_exit_code=1,
            git_status_lines=[],
            runner_status=None,
            runner_run_dir=None,
            pr_body_draft_path="x.md",
            evidence_path="e.json",
            stop_reason="pytest exit 1",
        )

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        pr_loop_runner=pr_runner,
        continue_on_task_failure=True,
        max_task_failures=3,
    )
    assert result.tasks_executed == 3
    assert "max_task_failures reached: 3" in result.stop_reason
    assert dev_loop_should_exit_nonzero(result)
    assert "max_task_failures reached: 3" in capsys.readouterr().out


def test_critical_task_failure_stops_with_continue_flag(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file_raw(
        tmp_path,
        """version: ops_dev_queue.v1
tasks:
  - task_id: critical_t
    pr_title: Critical
    branch: work/critical
    pytest_cmd: pytest -q
    risk_level: critical
  - task_id: t2
    pr_title: T2
    branch: work/t2
    pytest_cmd: pytest -q
""",
    )
    seen: list[str] = []

    def pr_runner(**kwargs):  # type: ignore[no-untyped-def]
        seen.append(kwargs["branch"])
        return PrLoopResult(
            run_id="r",
            status="stopped",
            pr_create_mode="draft_only",
            branch=kwargs["branch"],
            pr_title=kwargs["pr_title"],
            pytest_cmd=kwargs["pytest_cmd"],
            pytest_exit_code=1,
            git_status_lines=[],
            runner_status=None,
            runner_run_dir=None,
            pr_body_draft_path="x.md",
            evidence_path="e.json",
            stop_reason="pytest exit 1",
        )

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        pr_loop_runner=pr_runner,
        continue_on_task_failure=True,
        max_task_failures=3,
    )
    assert seen == ["work/critical"]
    assert "task_failed: critical_t" in result.stop_reason


def test_safety_failure_stops_with_continue_flag(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file(
        tmp_path,
        [
            {"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"},
            {"task_id": "t2", "pr_title": "Task 2", "branch": "work/t2", "pytest_cmd": "pytest -q"},
        ],
    )

    def dirty_outputs(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:3] == ["git", "status", "--short"]:
            return subprocess.CompletedProcess(cmd, 0, "?? outputs/foo.txt\n", "")
        return _git_clean(cmd, **kwargs)

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=dirty_outputs,
        continue_on_task_failure=True,
        max_task_failures=3,
    )
    assert result.safety_validator_status == "failed"
    assert result.tasks_executed == 0
    assert "outputs/" in result.stop_reason


def test_normalize_failure_category_mapping() -> None:
    assert normalize_failure_category("prep_failed") == "prepare_failed"
    assert normalize_failure_category("pytest_failed") == "pytest_failed"
    assert normalize_failure_category("task_failed", raw_reason="ci_wait_status=timeout") == "ci_failed"


def test_max_task_failures_budget_eight(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    tasks = [
        {
            "task_id": f"t{i}",
            "pr_title": f"T{i}",
            "branch": f"work/t{i}",
            "pytest_cmd": "pytest -q",
        }
        for i in range(1, 10)
    ]
    queue = _queue_file(tmp_path, tasks)

    def pr_runner(**kwargs):  # type: ignore[no-untyped-def]
        return PrLoopResult(
            run_id="r",
            status="stopped",
            pr_create_mode="draft_only",
            branch=kwargs["branch"],
            pr_title=kwargs["pr_title"],
            pytest_cmd=kwargs["pytest_cmd"],
            pytest_exit_code=1,
            git_status_lines=[],
            runner_status=None,
            runner_run_dir=None,
            pr_body_draft_path="x.md",
            evidence_path="e.json",
            stop_reason="pytest exit 1",
        )

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        pr_loop_runner=pr_runner,
        continue_on_task_failure=True,
        max_task_failures=8,
        max_tasks=100,
    )
    assert result.tasks_executed == 8
    assert "max_task_failures reached: 8" in result.stop_reason
    assert len(result.failed_tasks) == 8


def test_max_same_failure_category_stops(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file(
        tmp_path,
        [
            {"task_id": f"t{i}", "pr_title": f"T{i}", "branch": f"work/t{i}", "pytest_cmd": "pytest -q"}
            for i in range(1, 6)
        ],
    )

    def pr_runner(**kwargs):  # type: ignore[no-untyped-def]
        return PrLoopResult(
            run_id="r",
            status="stopped",
            pr_create_mode="draft_only",
            branch=kwargs["branch"],
            pr_title=kwargs["pr_title"],
            pytest_cmd=kwargs["pytest_cmd"],
            pytest_exit_code=1,
            git_status_lines=[],
            runner_status=None,
            runner_run_dir=None,
            pr_body_draft_path="x.md",
            evidence_path="e.json",
            stop_reason="pytest exit 1",
        )

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        pr_loop_runner=pr_runner,
        continue_on_task_failure=True,
        max_task_failures=8,
        max_same_failure_category=4,
        max_tasks=100,
    )
    assert result.tasks_executed == 4
    assert "max_same_failure_category reached: pytest_failed=4" in result.stop_reason


def _git_no_remote_branch(cmd, **kwargs):  # type: ignore[no-untyped-def]
    if cmd[:3] == ["git", "status", "--short"]:
        return _git_clean(cmd, **kwargs)
    if cmd[:2] == ["git", "rev-parse"] and any(
        token.startswith("refs/remotes/origin/") for token in cmd
    ):
        return subprocess.CompletedProcess(cmd, 1, "", "")
    if cmd[:2] == ["git", "ls-remote"]:
        return subprocess.CompletedProcess(cmd, 0, "", "")
    return _git_clean(cmd, **kwargs)


def test_skip_existing_open_pr_not_counted_as_failure(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file(
        tmp_path,
        [{"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"}],
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

    def gh_list_runner(argv, **kwargs):  # type: ignore[no-untyped-def]
        payload = json.dumps(
            [{"headRefName": "work/t1", "title": "Task 1", "state": "OPEN", "url": "https://x/1"}]
        )
        return 0, payload, "", []

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=_git_no_remote_branch,
        pr_loop_runner=pr_runner,
        skip_existing_task_artifacts=True,
        gh_list_runner=gh_list_runner,
    )
    assert seen == []
    assert len(result.skipped_tasks) == 1
    assert result.skipped_tasks[0]["reason"] == "existing_pr"
    assert len(result.failed_tasks) == 0
    evidence = json.loads(Path(result.evidence_path).read_text(encoding="utf-8"))
    assert evidence["resume_policy"]["skip_existing_task_artifacts"] is True


def test_gh_transient_readonly_records_warning_and_continues(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONFIRM_OPERATOR_DEV_LOOP", "YES")
    queue = _queue_file(
        tmp_path,
        [{"task_id": "t1", "pr_title": "Task 1", "branch": "work/t1", "pytest_cmd": "pytest -q"}],
    )

    def gh_list_runner(argv, **kwargs):  # type: ignore[no-untyped-def]
        return 1, "", "502 Bad Gateway", []

    result = run_dev_loop(
        task_queue_path=queue,
        execute_dev_loop=True,
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        pr_loop_runner=lambda **k: PrLoopResult(
            run_id="r",
            status="completed",
            pr_create_mode="draft_only",
            branch=k["branch"],
            pr_title=k["pr_title"],
            pytest_cmd=k["pytest_cmd"],
            pytest_exit_code=0,
            git_status_lines=[],
            runner_status=None,
            runner_run_dir=None,
            pr_body_draft_path="x.md",
            evidence_path="e.json",
        ),
        skip_existing_task_artifacts=True,
        gh_list_runner=gh_list_runner,
    )
    assert result.status == "completed"
    assert any("gh" in w for w in result.resume_policy.get("gh_read_warnings", []))


def test_productive_script_i4_failure_budget_resume_skip() -> None:
    text = (ROOT_DIR / "scripts/run_productive_true_longrun_8h.sh").read_text(encoding="utf-8")
    assert "--continue-on-task-failure" in text
    assert "--max-task-failures 8" in text
    assert "--max-same-failure-category 4" in text
    assert "--skip-existing-task-artifacts" in text
    assert "--failure-summary" in text
    assert "SUCCEEDED_WITH_RECORDED_FAILURES" in text
    assert "--stop-on-failure" not in text
    assert "autonomous_dev_queue_productive_8h.yaml" in text
    assert "true_longrun_8h" in text


def test_longrun_profile_min_gt_max_warning() -> None:
    bad = DevLoopProfile(
        name="bad_test",
        max_runtime_minutes=60,
        max_tasks=1,
        max_prs=1,
        wait_ci=False,
        ci_timeout_seconds=600,
        ci_poll_seconds=30,
        stop_on_failure=True,
        stop_on_dirty_tree=True,
        min_runtime_minutes=120,
    )
    warnings = longrun_profile_runtime_warnings(bad)
    assert any("min_runtime_minutes" in item for item in warnings)


def test_true_longrun_8h_profile_passes_validation() -> None:
    profile = _load_profile("true_longrun_8h", profile_path=default_profile_path())
    assert not longrun_profile_runtime_warnings(profile)
    assert profile.min_runtime_minutes == 480
    assert profile.max_runtime_minutes >= 480


def test_productive_dry_run_emits_queue_preflight(capsys, tmp_path: Path) -> None:
    run_dev_loop(
        task_queue_path=default_productive_8h_task_queue_path(),
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        max_tasks=1,
    )
    out = capsys.readouterr().out
    assert "productive-longrun preflight:" in out


def test_effective_min_runtime_exceeds_max_runtime_warning(capsys, tmp_path: Path) -> None:
    run_dev_loop(
        task_queue_path=default_task_queue_path(),
        outputs_root=tmp_path,
        subprocess_run=_git_clean,
        max_tasks=1,
        min_runtime_minutes=500,
        max_runtime_minutes=10,
    )
    out = capsys.readouterr().out
    assert "effective min_runtime_minutes" in out
    assert "max_runtime_minutes" in out
- dev-loop smoke marker: 20260521T142301Z (2026-05-21T14:23:05Z)
