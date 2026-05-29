"""Template for recording GitHub UI manual security settings checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.security.github_settings_evidence_pack import build_github_settings_evidence_pack


MANUAL_CHECK_IDS: tuple[str, ...] = (
    "branch_protection",
    "secret_scanning",
    "push_protection",
    "dependabot_alerts",
    "dependabot_security_updates",
    "codeql",
    "actions_default_permissions",
    "codeowners",
    "security_md",
)


@dataclass(frozen=True)
class GithubSettingsManualEvidenceTemplateResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_github_settings_manual_evidence_template(
    *,
    repo: str,
    repo_root: Path,
) -> GithubSettingsManualEvidenceTemplateResult:
    evidence = build_github_settings_evidence_pack(repo=repo, repo_root=repo_root)
    checks: list[dict[str, Any]] = []
    for check_id in MANUAL_CHECK_IDS:
        checks.append(
            {
                "id": check_id,
                "manual_check_status": "not_checked",
                "notes": "",
                "checked_at": None,
            }
        )
    payload: dict[str, Any] = {
        "generated_at": _now_iso(),
        "repo": repo,
        "secrets_printed": False,
        "manual_check_status_values": [
            "not_checked",
            "checked_pass",
            "checked_fail",
            "not_available_on_plan",
            "not_applicable",
        ],
        "checks": checks,
        "evidence_pack_summary": {
            "auto_evidence_count": len(evidence.json_payload.get("auto_evidence", [])),
            "manual_ui_steps_count": len(evidence.json_payload.get("manual_ui_steps", [])),
        },
    }
    lines = [
        "# GitHub Settings Manual Evidence Template",
        "",
        f"- repo: {repo}",
        "",
        "Fill `manual_check_status` in JSON; do not paste secrets.",
        "",
        "## Browser checklist",
        "",
    ]
    for step in evidence.json_payload.get("manual_ui_steps", []):
        lines.append(f"- [ ] {step.get('checkbox', step.get('id', 'check'))}")
    lines.append("")
    return GithubSettingsManualEvidenceTemplateResult(markdown_text="\n".join(lines), json_payload=payload)
