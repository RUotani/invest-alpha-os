"""Read-only operator autopilot status (reduce human terminal copy-paste)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from invis_alpha_os.config.paths import ROOT_DIR
from invis_alpha_os.operator.post_run_integrate import pr_numbers_from_evidence
from invis_alpha_os.operator.post_run_review import (
    find_latest_run_id,
    load_evidence_summary,
    resolve_productive_run_paths,
)

SECRET_PATH_FRAGMENTS = (".env", "credentials", "secret", "token")
AUTOPILOT_STATUS_SCHEMA_VERSION = "1"


@dataclass
class OpenPrSummary:
    number: int
    title: str
    state: str
    is_draft: bool
    merge_state_status: str
    head_ref: str


@dataclass
class MainCiSummary:
    status: str
    conclusion: str
    workflow_name: str
    head_branch: str
    updated_at: str
    run_id: str
    ok: bool


@dataclass
class AutopilotStatusResult:
    origin_main_sha: str
    local_branch: str
    working_tree_clean: bool
    dirty_paths_count: int
    open_pr_count: int
    redacted_dirty_paths_count: int = 0
    dirty_paths_redacted: bool = False
    safe_to_start_next_work: bool = False
    open_prs: list[OpenPrSummary] = field(default_factory=list)
    main_ci: MainCiSummary | None = None
    main_ci_ok: bool = False
    latest_run_id: str | None = None
    latest_run_stop_reason: str = ""
    latest_run_tasks: str = ""
    latest_run_prs: int = 0
    latest_pr_range: str = ""
    suggested_commands: list[str] = field(default_factory=list)
    agent_next_actions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _redact_path(path: str) -> bool:
    low = path.lower()
    return any(frag in low for frag in SECRET_PATH_FRAGMENTS)


def _sanitize_warning(msg: str) -> str:
    if "evidence not found:" in msg:
        return "evidence not found (path redacted)"
    return msg


def _escape_markdown_table_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> subprocess.CompletedProcess[str]:
    fn = runner or subprocess.run
    return fn(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def collect_origin_main_sha(
    *,
    repo_root: Path | None = None,
    git_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    fetch: bool = True,
) -> tuple[str, list[str]]:
    root = repo_root or ROOT_DIR
    warnings: list[str] = []
    if fetch:
        proc = _run(["git", "fetch", "origin", "main"], cwd=root, runner=git_runner)
        if proc.returncode != 0:
            warnings.append("git fetch origin main failed")
    proc = _run(["git", "rev-parse", "origin/main"], cwd=root, runner=git_runner)
    if proc.returncode != 0:
        return "", warnings + ["origin/main not resolved"]
    return proc.stdout.strip(), warnings


def collect_git_worktree(
    *,
    repo_root: Path | None = None,
    git_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> tuple[str, bool, int, int, bool, list[str]]:
    root = repo_root or ROOT_DIR
    warnings: list[str] = []
    branch_proc = _run(["git", "branch", "--show-current"], cwd=root, runner=git_runner)
    branch = branch_proc.stdout.strip() if branch_proc.returncode == 0 else "unknown"
    status_proc = _run(["git", "status", "--porcelain"], cwd=root, runner=git_runner)
    if status_proc.returncode != 0:
        return branch, False, 0, 0, False, warnings + ["git status failed"]
    lines = [ln for ln in status_proc.stdout.splitlines() if ln.strip()]
    dirty_count = len(lines)
    redacted_count = sum(1 for ln in lines if _redact_path(ln))
    dirty_redacted = redacted_count > 0
    if dirty_redacted:
        warnings.append("some dirty paths were redacted (secret-like path fragments)")
    clean = dirty_count == 0
    return branch, clean, dirty_count, redacted_count, dirty_redacted, warnings


def collect_open_prs(
    *,
    limit: int = 20,
    gh_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> tuple[list[OpenPrSummary], list[str]]:
    warnings: list[str] = []
    proc = _run(
        [
            "gh",
            "pr",
            "list",
            "--state",
            "open",
            "--limit",
            str(limit),
            "--json",
            "number,title,state,isDraft,mergeStateStatus,headRefName",
        ],
        runner=gh_runner,
    )
    if proc.returncode != 0:
        return [], warnings + ["gh pr list failed"]
    try:
        rows = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return [], warnings + ["gh pr list invalid json"]
    if not isinstance(rows, list):
        return [], warnings + ["gh pr list unexpected payload"]
    out: list[OpenPrSummary] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(
            OpenPrSummary(
                number=int(row["number"]),
                title=str(row.get("title") or ""),
                state=str(row.get("state") or ""),
                is_draft=bool(row.get("isDraft")),
                merge_state_status=str(row.get("mergeStateStatus") or ""),
                head_ref=str(row.get("headRefName") or ""),
            )
        )
    return out, warnings


def collect_main_ci(
    *,
    gh_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> tuple[MainCiSummary | None, list[str]]:
    warnings: list[str] = []
    proc = _run(
        [
            "gh",
            "run",
            "list",
            "--branch",
            "main",
            "--limit",
            "5",
            "--json",
            "databaseId,workflowName,status,conclusion,headBranch,updatedAt",
        ],
        runner=gh_runner,
    )
    if proc.returncode != 0:
        return None, warnings + ["gh run list --branch main failed"]
    try:
        rows = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None, warnings + ["gh run list invalid json"]
    if not isinstance(rows, list) or not rows:
        return None, warnings + ["no workflow runs on main"]
    row = rows[0] if isinstance(rows[0], dict) else {}
    conclusion = str(row.get("conclusion") or "")
    status = str(row.get("status") or "")
    ok = conclusion == "success" or (status == "completed" and conclusion == "success")
    summary = MainCiSummary(
        status=status,
        conclusion=conclusion,
        workflow_name=str(row.get("workflowName") or ""),
        head_branch=str(row.get("headBranch") or ""),
        updated_at=str(row.get("updatedAt") or ""),
        run_id=str(row.get("databaseId") or ""),
        ok=ok,
    )
    return summary, warnings


def _latest_longrun_snippet(
    run_id: str | None,
    *,
    outputs_root: Path | None = None,
) -> tuple[str, str, int, str, list[str]]:
    warnings: list[str] = []
    if not run_id:
        return "", "", 0, "", warnings
    try:
        paths = resolve_productive_run_paths(run_id, outputs_root=outputs_root)
        evidence = load_evidence_summary(paths.evidence_path)
    except ValueError as exc:
        return run_id, "", 0, "", [_sanitize_warning(str(exc))]
    stop = str(evidence.get("stop_reason") or "")
    tasks_seen = int(evidence.get("tasks_seen") or 0)
    tasks_executed = int(evidence.get("tasks_executed") or 0)
    prs = int(evidence.get("prs_created") or 0)
    task_line = f"{tasks_executed}/{tasks_seen}"
    return run_id, stop, prs, task_line, warnings


def build_suggested_commands(result: AutopilotStatusResult) -> list[str]:
    cmds: list[str] = []
    rid = result.latest_run_id
    if rid:
        cmds.append(f"operator-runner post-run-review --run-id {rid}")
        if result.latest_pr_range:
            cmds.append(
                f"operator-runner post-run-integrate --run-id {rid} "
                f"--pr-range {result.latest_pr_range} --dry-run"
            )
        else:
            cmds.append(f"operator-runner post-run-integrate --run-id {rid} --dry-run")
    cmds.append("gh pr list --state open --limit 25")
    if result.origin_main_sha:
        cmds.append("git fetch origin main && git rev-parse origin/main")
    return cmds


def build_agent_next_actions(result: AutopilotStatusResult) -> list[str]:
    actions: list[str] = []
    if not result.working_tree_clean:
        msg = "Resolve dirty working tree before new branch or longrun."
        if result.dirty_paths_redacted:
            msg += " (some paths redacted from output — do not assume clean)."
        actions.append(msg)
    if result.open_pr_count > 0:
        actions.append("Review open PRs; use post-run-integrate dry-run before merge approval.")
    elif result.safe_to_start_next_work:
        actions.append("Main CI green and tree clean — safe to plan next branch from origin/main.")
    if not result.main_ci_ok:
        actions.append("Wait for or inspect main CI before starting new productive work.")
    if result.latest_run_stop_reason.startswith("early_completion"):
        actions.append("Prior run ended early — consider I12 wave design (docs/134) before next 12h.")
    actions.append("Human retains: merge approval, high-risk gates, live HTTP/cache/Gmail.")
    return actions


def collect_autopilot_status(
    *,
    run_id: str | None = None,
    repo_root: Path | None = None,
    outputs_root: Path | None = None,
    fetch_main: bool = True,
    git_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    gh_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> AutopilotStatusResult:
    root = repo_root or ROOT_DIR
    out_root = outputs_root
    main_sha, w = collect_origin_main_sha(repo_root=root, git_runner=git_runner, fetch=fetch_main)
    branch, clean, dirty_count, redacted_dirty, dirty_redacted, w2 = collect_git_worktree(
        repo_root=root, git_runner=git_runner
    )
    open_prs, w3 = collect_open_prs(gh_runner=gh_runner)
    main_ci, w4 = collect_main_ci(gh_runner=gh_runner)
    latest = run_id or find_latest_run_id(outputs_root=out_root)
    rid, stop, prs, task_line, w5 = _latest_longrun_snippet(latest, outputs_root=out_root)
    pr_range = ""
    if latest:
        try:
            evidence = load_evidence_summary(
                resolve_productive_run_paths(latest, outputs_root=out_root).evidence_path
            )
            nums = pr_numbers_from_evidence(evidence)
            if nums:
                pr_range = f"{nums[0]}-{nums[-1]}"
        except ValueError:
            pass

    main_ci_ok = bool(main_ci and main_ci.ok)
    open_pr_count = len(open_prs)
    result = AutopilotStatusResult(
        origin_main_sha=main_sha,
        local_branch=branch,
        working_tree_clean=clean,
        dirty_paths_count=dirty_count,
        redacted_dirty_paths_count=redacted_dirty,
        dirty_paths_redacted=dirty_redacted,
        safe_to_start_next_work=clean and main_ci_ok and open_pr_count == 0,
        open_pr_count=open_pr_count,
        open_prs=open_prs,
        main_ci=main_ci,
        main_ci_ok=main_ci_ok,
        latest_run_id=rid or None,
        latest_run_stop_reason=stop,
        latest_run_tasks=task_line,
        latest_run_prs=prs,
        latest_pr_range=pr_range,
        warnings=[*w, *w2, *w3, *w4, *[_sanitize_warning(x) for x in w5]],
    )
    result.suggested_commands = build_suggested_commands(result)
    result.agent_next_actions = build_agent_next_actions(result)
    return result


def format_autopilot_status_markdown(result: AutopilotStatusResult) -> str:
    lines = [
        "# Operator autopilot status",
        "",
        "## Repository",
        f"- origin/main: `{result.origin_main_sha or '(unknown)'}`",
        f"- local branch: `{result.local_branch}`",
        f"- working tree clean: `{result.working_tree_clean}`"
        + (f" ({result.dirty_paths_count} dirty paths)" if result.dirty_paths_count else ""),
        f"- safe_to_start_next_work: `{result.safe_to_start_next_work}`",
    ]
    if result.dirty_paths_redacted:
        lines.append(
            f"- dirty paths redacted: `{result.redacted_dirty_paths_count}` "
            f"(secret-like fragments hidden from output)"
        )
    lines.extend(
        [
        "",
        "## Main CI (latest on main)",
        ]
    )
    if result.main_ci:
        ci = result.main_ci
        lines.extend(
            [
                f"- workflow: `{ci.workflow_name}`",
                f"- status: `{ci.status}` / conclusion: `{ci.conclusion}`",
                f"- updated: `{ci.updated_at}`",
                f"- ok: `{result.main_ci_ok}`",
            ]
        )
    else:
        lines.append("- (unavailable)")
    lines.extend(
        [
            "",
            "## Open PRs",
            f"- count: `{result.open_pr_count}`",
        ]
    )
    if result.open_prs:
        lines.append("")
        lines.append("| PR | merge | draft | title |")
        lines.append("|---:|---|:---:|---|")
        for pr in result.open_prs[:15]:
            lines.append(
                f"| {pr.number} | {pr.merge_state_status} | {pr.is_draft} | "
                f"{_escape_markdown_table_cell(pr.title[:60])} |"
            )
    lines.extend(
        [
            "",
            "## Latest productive longrun",
            f"- run_id: `{result.latest_run_id or '(none)'}`",
            f"- tasks: `{result.latest_run_tasks or '-'}`",
            f"- prs_created: `{result.latest_run_prs}`",
            f"- stop_reason: `{result.latest_run_stop_reason or '-'}`",
            f"- pr_range (evidence): `{result.latest_pr_range or '-'}`",
            "",
            "## Suggested commands (copy to agent)",
        ]
    )
    for cmd in result.suggested_commands:
        lines.append(f"- `{cmd}`")
    lines.extend(["", "## Agent next actions"])
    for act in result.agent_next_actions:
        lines.append(f"- {act}")
    if result.warnings:
        lines.extend(["", "## Warnings"])
        for warn in result.warnings:
            lines.append(f"- {warn}")
    lines.append("")
    return "\n".join(lines)


def format_autopilot_status_json(result: AutopilotStatusResult) -> str:
    payload: dict[str, Any] = asdict(result)
    payload["schema_version"] = AUTOPILOT_STATUS_SCHEMA_VERSION
    if result.main_ci:
        payload["main_ci"] = asdict(result.main_ci)
    payload["open_prs"] = [asdict(p) for p in result.open_prs]
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
