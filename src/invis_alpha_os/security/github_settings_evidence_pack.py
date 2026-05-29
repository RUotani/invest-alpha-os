"""GitHub repository settings evidence pack (read-only, UI-oriented)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.security.github_repo_settings_checklist import build_github_repo_settings_checklist


@dataclass(frozen=True)
class GithubSettingsEvidencePackResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gh_api(path: str) -> dict[str, Any] | None:
    try:
        proc = subprocess.run(
            ["gh", "api", path],
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
    return data if isinstance(data, dict) else None


def _owner_repo(repo: str) -> tuple[str, str]:
    owner, name = repo.split("/", 1)
    return owner, name


def build_github_settings_evidence_pack(
    *,
    repo: str,
    repo_root: Path | None = None,
) -> GithubSettingsEvidencePackResult:
    root = repo_root or Path.cwd()
    checklist = build_github_repo_settings_checklist(repo=repo, repo_root=root)
    owner, name = _owner_repo(repo)

    auto_evidence: list[dict[str, Any]] = []
    manual_ui_steps: list[dict[str, Any]] = []

    repo_meta = _gh_api(f"repos/{owner}/{name}")
    if repo_meta:
        auto_evidence.append(
            {
                "id": "repo_visibility",
                "status": "observed",
                "private": bool(repo_meta.get("private")),
            }
        )

    protection = _gh_api(f"repos/{owner}/{name}/branches/main/protection")
    if protection:
        auto_evidence.append(
            {
                "id": "branch_protection_main",
                "status": "observed",
                "required_status_checks": bool(protection.get("required_status_checks")),
            }
        )
    else:
        manual_ui_steps.append(
            {
                "checkbox": "[ ] Enable branch protection on `main`",
                "path": "Settings → Branches → Branch protection rules",
            }
        )

    for step in [
        ("secret_scanning", "[ ] Enable secret scanning", "Settings → Code security and analysis"),
        ("push_protection", "[ ] Enable push protection", "Settings → Code security and analysis"),
        ("dependabot_alerts", "[ ] Enable Dependabot alerts", "Settings → Code security and analysis → Dependabot"),
        (
            "dependabot_security_updates",
            "[ ] Enable Dependabot security updates",
            "Settings → Code security and analysis → Dependabot",
        ),
        ("codeql", "[ ] Enable CodeQL / code scanning", "Settings → Code security and analysis → Code scanning"),
        (
            "actions_default_permissions",
            "[ ] Set Actions default permissions to read-only",
            "Settings → Actions → General → Workflow permissions",
        ),
        (
            "fork_pr_approval",
            "[ ] Require approval for fork PR workflows",
            "Settings → Actions → General → Fork pull request workflows",
        ),
    ]:
        manual_ui_steps.append({"id": step[0], "checkbox": step[1], "path": step[2]})

    codeowners = (root / ".github" / "CODEOWNERS").is_file() or (root / "CODEOWNERS").is_file()
    security_md = (root / "SECURITY.md").is_file()

    payload: dict[str, Any] = {
        "generated_at": _now_iso(),
        "repo": repo,
        "secrets_printed": False,
        "settings_mutated": False,
        "auto_evidence": auto_evidence,
        "manual_ui_steps": manual_ui_steps,
        "checklist": checklist.json_payload,
        "codeowners_exists": codeowners,
        "security_md_exists": security_md,
    }
    lines = [
        "# GitHub Settings Evidence Pack",
        "",
        f"- repo: {repo}",
        f"- auto_evidence_count: {len(auto_evidence)}",
        f"- manual_ui_steps_count: {len(manual_ui_steps)}",
        "",
        "## Auto evidence (gh api)",
        "",
    ]
    for item in auto_evidence:
        lines.append(f"- {item['id']}: {item.get('status', 'observed')}")
    lines.extend(["", "## Manual UI checklist", ""])
    for step in manual_ui_steps:
        lines.append(f"- {step['checkbox']} — {step['path']}")
    lines.append("")
    return GithubSettingsEvidencePackResult(markdown_text="\n".join(lines), json_payload=payload)
