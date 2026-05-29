"""Template for recording GitHub UI manual security settings checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.security.github_settings_evidence_pack import build_github_settings_evidence_pack
from invis_alpha_os.security.github_settings_manual_check_ids import MANUAL_CHECK_IDS
from invis_alpha_os.security.github_settings_manual_evidence_auto_judge import (
    build_manual_evidence_json_payload,
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
    auto_judge: bool = True,
) -> GithubSettingsManualEvidenceTemplateResult:
    evidence = build_github_settings_evidence_pack(repo=repo, repo_root=repo_root)
    summary = {
        "auto_evidence_count": len(evidence.json_payload.get("auto_evidence", [])),
        "manual_ui_steps_count": len(evidence.json_payload.get("manual_ui_steps", [])),
    }

    if auto_judge:
        payload = build_manual_evidence_json_payload(
            repo=repo,
            repo_root=repo_root,
            evidence_pack_summary=summary,
        )
    else:
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
        payload = {
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
            "evidence_pack_summary": summary,
        }

    lines = [
        "# GitHub Settings Manual Evidence Template",
        "",
        f"- repo: {repo}",
        f"- auto_judgement: {payload.get('auto_judgement', False)}",
        "",
        "Fill `manual_check_status` in JSON; do not paste secrets.",
        "",
        "## Browser checklist (auto-judged when enabled)",
        "",
    ]
    for check in payload.get("checks", []):
        if not isinstance(check, dict):
            continue
        cid = check.get("id", "check")
        status = check.get("manual_check_status", "not_checked")
        lines.append(f"- [x] {cid} — **{status}**")
    lines.append("")
    if payload.get("ruleset_operational_risk"):
        risk = payload["ruleset_operational_risk"]
        lines.extend(
            [
                "## Ruleset operational risk",
                "",
                f"- solo_operation_review_required: {risk.get('solo_operation_review_required')}",
                "",
            ]
        )
    return GithubSettingsManualEvidenceTemplateResult(markdown_text="\n".join(lines), json_payload=payload)
