"""CodeQL default-setup and analysis status evidence (read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

CodeqlEvidenceState = Literal[
    "default_setup_configured",
    "analysis_present",
    "analysis_pending",
    "not_configured",
    "not_available_on_plan",
    "not_checked",
]

ManualCodeqlVerdict = Literal["checked_pass", "checked_fail", "not_available_on_plan", "not_checked"]


@dataclass(frozen=True)
class CodeqlStatusEvidence:
    evidence_state: CodeqlEvidenceState
    manual_verdict: ManualCodeqlVerdict
    default_setup_state: str | None
    analyses_available: bool
    notes_redacted: str


def classify_codeql_status(
    *,
    default_setup: dict[str, Any] | None,
    analyses_http_status: int | None,
) -> CodeqlStatusEvidence:
    if default_setup is None and analyses_http_status is None:
        return CodeqlStatusEvidence(
            evidence_state="not_checked",
            manual_verdict="not_checked",
            default_setup_state=None,
            analyses_available=False,
            notes_redacted="codeql APIs unavailable",
        )

    if default_setup is None and analyses_http_status == 403:
        return CodeqlStatusEvidence(
            evidence_state="not_available_on_plan",
            manual_verdict="not_available_on_plan",
            default_setup_state=None,
            analyses_available=False,
            notes_redacted="code-scanning API forbidden (plan or scope)",
        )

    setup_state: str | None = None
    if default_setup is not None:
        setup_state = str(default_setup.get("state", "")) or None

    if setup_state in (None, "", "not-configured"):
        return CodeqlStatusEvidence(
            evidence_state="not_configured",
            manual_verdict="checked_fail",
            default_setup_state=setup_state,
            analyses_available=analyses_http_status == 200,
            notes_redacted="default-setup not configured",
        )

    analyses_present = analyses_http_status == 200
    if setup_state == "configured":
        if analyses_present:
            state: CodeqlEvidenceState = "analysis_present"
            notes = "default-setup configured; analyses present"
        else:
            state = "analysis_pending"
            notes = "default-setup configured; analyses pending (404 expected before first run)"
        return CodeqlStatusEvidence(
            evidence_state=state,
            manual_verdict="checked_pass",
            default_setup_state=setup_state,
            analyses_available=analyses_present,
            notes_redacted=notes,
        )

    return CodeqlStatusEvidence(
        evidence_state="not_checked",
        manual_verdict="not_checked",
        default_setup_state=setup_state,
        analyses_available=analyses_present,
        notes_redacted=f"unhandled default-setup state={setup_state}",
    )


def codeql_status_to_dict(evidence: CodeqlStatusEvidence) -> dict[str, Any]:
    return {
        "evidence_state": evidence.evidence_state,
        "manual_verdict": evidence.manual_verdict,
        "default_setup_state": evidence.default_setup_state,
        "analyses_available": evidence.analyses_available,
        "notes_redacted": evidence.notes_redacted,
    }
