"""Read-only post-run review summaries for productive longrun runs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import OUTPUTS_DIR, ROOT_DIR

DEV_LOOP_REL = Path("operator/dev_loop")
PRODUCTIVE_LOG_DIRS = (
    "productive_true_longrun_12h_v3",
    "productive_true_longrun_12h_v2",
    "productive_true_longrun_12h",
    "productive_true_longrun_8h",
)


@dataclass(frozen=True)
class ProductiveRunReviewPaths:
    run_id: str
    evidence_path: Path
    productive_log_path: Path | None
    productive_variant: str | None


def default_outputs_root() -> Path:
    return OUTPUTS_DIR


def dev_loop_evidence_path(run_id: str, *, outputs_root: Path | None = None) -> Path:
    root = outputs_root or default_outputs_root()
    return root / DEV_LOOP_REL / run_id / "evidence_summary.json"


def find_latest_run_id(*, outputs_root: Path | None = None) -> str | None:
    root = outputs_root or default_outputs_root()
    base = root / DEV_LOOP_REL
    if not base.is_dir():
        return None
    candidates = sorted(
        (p.parent.name for p in base.glob("*/evidence_summary.json") if p.is_file()),
        reverse=True,
    )
    return candidates[0] if candidates else None


def resolve_productive_run_paths(
    run_id: str | None = None,
    *,
    outputs_root: Path | None = None,
) -> ProductiveRunReviewPaths:
    root = outputs_root or default_outputs_root()
    rid = (run_id or find_latest_run_id(outputs_root=root) or "").strip()
    if not rid:
        raise ValueError("run_id not found; pass --run-id or ensure dev_loop evidence exists")
    evidence = dev_loop_evidence_path(rid, outputs_root=root)
    if not evidence.is_file():
        raise ValueError(f"evidence not found: {evidence}")
    log_path: Path | None = None
    variant: str | None = None
    for sub in PRODUCTIVE_LOG_DIRS:
        candidate = root / "operator" / sub / rid / "run.log"
        if candidate.is_file():
            log_path = candidate
            variant = sub
            break
    return ProductiveRunReviewPaths(
        run_id=rid,
        evidence_path=evidence,
        productive_log_path=log_path,
        productive_variant=variant,
    )


def load_evidence_summary(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"invalid evidence payload: {path}")
    return data


def _collect_pr_urls(evidence: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for row in evidence.get("task_results") or []:
        if not isinstance(row, dict):
            continue
        url = str(row.get("pr_url") or "").strip()
        if url and url not in urls:
            urls.append(url)
    return urls


def _skipped_summary(evidence: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for row in evidence.get("skipped_tasks") or []:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- {row.get('task_id', '?')}: {row.get('reason', '')} ({row.get('detail', '')})"
        )
    return lines


def _failed_summary(evidence: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for row in evidence.get("failed_tasks") or []:
        if not isinstance(row, dict):
            continue
        diag = row.get("pytest_diagnostics") if isinstance(row.get("pytest_diagnostics"), dict) else {}
        exit_code = diag.get("pytest_exit_code")
        extra = f" exit={exit_code}" if exit_code is not None else ""
        lines.append(f"- {row.get('task_id', '?')}: {row.get('reason', '')}{extra}")
    return lines


def _ci_summary(evidence: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for row in evidence.get("task_results") or []:
        if not isinstance(row, dict):
            continue
        status = row.get("ci_wait_status")
        if status:
            lines.append(f"- {row.get('task_id', '?')}: ci_wait_status={status}")
    return lines


def format_post_run_review_markdown(
    paths: ProductiveRunReviewPaths,
    evidence: dict[str, Any],
) -> str:
    longrun = evidence.get("longrun") if isinstance(evidence.get("longrun"), dict) else {}
    failure_policy = (
        evidence.get("failure_policy") if isinstance(evidence.get("failure_policy"), dict) else {}
    )
    resume_policy = (
        evidence.get("resume_policy") if isinstance(evidence.get("resume_policy"), dict) else {}
    )
    failed_count = len(evidence.get("failed_tasks") or [])
    skipped_count = len(evidence.get("skipped_tasks") or [])
    pr_urls = _collect_pr_urls(evidence)

    lines = [
        "## Productive longrun post-run review",
        "",
        f"- run_id: `{paths.run_id}`",
        f"- evidence: `{paths.evidence_path}`",
        f"- productive_log: `{paths.productive_log_path or 'not found'}`",
        f"- productive_variant: `{paths.productive_variant or 'unknown'}`",
        f"- status: `{evidence.get('status', '')}`",
        f"- stop_reason: `{evidence.get('stop_reason', '')}`",
        f"- longrun_exit_success: `{evidence.get('longrun_exit_success', False)}`",
        f"- longrun_state: `{longrun.get('longrun_state', '')}`",
        f"- elapsed_minutes: `{longrun.get('elapsed_minutes', '')}`",
        f"- min_runtime_minutes: `{longrun.get('min_runtime_minutes', '')}`",
        f"- tasks_seen: `{evidence.get('tasks_seen', 0)}`",
        f"- tasks_executed: `{evidence.get('tasks_executed', 0)}`",
        f"- prs_created: `{evidence.get('prs_created', 0)}`",
        f"- failed_task_count: `{failed_count}`",
        f"- skipped_task_count: `{skipped_count}`",
        "",
        "### Failure policy",
        f"- continue_on_task_failure: `{failure_policy.get('continue_on_task_failure', '')}`",
        f"- max_task_failures: `{failure_policy.get('max_task_failures', '')}`",
        f"- failure_category_counts: `{failure_policy.get('failure_category_counts', {})}`",
        "",
        "### Resume policy",
        f"- skip_existing_task_artifacts: `{resume_policy.get('skip_existing_task_artifacts', '')}`",
        f"- skipped_task_count: `{resume_policy.get('skipped_task_count', '')}`",
        "",
    ]

    failed_lines = _failed_summary(evidence)
    lines.append("### Failed tasks")
    lines.extend(failed_lines if failed_lines else ["- (none)"])
    lines.append("")

    skipped_lines = _skipped_summary(evidence)
    lines.append("### Skipped tasks")
    lines.extend(skipped_lines if skipped_lines else ["- (none)"])
    lines.append("")

    ci_lines = _ci_summary(evidence)
    lines.append("### CI (from evidence)")
    lines.extend(ci_lines if ci_lines else ["- (no ci_wait_status recorded)"])
    lines.append("")

    lines.append("### PR URLs")
    if pr_urls:
        lines.extend(f"- {url}" for url in pr_urls)
    else:
        lines.append("- (none recorded in evidence)")
    lines.append("")

    pr_numbers = sorted(
        {int(m.group(1)) for url in pr_urls for m in [re.search(r"/pull/(\d+)", url)] if m}
    )
    if pr_numbers:
        lines.append("### Suggested merge helper (human gate)")
        lines.append(
            f"`CONFIRM_PRODUCTIVE_PR_MERGE=YES bash scripts/merge_productive_prs_after_review.sh "
            f"--prs {pr_numbers[0]}-{pr_numbers[-1]}`"
        )
        lines.append("")

    lines.append("### Morning checklist")
    lines.append("1. Review this summary and evidence JSON")
    lines.append("2. `gh pr list --state open`")
    lines.append("3. Merge green PRs with gated helper (no autonomous merge)")
    lines.append("4. `git fetch origin main --prune && git checkout main && git pull`")
    lines.append("5. Confirm clean working tree before next productive run")
    lines.append("")
    return "\n".join(lines)


def build_post_run_review_markdown(
    run_id: str | None = None,
    *,
    outputs_root: Path | None = None,
) -> str:
    paths = resolve_productive_run_paths(run_id, outputs_root=outputs_root)
    evidence = load_evidence_summary(paths.evidence_path)
    return format_post_run_review_markdown(paths, evidence)
