"""GitHub repository settings security checklist (read-only, redacted)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GithubRepoSettingsChecklistResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gh_json(args: list[str]) -> dict[str, Any] | None:
    try:
        proc = subprocess.run(
            ["gh", *args, "--json", "name,isPrivate,defaultBranchRef,visibility"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if isinstance(data, list) and data:
        return data[0] if isinstance(data[0], dict) else None
    if isinstance(data, dict):
        return data
    return None


def _file_exists(repo_root: Path, rel: str) -> bool:
    return (repo_root / rel).is_file()


def build_github_repo_settings_checklist(
    *,
    repo: str,
    repo_root: Path | None = None,
) -> GithubRepoSettingsChecklistResult:
    root = repo_root or Path.cwd()
    meta = _gh_json(["repo", "view", repo])
    checks: list[dict[str, Any]] = []

    def add(item_id: str, status: str, note: str = "") -> None:
        checks.append({"id": item_id, "status": status, "note": note})

    if meta:
        add("repo_private", "pass" if meta.get("isPrivate") else "manual_check_required", "via gh")
        default_branch = ""
        ref = meta.get("defaultBranchRef")
        if isinstance(ref, dict):
            default_branch = str(ref.get("name", ""))
        add("default_branch", "info", default_branch or "unknown")
    else:
        add("repo_metadata", "manual_check_required", "gh repo view unavailable")

    add("branch_protection", "manual_check_required", "verify in GitHub UI")
    add("required_status_checks", "manual_check_required", "verify in GitHub UI")
    add("require_pr_before_merge", "manual_check_required", "verify in GitHub UI")
    add("dismiss_stale_reviews", "manual_check_required", "verify in GitHub UI")
    add("restrict_force_pushes", "manual_check_required", "verify in GitHub UI")
    add("secret_scanning", "manual_check_required", "Settings → Code security")
    add("push_protection", "manual_check_required", "Settings → Code security")
    add("dependabot_alerts", "manual_check_required", "Settings → Dependabot")
    add("dependabot_security_updates", "manual_check_required", "Settings → Dependabot")
    add("codeql", "manual_check_required", "Settings → Code scanning")
    add("actions_default_permissions", "manual_check_required", "Settings → Actions → General")
    add("actions_allowlist", "manual_check_required", "Settings → Actions → General")
    add("fork_pr_approval", "manual_check_required", "Settings → Actions")

    codeowners = _file_exists(root, ".github/CODEOWNERS") or _file_exists(root, "CODEOWNERS")
    security_md = _file_exists(root, "SECURITY.md")
    add("codeowners_exists", "pass" if codeowners else "review_recommended")
    add("security_md_exists", "pass" if security_md else "review_recommended")

    manual_count = sum(1 for c in checks if c["status"] == "manual_check_required")
    payload: dict[str, Any] = {
        "generated_at": _now_iso(),
        "repo": repo,
        "checks": checks,
        "manual_check_required_count": manual_count,
        "secrets_printed": False,
        "settings_mutated": False,
    }
    lines = [
        "# GitHub Repository Settings Checklist",
        "",
        f"- repo: {repo}",
        f"- manual_check_required_count: {manual_count}",
        f"- codeowners_exists: {str(codeowners).lower()}",
        f"- security_md_exists: {str(security_md).lower()}",
        "",
        "## Manual checks (browser)",
        "",
        "- Branch protection on default branch",
        "- Secret scanning + push protection",
        "- Dependabot alerts / security updates",
        "- Actions default permissions: read-only",
        "",
    ]
    return GithubRepoSettingsChecklistResult(markdown_text="\n".join(lines), json_payload=payload)
