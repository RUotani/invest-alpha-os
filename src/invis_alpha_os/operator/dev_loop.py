"""Overnight autonomous development loop (safe, queue-driven, no auto-merge)."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from invis_alpha_os.config.loader import load_yaml
from invis_alpha_os.config.paths import OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.operator.policy import GateSpec
from invis_alpha_os.operator.pr_loop import PrLoopResult, run_pr_loop

DEV_LOOP_REL_ROOT = Path("operator/dev_loop")
DEV_LOOP_EXEC_ENV = "CONFIRM_OPERATOR_DEV_LOOP"


@dataclass(frozen=True)
class DevLoopTask:
    task_id: str
    pr_title: str
    branch: str
    pytest_cmd: str
    scope: str = ""
    risk: str = "low"
    allowed_commands: tuple[str, ...] = ()
    expected_files: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()


@dataclass
class DevLoopTaskResult:
    task_id: str
    status: str
    stop_reason: str = ""
    pr_url: str | None = None
    ci_wait_status: str | None = None
    ci_wait_poll_count: int = 0
    pr_loop_evidence_path: str = ""


@dataclass
class DevLoopResult:
    run_id: str
    status: str
    mode: str
    queue_path: str
    evidence_path: str
    stop_reason: str = ""
    tasks_seen: int = 0
    tasks_executed: int = 0
    prs_created: int = 0
    task_results: list[DevLoopTaskResult] = field(default_factory=list)


def dev_loop_execute_gate() -> GateSpec:
    return GateSpec(env_var=DEV_LOOP_EXEC_ENV, required_value="YES")


def check_dev_loop_execute_gate() -> tuple[bool, list[str]]:
    gate = dev_loop_execute_gate()
    ok = os.environ.get(gate.env_var, "").strip() == gate.required_value
    return ok, ([] if ok else [gate.env_var])


def default_task_queue_path() -> Path:
    return ROOT_DIR / "config" / "tasks" / "autonomous_dev_queue.yaml"


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_queue(path: Path) -> list[DevLoopTask]:
    raw = load_yaml(path)
    rows = raw.get("tasks") if isinstance(raw, dict) else None
    if not isinstance(rows, list):
        raise ValueError("task queue must have tasks list")
    tasks: list[DevLoopTask] = []
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError("task row must be mapping")
        task_id = str(item.get("task_id") or "").strip()
        pr_title = str(item.get("pr_title") or "").strip()
        branch = str(item.get("branch") or "").strip()
        pytest_cmd = str(item.get("pytest_cmd") or "").strip()
        if not task_id or not pr_title or not branch or not pytest_cmd:
            raise ValueError("task_id, pr_title, branch, pytest_cmd are required")
        tasks.append(
            DevLoopTask(
                task_id=task_id,
                pr_title=pr_title,
                branch=branch,
                pytest_cmd=pytest_cmd,
                scope=str(item.get("scope") or "").strip(),
                risk=str(item.get("risk") or "low").strip() or "low",
                allowed_commands=tuple(str(x) for x in (item.get("allowed_commands") or [])),
                expected_files=tuple(str(x) for x in (item.get("expected_files") or [])),
                stop_conditions=tuple(str(x) for x in (item.get("stop_conditions") or [])),
            )
        )
    return tasks


def _git_status_paths(
    *,
    repo_root: Path,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> list[str]:
    runner = subprocess_run or subprocess.run
    proc = runner(
        ["git", "status", "--short"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    paths: list[str] = []
    for line in (proc.stdout or "").splitlines():
        if not line.strip():
            continue
        maybe_path = line[3:].strip() if len(line) > 3 else line.strip()
        if "->" in maybe_path:
            maybe_path = maybe_path.split("->", maxsplit=1)[-1].strip()
        if maybe_path:
            paths.append(maybe_path)
    return paths


def _has_forbidden_dirty_paths(paths: list[str]) -> str:
    for path in paths:
        norm = path.strip()
        low = norm.lower()
        if low.startswith("outputs/"):
            return f"forbidden dirty path: {norm}"
        if low.endswith(".env") or low.endswith("/.env") or low.startswith(".env"):
            return f"forbidden dirty path: {norm}"
        if "cache" in low and low.endswith(".json"):
            return f"forbidden dirty path: {norm}"
    return ""


def run_dev_loop(
    *,
    task_queue_path: Path,
    execute_dev_loop: bool = False,
    create_pr: bool = False,
    wait_ci: bool = False,
    ci_timeout_seconds: int = 600,
    ci_poll_seconds: int = 30,
    max_runtime_minutes: int = 180,
    max_tasks: int = 3,
    max_prs: int = 2,
    stop_on_failure: bool = True,
    stop_on_dirty_tree: bool = True,
    repo_root: Path | None = None,
    outputs_root: Path | None = None,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    pr_loop_runner: Callable[..., PrLoopResult] | None = None,
    monotonic_fn: Callable[[], float] | None = None,
) -> DevLoopResult:
    root = repo_root or ROOT_DIR
    out_root = outputs_root or OUTPUTS_DIR
    run_id = _utc_run_id()
    out_dir = out_root / DEV_LOOP_REL_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks = _load_queue(task_queue_path)
    now = monotonic_fn or time.monotonic
    deadline = now() + float(max_runtime_minutes * 60)
    loop_mode = "execute" if execute_dev_loop else "dry_run"
    gate_ok, gate_missing = check_dev_loop_execute_gate()
    result = DevLoopResult(
        run_id=run_id,
        status="completed",
        mode=loop_mode,
        queue_path=str(task_queue_path),
        evidence_path=str(out_dir / "evidence_summary.json"),
        tasks_seen=len(tasks),
    )
    if execute_dev_loop and not gate_ok:
        result.status = "blocked"
        result.stop_reason = f"missing gate {DEV_LOOP_EXEC_ENV}=YES"
        _write_dev_loop_evidence(out_dir, result, gate_missing=gate_missing)
        return result

    pr_runner = pr_loop_runner or run_pr_loop
    for task in tasks:
        if result.tasks_executed >= max_tasks:
            result.status = "stopped"
            result.stop_reason = f"max_tasks reached: {max_tasks}"
            break
        if result.prs_created >= max_prs:
            result.status = "stopped"
            result.stop_reason = f"max_prs reached: {max_prs}"
            break
        if now() >= deadline:
            result.status = "stopped"
            result.stop_reason = f"max_runtime reached: {max_runtime_minutes}m"
            break

        dirty_paths = _git_status_paths(repo_root=root, subprocess_run=subprocess_run)
        forbidden_reason = _has_forbidden_dirty_paths(dirty_paths)
        if forbidden_reason:
            result.status = "stopped"
            result.stop_reason = forbidden_reason
            break
        if stop_on_dirty_tree and dirty_paths:
            result.status = "stopped"
            result.stop_reason = "dirty tree detected"
            break

        if not execute_dev_loop:
            result.tasks_executed += 1
            result.task_results.append(
                DevLoopTaskResult(task_id=task.task_id, status="planned", stop_reason="dry_run")
            )
            continue

        loop_res = pr_runner(
            branch=task.branch,
            pr_title=task.pr_title,
            pytest_cmd=task.pytest_cmd,
            execute_checks=True,
            create_pr=create_pr,
            wait_ci=wait_ci,
            ci_timeout_seconds=ci_timeout_seconds,
            ci_poll_seconds=ci_poll_seconds,
            check_ci=False,
            repo_root=root,
            outputs_root=out_root,
            subprocess_run=subprocess_run,
        )
        result.tasks_executed += 1
        if loop_res.pr_url:
            result.prs_created += 1
        task_rec = DevLoopTaskResult(
            task_id=task.task_id,
            status=loop_res.status,
            stop_reason=loop_res.stop_reason,
            pr_url=loop_res.pr_url,
            ci_wait_status=loop_res.ci_wait_status,
            ci_wait_poll_count=loop_res.ci_wait_poll_count,
            pr_loop_evidence_path=loop_res.evidence_path,
        )
        result.task_results.append(task_rec)
        if stop_on_failure and loop_res.status in {"stopped", "blocked"}:
            result.status = "stopped"
            result.stop_reason = f"task_failed: {task.task_id} ({loop_res.status})"
            break

    _write_dev_loop_evidence(out_dir, result, gate_missing=gate_missing if execute_dev_loop else [])
    return result


def _write_dev_loop_evidence(out_dir: Path, result: DevLoopResult, *, gate_missing: list[str]) -> None:
    payload: dict[str, Any] = {
        "run_id": result.run_id,
        "status": result.status,
        "mode": result.mode,
        "queue_path": result.queue_path,
        "stop_reason": result.stop_reason,
        "tasks_seen": result.tasks_seen,
        "tasks_executed": result.tasks_executed,
        "prs_created": result.prs_created,
        "gate_missing": gate_missing,
        "forbidden_auto_merge": True,
        "task_results": [asdict(t) for t in result.task_results],
    }
    (out_dir / "evidence_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "dev_loop_result.json").write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
