"""GitHub Actions workflow security audit (read-only, redacted)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GithubActionsSecurityAuditResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_workflow(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    uses_refs = re.findall(r"uses:\s*([^\s]+)", text)
    secret_refs = re.findall(r"secrets\.([A-Z0-9_]+)", text)
    has_schedule = "schedule:" in text
    top_permissions = re.search(r"^permissions:\s*$", text, re.MULTILINE) is not None
    contents_write = "contents: write" in text or "contents:write" in text
    return {
        "file": str(path.relative_to(path.parents[2]) if len(path.parts) > 2 else path.name),
        "uses_count": len(uses_refs),
        "uses_refs": uses_refs[:20],
        "unpinned_uses": [u for u in uses_refs if "@" in u and not re.match(r".+@[0-9a-f]{40}$", u)],
        "secret_refs": secret_refs,
        "has_schedule": has_schedule,
        "top_level_permissions": top_permissions,
        "contents_write": contents_write,
    }


def build_github_actions_security_audit(*, repo_path: Path) -> GithubActionsSecurityAuditResult:
    workflows_dir = repo_path / ".github" / "workflows"
    workflows: list[dict[str, Any]] = []
    if workflows_dir.is_dir():
        for wf in sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml")):
            workflows.append(_parse_workflow(wf))

    findings: list[dict[str, Any]] = []
    for wf in workflows:
        if wf.get("has_schedule"):
            findings.append({"severity": "medium", "code": "schedule_trigger", "workflow": wf["file"]})
        if wf.get("contents_write"):
            findings.append({"severity": "medium", "code": "contents_write", "workflow": wf["file"]})
        if wf.get("secret_refs"):
            findings.append(
                {
                    "severity": "low",
                    "code": "secrets_reference",
                    "workflow": wf["file"],
                    "secret_names": wf["secret_refs"],
                }
            )
        for uses in wf.get("unpinned_uses", []):
            findings.append({"severity": "low", "code": "unpinned_action_ref", "workflow": wf["file"], "uses": uses})

    overall = "pass" if not any(f["severity"] == "high" for f in findings) else "review_required"
    if any(f["severity"] == "medium" for f in findings):
        overall = "review_required"

    payload = {
        "overall_status": overall,
        "generated_at": _now_iso(),
        "workflow_count": len(workflows),
        "workflows": workflows,
        "findings": findings,
        "secrets_printed": False,
        "recommended_hardening": [
            "Add top-level permissions: contents: read",
            "Avoid schedule triggers unless required",
            "Pin third-party actions to commit SHA when feasible",
        ],
    }
    lines = [
        "# GitHub Actions Security Audit",
        "",
        f"- overall_status: {overall}",
        f"- workflow_count: {len(workflows)}",
        f"- finding_count: {len(findings)}",
        "",
    ]
    return GithubActionsSecurityAuditResult(markdown_text="\n".join(lines), json_payload=payload)
