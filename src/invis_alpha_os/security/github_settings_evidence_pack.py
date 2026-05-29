"""GitHub repository settings evidence pack (read-only, UI-oriented)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.security.github_codeql_status_evidence import (
    classify_codeql_status,
    codeql_status_to_dict,
)
from invis_alpha_os.security.github_gh_client import gh_api_json, gh_api_list, gh_api_status, owner_repo
from invis_alpha_os.security.github_ruleset_branch_protection_evidence import (
    branch_protection_evidence_to_dict,
    evaluate_branch_protection_evidence,
    fetch_ruleset_payloads,
)
from invis_alpha_os.security.github_ruleset_operational_risk import (
    assess_ruleset_operational_risk,
    ruleset_operational_risk_to_dict,
)
from invis_alpha_os.security.github_repo_settings_checklist import build_github_repo_settings_checklist


@dataclass(frozen=True)
class GithubSettingsEvidencePackResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_github_settings_evidence_pack(
    *,
    repo: str,
    repo_root: Path | None = None,
) -> GithubSettingsEvidencePackResult:
    root = repo_root or Path.cwd()
    checklist = build_github_repo_settings_checklist(repo=repo, repo_root=root)
    owner, name = owner_repo(repo)

    auto_evidence: list[dict[str, Any]] = []
    manual_ui_steps: list[dict[str, Any]] = []

    repo_meta = gh_api_json(f"repos/{owner}/{name}")
    default_branch = "main"
    if repo_meta:
        default_branch = str(repo_meta.get("default_branch") or "main")
        auto_evidence.append(
            {
                "id": "repo_visibility",
                "status": "observed",
                "private": bool(repo_meta.get("private")),
            }
        )

    protection = gh_api_json(f"repos/{owner}/{name}/branches/{default_branch}/protection")
    ruleset_payloads = fetch_ruleset_payloads(repo)
    branch_evidence = evaluate_branch_protection_evidence(
        default_branch=default_branch,
        classic_protection=protection,
        ruleset_payloads=ruleset_payloads,
    )
    auto_evidence.append(
        {
            "id": "branch_protection_main",
            "status": "observed" if branch_evidence.verdict == "checked_pass" else "gap",
            "ruleset_aware": True,
            **branch_protection_evidence_to_dict(branch_evidence),
        }
    )
    if branch_evidence.verdict != "checked_pass":
        manual_ui_steps.append(
            {
                "checkbox": "[ ] Enable branch protection on `main` (classic or Repository Ruleset)",
                "path": "Settings → Rules → Rulesets or Branches",
            }
        )

    default_setup = gh_api_json(f"repos/{owner}/{name}/code-scanning/default-setup")
    analyses_status = gh_api_status(f"repos/{owner}/{name}/code-scanning/analyses")
    codeql_evidence = classify_codeql_status(
        default_setup=default_setup,
        analyses_http_status=analyses_status,
    )
    auto_evidence.append({"id": "codeql_status", **codeql_status_to_dict(codeql_evidence)})

    qualifying = branch_evidence.qualifying_ruleset
    approvals = qualifying.required_approving_review_count if qualifying else 0
    bypass_actors: list[dict[str, Any]] = []
    if qualifying is not None:
        detail = gh_api_json(f"repos/{owner}/{name}/rulesets/{qualifying.ruleset_id}")
        if detail and isinstance(detail.get("bypass_actors"), list):
            bypass_actors = [a for a in detail["bypass_actors"] if isinstance(a, dict)]
    collab_count: int | None = None
    if gh_api_status(f"repos/{owner}/{name}/collaborators") == 200:
        collab_count = len(gh_api_list(f"repos/{owner}/{name}/collaborators"))
    operational_risk = assess_ruleset_operational_risk(
        collaborator_count=collab_count,
        bypass_actors=bypass_actors,
        required_approving_review_count=approvals,
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

    if codeql_evidence.manual_verdict != "checked_pass":
        manual_ui_steps.append(
            {
                "id": "codeql",
                "checkbox": "[ ] Enable CodeQL / code scanning",
                "path": "Settings → Code security and analysis → Code scanning",
            }
        )

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
        "branch_protection_evidence": branch_protection_evidence_to_dict(branch_evidence),
        "codeql_status_evidence": codeql_status_to_dict(codeql_evidence),
        "ruleset_operational_risk": ruleset_operational_risk_to_dict(operational_risk),
    }
    lines = [
        "# GitHub Settings Evidence Pack",
        "",
        f"- repo: {repo}",
        f"- auto_evidence_count: {len(auto_evidence)}",
        f"- manual_ui_steps_count: {len(manual_ui_steps)}",
        "",
        "## Branch protection (ruleset-aware)",
        "",
        f"- verdict: {branch_evidence.verdict}",
        f"- notes: {branch_evidence.notes_redacted}",
        "",
        "## CodeQL status",
        "",
        f"- evidence_state: {codeql_evidence.evidence_state}",
        f"- manual_verdict: {codeql_evidence.manual_verdict}",
        f"- notes: {codeql_evidence.notes_redacted}",
        "",
        "## Ruleset operational risk",
        "",
        f"- solo_operation_review_required: {operational_risk.solo_operation_review_required}",
        "",
        "## Auto evidence (gh api)",
        "",
    ]
    for item in auto_evidence:
        lines.append(f"- {item['id']}: {item.get('status', item.get('evidence_state', 'observed'))}")
    lines.extend(["", "## Manual UI checklist", ""])
    for step in manual_ui_steps:
        lines.append(f"- {step['checkbox']} — {step['path']}")
    lines.append("")
    return GithubSettingsEvidencePackResult(markdown_text="\n".join(lines), json_payload=payload)
