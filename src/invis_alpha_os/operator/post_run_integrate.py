"""Post-run PR integration audit and guarded merge helpers (no auto-merge)."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from invis_alpha_os.operator.post_run_review import (
    load_evidence_summary,
    resolve_productive_run_paths,
)

PRODUCTIVE_PR_MERGE_ENV = "CONFIRM_PRODUCTIVE_PR_MERGE"
BLOCKED_PATH_EXACT = frozenset({"pyproject.toml", "Makefile"})
BLOCKED_PATH_PREFIXES = (".github/workflows/",)
FORBIDDEN_PRODUCT_PREFIX = "src/invis_alpha_os/"
ALLOWED_PREFIXES = ("docs/", "tests/", "scripts/", ".agent/")

RiskClass = str
Strategy = str


@dataclass
class PrAuditRecord:
    number: int
    title: str
    state: str
    is_draft: bool
    merge_state_status: str
    checks_ok: bool
    files: list[str]
    risk_class: RiskClass
    safe_auto_merge_candidate: bool
    not_safe_reason: str = ""
    head_ref: str = ""


@dataclass
class PostRunIntegrateResult:
    run_id: str
    pr_numbers: list[int]
    strategy: Strategy
    stacked_detected: bool
    dry_run: bool
    integrate_requested: bool
    integrate_executed: bool
    gate_ok: bool
    audits: list[PrAuditRecord] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    consolidation_pr_url: str = ""
    merged_prs: list[int] = field(default_factory=list)
    closed_prs: list[int] = field(default_factory=list)


def parse_pr_range(spec: str) -> list[int]:
    token = spec.strip()
    if not token:
        raise ValueError("pr-range must not be empty")
    if "-" in token and "," not in token:
        start_s, end_s = token.split("-", 1)
        start, end = int(start_s), int(end_s)
        if start > end:
            raise ValueError(f"invalid pr-range: {spec}")
        return list(range(start, end + 1))
    numbers: list[int] = []
    for part in token.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            numbers.extend(parse_pr_range(part))
        else:
            numbers.append(int(part))
    return sorted(set(numbers))


def pr_numbers_from_evidence(evidence: dict[str, Any]) -> list[int]:
    numbers: list[int] = []
    for row in evidence.get("task_results") or []:
        if not isinstance(row, dict):
            continue
        url = str(row.get("pr_url") or "").strip()
        match = re.search(r"/pull/(\d+)", url)
        if match:
            numbers.append(int(match.group(1)))
    return sorted(set(numbers))


def classify_pr_risk(files: list[str]) -> RiskClass:
    if not files:
        return "unknown"
    if any(p in BLOCKED_PATH_EXACT for p in files):
        return "workflow_or_build"
    if any(p.startswith(BLOCKED_PATH_PREFIXES) for p in files):
        return "workflow_or_build"
    if any(p.startswith(FORBIDDEN_PRODUCT_PREFIX) for p in files):
        return "product_code"
    docs_only = all(p.startswith("docs/") for p in files)
    tests_only = all(p.startswith("tests/") for p in files)
    scripts_only = all(p.startswith("scripts/") for p in files)
    agent_only = all(p.startswith(".agent/") for p in files)
    if docs_only:
        return "docs_only"
    if tests_only:
        return "tests_only"
    if scripts_only:
        return "scripts_only"
    if agent_only:
        return "agent_only"
    allowed = all(any(p.startswith(prefix) for prefix in ALLOWED_PREFIXES) for p in files)
    return "mixed_low_risk" if allowed else "dangerous"


def _checks_successful(status_check_rollup: list[Any]) -> bool:
    if not status_check_rollup:
        return False
    for item in status_check_rollup:
        if not isinstance(item, dict):
            continue
        if item.get("__typename") != "CheckRun":
            continue
        if item.get("conclusion") != "SUCCESS":
            return False
    return True


def evaluate_safe_candidate(record: PrAuditRecord) -> PrAuditRecord:
    reasons: list[str] = []
    if record.state != "OPEN":
        reasons.append(f"state={record.state}")
    if record.is_draft:
        reasons.append("isDraft")
    if record.merge_state_status != "CLEAN":
        reasons.append(f"mergeStateStatus={record.merge_state_status}")
    if not record.checks_ok:
        reasons.append("checks_not_success")
    if record.risk_class not in {"docs_only", "tests_only", "scripts_only", "agent_only", "mixed_low_risk"}:
        reasons.append(f"risk={record.risk_class}")
    safe = not reasons
    return PrAuditRecord(
        **{
            **asdict(record),
            "safe_auto_merge_candidate": safe,
            "not_safe_reason": "; ".join(reasons),
        }
    )


def audit_pr(
    number: int,
    *,
    gh_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> PrAuditRecord:
    runner = gh_runner or subprocess.run
    proc = runner(
        [
            "gh",
            "pr",
            "view",
            str(number),
            "--json",
            "number,title,state,isDraft,mergeStateStatus,headRefName,files,statusCheckRollup",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise ValueError(f"gh pr view {number} failed: {proc.stderr.strip() or proc.stdout}")
    data = json.loads(proc.stdout)
    files = [str(f.get("path", "")) for f in data.get("files") or [] if isinstance(f, dict)]
    base = PrAuditRecord(
        number=int(data["number"]),
        title=str(data.get("title") or ""),
        state=str(data.get("state") or ""),
        is_draft=bool(data.get("isDraft")),
        merge_state_status=str(data.get("mergeStateStatus") or ""),
        checks_ok=_checks_successful(data.get("statusCheckRollup") or []),
        files=files,
        risk_class=classify_pr_risk(files),
        safe_auto_merge_candidate=False,
        head_ref=str(data.get("headRefName") or ""),
    )
    return evaluate_safe_candidate(base)


def detect_stacked_pr_chain(audits: list[PrAuditRecord]) -> bool:
    if len(audits) < 2:
        return False
    prev = 0
    for row in audits:
        count = len(row.files)
        if count <= prev:
            return False
        prev = count
    return True


def choose_integration_strategy(audits: list[PrAuditRecord]) -> Strategy:
    if not audits:
        return "manual_review"
    if any(not a.safe_auto_merge_candidate for a in audits):
        return "manual_review"
    if detect_stacked_pr_chain(audits):
        return "consolidation"
    if all(a.merge_state_status == "CLEAN" for a in audits):
        return "sequential_squash"
    return "manual_review"


def format_integrate_markdown(result: PostRunIntegrateResult) -> str:
    lines = [
        f"# Post-run integrate — `{result.run_id}`",
        "",
        f"- dry_run: `{result.dry_run}`",
        f"- integrate_requested: `{result.integrate_requested}`",
        f"- integrate_executed: `{result.integrate_executed}`",
        f"- gate_ok: `{result.gate_ok}`",
        f"- pr_range: `{result.pr_numbers[0]}-{result.pr_numbers[-1]}`"
        if result.pr_numbers
        else "- pr_range: (none)",
        f"- stacked_detected: `{result.stacked_detected}`",
        f"- strategy: **{result.strategy}**",
        "",
        "## PR audit",
        "",
        "| PR | merge | checks | risk | safe | reason |",
        "|---:|---|---|---|:---:|---|",
    ]
    for a in result.audits:
        lines.append(
            f"| {a.number} | {a.merge_state_status} | "
            f"{'ok' if a.checks_ok else 'fail'} | {a.risk_class} | "
            f"{'yes' if a.safe_auto_merge_candidate else 'no'} | {a.not_safe_reason or '-'} |"
        )
    lines.append("")
    if result.actions:
        lines.append("## Actions")
        lines.extend(f"- {act}" for act in result.actions)
        lines.append("")
    if result.merged_prs:
        lines.append(f"## Merged PRs: {result.merged_prs}")
        lines.append("")
    if result.closed_prs:
        lines.append(f"## Closed PRs: {result.closed_prs}")
        lines.append("")
    if result.consolidation_pr_url:
        lines.append(f"## Consolidation PR: {result.consolidation_pr_url}")
        lines.append("")
    if result.errors:
        lines.append("## Errors")
        lines.extend(f"- {err}" for err in result.errors)
        lines.append("")
    lines.append("## Safety")
    lines.append("- No auto-merge; squash only when gated integrate runs.")
    lines.append(f"- Merge gate: `{PRODUCTIVE_PR_MERGE_ENV}=YES`")
    lines.append("")
    return "\n".join(lines)


def check_productive_pr_merge_gate() -> tuple[bool, list[str]]:
    import os

    ok = os.environ.get(PRODUCTIVE_PR_MERGE_ENV, "").strip() == "YES"
    return ok, ([] if ok else [PRODUCTIVE_PR_MERGE_ENV])


def _squash_merge_pr(
    number: int,
    *,
    gh_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> bool:
    runner = gh_runner or subprocess.run
    proc = runner(
        [
            "gh",
            "pr",
            "merge",
            str(number),
            "--squash",
            "--delete-branch=false",
            "--subject",
            f"Post-run integrate squash merge (#{number})",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def _close_pr(
    number: int,
    *,
    comment: str,
    gh_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> bool:
    runner = gh_runner or subprocess.run
    proc = runner(
        ["gh", "pr", "close", str(number), "--comment", comment],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def _fetch_pr_head_ref(
    number: int,
    *,
    git_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> str:
    runner = git_runner or subprocess.run
    proc = runner(
        ["git", "fetch", "origin", f"pull/{number}/head:refs/remotes/origin/pr-tip-{number}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git fetch pull/{number}/head failed: {proc.stderr}")
    return f"origin/pr-tip-{number}"


def _diff_paths_vs_main(
    tip_ref: str,
    *,
    git_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> list[str]:
    runner = git_runner or subprocess.run
    proc = runner(
        ["git", "diff", "--name-only", "origin/main", tip_ref],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git diff failed: {proc.stderr}")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def run_post_run_integrate(
    *,
    run_id: str | None = None,
    pr_range: str | None = None,
    outputs_root: Path | None = None,
    dry_run: bool = True,
    integrate: bool = False,
    repo_root: Path | None = None,
    gh_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    git_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> PostRunIntegrateResult:
    paths = resolve_productive_run_paths(run_id, outputs_root=outputs_root)
    evidence = load_evidence_summary(paths.evidence_path)
    pr_numbers = pr_numbers_from_evidence(evidence)
    if pr_range:
        pr_numbers = parse_pr_range(pr_range)
    elif not pr_numbers:
        raise ValueError("no PR numbers in evidence; pass --pr-range")

    audits = [audit_pr(n, gh_runner=gh_runner) for n in pr_numbers]
    stacked = detect_stacked_pr_chain(audits)
    strategy = choose_integration_strategy(audits)
    gate_ok, gate_missing = check_productive_pr_merge_gate()

    result = PostRunIntegrateResult(
        run_id=paths.run_id,
        pr_numbers=pr_numbers,
        strategy=strategy,
        stacked_detected=stacked,
        dry_run=dry_run,
        integrate_requested=integrate,
        integrate_executed=False,
        gate_ok=gate_ok,
        audits=audits,
    )

    if dry_run or not integrate:
        result.actions.append(f"dry_run audit complete; strategy={strategy}")
        if integrate and not gate_ok:
            result.errors.append(f"missing gate: {', '.join(gate_missing)}")
        return result

    if not gate_ok:
        result.errors.append(f"integrate blocked: set {PRODUCTIVE_PR_MERGE_ENV}=YES")
        return result

    result.integrate_executed = True

    if strategy == "manual_review":
        result.actions.append("manual_review_required; no merges performed")
        return result

    if strategy == "sequential_squash":
        for pr in pr_numbers:
            fresh = audit_pr(pr, gh_runner=gh_runner)
            if not fresh.safe_auto_merge_candidate or fresh.merge_state_status != "CLEAN":
                result.errors.append(f"stopped at PR #{pr}: {fresh.not_safe_reason or fresh.merge_state_status}")
                break
            if _squash_merge_pr(pr, gh_runner=gh_runner):
                result.merged_prs.append(pr)
                result.actions.append(f"squash merged PR #{pr}")
            else:
                result.errors.append(f"squash merge failed for PR #{pr}")
                break
        return result

    # consolidation: merge lowest if CLEAN alone, else open consolidation from tip
    tip = pr_numbers[-1]
    first = pr_numbers[0]
    first_audit = audit_pr(first, gh_runner=gh_runner)
    if first_audit.safe_auto_merge_candidate and first_audit.merge_state_status == "CLEAN":
        if _squash_merge_pr(first, gh_runner=gh_runner):
            result.merged_prs.append(first)
            result.actions.append(f"squash merged first PR #{first}")
        else:
            result.errors.append(f"failed to merge first PR #{first}")
            return result

    remaining = [n for n in pr_numbers if n not in result.merged_prs]
    if not remaining:
        return result

    tip_audit = audit_pr(tip, gh_runner=gh_runner)
    if not tip_audit.safe_auto_merge_candidate:
        result.errors.append(f"tip PR #{tip} not safe: {tip_audit.not_safe_reason}")
        return result

    root = repo_root
    if root is None:
        from invis_alpha_os.config.paths import ROOT_DIR

        root = ROOT_DIR

    branch_name = f"work/post-run-integrate-{paths.run_id.lower()}"
    try:
        tip_ref = _fetch_pr_head_ref(tip, git_runner=git_runner)
        paths_to_apply = _diff_paths_vs_main(tip_ref, git_runner=git_runner)
        if not paths_to_apply:
            result.actions.append("no file diff vs main; nothing to consolidate")
        else:
            runner = git_runner or subprocess.run
            for cmd in (
                ["git", "fetch", "origin", "main"],
                ["git", "switch", "-c", branch_name, "origin/main"],
            ):
                proc = runner(cmd, cwd=root, capture_output=True, text=True, check=False)
                if proc.returncode != 0 and "already exists" not in (proc.stderr or ""):
                    if cmd[1] != "switch" or proc.returncode != 0:
                        raise RuntimeError(f"{' '.join(cmd)} failed: {proc.stderr}")
            checkout_cmd = ["git", "checkout", tip_ref, "--", *paths_to_apply]
            proc = runner(checkout_cmd, cwd=root, capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                raise RuntimeError(f"checkout failed: {proc.stderr}")
            result.actions.append(
                f"consolidation branch {branch_name} prepared with {len(paths_to_apply)} paths from PR #{tip}"
            )
            result.actions.append(
                "operator must: git commit, git push, gh pr create, squash merge (no auto-merge)"
            )
    except RuntimeError as exc:
        result.errors.append(str(exc))
        return result

    for n in remaining:
        if n in result.merged_prs:
            continue
        if _close_pr(
            n,
            comment="Superseded by post-run-integrate consolidation (branch preserved).",
            gh_runner=gh_runner,
        ):
            result.closed_prs.append(n)
    return result
