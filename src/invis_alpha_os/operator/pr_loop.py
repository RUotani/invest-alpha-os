"""Autonomous PR loop foundation (draft-first; no auto-merge)."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from invis_alpha_os.config.paths import OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.discovery.cross_market_contract import assert_no_forbidden_terms
from invis_alpha_os.operator.policy import GateSpec
from invis_alpha_os.operator.runner import RunState, run_operator_task
from invis_alpha_os.operator.task_spec import OperatorTaskSpec, load_operator_task

PR_LOOP_REL_ROOT = Path("operator/pr_loop")
GITHUB_PR_CREATE_ENV = "CONFIRM_GITHUB_PR_CREATE"
FORBIDDEN_GH_SUBCOMMANDS: tuple[str, ...] = ("pr merge", "pr close")


@dataclass
class PrLoopGateCheck:
    ok: bool
    missing: list[str] = field(default_factory=list)


@dataclass
class PrLoopResult:
    run_id: str
    status: str
    pr_create_mode: str
    branch: str
    pr_title: str
    pytest_cmd: str
    pytest_exit_code: int | None
    git_status_lines: list[str]
    runner_status: str | None
    runner_run_dir: str | None
    pr_body_draft_path: str
    evidence_path: str
    pr_url: str | None = None
    stop_reason: str = ""


def github_pr_create_gate() -> GateSpec:
    return GateSpec(env_var=GITHUB_PR_CREATE_ENV, required_value="YES")


def check_github_pr_create_gate() -> PrLoopGateCheck:
    gate = github_pr_create_gate()
    ok = os.environ.get(gate.env_var, "").strip() == gate.required_value
    return PrLoopGateCheck(ok=ok, missing=[] if ok else [gate.env_var])


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def assert_gh_command_allowed(argv: list[str]) -> None:
    joined = " ".join(argv).lower()
    for forbidden in FORBIDDEN_GH_SUBCOMMANDS:
        if forbidden in joined:
            raise ValueError(f"forbidden gh command: {forbidden}")
    if "gh" in argv and "merge" in argv:
        raise ValueError("forbidden gh command: merge")


def build_pr_body_draft(
    *,
    pr_title: str,
    branch: str,
    task: OperatorTaskSpec | None,
    runner_state: RunState | None,
    pytest_cmd: str,
    pytest_exit_code: int | None,
    git_status_lines: list[str],
    create_pr_requested: bool,
    gate_ok: bool,
) -> str:
    task_line = task.task_id if task else "(none)"
    runner_line = runner_state.status if runner_state else "skipped"
    pytest_line = "not run" if pytest_exit_code is None else str(pytest_exit_code)
    pr_mode = "create" if create_pr_requested and gate_ok else "draft_only"
    lines = [
        "## Summary",
        f"- PR loop draft for `{pr_title}` on branch `{branch}`",
        f"- Task: `{task_line}` · runner: `{runner_line}`",
        "",
        "## Safety",
        "- No auto-merge · no live HTTP/cache write in this loop",
        "- Observation-only outputs · not trading advice",
        "",
        "## Tests",
        f"- Command: `{pytest_cmd}`",
        f"- Exit code: `{pytest_line}`",
        "",
        "## Evidence",
        f"- Git status lines: {len(git_status_lines)}",
        f"- PR create mode: `{pr_mode}`",
        "",
        "## Not done",
        "- Automatic merge (human decision required)",
        "- Live ingest unless separately gated",
        "",
        "## Next action",
        "1. Review draft and CI",
        "2. Human merge via PR",
        "",
        "## Final report rule",
        "Return one single Markdown code block only.",
    ]
    body = "\n".join(lines)
    assert_no_forbidden_terms(body)
    return body + "\n"


def _run_pytest(
    cmd: str,
    *,
    repo_root: Path,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> int:
    runner = subprocess_run or subprocess.run
    proc = runner(
        shlex.split(cmd),
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    assert_no_forbidden_terms(combined[:5000])
    return int(proc.returncode)


def _run_git_status(
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
    return [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]


def _run_gh_pr_create(
    *,
    title: str,
    body_path: Path,
    branch: str,
    repo_root: Path,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> str:
    argv = [
        "gh",
        "pr",
        "create",
        "--title",
        title,
        "--body-file",
        str(body_path),
        "--head",
        branch,
    ]
    assert_gh_command_allowed(argv)
    runner = subprocess_run or subprocess.run
    proc = runner(
        argv,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gh pr create failed exit {proc.returncode}")
    url = (proc.stdout or "").strip()
    assert url.startswith("http"), "gh pr create did not return URL"
    return url


def run_pr_loop(
    *,
    branch: str,
    pr_title: str,
    task_path: Path | None = None,
    policy_path: Path | None = None,
    pytest_cmd: str = "pytest -q tests/test_operator_runner.py tests/test_operator_runner_gated.py tests/test_operator_runner_jquants_wiring.py",
    execute_checks: bool = False,
    create_pr: bool = False,
    repo_root: Path | None = None,
    outputs_root: Path | None = None,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> PrLoopResult:
    """Run PR loop: optional runner dry-run, optional tests/git, draft body, gated gh pr create."""
    root = repo_root or ROOT_DIR
    run_id = _utc_run_id()
    out_dir = (outputs_root or OUTPUTS_DIR) / PR_LOOP_REL_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    gate = check_github_pr_create_gate()
    task: OperatorTaskSpec | None = None
    runner_state: RunState | None = None
    runner_run_dir: Path | None = None

    if task_path is not None:
        task = load_operator_task(task_path)
        if execute_checks:
            runner_state = run_operator_task(
                task_path=task_path,
                policy_path=policy_path,
                mode="dry_run",
                repo_root=root,
                outputs_root=outputs_root,
            )
            runner_run_dir = (
                (outputs_root or OUTPUTS_DIR)
                / "operator"
                / "runner"
                / runner_state.task_id
                / runner_state.run_id
            )

    pytest_exit: int | None = None
    git_lines: list[str] = []
    if execute_checks:
        pytest_exit = _run_pytest(pytest_cmd, repo_root=root, subprocess_run=subprocess_run)
        if pytest_exit != 0:
            result = PrLoopResult(
                run_id=run_id,
                status="stopped",
                pr_create_mode="blocked",
                branch=branch,
                pr_title=pr_title,
                pytest_cmd=pytest_cmd,
                pytest_exit_code=pytest_exit,
                git_status_lines=git_lines,
                runner_status=runner_state.status if runner_state else None,
                runner_run_dir=str(runner_run_dir) if runner_run_dir else None,
                pr_body_draft_path=str(out_dir / "pr_body_draft.md"),
                evidence_path=str(out_dir / "evidence_summary.json"),
                stop_reason=f"pytest exit {pytest_exit}",
            )
            _write_pr_loop_evidence(out_dir, result, task, gate)
            return result
        git_lines = _run_git_status(repo_root=root, subprocess_run=subprocess_run)

    pr_mode = "draft_only"
    if create_pr and gate.ok and execute_checks:
        pr_mode = "create"
    elif create_pr and not gate.ok:
        pr_mode = "blocked"

    body = build_pr_body_draft(
        pr_title=pr_title,
        branch=branch,
        task=task,
        runner_state=runner_state,
        pytest_cmd=pytest_cmd,
        pytest_exit_code=pytest_exit,
        git_status_lines=git_lines,
        create_pr_requested=create_pr,
        gate_ok=gate.ok,
    )
    body_path = out_dir / "pr_body_draft.md"
    body_path.write_text(body, encoding="utf-8")

    pr_url: str | None = None
    status = "completed"
    stop_reason = ""
    if create_pr and gate.ok and execute_checks:
        pr_url = _run_gh_pr_create(
            title=pr_title,
            body_path=body_path,
            branch=branch,
            repo_root=root,
            subprocess_run=subprocess_run,
        )
    elif create_pr and not gate.ok:
        status = "blocked"
        stop_reason = f"missing gate {GITHUB_PR_CREATE_ENV}=YES"

    result = PrLoopResult(
        run_id=run_id,
        status=status,
        pr_create_mode=pr_mode,
        branch=branch,
        pr_title=pr_title,
        pytest_cmd=pytest_cmd,
        pytest_exit_code=pytest_exit,
        git_status_lines=git_lines,
        runner_status=runner_state.status if runner_state else None,
        runner_run_dir=str(runner_run_dir) if runner_run_dir else None,
        pr_body_draft_path=str(body_path),
        evidence_path=str(out_dir / "evidence_summary.json"),
        pr_url=pr_url,
        stop_reason=stop_reason,
    )
    _write_pr_loop_evidence(out_dir, result, task, gate)
    return result


def _write_pr_loop_evidence(
    out_dir: Path,
    result: PrLoopResult,
    task: OperatorTaskSpec | None,
    gate: PrLoopGateCheck,
) -> None:
    payload: dict[str, Any] = {
        "run_id": result.run_id,
        "status": result.status,
        "pr_create_mode": result.pr_create_mode,
        "branch": result.branch,
        "pr_title": result.pr_title,
        "task_id": task.task_id if task else None,
        "pytest_cmd": result.pytest_cmd,
        "pytest_exit_code": result.pytest_exit_code,
        "git_status_line_count": len(result.git_status_lines),
        "gate_ok": gate.ok,
        "gate_missing": gate.missing,
        "pr_url": result.pr_url,
        "stop_reason": result.stop_reason,
        "forbidden_auto_merge": True,
    }
    (out_dir / "evidence_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "pr_loop_result.json").write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
