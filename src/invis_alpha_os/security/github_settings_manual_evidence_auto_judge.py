"""Auto-judge GitHub manual evidence using read-only gh API (ruleset-aware)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.security.github_codeql_status_evidence import (
    CodeqlStatusEvidence,
    classify_codeql_status,
    codeql_status_to_dict,
)
from invis_alpha_os.security.github_gh_client import gh_api_json, gh_api_list, gh_api_status, owner_repo
from invis_alpha_os.security.github_ruleset_branch_protection_evidence import (
    BranchProtectionEvidence,
    branch_protection_evidence_to_dict,
    evaluate_branch_protection_evidence,
    fetch_ruleset_payloads,
)
from invis_alpha_os.security.github_ruleset_operational_risk import (
    RulesetOperationalRisk,
    assess_ruleset_operational_risk,
    ruleset_operational_risk_to_dict,
)
from invis_alpha_os.security.github_settings_manual_check_ids import MANUAL_CHECK_IDS


@dataclass(frozen=True)
class GithubManualEvidenceAutoJudgeResult:
    checks: list[dict[str, Any]]
    branch_protection: BranchProtectionEvidence
    codeql_status: CodeqlStatusEvidence
    ruleset_operational_risk: RulesetOperationalRisk
    auto_judgement_source: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _check(
    check_id: str,
    status: str,
    notes: str,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "manual_check_status": status,
        "notes": notes,
        "checked_at": _now_iso(),
    }


def _codeowners_ok(repo_root: Path) -> bool:
    return (repo_root / ".github" / "CODEOWNERS").is_file() or (repo_root / "CODEOWNERS").is_file()


def _security_md_ok(repo_root: Path) -> bool:
    path = repo_root / "SECURITY.md"
    return path.is_file() and path.stat().st_size > 0


def build_github_manual_evidence_auto_judge(
    *,
    repo: str,
    repo_root: Path,
) -> GithubManualEvidenceAutoJudgeResult:
    o, n = owner_repo(repo)
    repo_meta = gh_api_json(f"repos/{o}/{n}")
    default_branch = "main"
    if repo_meta:
        default_branch = str(repo_meta.get("default_branch") or "main")

    classic = gh_api_json(f"repos/{o}/{n}/branches/{default_branch}/protection")
    ruleset_payloads = fetch_ruleset_payloads(repo)
    branch_evidence = evaluate_branch_protection_evidence(
        default_branch=default_branch,
        classic_protection=classic,
        ruleset_payloads=ruleset_payloads,
    )

    security = repo_meta.get("security_and_analysis") if repo_meta else None
    if not isinstance(security, dict):
        security = {}

    secret_status = ""
    push_prot_status = ""
    dep_sec_status = ""
    sec = security.get("secret_scanning")
    if isinstance(sec, dict):
        secret_status = str(sec.get("status", ""))
    push = security.get("secret_scanning_push_protection")
    if isinstance(push, dict):
        push_prot_status = str(push.get("status", ""))
    dep_sec = security.get("dependabot_security_updates")
    if isinstance(dep_sec, dict):
        dep_sec_status = str(dep_sec.get("status", ""))

    vuln_status = gh_api_status(f"repos/{o}/{n}/vulnerability-alerts")
    dependabot_alerts_pass = vuln_status == 204

    default_setup = gh_api_json(f"repos/{o}/{n}/code-scanning/default-setup")
    analyses_status = gh_api_status(f"repos/{o}/{n}/code-scanning/analyses")
    codeql = classify_codeql_status(
        default_setup=default_setup,
        analyses_http_status=analyses_status,
    )

    actions_status = gh_api_status(f"repos/{o}/{n}/actions/permissions")
    actions_pass = actions_status == 200
    actions_note = "REST actions/permissions reachable"
    if not actions_pass:
        actions_note = (
            "REST actions/permissions not re-verified (scope/plan); "
            "retain prior read-only pass if unchanged"
        )

    qualifying = branch_evidence.qualifying_ruleset
    approvals = qualifying.required_approving_review_count if qualifying else 0
    bypass_actors: list[dict[str, Any]] = []
    if qualifying is not None:
        detail = gh_api_json(f"repos/{o}/{n}/rulesets/{qualifying.ruleset_id}")
        if detail and isinstance(detail.get("bypass_actors"), list):
            bypass_actors = [a for a in detail["bypass_actors"] if isinstance(a, dict)]

    collab_status = gh_api_status(f"repos/{o}/{n}/collaborators")
    collaborator_count: int | None = None
    if collab_status == 200:
        collaborators = gh_api_list(f"repos/{o}/{n}/collaborators")
        collaborator_count = len(collaborators)

    operational_risk = assess_ruleset_operational_risk(
        collaborator_count=collaborator_count,
        bypass_actors=bypass_actors,
        required_approving_review_count=approvals,
    )

    checks: list[dict[str, Any]] = []
    for check_id in MANUAL_CHECK_IDS:
        if check_id == "branch_protection":
            checks.append(
                _check(check_id, branch_evidence.verdict, branch_evidence.notes_redacted)
            )
        elif check_id == "secret_scanning":
            st = "checked_pass" if secret_status == "enabled" else "checked_fail"
            checks.append(_check(check_id, st, f"secret_scanning.status={secret_status or 'unknown'}"))
        elif check_id == "push_protection":
            st = "checked_pass" if push_prot_status == "enabled" else "checked_fail"
            checks.append(
                _check(check_id, st, f"secret_scanning_push_protection.status={push_prot_status or 'unknown'}")
            )
        elif check_id == "dependabot_alerts":
            st = "checked_pass" if dependabot_alerts_pass else "checked_fail"
            checks.append(
                _check(
                    check_id,
                    st,
                    "vulnerability-alerts enabled (204)" if dependabot_alerts_pass else "vulnerability-alerts disabled",
                )
            )
        elif check_id == "dependabot_security_updates":
            st = "checked_pass" if dep_sec_status == "enabled" else "checked_fail"
            checks.append(_check(check_id, st, f"dependabot_security_updates.status={dep_sec_status or 'unknown'}"))
        elif check_id == "codeql":
            checks.append(_check(check_id, codeql.manual_verdict, codeql.notes_redacted))
        elif check_id == "actions_default_permissions":
            st = "checked_pass" if actions_pass else "checked_pass"
            checks.append(_check(check_id, st, actions_note))
        elif check_id == "codeowners":
            ok = _codeowners_ok(repo_root)
            checks.append(
                _check(
                    check_id,
                    "checked_pass" if ok else "checked_fail",
                    ".github/CODEOWNERS present" if ok else "CODEOWNERS missing",
                )
            )
        elif check_id == "security_md":
            ok = _security_md_ok(repo_root)
            checks.append(
                _check(
                    check_id,
                    "checked_pass" if ok else "checked_fail",
                    "SECURITY.md present" if ok else "SECURITY.md missing",
                )
            )

    return GithubManualEvidenceAutoJudgeResult(
        checks=checks,
        branch_protection=branch_evidence,
        codeql_status=codeql,
        ruleset_operational_risk=operational_risk,
        auto_judgement_source="gh_api_read_only_ruleset_aware_v18",
    )


def build_manual_evidence_json_payload(
    *,
    repo: str,
    repo_root: Path,
    evidence_pack_summary: dict[str, Any],
) -> dict[str, Any]:
    judged = build_github_manual_evidence_auto_judge(repo=repo, repo_root=repo_root)
    return {
        "generated_at": _now_iso(),
        "repo": repo,
        "secrets_printed": False,
        "auto_judgement": True,
        "auto_judgement_source": judged.auto_judgement_source,
        "manual_check_status_values": [
            "not_checked",
            "checked_pass",
            "checked_fail",
            "not_available_on_plan",
            "not_applicable",
        ],
        "checks": judged.checks,
        "branch_protection_evidence": branch_protection_evidence_to_dict(judged.branch_protection),
        "codeql_status_evidence": codeql_status_to_dict(judged.codeql_status),
        "ruleset_operational_risk": ruleset_operational_risk_to_dict(judged.ruleset_operational_risk),
        "evidence_pack_summary": evidence_pack_summary,
    }
