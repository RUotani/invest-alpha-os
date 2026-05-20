"""Overnight autonomous development loop (safe, queue-driven, no auto-merge)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from invis_alpha_os.config.loader import load_yaml
from invis_alpha_os.config.paths import OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.operator.policy import GateSpec
from invis_alpha_os.operator.pr_loop import PrLoopResult, check_github_pr_create_gate, run_pr_loop

DEV_LOOP_REL_ROOT = Path("operator/dev_loop")
DEV_LOOP_EXEC_ENV = "CONFIRM_OPERATOR_DEV_LOOP"
DEFAULT_FORBIDDEN_PATHS: tuple[str, ...] = (
    ".github/workflows/",
    "Makefile",
    "pyproject.toml",
    "outputs/",
)
DEFAULT_FORBIDDEN_COMMAND_PATTERNS: tuple[str, ...] = (
    r"\bgh\s+pr\s+merge\b",
    r"\bgh\s+pr\s+close\b",
    r"\bgit\s+push\b.*\s--force\b",
    r"\bgit\s+branch\s+-D\b",
    r"\bgit\s+worktree\s+remove\b",
)
DEFAULT_FORBIDDEN_TEXT_PATTERNS: tuple[str, ...] = (
    r"\bbuy\b",
    r"\bsell\b",
    r"\btarget\s+price\b",
    r"\ballocation\b",
    r"\btrading\s+recommendation\b",
)


@dataclass(frozen=True)
class DevLoopTask:
    task_id: str
    pr_title: str
    branch: str
    pytest_cmd: str
    scope: str = ""
    risk: str = "low"
    allowed_commands: tuple[str, ...] = ()
    allowed_paths: tuple[str, ...] = ()
    forbidden_paths: tuple[str, ...] = ()
    forbidden_commands: tuple[str, ...] = ()
    expected_files: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()
    risk_level: str = "low"


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
    profile_name: str | None
    queue_path: str
    evidence_path: str
    started_at: str
    ended_at: str = ""
    stop_reason: str = ""
    tasks_seen: int = 0
    tasks_executed: int = 0
    prs_created: int = 0
    safety_validator_status: str = "ok"
    scope_violations: list[str] = field(default_factory=list)
    dirty_tree_violations: list[str] = field(default_factory=list)
    forbidden_command_violations: list[str] = field(default_factory=list)
    forbidden_text_violations: list[str] = field(default_factory=list)
    checked_paths: list[str] = field(default_factory=list)
    task_results: list[DevLoopTaskResult] = field(default_factory=list)


@dataclass(frozen=True)
class DevLoopProfile:
    name: str
    max_runtime_minutes: int
    max_tasks: int
    max_prs: int
    wait_ci: bool
    ci_timeout_seconds: int
    ci_poll_seconds: int
    stop_on_failure: bool
    stop_on_dirty_tree: bool


def dev_loop_execute_gate() -> GateSpec:
    return GateSpec(env_var=DEV_LOOP_EXEC_ENV, required_value="YES")


def check_dev_loop_execute_gate() -> tuple[bool, list[str]]:
    gate = dev_loop_execute_gate()
    ok = os.environ.get(gate.env_var, "").strip() == gate.required_value
    return ok, ([] if ok else [gate.env_var])


def default_task_queue_path() -> Path:
    return ROOT_DIR / "config" / "tasks" / "autonomous_dev_queue.yaml"


def default_profile_path() -> Path:
    return ROOT_DIR / "config" / "operator_dev_loop_profiles.yaml"


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_profile(name: str, *, profile_path: Path | None = None) -> DevLoopProfile:
    path = profile_path or default_profile_path()
    raw = load_yaml(path)
    profiles = raw.get("profiles") if isinstance(raw, dict) else None
    if not isinstance(profiles, dict):
        raise ValueError(f"profiles mapping required: {path}")
    block = profiles.get(name)
    if not isinstance(block, dict):
        raise ValueError(f"profile not found: {name}")
    return DevLoopProfile(
        name=name,
        max_runtime_minutes=int(block.get("max_runtime_minutes", 180)),
        max_tasks=int(block.get("max_tasks", 3)),
        max_prs=int(block.get("max_prs", 2)),
        wait_ci=bool(block.get("wait_ci", False)),
        ci_timeout_seconds=int(block.get("ci_timeout_seconds", 600)),
        ci_poll_seconds=int(block.get("ci_poll_seconds", 30)),
        stop_on_failure=bool(block.get("stop_on_failure", True)),
        stop_on_dirty_tree=bool(block.get("stop_on_dirty_tree", True)),
    )


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
                allowed_paths=tuple(str(x) for x in (item.get("allowed_paths") or [])),
                forbidden_paths=tuple(str(x) for x in (item.get("forbidden_paths") or [])),
                forbidden_commands=tuple(str(x) for x in (item.get("forbidden_commands") or [])),
                expected_files=tuple(str(x) for x in (item.get("expected_files") or [])),
                stop_conditions=tuple(str(x) for x in (item.get("stop_conditions") or [])),
                risk_level=str(item.get("risk_level") or item.get("risk") or "low").strip() or "low",
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


def _has_forbidden_dirty_paths(paths: list[str]) -> list[str]:
    violations: list[str] = []
    for path in paths:
        norm = path.strip()
        low = norm.lower()
        if low.startswith("outputs/"):
            violations.append(f"forbidden dirty path: {norm}")
            continue
        if low.endswith(".env") or low.endswith("/.env") or low.startswith(".env"):
            violations.append(f"forbidden dirty path: {norm}")
            continue
        if any(term in low for term in ("token", "credential", "secret")):
            violations.append(f"forbidden dirty path: {norm}")
            continue
        if "cache" in low and low.endswith(".json"):
            violations.append(f"forbidden dirty path: {norm}")
    return violations


def _path_matches_rule(path: str, rule: str) -> bool:
    norm_path = path.strip().lstrip("./")
    norm_rule = rule.strip().lstrip("./")
    if not norm_rule:
        return False
    if norm_rule.endswith("/"):
        return norm_path.startswith(norm_rule)
    return norm_path == norm_rule or norm_path.startswith(norm_rule + "/")


def _check_scope(task: DevLoopTask, changed_paths: list[str]) -> list[str]:
    violations: list[str] = []
    if task.allowed_paths:
        for p in changed_paths:
            if not any(_path_matches_rule(p, allow) for allow in task.allowed_paths):
                violations.append(f"scope violation for task {task.task_id}: {p}")
    for p in changed_paths:
        for forbid in (*DEFAULT_FORBIDDEN_PATHS, *task.forbidden_paths):
            if _path_matches_rule(p, forbid):
                violations.append(f"forbidden path for task {task.task_id}: {p}")
                break
    return violations


def _check_forbidden_commands(task: DevLoopTask) -> list[str]:
    violations: list[str] = []
    candidates = [task.pytest_cmd, *task.allowed_commands, *task.forbidden_commands]
    patterns = [*DEFAULT_FORBIDDEN_COMMAND_PATTERNS, *(f"\\b{re.escape(x)}\\b" for x in task.forbidden_commands)]
    for cmd in candidates:
        text = cmd.strip()
        if not text:
            continue
        for pat in patterns:
            if re.search(pat, text, flags=re.IGNORECASE):
                violations.append(f"forbidden command in task {task.task_id}: {text}")
                break
    return violations


def _check_forbidden_text(task: DevLoopTask) -> list[str]:
    violations: list[str] = []
    texts = [task.pr_title, task.scope, *task.stop_conditions]
    for text in texts:
        probe = text.strip()
        if not probe:
            continue
        for pat in DEFAULT_FORBIDDEN_TEXT_PATTERNS:
            if re.search(pat, probe, flags=re.IGNORECASE):
                violations.append(f"forbidden text in task {task.task_id}: {probe}")
                break
    return violations


def run_dev_loop(
    *,
    task_queue_path: Path,
    profile_name: str | None = None,
    profile_path: Path | None = None,
    execute_dev_loop: bool = False,
    create_pr: bool = False,
    wait_ci: bool | None = None,
    ci_timeout_seconds: int | None = None,
    ci_poll_seconds: int | None = None,
    max_runtime_minutes: int | None = None,
    max_tasks: int | None = None,
    max_prs: int | None = None,
    stop_on_failure: bool | None = None,
    stop_on_dirty_tree: bool | None = None,
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
    profile = _load_profile(profile_name, profile_path=profile_path) if profile_name else None
    effective_max_runtime = max_runtime_minutes if max_runtime_minutes is not None else (
        profile.max_runtime_minutes if profile else 180
    )
    effective_max_tasks = max_tasks if max_tasks is not None else (profile.max_tasks if profile else 3)
    effective_max_prs = max_prs if max_prs is not None else (profile.max_prs if profile else 2)
    effective_wait_ci = wait_ci if wait_ci is not None else (profile.wait_ci if profile else False)
    effective_ci_timeout = (
        ci_timeout_seconds if ci_timeout_seconds is not None else (profile.ci_timeout_seconds if profile else 600)
    )
    effective_ci_poll = ci_poll_seconds if ci_poll_seconds is not None else (profile.ci_poll_seconds if profile else 30)
    effective_stop_on_failure = (
        stop_on_failure if stop_on_failure is not None else (profile.stop_on_failure if profile else True)
    )
    effective_stop_on_dirty_tree = (
        stop_on_dirty_tree if stop_on_dirty_tree is not None else (profile.stop_on_dirty_tree if profile else True)
    )
    now = monotonic_fn or time.monotonic
    started_at = _utc_now_iso()
    deadline = now() + float(effective_max_runtime * 60)
    loop_mode = "execute" if execute_dev_loop else "dry_run"
    gate_ok, gate_missing = check_dev_loop_execute_gate()
    pr_gate = check_github_pr_create_gate()
    result = DevLoopResult(
        run_id=run_id,
        status="completed",
        mode=loop_mode,
        profile_name=profile_name,
        queue_path=str(task_queue_path),
        evidence_path=str(out_dir / "evidence_summary.json"),
        started_at=started_at,
        tasks_seen=len(tasks),
    )
    if execute_dev_loop and not gate_ok:
        result.status = "blocked"
        result.stop_reason = f"missing gate {DEV_LOOP_EXEC_ENV}=YES"
        result.ended_at = _utc_now_iso()
        _write_dev_loop_evidence(
            out_dir,
            result,
            gate_missing=gate_missing,
            effective_limits={
                "max_runtime_minutes": effective_max_runtime,
                "max_tasks": effective_max_tasks,
                "max_prs": effective_max_prs,
                "wait_ci": effective_wait_ci,
                "ci_timeout_seconds": effective_ci_timeout,
                "ci_poll_seconds": effective_ci_poll,
                "stop_on_failure": effective_stop_on_failure,
                "stop_on_dirty_tree": effective_stop_on_dirty_tree,
            },
            pr_create_gate_status={
                "requested": create_pr,
                "ok": check_github_pr_create_gate().ok,
                "missing": check_github_pr_create_gate().missing,
            },
        )
        return result

    pr_runner = pr_loop_runner or run_pr_loop
    for task in tasks:
        if result.tasks_executed >= effective_max_tasks:
            result.status = "stopped"
            result.stop_reason = f"max_tasks reached: {effective_max_tasks}"
            break
        if result.prs_created >= effective_max_prs:
            result.status = "stopped"
            result.stop_reason = f"max_prs reached: {effective_max_prs}"
            break
        if now() >= deadline:
            result.status = "stopped"
            result.stop_reason = f"max_runtime reached: {effective_max_runtime}m"
            break

        if not execute_dev_loop:
            result.tasks_executed += 1
            result.task_results.append(
                DevLoopTaskResult(task_id=task.task_id, status="planned", stop_reason="dry_run")
            )
            continue

        dirty_paths = _git_status_paths(repo_root=root, subprocess_run=subprocess_run)
        result.checked_paths.extend(dirty_paths)
        dirty_violations = _has_forbidden_dirty_paths(dirty_paths)
        if dirty_violations:
            result.dirty_tree_violations.extend(dirty_violations)
            result.status = "stopped"
            result.stop_reason = dirty_violations[0]
            result.safety_validator_status = "failed"
            break
        scope_violations = _check_scope(task, dirty_paths)
        if scope_violations:
            result.scope_violations.extend(scope_violations)
            result.status = "stopped"
            result.stop_reason = scope_violations[0]
            result.safety_validator_status = "failed"
            break
        command_violations = _check_forbidden_commands(task)
        if command_violations:
            result.forbidden_command_violations.extend(command_violations)
            result.status = "stopped"
            result.stop_reason = command_violations[0]
            result.safety_validator_status = "failed"
            break
        text_violations = _check_forbidden_text(task)
        if text_violations:
            result.forbidden_text_violations.extend(text_violations)
            result.status = "stopped"
            result.stop_reason = text_violations[0]
            result.safety_validator_status = "failed"
            break
        if effective_stop_on_dirty_tree and dirty_paths:
            result.status = "stopped"
            result.stop_reason = "dirty tree detected"
            result.safety_validator_status = "failed"
            break

        loop_res = pr_runner(
            branch=task.branch,
            pr_title=task.pr_title,
            pytest_cmd=task.pytest_cmd,
            execute_checks=True,
            create_pr=create_pr,
            wait_ci=effective_wait_ci,
            ci_timeout_seconds=effective_ci_timeout,
            ci_poll_seconds=effective_ci_poll,
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
        if effective_stop_on_failure and loop_res.status in {"stopped", "blocked"}:
            result.status = "stopped"
            result.stop_reason = f"task_failed: {task.task_id} ({loop_res.status})"
            break

    result.ended_at = _utc_now_iso()
    _write_dev_loop_evidence(
        out_dir,
        result,
        gate_missing=gate_missing if execute_dev_loop else [],
        effective_limits={
            "max_runtime_minutes": effective_max_runtime,
            "max_tasks": effective_max_tasks,
            "max_prs": effective_max_prs,
            "wait_ci": effective_wait_ci,
            "ci_timeout_seconds": effective_ci_timeout,
            "ci_poll_seconds": effective_ci_poll,
            "stop_on_failure": effective_stop_on_failure,
            "stop_on_dirty_tree": effective_stop_on_dirty_tree,
        },
        pr_create_gate_status={
            "requested": create_pr,
            "ok": pr_gate.ok,
            "missing": pr_gate.missing,
        },
    )
    return result


def _write_dev_loop_evidence(
    out_dir: Path,
    result: DevLoopResult,
    *,
    gate_missing: list[str],
    effective_limits: dict[str, Any],
    pr_create_gate_status: dict[str, Any],
) -> None:
    payload: dict[str, Any] = {
        "run_id": result.run_id,
        "status": result.status,
        "mode": result.mode,
        "profile_name": result.profile_name,
        "queue_path": result.queue_path,
        "started_at": result.started_at,
        "ended_at": result.ended_at,
        "stop_reason": result.stop_reason,
        "tasks_seen": result.tasks_seen,
        "tasks_executed": result.tasks_executed,
        "prs_created": result.prs_created,
        "gate_missing": gate_missing,
        "safety_validator_status": result.safety_validator_status,
        "scope_violations": result.scope_violations,
        "dirty_tree_violations": result.dirty_tree_violations,
        "forbidden_command_violations": result.forbidden_command_violations,
        "forbidden_text_violations": result.forbidden_text_violations,
        "checked_paths": result.checked_paths,
        "effective_limits": effective_limits,
        "pr_create_gate_status": pr_create_gate_status,
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
