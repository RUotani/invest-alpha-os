from __future__ import annotations

from invis_alpha_os.security.github_codeql_status_evidence import classify_codeql_status


def test_configured_with_analyses_present() -> None:
    evidence = classify_codeql_status(
        default_setup={"state": "configured"},
        analyses_http_status=200,
    )
    assert evidence.evidence_state == "analysis_present"
    assert evidence.manual_verdict == "checked_pass"
    assert evidence.analyses_available is True


def test_configured_with_analyses_404_is_pending_pass() -> None:
    evidence = classify_codeql_status(
        default_setup={"state": "configured"},
        analyses_http_status=404,
    )
    assert evidence.evidence_state == "analysis_pending"
    assert evidence.manual_verdict == "checked_pass"
    assert evidence.analyses_available is False


def test_not_configured_fails() -> None:
    evidence = classify_codeql_status(
        default_setup={"state": "not-configured"},
        analyses_http_status=404,
    )
    assert evidence.evidence_state == "not_configured"
    assert evidence.manual_verdict == "checked_fail"


def test_api_forbidden_plan_unavailable() -> None:
    evidence = classify_codeql_status(
        default_setup=None,
        analyses_http_status=403,
    )
    assert evidence.evidence_state == "not_available_on_plan"
    assert evidence.manual_verdict == "not_available_on_plan"


def test_not_checked_when_no_api_data() -> None:
    evidence = classify_codeql_status(default_setup=None, analyses_http_status=None)
    assert evidence.evidence_state == "not_checked"
    assert evidence.manual_verdict == "not_checked"
