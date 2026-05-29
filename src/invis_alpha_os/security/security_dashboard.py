"""Consolidated security dashboard from audit modules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.manual_data_discovery import build_manual_data_discovery
from invis_alpha_os.reports.manual_data_export_package import build_manual_data_export_package
from invis_alpha_os.reports.manual_file_security import scan_manual_file_security
from invis_alpha_os.security.dependency_security_audit import build_dependency_security_audit
from invis_alpha_os.security.github_actions_security_audit import build_github_actions_security_audit
from invis_alpha_os.security.security_leakage_audit import build_security_leakage_audit


@dataclass(frozen=True)
class SecurityDashboardResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _grade_from_statuses(statuses: list[str]) -> str:
    if any(s == "fail" or s == "review_required" for s in statuses):
        return "review_required"
    if any(s == "inventory_only" for s in statuses):
        return "acceptable_with_notes"
    return "pass"


def build_security_dashboard(
    *,
    source_repo_path: Path,
    reports_repo_path: Path | None,
    report_date: str,
    export_targets_csv: str = "5802,6645,5801,285A,5803",
) -> SecurityDashboardResult:
    leakage = build_security_leakage_audit(
        source_repo_path=source_repo_path,
        reports_repo_path=reports_repo_path,
    )
    actions = build_github_actions_security_audit(repo_path=source_repo_path)
    deps = build_dependency_security_audit()
    discovery = build_manual_data_discovery(report_date=report_date, repo_root=source_repo_path)
    export_pkg = build_manual_data_export_package(
        report_date=report_date,
        targets_csv=export_targets_csv,
    )

    file_intake_status = "not_run"
    if discovery.selected_path is not None:
        sec = scan_manual_file_security(discovery.selected_path)
        file_intake_status = sec.status

    statuses = [
        str(leakage.json_payload.get("overall_status", "")),
        str(actions.json_payload.get("overall_status", "")),
        str(deps.json_payload.get("overall_status", "")),
        file_intake_status,
    ]
    grade = _grade_from_statuses(statuses)

    high_findings: list[dict[str, Any]] = []
    medium_findings: list[dict[str, Any]] = []
    for finding in actions.json_payload.get("findings", []):
        if finding.get("severity") == "high":
            high_findings.append(finding)
        elif finding.get("severity") == "medium":
            medium_findings.append(finding)

    payload: dict[str, Any] = {
        "overall_grade": grade,
        "generated_at": _now_iso(),
        "report_date": report_date,
        "secrets_printed": False,
        "redaction_status": "all_audits_redacted",
        "high_severity_findings": high_findings,
        "medium_severity_findings": medium_findings,
        "accepted_risks": [
            "xlsx_supported may be false without openpyxl",
            "dependency audit is inventory-only when pip-audit unavailable",
        ],
        "next_actions": [
            "Review leakage audit if overall_status is review_required",
            "Add top-level permissions to workflows if missing",
            "Place manual data files only in untracked paths",
        ],
        "github_browser_actions": [
            "Enable branch protection on main if not already",
            "Restrict GitHub Actions permissions at org/repo level",
        ],
        "leakage_audit": {"overall_status": leakage.json_payload.get("overall_status")},
        "github_actions_audit": {"overall_status": actions.json_payload.get("overall_status")},
        "dependency_audit": {"overall_status": deps.json_payload.get("overall_status")},
        "manual_data_discovery": {
            "safe_to_parse": discovery.json_payload.get("safe_to_parse"),
            "xlsx_supported": discovery.json_payload.get("xlsx_supported"),
        },
        "manual_data_export_package": {
            "targets_count": len(export_pkg.json_payload.get("targets", [])),
        },
        "manual_file_intake": {"status": file_intake_status},
    }
    lines = [
        "# Security Dashboard",
        "",
        f"- overall_grade: {grade}",
        f"- secrets_printed: false",
        f"- leakage_status: {leakage.json_payload.get('overall_status')}",
        f"- actions_status: {actions.json_payload.get('overall_status')}",
        f"- dependency_status: {deps.json_payload.get('overall_status')}",
        f"- manual_file_intake: {file_intake_status}",
        "",
        "## Next actions",
        "",
    ]
    for action in payload["next_actions"]:
        lines.append(f"- {action}")
    lines.append("")
    return SecurityDashboardResult(markdown_text="\n".join(lines), json_payload=payload)
