"""Consolidated security dashboard from audit modules."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.manual_data_discovery import build_manual_data_discovery
from invis_alpha_os.reports.manual_data_export_package import build_manual_data_export_package
from invis_alpha_os.reports.manual_file_security import scan_manual_file_security
from invis_alpha_os.security.dependency_security_audit import build_dependency_security_audit
from invis_alpha_os.security.github_actions_security_audit import build_github_actions_security_audit
from invis_alpha_os.security.github_repo_settings_checklist import build_github_repo_settings_checklist
from invis_alpha_os.security.github_settings_manual_evidence_ingest import ManualEvidenceSummary
from invis_alpha_os.security.security_leakage_audit import build_security_leakage_audit
from invis_alpha_os.security.source_generated_tracking_plan import build_source_generated_tracking_plan


@dataclass(frozen=True)
class SecurityDashboardResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_grade(
    *,
    leakage_status: str,
    actions_status: str,
    deps_status: str,
    file_intake_status: str,
    manual_check_count: int,
    tracked_reports_count: int,
    retained_secret_hit_count: int,
    manual_evidence: ManualEvidenceSummary | None = None,
) -> str:
    if file_intake_status == "rejected" or retained_secret_hit_count > 0:
        return "review_required"
    if actions_status in {"fail", "review_required"}:
        return "review_required"
    if leakage_status == "fail":
        return "review_required"
    if tracked_reports_count > 1:
        return "review_required"
    if manual_evidence is not None and manual_evidence.loaded:
        if manual_evidence.invalid_status_count > 0 or manual_evidence.validation_errors:
            return "review_required"
        if manual_evidence.manual_checks_failed > 0:
            return "review_required"
        if manual_evidence.manual_checks_not_checked > 0:
            return "pass_with_manual_checks"
        if manual_evidence.manual_checks_total > 0:
            return "pass"
    if manual_check_count > 0:
        return "pass_with_manual_checks"
    if deps_status == "inventory_only":
        return "acceptable_with_notes"
    return "pass"


def build_security_dashboard(
    *,
    source_repo_path: Path,
    reports_repo_path: Path | None,
    report_date: str,
    export_targets_csv: str = "5802,6645,5801,285A,5803",
    github_repo: str = "RUotani/invest-alpha-os",
    manual_evidence: ManualEvidenceSummary | None = None,
) -> SecurityDashboardResult:
    leakage = build_security_leakage_audit(
        source_repo_path=source_repo_path,
        reports_repo_path=reports_repo_path,
    )
    actions = build_github_actions_security_audit(repo_path=source_repo_path)
    deps = build_dependency_security_audit()
    tracking = build_source_generated_tracking_plan(source_repo_path=source_repo_path)
    settings = build_github_repo_settings_checklist(repo=github_repo, repo_root=source_repo_path)
    discovery = build_manual_data_discovery(report_date=report_date, repo_root=source_repo_path)
    export_pkg = build_manual_data_export_package(
        report_date=report_date,
        targets_csv=export_targets_csv,
    )

    file_intake_status = "not_run"
    if discovery.selected_path is not None:
        sec = scan_manual_file_security(discovery.selected_path)
        file_intake_status = sec.status

    tracked_reports_count = int(tracking.json_payload.get("tracked_reports_count", 0))
    manual_check_count = int(settings.json_payload.get("manual_check_required_count", 0))
    retained_secret_hits = len(leakage.json_payload.get("source_repo", {}).get("suspected_secret_hits", []))
    retained_secret_hits += len(leakage.json_payload.get("reports_repo", {}).get("suspected_secret_hits", []))
    suppressed_count = int(
        leakage.json_payload.get("source_repo", {}).get("suppressed_false_positive_count", 0)
    )

    grade = _resolve_grade(
        leakage_status=str(leakage.json_payload.get("overall_status", "")),
        actions_status=str(actions.json_payload.get("overall_status", "")),
        deps_status=str(deps.json_payload.get("overall_status", "")),
        file_intake_status=file_intake_status,
        manual_check_count=manual_check_count,
        tracked_reports_count=tracked_reports_count,
        retained_secret_hit_count=retained_secret_hits,
        manual_evidence=manual_evidence,
    )

    high_findings: list[dict[str, Any]] = []
    medium_findings: list[dict[str, Any]] = []
    for finding in actions.json_payload.get("findings", []):
        if finding.get("severity") == "high":
            high_findings.append(finding)
        elif finding.get("severity") == "medium":
            medium_findings.append(finding)

    remaining_risks: list[str] = []
    if manual_evidence is not None and manual_evidence.loaded and manual_evidence.manual_checks_not_checked > 0:
        remaining_risks.append("GitHub manual evidence template has unchecked items")
    elif manual_check_count > 0:
        remaining_risks.append("GitHub UI settings require manual verification")
    codeql_section: dict[str, Any] = {}
    ruleset_risk_section: dict[str, Any] = {}
    branch_bp_section: dict[str, Any] = {}
    if manual_evidence is not None and manual_evidence.source_path:
        try:
            raw = json.loads(Path(manual_evidence.source_path).read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                codeql_section = raw.get("codeql_status_evidence") or {}
                ruleset_risk_section = raw.get("ruleset_operational_risk") or {}
                branch_bp_section = raw.get("branch_protection_evidence") or {}
        except (OSError, json.JSONDecodeError):
            pass
    if ruleset_risk_section.get("solo_operation_review_required") and not ruleset_risk_section.get(
        "solo_approval_requirement_waived"
    ):
        remaining_risks.append(
            "Solo-operation ruleset risk: required PR approvals with single collaborator and no bypass actors"
        )
    if codeql_section.get("evidence_state") == "analysis_pending":
        remaining_risks.append("CodeQL default setup configured; first analysis run still pending")
    if tracked_reports_count > 1:
        remaining_risks.append("Multiple tracked reports remain in source repo")
    if not discovery.json_payload.get("safe_to_parse"):
        remaining_risks.append("Manual data files not present locally for dry-run validation")

    payload: dict[str, Any] = {
        "overall_grade": grade,
        "generated_at": _now_iso(),
        "report_date": report_date,
        "secrets_printed": False,
        "redaction_status": "all_audits_redacted",
        "high_severity_findings": high_findings,
        "medium_severity_findings": medium_findings,
        "remaining_risks": remaining_risks,
        "accepted_risks": [
            "xlsx_supported may be false without openpyxl",
            "dependency audit is inventory-only when pip-audit unavailable",
            "daily_report runs on workflow_dispatch only after remediation",
        ],
        "next_actions": [
            "Complete GitHub repo settings checklist items in browser",
            "Keep generated reports in reports-private only",
            "Place manual data files only in untracked paths",
        ],
        "github_browser_actions": settings.json_payload.get("checks", [])[:5],
        "leakage_audit": {
            "overall_status": leakage.json_payload.get("overall_status"),
            "retained_secret_hit_count": retained_secret_hits,
            "suppressed_false_positive_count": suppressed_count,
        },
        "github_actions_audit": {
            "overall_status": actions.json_payload.get("overall_status"),
            "schedule_findings": [
                f for f in actions.json_payload.get("findings", []) if f.get("code") == "schedule_trigger"
            ],
        },
        "dependency_audit": {"overall_status": deps.json_payload.get("overall_status")},
        "source_generated_tracking": {
            "tracked_reports_count": tracked_reports_count,
            "untrack_generated_count": tracking.json_payload.get("classification_counts", {}).get(
                "untrack_generated", 0
            ),
            "de_index_recommended_count": len(tracking.json_payload.get("de_index_recommended", [])),
        },
        "github_repo_settings": {
            "manual_check_required_count": manual_check_count,
        },
        "github_manual_evidence": {
            "loaded": manual_evidence.loaded if manual_evidence is not None else False,
            "source_path": manual_evidence.source_path if manual_evidence is not None else None,
            "manual_checks_total": manual_evidence.manual_checks_total if manual_evidence else 0,
            "manual_checks_passed": manual_evidence.manual_checks_passed if manual_evidence else 0,
            "manual_checks_failed": manual_evidence.manual_checks_failed if manual_evidence else 0,
            "manual_checks_not_checked": manual_evidence.manual_checks_not_checked if manual_evidence else 0,
            "manual_checks_not_available_on_plan": (
                manual_evidence.manual_checks_not_available_on_plan if manual_evidence else 0
            ),
            "manual_checks_not_applicable": manual_evidence.manual_checks_not_applicable if manual_evidence else 0,
            "invalid_status_count": manual_evidence.invalid_status_count if manual_evidence else 0,
            "validation_errors": list(manual_evidence.validation_errors) if manual_evidence else [],
        },
        "manual_data_discovery": {
            "safe_to_parse": discovery.json_payload.get("safe_to_parse"),
            "xlsx_supported": discovery.json_payload.get("xlsx_supported"),
        },
        "manual_data_export_package": {
            "targets_count": len(export_pkg.json_payload.get("required_targets", [])),
        },
        "manual_file_intake": {"status": file_intake_status},
        "branch_protection_evidence": branch_bp_section,
        "codeql_status_evidence": codeql_section,
        "ruleset_operational_risk": ruleset_risk_section,
    }
    lines = [
        "# Security Dashboard",
        "",
        f"- overall_grade: {grade}",
        "- secrets_printed: false",
        f"- leakage_status: {leakage.json_payload.get('overall_status')}",
        f"- actions_status: {actions.json_payload.get('overall_status')}",
        f"- tracked_reports_count: {tracked_reports_count}",
        f"- manual_check_required_count: {manual_check_count}",
        "",
        "## Branch protection (ruleset-aware)",
        "",
        f"- verdict: {branch_bp_section.get('verdict', 'n/a')}",
        "",
        "## CodeQL follow-up",
        "",
        f"- evidence_state: {codeql_section.get('evidence_state', 'n/a')}",
        f"- analyses_available: {codeql_section.get('analyses_available', 'n/a')}",
        "",
        "## Ruleset operational risk",
        "",
        f"- solo_operation_review_required: {ruleset_risk_section.get('solo_operation_review_required', 'n/a')}",
        "",
        "## Remaining risks",
        "",
    ]
    for risk in remaining_risks or ["none"]:
        lines.append(f"- {risk}")
    lines.append("")
    return SecurityDashboardResult(markdown_text="\n".join(lines), json_payload=payload)
