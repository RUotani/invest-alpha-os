"""Overnight autonomous development loop (safe, queue-driven, no auto-merge)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

ContinueAfterLimit = Literal["wait", "heartbeat", "next-cycle", "stop"]
CONTINUE_AFTER_LIMITS: frozenset[str] = frozenset({"wait", "heartbeat", "next-cycle", "stop"})
CriticalFailurePolicy = Literal["stop", "record"]
CRITICAL_FAILURE_POLICIES: frozenset[str] = frozenset({"stop", "record"})

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
BRANCH_RUN_ID_PLACEHOLDER = "{run_id}"
BRANCH_TASK_ID_PLACEHOLDER = "{task_id}"

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
    critical: bool | None = None
    smoke_file: str = ""
    change_file: str = ""
    commit_message: str = ""
    prepare_for_pr: bool = False
    allow_smoke_file: bool = False


@dataclass
class DevLoopTaskResult:
    task_id: str
    status: str
    stop_reason: str = ""
    preparation_status: str = ""
    preparation_detail: str = ""
    preparation_preflight: dict[str, Any] = field(default_factory=dict)
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
    longrun_state: str = ""
    longrun_exit_success: bool = False
    failed_tasks: list[dict[str, Any]] = field(default_factory=list)
    skipped_tasks: list[dict[str, Any]] = field(default_factory=list)
    failure_policy: dict[str, Any] = field(default_factory=dict)
    resume_policy: dict[str, Any] = field(default_factory=dict)


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
    min_runtime_minutes: int | None = None
    no_early_success_exit: bool = False
    heartbeat_interval_minutes: int | None = None
    continue_after_pr_limit: str | None = None
    continue_after_task_limit: str | None = None


def dev_loop_execute_gate() -> GateSpec:
    return GateSpec(env_var=DEV_LOOP_EXEC_ENV, required_value="YES")


def check_dev_loop_execute_gate() -> tuple[bool, list[str]]:
    gate = dev_loop_execute_gate()
    ok = os.environ.get(gate.env_var, "").strip() == gate.required_value
    return ok, ([] if ok else [gate.env_var])


def default_task_queue_path() -> Path:
    return ROOT_DIR / "config" / "tasks" / "autonomous_dev_queue.yaml"


def default_pr_create_smoke_queue_path() -> Path:
    return ROOT_DIR / "config" / "tasks" / "dev_loop_pr_create_smoke_queue.yaml"


def default_longrun_task_queue_path() -> Path:
    return ROOT_DIR / "config" / "tasks" / "autonomous_dev_queue_longrun.yaml"


def default_productive_8h_task_queue_path() -> Path:
    return ROOT_DIR / "config" / "tasks" / "autonomous_dev_queue_productive_8h.yaml"


def default_productive_12h_task_queue_path() -> Path:
    return ROOT_DIR / "config" / "tasks" / "autonomous_dev_queue_productive_12h.yaml"


def default_productive_12h_v2_task_queue_path() -> Path:
    return ROOT_DIR / "config" / "tasks" / "autonomous_dev_queue_productive_12h_v2.yaml"


PRODUCTIVE_QUARANTINE_PATHS: frozenset[str] = frozenset(
    {
        "docs/smoke.md",
        "docs/dev_loop_marker_fixture.md",
        "docs/ops_dev_loop_test_marker.md",
    }
)

PRODUCTIVE_FORBIDDEN_CHANGE_FILES: frozenset[str] = PRODUCTIVE_QUARANTINE_PATHS

FORBIDDEN_PREPARE_CHANGE_FILES: frozenset[str] = PRODUCTIVE_QUARANTINE_PATHS


def _is_productive_fixture_change_file(change_file: str) -> bool:
    """Block scratch/quarantine docs used as productive task change_file targets."""
    norm = change_file.strip().lstrip("./")
    if norm in PRODUCTIVE_QUARANTINE_PATHS:
        return True
    low = norm.lower()
    if not (low.startswith("docs/") and low.endswith(".md")):
        return False
    return "fixture" in low or "test_marker" in low


def _is_productive_scratch_dirty_path(path: str) -> bool:
    norm = path.strip().lstrip("./")
    if norm in PRODUCTIVE_QUARANTINE_PATHS:
        return True
    return _is_productive_fixture_change_file(norm)


def _productive_unallowed_dirty_paths(task: DevLoopTask, dirty_paths: list[str]) -> list[str]:
    """Flag dirty paths outside task allowed_paths (productive runtime guard)."""
    change_file = _productive_task_change_file(task)
    violations: list[str] = []
    for path in dirty_paths:
        norm = path.strip()
        if _is_productive_scratch_dirty_path(norm):
            continue
        if norm == change_file:
            continue
        if task.allowed_paths and any(_path_matches_rule(norm, allow) for allow in task.allowed_paths):
            continue
        violations.append(
            f"unexpected dirty path outside allowed_paths for task {task.task_id}: {norm}"
        )
    return violations

PRODUCTIVE_FORBIDDEN_CHANGE_PREFIXES: tuple[str, ...] = (
    "tmp/",
    "outputs/",
    ".env",
)


def is_productive_task_queue_path(path: Path) -> bool:
    name = path.name
    return "productive" in name or name.endswith(("_productive_8h.yaml", "_productive_12h.yaml"))


def productive_queue_prepare_violations(queue_path: Path, tasks: list[DevLoopTask]) -> list[str]:
    """Require explicit YAML change_file for every productive prepare_for_pr task."""
    raw = load_yaml(queue_path)
    rows = raw.get("tasks") if isinstance(raw, dict) else None
    if not isinstance(rows, list):
        return ["productive queue validation failed: tasks list missing"]
    by_id = {t.task_id: t for t in tasks}
    violations: list[str] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        task_id = str(item.get("task_id") or "").strip()
        if not bool(item.get("prepare_for_pr", False)):
            continue
        change_file = str(item.get("change_file") or "").strip()
        if not change_file:
            violations.append(
                f"productive queue validation failed: task_id={task_id} missing change_file"
            )
            continue
        if change_file in PRODUCTIVE_FORBIDDEN_CHANGE_FILES or _is_productive_fixture_change_file(
            change_file
        ):
            violations.append(
                f"productive queue validation failed: forbidden fixture path {change_file}"
            )
        task = by_id.get(task_id)
        if task and not task.change_file.strip():
            violations.append(
                f"productive queue validation failed: task_id={task_id} missing loaded change_file"
            )
    return violations


def productive_queue_scratch_violations(tasks: list[DevLoopTask]) -> list[str]:
    """Flag scratch or quarantine paths used as productive task change_file."""
    violations: list[str] = []
    for task in tasks:
        change_file = _productive_task_change_file(task)
        if not change_file:
            continue
        if change_file in PRODUCTIVE_FORBIDDEN_CHANGE_FILES or _is_productive_fixture_change_file(
            change_file
        ):
            violations.append(
                f"task {task.task_id}: forbidden fixture path {change_file}"
            )
            continue
        low = change_file.lower()
        for prefix in PRODUCTIVE_FORBIDDEN_CHANGE_PREFIXES:
            if low.startswith(prefix) or low == prefix.rstrip("/"):
                violations.append(
                    f"task {task.task_id}: forbidden change_file prefix {prefix} ({change_file})"
                )
                break
        if low.endswith(".json") and "cache" in low:
            violations.append(f"task {task.task_id}: forbidden cache-like change_file {change_file}")
    return violations


def productive_quarantine_repo_violations(
    *,
    repo_root: Path,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> list[str]:
    """Detect quarantine scratch paths before productive dev-loop executes tasks."""
    violations: list[str] = []
    status_paths = set(_git_status_paths(repo_root=repo_root, subprocess_run=subprocess_run))
    for quarantine_path in sorted(PRODUCTIVE_QUARANTINE_PATHS):
        path = repo_root / quarantine_path
        if path.is_file():
            violations.append(
                f"productive dev-loop blocked: quarantine path {quarantine_path} exists on disk"
            )
        if quarantine_path in status_paths:
            violations.append(
                f"productive dev-loop blocked: quarantine path {quarantine_path} is dirty"
            )
    return violations


def default_productive_superseded_tasks_path() -> Path:
    return ROOT_DIR / "config" / "tasks" / "productive_8h_superseded_tasks.yaml"


def _load_superseded_tasks(path: Path | None = None) -> dict[str, str]:
    p = path or default_productive_superseded_tasks_path()
    if not p.is_file():
        return {}
    raw = load_yaml(p)
    rows = raw.get("superseded_tasks") if isinstance(raw, dict) else None
    if not isinstance(rows, list):
        return {}
    out: dict[str, str] = {}
    for item in rows:
        if not isinstance(item, dict):
            continue
        task_id = str(item.get("task_id") or "").strip()
        reason = str(item.get("reason") or "superseded").strip()
        if task_id:
            out[task_id] = reason
    return out


def _smoke_marker_line(change_file: str, run_id: str) -> str:
    stamp = _utc_now_iso()
    if change_file.endswith(".py"):
        return f"\n# dev-loop smoke marker: {run_id} ({stamp})\n"
    return f"\n- dev-loop smoke marker: {run_id} ({stamp})\n"


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
    min_runtime_raw = block.get("min_runtime_minutes")
    heartbeat_raw = block.get("heartbeat_interval_minutes")
    continue_pr_raw = block.get("continue_after_pr_limit")
    continue_task_raw = block.get("continue_after_task_limit")
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
        min_runtime_minutes=int(min_runtime_raw) if min_runtime_raw is not None else None,
        no_early_success_exit=bool(block.get("no_early_success_exit", False)),
        heartbeat_interval_minutes=int(heartbeat_raw) if heartbeat_raw is not None else None,
        continue_after_pr_limit=str(continue_pr_raw).strip() if continue_pr_raw else None,
        continue_after_task_limit=str(continue_task_raw).strip() if continue_task_raw else None,
    )


def apply_profile_longrun_defaults(
    profile: DevLoopProfile | None,
    *,
    min_runtime_minutes: int | None,
    no_early_success_exit: bool,
    heartbeat_interval_minutes: int,
    continue_after_pr_limit: str | None,
    continue_after_task_limit: str | None,
) -> tuple[int | None, bool, int, str | None, str | None]:
    """Merge profile long-run settings; explicit CLI args take precedence when set."""
    if profile is None:
        return (
            min_runtime_minutes,
            no_early_success_exit,
            heartbeat_interval_minutes,
            continue_after_pr_limit,
            continue_after_task_limit,
        )
    mr = min_runtime_minutes if min_runtime_minutes is not None else profile.min_runtime_minutes
    ne = no_early_success_exit or profile.no_early_success_exit
    hb = (
        profile.heartbeat_interval_minutes
        if profile.heartbeat_interval_minutes is not None
        else heartbeat_interval_minutes
    )
    cpr = continue_after_pr_limit if continue_after_pr_limit is not None else profile.continue_after_pr_limit
    ctk = (
        continue_after_task_limit if continue_after_task_limit is not None else profile.continue_after_task_limit
    )
    return mr, ne, hb, cpr, ctk


def longrun_profile_runtime_warnings(profile: DevLoopProfile | None) -> list[str]:
    if profile is None:
        return []
    warnings: list[str] = []
    if profile.min_runtime_minutes is not None and profile.min_runtime_minutes > profile.max_runtime_minutes:
        warnings.append(
            f"profile {profile.name}: min_runtime_minutes ({profile.min_runtime_minutes}) "
            f"> max_runtime_minutes ({profile.max_runtime_minutes})"
        )
    if profile.name.startswith("true_longrun_"):
        if profile.min_runtime_minutes is None:
            warnings.append(f"profile {profile.name}: missing min_runtime_minutes")
        if not profile.no_early_success_exit:
            warnings.append(f"profile {profile.name}: no_early_success_exit should be true")
    return warnings


def format_productive_longrun_preflight_notice(
    tasks: list[DevLoopTask],
    *,
    max_tasks: int,
    max_prs: int,
    min_runtime_minutes: int | None,
) -> str:
    preparable = sum(1 for t in tasks if t.prepare_for_pr)
    min_token = f"{min_runtime_minutes}m" if min_runtime_minutes else "0m"
    return (
        f"productive-longrun preflight: tasks={len(tasks)} preparable={preparable} "
        f"max_tasks={max_tasks} max_prs={max_prs} min_runtime={min_token} "
        f"note=queue may exhaust before min_runtime; runner will heartbeat after exhaustion"
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
        critical_raw = item.get("critical")
        critical = bool(critical_raw) if critical_raw is not None else None
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
                critical=critical,
                smoke_file=str(item.get("smoke_file") or item.get("change_file") or "").strip(),
                change_file=str(item.get("change_file") or item.get("smoke_file") or "").strip(),
                commit_message=str(item.get("commit_message") or "").strip(),
                prepare_for_pr=bool(item.get("prepare_for_pr", False)),
                allow_smoke_file=bool(item.get("allow_smoke_file", False)),
            )
        )
    return tasks


def _task_change_file(task: DevLoopTask) -> str:
    return (task.change_file or task.smoke_file).strip()


def _productive_task_change_file(task: DevLoopTask) -> str:
    return task.change_file.strip()


def _resolve_prepare_change_file(
    task: DevLoopTask,
    *,
    productive: bool,
) -> tuple[str, str | None]:
    if productive:
        path = _productive_task_change_file(task)
    elif task.change_file.strip():
        path = task.change_file.strip()
    elif task.allow_smoke_file and task.smoke_file.strip():
        path = task.smoke_file.strip()
    else:
        path = task.smoke_file.strip()
    if not path:
        return (
            "",
            f"missing change_file for prepare_for_pr task {task.task_id}; "
            "refusing docs/smoke.md fallback",
        )
    if (
        path in FORBIDDEN_PREPARE_CHANGE_FILES or _is_productive_fixture_change_file(path)
    ) and not task.allow_smoke_file:
        return (
            "",
            f"forbidden prepare change_file {path} for task {task.task_id}; "
            "refusing scratch fixture fallback",
        )
    return path, None


def _sanitize_branch_token(value: str) -> str:
    token = value.strip().lower()
    token = re.sub(r"[^a-z0-9]+", "-", token).strip("-")
    return token or "run"


def resolve_branch_name(template: str, run_id: str, *, task_id: str = "") -> str:
    """Expand ``{task_id}`` / ``{run_id}`` branch template placeholders to git-safe tokens."""
    text = template.strip()
    if task_id and BRANCH_TASK_ID_PLACEHOLDER in text:
        text = text.replace(BRANCH_TASK_ID_PLACEHOLDER, _sanitize_branch_token(task_id))
    if BRANCH_RUN_ID_PLACEHOLDER in text:
        text = text.replace(BRANCH_RUN_ID_PLACEHOLDER, _sanitize_branch_token(run_id))
    return text


def _resolve_task_branch(task: DevLoopTask, run_id: str) -> tuple[DevLoopTask, str]:
    template = task.branch.strip()
    resolved = resolve_branch_name(template, run_id, task_id=task.task_id)
    if resolved == template:
        return task, template
    return replace(task, branch=resolved), template


def _current_git_branch(
    *,
    repo_root: Path,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None,
) -> str:
    proc = _run_git(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        repo_root=repo_root,
        subprocess_run=subprocess_run,
    )
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def _remote_branch_exists_lsremote(
    branch: str,
    *,
    repo_root: Path,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None,
) -> bool:
    proc = _run_git(
        ["git", "ls-remote", "--heads", "origin", branch],
        repo_root=repo_root,
        subprocess_run=subprocess_run,
    )
    if proc.returncode != 0:
        return False
    return bool((proc.stdout or "").strip())


def _sanitize_git_detail(detail: str, *, limit: int = 200) -> str:
    text = detail.strip()
    for pat in (
        r"(?i)(api[_-]?key|token|secret|credential|password)\s*[=:]\s*\S+",
        r"(?i)Bearer\s+\S+",
    ):
        text = re.sub(pat, "[redacted]", text)
    return text[:limit]


def _build_prepare_preflight(
    task: DevLoopTask,
    *,
    run_id: str,
    branch_template: str,
    repo_root: Path,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None,
    base_branch: str = "main",
    changed_files: list[str] | None = None,
) -> dict[str, Any]:
    branch = task.branch.strip()
    change_file = _task_change_file(task)
    payload: dict[str, Any] = {
        "run_id": run_id,
        "task_id": task.task_id,
        "branch_template": branch_template,
        "intended_branch": branch,
        "current_branch": _current_git_branch(repo_root=repo_root, subprocess_run=subprocess_run),
        "base_branch": base_branch,
        "prepare_for_pr": task.prepare_for_pr,
        "change_file": change_file,
        "remote_branch_exists": _remote_branch_exists_lsremote(
            branch, repo_root=repo_root, subprocess_run=subprocess_run
        ),
        "commits_ahead_of_main": _commits_ahead_of_main(
            branch, repo_root=repo_root, subprocess_run=subprocess_run, base=base_branch
        ),
    }
    if changed_files is not None:
        payload["changed_files"] = changed_files
    elif change_file:
        payload["changed_files"] = [change_file]
    return payload


def _format_preparation_detail(preflight: dict[str, Any], extra: str = "") -> str:
    payload = dict(preflight)
    if extra:
        payload["detail"] = _sanitize_git_detail(extra)
    return json.dumps(payload, ensure_ascii=False)


def _run_git(
    argv: list[str],
    *,
    repo_root: Path,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None,
) -> subprocess.CompletedProcess[str]:
    runner = subprocess_run or subprocess.run
    return runner(
        argv,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )


def _branch_on_origin(branch: str, *, repo_root: Path, subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None) -> bool:
    proc = _run_git(
        ["git", "rev-parse", "--verify", f"refs/remotes/origin/{branch}"],
        repo_root=repo_root,
        subprocess_run=subprocess_run,
    )
    return proc.returncode == 0


def _commits_ahead_of_main(
    branch: str,
    *,
    repo_root: Path,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None,
    base: str = "main",
) -> int:
    if _branch_on_origin(branch, repo_root=repo_root, subprocess_run=subprocess_run):
        ref_range = f"origin/{base}..origin/{branch}"
    else:
        ref_range = f"origin/{base}..HEAD"
    proc = _run_git(
        ["git", "rev-list", "--count", ref_range],
        repo_root=repo_root,
        subprocess_run=subprocess_run,
    )
    if proc.returncode != 0:
        return 0
    try:
        return int((proc.stdout or "0").strip())
    except ValueError:
        return 0


def _check_pr_ready_preflight(
    task: DevLoopTask,
    *,
    repo_root: Path,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None,
    productive: bool = False,
) -> str | None:
    branch = task.branch.strip()
    if not branch:
        return "preflight: empty branch"
    if branch in {"main", "master"}:
        return "preflight: cannot create PR from main/master"
    if not _branch_on_origin(branch, repo_root=repo_root, subprocess_run=subprocess_run):
        return f"preflight: branch not pushed to origin: {branch}"
    ahead = _commits_ahead_of_main(branch, repo_root=repo_root, subprocess_run=subprocess_run)
    if ahead <= 0:
        return "preflight: no commits ahead of origin/main"
    if task.prepare_for_pr:
        change_file, resolve_err = _resolve_prepare_change_file(task, productive=productive)
        if resolve_err:
            return resolve_err
        if not change_file:
            return (
                f"missing change_file for prepare_for_pr task {task.task_id}; "
                "refusing docs/smoke.md fallback"
            )
    else:
        change_file = _task_change_file(task)
    if change_file and task.allowed_paths:
        if not any(_path_matches_rule(change_file, allow) for allow in task.allowed_paths):
            return f"preflight: change file outside allowed_paths: {change_file}"
    return None


def _prepare_smoke_task(
    task: DevLoopTask,
    *,
    run_id: str,
    branch_template: str,
    repo_root: Path,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None,
    execute: bool,
    productive: bool = False,
) -> tuple[bool, str, str, dict[str, Any]]:
    change_file, resolve_err = _resolve_prepare_change_file(task, productive=productive)
    preflight = _build_prepare_preflight(
        task,
        run_id=run_id,
        branch_template=branch_template,
        repo_root=repo_root,
        subprocess_run=subprocess_run,
    )
    if not task.prepare_for_pr:
        return True, "skipped", "prepare_for_pr not requested", preflight
    if resolve_err:
        return False, resolve_err, resolve_err, preflight
    if not change_file:
        msg = (
            f"missing change_file for prepare_for_pr task {task.task_id}; "
            "refusing docs/smoke.md fallback"
        )
        return False, msg, msg, preflight
    branch = task.branch.strip()
    commit_msg = (
        task.commit_message.strip()
        or f"R7.0-Ops-E6 autonomous prep ({task.task_id}, {run_id})"
    )
    plan = _format_preparation_detail(
        preflight,
        extra=f"prepare branch={branch} file={change_file} commit={commit_msg}",
    )
    if not execute:
        return True, "planned", plan, preflight
    if preflight.get("remote_branch_exists"):
        return (
            False,
            "remote_branch_exists",
            _format_preparation_detail(
                preflight,
                extra=f"origin branch already exists: {branch}",
            ),
            preflight,
        )
    target = repo_root / change_file
    target.parent.mkdir(parents=True, exist_ok=True)
    marker = _smoke_marker_line(change_file, run_id)
    if target.is_file():
        existing = target.read_text(encoding="utf-8")
        target.write_text(existing.rstrip() + marker, encoding="utf-8")
    else:
        header = (
            f"# Dev-loop marker: {task.task_id}\n"
            if productive
            else "# Dev-loop PR create smoke\n"
        )
        target.write_text(header + marker, encoding="utf-8")
    checkout = _run_git(["git", "checkout", "-B", branch], repo_root=repo_root, subprocess_run=subprocess_run)
    if checkout.returncode != 0:
        return False, "prepare_failed", _format_preparation_detail(preflight, extra="git checkout failed"), preflight
    preflight = _build_prepare_preflight(
        task,
        run_id=run_id,
        branch_template=branch_template,
        repo_root=repo_root,
        subprocess_run=subprocess_run,
    )
    add_proc = _run_git(["git", "add", change_file], repo_root=repo_root, subprocess_run=subprocess_run)
    if add_proc.returncode != 0:
        return False, "prepare_failed", _format_preparation_detail(preflight, extra="git add failed"), preflight
    commit_proc = _run_git(
        ["git", "commit", "-m", commit_msg],
        repo_root=repo_root,
        subprocess_run=subprocess_run,
    )
    if commit_proc.returncode != 0:
        detail = (commit_proc.stderr or commit_proc.stdout or "git commit failed").strip()
        if "nothing to commit" in detail.lower():
            return False, "no_diff_to_commit", _format_preparation_detail(preflight, extra=detail), preflight
        return False, "prepare_failed", _format_preparation_detail(preflight, extra=detail), preflight
    push_proc = _run_git(
        ["git", "push", "-u", "origin", branch],
        repo_root=repo_root,
        subprocess_run=subprocess_run,
    )
    if push_proc.returncode != 0:
        raw = (push_proc.stderr or push_proc.stdout or "git push failed").strip()
        detail = _sanitize_git_detail(raw)
        low = raw.lower()
        if "non-fast-forward" in low or "[rejected]" in low or "failed to push" in low:
            status = "push_rejected_non_ff"
        else:
            status = "prepare_failed"
        return False, status, _format_preparation_detail(preflight, extra=detail), preflight
    preflight = _build_prepare_preflight(
        task,
        run_id=run_id,
        branch_template=branch_template,
        repo_root=repo_root,
        subprocess_run=subprocess_run,
    )
    ready_reason = _check_pr_ready_preflight(
        task,
        repo_root=repo_root,
        subprocess_run=subprocess_run,
        productive=productive,
    )
    if ready_reason:
        return False, ready_reason, _format_preparation_detail(preflight, extra="post-prepare preflight failed"), preflight
    return True, "prepared", plan, preflight


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
            continue
        if _is_productive_scratch_dirty_path(norm):
            violations.append(f"forbidden quarantine dirty path: {norm}")
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


def _normalize_continue_after_limit(value: str | None, *, default: str = "stop") -> str:
    token = (value or default).strip().lower()
    if token not in CONTINUE_AFTER_LIMITS:
        raise ValueError(f"continue-after limit must be one of {sorted(CONTINUE_AFTER_LIMITS)}")
    return token


def _native_longrun_enabled(*, min_runtime_minutes: int | None, no_early_success_exit: bool) -> bool:
    return bool(no_early_success_exit and min_runtime_minutes is not None and min_runtime_minutes > 0)


def _elapsed_minutes_since(start_mono: float, now_fn: Callable[[], float]) -> float:
    return max(0.0, (now_fn() - start_mono) / 60.0)


def _min_runtime_satisfied(
    start_mono: float,
    min_runtime_minutes: int | None,
    now_fn: Callable[[], float],
) -> bool:
    if min_runtime_minutes is None or min_runtime_minutes <= 0:
        return False
    return _elapsed_minutes_since(start_mono, now_fn) >= float(min_runtime_minutes)


def _should_continue_after_cap(*, native_longrun: bool, continue_mode: str) -> bool:
    return native_longrun and continue_mode != "stop"


def _normalize_critical_failure_policy(value: str | None) -> str:
    token = (value or "stop").strip().lower()
    if token not in CRITICAL_FAILURE_POLICIES:
        raise ValueError(f"critical task failure policy must be one of {sorted(CRITICAL_FAILURE_POLICIES)}")
    return token


def task_is_critical(task: DevLoopTask) -> bool:
    if task.critical is not None:
        return task.critical
    level = (task.risk_level or task.risk or "low").strip().lower()
    return level in {"high", "critical"}


FAILURE_CATEGORIES: frozenset[str] = frozenset(
    {
        "pytest_failed",
        "prepare_failed",
        "pr_create_failed",
        "ci_failed",
        "unknown_task_failure",
    }
)


def normalize_failure_category(reason_code: str, *, raw_reason: str = "") -> str:
    if reason_code in {"prep_failed", "prepare_failed"}:
        return "prepare_failed"
    if reason_code in {"pr_preflight_failed", "pr_create_failed"}:
        return "pr_create_failed"
    if reason_code == "pytest_failed":
        probe = f"{raw_reason} {reason_code}".lower()
        if "pytest exit 5" in probe or (
            "exit 5" in probe and "pytest" in probe
        ):
            return "pytest_no_tests_collected"
        return "pytest_failed"
    if reason_code == "ci_failed" or "ci" in raw_reason.lower():
        return "ci_failed"
    return "unknown_task_failure"


def _gh_output_transient(text: str) -> bool:
    probe = text.lower()
    return "502" in probe or "504" in probe or "bad gateway" in probe or "gateway timeout" in probe


def _run_gh_readonly(
    argv: list[str],
    *,
    repo_root: Path,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    sleep_fn: Callable[[float], None] | None = None,
) -> tuple[int, str, str, list[str]]:
    warnings: list[str] = []
    runner = subprocess_run or subprocess.run
    sleeper = sleep_fn or time.sleep
    for attempt in range(2):
        proc = runner(
            argv,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        combined = f"{proc.stdout or ''}{proc.stderr or ''}"
        if proc.returncode == 0:
            return proc.returncode, proc.stdout or "", proc.stderr or "", warnings
        if _gh_output_transient(combined) and attempt == 0:
            warnings.append(f"gh transient error retry: {' '.join(argv)}")
            sleeper(1.0)
            continue
        return proc.returncode, proc.stdout or "", proc.stderr or "", warnings
    return 1, "", "", warnings


def _load_github_pr_index(
    *,
    repo_root: Path,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    sleep_fn: Callable[[float], None] | None = None,
    gh_list_runner: Callable[..., tuple[int, str, str, list[str]]] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    argv = [
        "gh",
        "pr",
        "list",
        "--state",
        "all",
        "--limit",
        "50",
        "--json",
        "headRefName,title,state,url",
    ]
    runner = gh_list_runner or _run_gh_readonly
    code, stdout, stderr, warnings = runner(
        argv,
        repo_root=repo_root,
        subprocess_run=subprocess_run,
        sleep_fn=sleep_fn,
    )
    if code != 0:
        detail = _sanitize_git_detail((stderr or stdout).strip() or f"exit {code}")
        warnings.append(f"gh pr list unavailable: {detail}")
        return [], warnings
    try:
        rows = json.loads(stdout or "[]")
    except json.JSONDecodeError:
        warnings.append("gh pr list returned invalid json")
        return [], warnings
    if not isinstance(rows, list):
        warnings.append("gh pr list unexpected payload")
        return [], warnings
    index: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            index.append(row)
    return index, warnings


def _pr_title_matches_task(task: DevLoopTask, title: str) -> bool:
    return task.pr_title.strip().lower() == title.strip().lower()


def _branch_matches_task_marker(task: DevLoopTask, branch: str) -> bool:
    marker = _sanitize_branch_token(task.task_id)
    normalized = branch.strip().lower()
    return marker in normalized and "dev-loop" in normalized


def _evaluate_task_skip(
    task: DevLoopTask,
    *,
    repo_root: Path,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None,
    gh_pr_index: list[dict[str, Any]],
    gh_warnings: list[str],
    completed_task_ids: set[str],
    skipped_task_ids: set[str],
    pr_created_task_ids: set[str],
) -> tuple[str, str] | None:
    if task.task_id in completed_task_ids or task.task_id in skipped_task_ids:
        return "already_processed", f"task_id={task.task_id} in current run"
    if task.task_id in pr_created_task_ids:
        return "already_processed", f"task_id={task.task_id} already has PR in run"

    branch = task.branch.strip()
    if branch:
        if _branch_on_origin(branch, repo_root=repo_root, subprocess_run=subprocess_run):
            return "existing_remote_branch", f"origin/{branch} exists"
        if _remote_branch_exists_lsremote(branch, repo_root=repo_root, subprocess_run=subprocess_run):
            return "existing_remote_branch", f"remote head exists for {branch}"

    if gh_pr_index:
        for row in gh_pr_index:
            head = str(row.get("headRefName") or "").strip()
            title = str(row.get("title") or "").strip()
            state = str(row.get("state") or "").strip().upper()
            if branch and head == branch:
                if state == "OPEN":
                    return "existing_pr", f"open PR for branch {branch}"
                return "existing_pr", f"PR state={state} for branch {branch}"
            if _pr_title_matches_task(task, title):
                return "existing_pr", f"PR title match state={state}"
            if branch and head and _branch_matches_task_marker(task, head):
                return "existing_pr", f"task branch marker match head={head}"
    elif gh_warnings:
        return None
    return None


def _record_task_skip(
    result: DevLoopResult,
    *,
    task: DevLoopTask,
    reason: str,
    detail: str,
    skipped_tasks: list[dict[str, Any]],
) -> None:
    skipped_tasks.append({"task_id": task.task_id, "reason": reason, "detail": detail})
    result.task_results.append(
        DevLoopTaskResult(
            task_id=task.task_id,
            status="skipped",
            stop_reason=reason,
            preparation_detail=detail,
        )
    )
    print(
        f"productive-longrun task skipped: task_id={task.task_id} reason={reason}",
        flush=True,
    )


def _pytest_failure_diagnostics(task: DevLoopTask, loop_res: Any) -> dict[str, Any]:
    return {
        "pytest_cmd": getattr(loop_res, "pytest_cmd", ""),
        "pytest_exit_code": getattr(loop_res, "pytest_exit_code", None),
        "change_file": _task_change_file(task),
        "output_tail": getattr(loop_res, "pytest_output_tail", ""),
    }


def _failed_task_record(
    task: DevLoopTask,
    *,
    reason: str,
    stop_reason: str,
    evidence_path: str = "",
    log_path: str = "",
    pytest_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "task_id": task.task_id,
        "title": task.pr_title,
        "reason": reason,
        "stop_reason": stop_reason,
        "critical": task_is_critical(task),
        "evidence_path": evidence_path,
        "log_path": log_path,
    }
    if pytest_diagnostics:
        record["pytest_diagnostics"] = pytest_diagnostics
    return record


def _handle_recoverable_task_failure(
    result: DevLoopResult,
    *,
    task: DevLoopTask,
    raw_reason: str,
    reason_code: str,
    failed_tasks: list[dict[str, Any]],
    continue_on_task_failure: bool,
    max_task_failures: int | None,
    critical_task_failure_policy: str,
    failure_category_counts: dict[str, int],
    max_same_failure_category: int | None = None,
    evidence_path: str = "",
    pytest_diagnostics: dict[str, Any] | None = None,
) -> bool:
    """Return True to continue the queue; False if the caller should break."""
    stop_reason = f"task_failed: {task.task_id} ({raw_reason})"
    if pytest_diagnostics and pytest_diagnostics.get("pytest_exit_code") is not None:
        print(
            "productive-longrun pytest failed: "
            f"task_id={task.task_id} exit={pytest_diagnostics.get('pytest_exit_code')} "
            f"cmd={pytest_diagnostics.get('pytest_cmd', '')}",
            flush=True,
        )
        tail = str(pytest_diagnostics.get("output_tail") or "").strip()
        if tail:
            print(f"productive-longrun pytest tail: {tail}", flush=True)
    is_critical = task_is_critical(task)
    if is_critical:
        if critical_task_failure_policy == "record":
            failed_tasks.append(
                _failed_task_record(
                    task,
                    reason=reason_code,
                    stop_reason=stop_reason,
                    evidence_path=evidence_path,
                )
            )
        result.status = "stopped"
        result.stop_reason = stop_reason
        return False
    if not continue_on_task_failure:
        result.status = "stopped"
        result.stop_reason = stop_reason
        return False

    category = normalize_failure_category(reason_code, raw_reason=raw_reason)
    failed_tasks.append(
        _failed_task_record(
            task,
            reason=category,
            stop_reason=stop_reason,
            evidence_path=evidence_path,
            pytest_diagnostics=pytest_diagnostics,
        )
    )
    failure_category_counts[category] = failure_category_counts.get(category, 0) + 1
    max_f = max_task_failures if max_task_failures is not None else 3
    print(
        f"productive-longrun task failed: task_id={task.task_id} critical=false "
        f"failed={len(failed_tasks)}/{max_f} action=continue",
        flush=True,
    )
    print(
        f"productive-longrun failure budget: failed={len(failed_tasks)}/{max_f}",
        flush=True,
    )
    if max_same_failure_category and failure_category_counts[category] >= max_same_failure_category:
        count = failure_category_counts[category]
        result.status = "stopped"
        result.stop_reason = f"max_same_failure_category reached: {category}={count}"
        print(f"PRODUCTIVE-LONGRUN-8H FAILED: {result.stop_reason}", flush=True)
        return False
    if len(failed_tasks) >= max_f:
        result.status = "stopped"
        result.stop_reason = f"max_task_failures reached: {max_f}"
        print(f"PRODUCTIVE-LONGRUN-8H FAILED: max_task_failures reached: {max_f}", flush=True)
        return False
    return True


def format_failure_summary(failed_tasks: list[dict[str, Any]]) -> str:
    if not failed_tasks:
        return "failure-summary: no recorded task failures"
    lines = ["failure-summary: recorded task failures:"]
    for item in failed_tasks:
        lines.append(
            f"- {item.get('task_id')}: {item.get('reason')} ({item.get('stop_reason')})"
        )
    return "\n".join(lines)


def _is_real_failure_stop(result: DevLoopResult) -> bool:
    if result.status == "blocked":
        return True
    if result.safety_validator_status == "failed":
        return True
    reason = result.stop_reason.strip()
    if not reason:
        return False
    if reason.startswith("min_runtime reached:"):
        return False
    if reason.startswith("max_tasks reached:") or reason.startswith("max_prs reached:"):
        return False
    if reason.startswith("max_task_failures reached:"):
        return True
    if reason.startswith("max_same_failure_category reached:"):
        return True
    return result.status == "stopped"


def dev_loop_should_exit_nonzero(result: DevLoopResult) -> bool:
    """CLI exit code: zero on successful min-runtime long-run; non-zero on real failure."""
    if result.longrun_exit_success:
        return False
    if result.status == "completed_with_failures":
        return False
    if result.stop_reason.strip().startswith("max_task_failures reached:"):
        return True
    if result.stop_reason.strip().startswith("max_same_failure_category reached:"):
        return True
    if result.status == "blocked":
        return True
    if result.status == "stopped" and result.stop_reason:
        return True
    return False


def format_longrun_heartbeat_line(
    result: DevLoopResult,
    *,
    start_mono: float,
    min_runtime_minutes: int,
    now_fn: Callable[[], float],
) -> str:
    elapsed = _elapsed_minutes_since(start_mono, now_fn)
    remaining = max(0.0, float(min_runtime_minutes) - elapsed)
    state = result.longrun_state or "heartbeat_waiting"
    return (
        f"true-longrun heartbeat: utc={_utc_now_iso()} elapsed={elapsed:.1f}m "
        f"remaining={remaining:.1f}m min_runtime={min_runtime_minutes}m "
        f"state={state} prs={result.prs_created} tasks={result.tasks_executed} "
        f"evidence={result.evidence_path}"
    )


def emit_longrun_heartbeat(
    result: DevLoopResult,
    *,
    start_mono: float,
    min_runtime_minutes: int,
    now_fn: Callable[[], float],
    emit_fn: Callable[[str], None] | None = None,
) -> None:
    line = format_longrun_heartbeat_line(
        result,
        start_mono=start_mono,
        min_runtime_minutes=min_runtime_minutes,
        now_fn=now_fn,
    )
    writer = emit_fn or (lambda text: print(text, flush=True))
    writer(line)


def _run_longrun_post_phase(
    result: DevLoopResult,
    *,
    start_mono: float,
    min_runtime_minutes: int,
    heartbeat_interval_minutes: int,
    max_runtime_minutes: int,
    cap_reached_tasks: bool,
    cap_reached_prs: bool,
    now_fn: Callable[[], float],
    sleep_fn: Callable[[float], None],
    finalize_evidence: Callable[[], None],
    longrun_evidence: dict[str, Any],
    heartbeat_emit_fn: Callable[[str], None] | None = None,
) -> None:
    deadline_mono = start_mono + float(max_runtime_minutes * 60)
    interval_secs = max(1.0, float(heartbeat_interval_minutes * 60))
    longrun_evidence["min_runtime_minutes"] = min_runtime_minutes
    longrun_evidence["no_early_success_exit"] = True
    longrun_evidence["heartbeat_interval_minutes"] = heartbeat_interval_minutes
    longrun_evidence["cap_reached"] = {"tasks": cap_reached_tasks, "prs": cap_reached_prs}

    if cap_reached_tasks or cap_reached_prs:
        result.longrun_state = "cap_reached_waiting"
        longrun_evidence["longrun_state"] = "cap_reached_waiting"
    else:
        result.longrun_state = "heartbeat_waiting"
        longrun_evidence["longrun_state"] = "heartbeat_waiting"

    result.status = "completed"
    result.stop_reason = ""

    while not _min_runtime_satisfied(start_mono, min_runtime_minutes, now_fn):
        longrun_evidence["elapsed_minutes"] = round(_elapsed_minutes_since(start_mono, now_fn), 2)
        if now_fn() >= deadline_mono:
            result.status = "stopped"
            result.stop_reason = f"max_runtime reached: {max_runtime_minutes}m"
            result.longrun_state = "controlled_stop"
            longrun_evidence["longrun_state"] = "controlled_stop"
            finalize_evidence()
            return
        result.longrun_state = "heartbeat_waiting"
        longrun_evidence["longrun_state"] = "heartbeat_waiting"
        finalize_evidence()
        emit_longrun_heartbeat(
            result,
            start_mono=start_mono,
            min_runtime_minutes=min_runtime_minutes,
            now_fn=now_fn,
            emit_fn=heartbeat_emit_fn,
        )
        remaining_min = float(min_runtime_minutes) - _elapsed_minutes_since(start_mono, now_fn)
        sleep_secs = min(interval_secs, max(0.0, remaining_min * 60.0))
        if sleep_secs <= 0:
            break
        sleep_fn(sleep_secs)

    result.status = "completed"
    result.stop_reason = f"min_runtime reached: {min_runtime_minutes}"
    result.longrun_state = "min_runtime_reached"
    result.longrun_exit_success = True
    longrun_evidence["longrun_state"] = "min_runtime_reached"
    longrun_evidence["elapsed_minutes"] = round(_elapsed_minutes_since(start_mono, now_fn), 2)
    finalize_evidence()


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
    sleep_fn: Callable[[float], None] | None = None,
    min_runtime_minutes: int | None = None,
    no_early_success_exit: bool = False,
    heartbeat_interval_minutes: int = 10,
    continue_after_pr_limit: str | None = None,
    continue_after_task_limit: str | None = None,
    heartbeat_emit_fn: Callable[[str], None] | None = None,
    continue_on_task_failure: bool = False,
    max_task_failures: int | None = None,
    critical_task_failure_policy: str = "stop",
    failure_summary: bool = False,
    max_same_failure_category: int | None = None,
    skip_existing_task_artifacts: bool = False,
    gh_list_runner: Callable[..., tuple[int, str, str, list[str]]] | None = None,
) -> DevLoopResult:
    root = repo_root or ROOT_DIR
    out_root = outputs_root or OUTPUTS_DIR
    run_id = _utc_run_id()
    out_dir = out_root / DEV_LOOP_REL_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks = _load_queue(task_queue_path)
    productive_queue = is_productive_task_queue_path(task_queue_path)
    if productive_queue:
        prepare_violations = productive_queue_prepare_violations(task_queue_path, tasks)
        scratch_violations = productive_queue_scratch_violations(tasks)
        quarantine_violations = productive_quarantine_repo_violations(
            repo_root=root,
            subprocess_run=subprocess_run,
        )
        all_violations = prepare_violations + scratch_violations + quarantine_violations
        if all_violations:
            raise ValueError("productive queue validation failed: " + "; ".join(all_violations))
    profile = _load_profile(profile_name, profile_path=profile_path) if profile_name else None
    queue_preflight_notice = ""
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
    effective_critical_policy = _normalize_critical_failure_policy(critical_task_failure_policy)
    if continue_on_task_failure and max_task_failures is None:
        max_task_failures = 3
    min_runtime_minutes, no_early_success_exit, heartbeat_interval_minutes, continue_after_pr_limit, continue_after_task_limit = (
        apply_profile_longrun_defaults(
            profile,
            min_runtime_minutes=min_runtime_minutes,
            no_early_success_exit=no_early_success_exit,
            heartbeat_interval_minutes=heartbeat_interval_minutes,
            continue_after_pr_limit=continue_after_pr_limit,
            continue_after_task_limit=continue_after_task_limit,
        )
    )
    now = monotonic_fn or time.monotonic
    sleeper = sleep_fn or time.sleep
    started_at = _utc_now_iso()
    run_start_mono = now()
    deadline = run_start_mono + float(effective_max_runtime * 60)
    continue_pr = _normalize_continue_after_limit(continue_after_pr_limit)
    continue_task = _normalize_continue_after_limit(continue_after_task_limit)
    native_longrun = _native_longrun_enabled(
        min_runtime_minutes=min_runtime_minutes,
        no_early_success_exit=no_early_success_exit,
    )
    if productive_queue:
        queue_preflight_notice = format_productive_longrun_preflight_notice(
            tasks,
            max_tasks=effective_max_tasks,
            max_prs=effective_max_prs,
            min_runtime_minutes=min_runtime_minutes,
        )
        print(queue_preflight_notice, flush=True)
    for warning in longrun_profile_runtime_warnings(profile):
        print(f"dev-loop warning: {warning}", flush=True)
    effective_runtime_warnings: list[str] = []
    if min_runtime_minutes is not None and min_runtime_minutes > effective_max_runtime:
        effective_runtime_warnings.append(
            f"effective min_runtime_minutes ({min_runtime_minutes}) "
            f"> max_runtime_minutes ({effective_max_runtime})"
        )
        print(f"dev-loop warning: {effective_runtime_warnings[-1]}", flush=True)
    cap_reached_tasks = False
    cap_reached_prs = False
    longrun_evidence: dict[str, Any] = {
        "min_runtime_minutes": min_runtime_minutes,
        "no_early_success_exit": no_early_success_exit,
        "heartbeat_interval_minutes": heartbeat_interval_minutes,
        "continue_after_pr_limit": continue_pr,
        "continue_after_task_limit": continue_task,
        "longrun_state": "",
        "cap_reached": {"tasks": False, "prs": False},
        "elapsed_minutes": 0.0,
    }
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
    result.failure_policy = {
        "continue_on_task_failure": continue_on_task_failure,
        "max_task_failures": max_task_failures,
        "failed_task_count": 0,
        "critical_failure_policy": effective_critical_policy,
    }
    failed_tasks: list[dict[str, Any]] = []
    skipped_tasks: list[dict[str, Any]] = []
    failure_category_counts: dict[str, int] = {}
    result.resume_policy = {
        "skip_existing_task_artifacts": skip_existing_task_artifacts,
        "skipped_task_count": 0,
        "gh_read_warnings": [],
    }
    result.failure_policy["max_same_failure_category"] = max_same_failure_category
    result.failure_policy["failure_category_counts"] = failure_category_counts
    gh_pr_index: list[dict[str, Any]] = []
    gh_read_warnings: list[str] = []
    superseded_tasks_map: dict[str, str] = {}
    if skip_existing_task_artifacts or productive_queue:
        superseded_tasks_map = _load_superseded_tasks()
    result.resume_policy["superseded_task_ids"] = sorted(superseded_tasks_map.keys())
    if execute_dev_loop and skip_existing_task_artifacts:
        gh_pr_index, gh_read_warnings = _load_github_pr_index(
            repo_root=root,
            subprocess_run=subprocess_run,
            sleep_fn=sleeper,
            gh_list_runner=gh_list_runner,
        )
        result.resume_policy["gh_read_warnings"] = list(gh_read_warnings)
    evidence_limits = {
        "queue_preflight_notice": queue_preflight_notice,
        "profile_runtime_warnings": longrun_profile_runtime_warnings(profile),
        "effective_runtime_warnings": effective_runtime_warnings,
        "max_runtime_minutes": effective_max_runtime,
        "max_tasks": effective_max_tasks,
        "max_prs": effective_max_prs,
        "wait_ci": effective_wait_ci,
        "ci_timeout_seconds": effective_ci_timeout,
        "ci_poll_seconds": effective_ci_poll,
        "stop_on_failure": effective_stop_on_failure,
        "stop_on_dirty_tree": effective_stop_on_dirty_tree,
    }
    evidence_pr_gate = {
        "requested": create_pr,
        "ok": pr_gate.ok,
        "missing": pr_gate.missing,
    }

    def _finalize_evidence() -> None:
        if native_longrun:
            longrun_evidence["elapsed_minutes"] = round(_elapsed_minutes_since(run_start_mono, now), 2)
            if result.longrun_state:
                longrun_evidence["longrun_state"] = result.longrun_state
            longrun_evidence["cap_reached"] = {
                "tasks": cap_reached_tasks,
                "prs": cap_reached_prs,
            }
        if not result.ended_at:
            result.ended_at = _utc_now_iso()
        result.failed_tasks = list(failed_tasks)
        result.skipped_tasks = list(skipped_tasks)
        result.failure_policy["failed_task_count"] = len(failed_tasks)
        result.failure_policy["failure_category_counts"] = dict(failure_category_counts)
        result.resume_policy["skipped_task_count"] = len(skipped_tasks)
        _write_dev_loop_evidence(
            out_dir,
            result,
            gate_missing=gate_missing if execute_dev_loop else [],
            effective_limits=evidence_limits,
            pr_create_gate_status=evidence_pr_gate,
            longrun_meta=longrun_evidence if (native_longrun or min_runtime_minutes) else None,
            failure_policy=result.failure_policy,
            failed_tasks=failed_tasks,
            skipped_tasks=skipped_tasks,
            resume_policy=result.resume_policy,
        )

    if execute_dev_loop and not gate_ok:
        result.status = "blocked"
        result.stop_reason = f"missing gate {DEV_LOOP_EXEC_ENV}=YES"
        _finalize_evidence()
        return result

    pr_runner = pr_loop_runner or run_pr_loop
    try:
        for raw_task in tasks:
            task, branch_template = _resolve_task_branch(raw_task, run_id)
            if result.tasks_executed >= effective_max_tasks:
                if _should_continue_after_cap(native_longrun=native_longrun, continue_mode=continue_task):
                    cap_reached_tasks = True
                    break
                result.status = "stopped"
                result.stop_reason = f"max_tasks reached: {effective_max_tasks}"
                break
            if result.prs_created >= effective_max_prs:
                if _should_continue_after_cap(native_longrun=native_longrun, continue_mode=continue_pr):
                    cap_reached_prs = True
                    break
                result.status = "stopped"
                result.stop_reason = f"max_prs reached: {effective_max_prs}"
                break
            if now() >= deadline:
                result.status = "stopped"
                result.stop_reason = f"max_runtime reached: {effective_max_runtime}m"
                break

            if not execute_dev_loop:
                prep_ok, prep_status, prep_detail, prep_preflight = _prepare_smoke_task(
                    task,
                    run_id=run_id,
                    branch_template=branch_template,
                    repo_root=root,
                    subprocess_run=subprocess_run,
                    execute=False,
                    productive=productive_queue,
                )
                result.tasks_executed += 1
                result.task_results.append(
                    DevLoopTaskResult(
                        task_id=task.task_id,
                        status="planned",
                        stop_reason="dry_run",
                        preparation_status=prep_status,
                        preparation_detail=prep_detail,
                        preparation_preflight=prep_preflight,
                    )
                )
                continue

            completed_task_ids = {
                tr.task_id for tr in result.task_results if tr.status == "completed"
            }
            skipped_task_ids = {item["task_id"] for item in skipped_tasks}
            pr_created_task_ids = {
                tr.task_id for tr in result.task_results if tr.pr_url
            }
            if task.task_id in superseded_tasks_map:
                _record_task_skip(
                    result,
                    task=task,
                    reason="superseded_task",
                    detail=superseded_tasks_map[task.task_id],
                    skipped_tasks=skipped_tasks,
                )
                continue

            if skip_existing_task_artifacts:
                skip_hit = _evaluate_task_skip(
                    task,
                    repo_root=root,
                    subprocess_run=subprocess_run,
                    gh_pr_index=gh_pr_index,
                    gh_warnings=gh_read_warnings,
                    completed_task_ids=completed_task_ids,
                    skipped_task_ids=skipped_task_ids,
                    pr_created_task_ids=pr_created_task_ids,
                )
                if skip_hit:
                    reason, detail = skip_hit
                    _record_task_skip(
                        result,
                        task=task,
                        reason=reason,
                        detail=detail,
                        skipped_tasks=skipped_tasks,
                    )
                    continue

            prep_ok, prep_status, prep_detail, prep_preflight = _prepare_smoke_task(
                task,
                run_id=run_id,
                branch_template=branch_template,
                repo_root=root,
                subprocess_run=subprocess_run,
                execute=True,
                productive=productive_queue,
            )
            if not prep_ok:
                result.tasks_executed += 1
                result.task_results.append(
                    DevLoopTaskResult(
                        task_id=task.task_id,
                        status="stopped",
                        stop_reason=prep_status,
                        preparation_status=prep_status,
                        preparation_detail=prep_detail,
                        preparation_preflight=prep_preflight,
                    )
                )
                if not _handle_recoverable_task_failure(
                    result,
                    task=task,
                    raw_reason=prep_status,
                    reason_code="prep_failed",
                    failed_tasks=failed_tasks,
                    continue_on_task_failure=continue_on_task_failure,
                    max_task_failures=max_task_failures,
                    critical_task_failure_policy=effective_critical_policy,
                    failure_category_counts=failure_category_counts,
                    max_same_failure_category=max_same_failure_category,
                ):
                    break
                continue

            dirty_paths = _git_status_paths(repo_root=root, subprocess_run=subprocess_run)
            result.checked_paths.extend(dirty_paths)
            dirty_violations = _has_forbidden_dirty_paths(dirty_paths)
            if productive_queue:
                dirty_violations.extend(_productive_unallowed_dirty_paths(task, dirty_paths))
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
            if effective_stop_on_dirty_tree and dirty_paths and not task.prepare_for_pr:
                result.status = "stopped"
                result.stop_reason = "dirty tree detected"
                result.safety_validator_status = "failed"
                break

            if create_pr:
                ready_reason = _check_pr_ready_preflight(
                    task,
                    repo_root=root,
                    subprocess_run=subprocess_run,
                    productive=productive_queue,
                )
                if ready_reason:
                    result.tasks_executed += 1
                    result.task_results.append(
                        DevLoopTaskResult(
                            task_id=task.task_id,
                            status="stopped",
                            stop_reason=ready_reason,
                            preparation_status=prep_status,
                            preparation_detail=prep_detail,
                            preparation_preflight=prep_preflight,
                        )
                    )
                    if not _handle_recoverable_task_failure(
                        result,
                        task=task,
                        raw_reason=ready_reason,
                        reason_code="pr_preflight_failed",
                        failed_tasks=failed_tasks,
                        continue_on_task_failure=continue_on_task_failure,
                        max_task_failures=max_task_failures,
                        critical_task_failure_policy=effective_critical_policy,
                        failure_category_counts=failure_category_counts,
                        max_same_failure_category=max_same_failure_category,
                    ):
                        break
                    continue

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
                preparation_status=prep_status,
                preparation_detail=prep_detail,
                preparation_preflight=prep_preflight,
                pr_url=loop_res.pr_url,
                ci_wait_status=loop_res.ci_wait_status,
                ci_wait_poll_count=loop_res.ci_wait_poll_count,
                pr_loop_evidence_path=loop_res.evidence_path,
            )
            result.task_results.append(task_rec)
            if loop_res.status in {"stopped", "blocked"}:
                stop_probe = (loop_res.stop_reason or "").lower()
                if loop_res.ci_wait_status and loop_res.ci_wait_status not in {"success", None}:
                    reason_code = "ci_failed"
                elif "pytest" in stop_probe:
                    reason_code = "pytest_failed"
                elif "pr create" in stop_probe or "pr_create" in stop_probe:
                    reason_code = "pr_create_failed"
                else:
                    reason_code = "task_failed"
                pytest_diag = (
                    _pytest_failure_diagnostics(task, loop_res)
                    if reason_code == "pytest_failed"
                    else None
                )
                if not _handle_recoverable_task_failure(
                    result,
                    task=task,
                    raw_reason=loop_res.stop_reason or loop_res.status,
                    reason_code=reason_code,
                    failed_tasks=failed_tasks,
                    continue_on_task_failure=continue_on_task_failure,
                    max_task_failures=max_task_failures,
                    critical_task_failure_policy=effective_critical_policy,
                    failure_category_counts=failure_category_counts,
                    max_same_failure_category=max_same_failure_category,
                    evidence_path=loop_res.evidence_path,
                    pytest_diagnostics=pytest_diag,
                ):
                    break
                continue
        if result.status == "completed" and failed_tasks:
            result.status = "completed_with_failures"
        if failure_summary and failed_tasks:
            print(format_failure_summary(failed_tasks), flush=True)
        if (
            native_longrun
            and not _is_real_failure_stop(result)
            and not _min_runtime_satisfied(run_start_mono, min_runtime_minutes, now)
        ):
            _run_longrun_post_phase(
                result,
                start_mono=run_start_mono,
                min_runtime_minutes=int(min_runtime_minutes or 0),
                heartbeat_interval_minutes=heartbeat_interval_minutes,
                max_runtime_minutes=effective_max_runtime,
                cap_reached_tasks=cap_reached_tasks,
                cap_reached_prs=cap_reached_prs,
                now_fn=now,
                sleep_fn=sleeper,
                finalize_evidence=_finalize_evidence,
                longrun_evidence=longrun_evidence,
                heartbeat_emit_fn=heartbeat_emit_fn,
            )
    finally:
        _finalize_evidence()
    return result


def _write_dev_loop_evidence(
    out_dir: Path,
    result: DevLoopResult,
    *,
    gate_missing: list[str],
    effective_limits: dict[str, Any],
    pr_create_gate_status: dict[str, Any],
    longrun_meta: dict[str, Any] | None = None,
    failure_policy: dict[str, Any] | None = None,
    failed_tasks: list[dict[str, Any]] | None = None,
    skipped_tasks: list[dict[str, Any]] | None = None,
    resume_policy: dict[str, Any] | None = None,
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
        "longrun_exit_success": result.longrun_exit_success,
    }
    if longrun_meta:
        payload["longrun"] = longrun_meta
    if failure_policy:
        payload["failure_policy"] = failure_policy
    if failed_tasks is not None:
        payload["failed_tasks"] = failed_tasks
    if skipped_tasks is not None:
        payload["skipped_tasks"] = skipped_tasks
    if resume_policy:
        payload["resume_policy"] = resume_policy
    (out_dir / "evidence_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "dev_loop_result.json").write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
