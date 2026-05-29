from __future__ import annotations

from invis_alpha_os.security.github_ruleset_branch_protection_evidence import (
    evaluate_branch_protection_evidence,
    parse_ruleset_payload,
    ruleset_meets_pass_criteria,
)


def _ruleset_payload(
    *,
    enforcement: str = "active",
    approvals: int = 1,
    contexts: list[str] | None = None,
    strict: bool = True,
    include_default: bool = True,
    omit_rules: list[str] | None = None,
) -> dict:
    omit = set(omit_rules or [])
    rules: list[dict] = []
    if "pull_request" not in omit:
        rules.append(
            {
                "type": "pull_request",
                "parameters": {"required_approving_review_count": approvals, "allowed_merge_methods": ["squash"]},
            }
        )
    if "required_status_checks" not in omit:
        rules.append(
            {
                "type": "required_status_checks",
                "parameters": {
                    "strict_required_status_checks_policy": strict,
                    "required_status_checks": [{"context": c} for c in (contexts or ["test"])],
                },
            }
        )
    if "non_fast_forward" not in omit:
        rules.append({"type": "non_fast_forward"})
    if "deletion" not in omit:
        rules.append({"type": "deletion"})
    includes = ["~DEFAULT_BRANCH"] if include_default else ["refs/heads/develop"]
    return {
        "id": 16538941,
        "name": "main",
        "target": "branch",
        "enforcement": enforcement,
        "conditions": {"ref_name": {"include": includes, "exclude": []}},
        "rules": rules,
    }


def test_classic_protection_pass_without_ruleset() -> None:
    classic = {
        "required_status_checks": {"contexts": ["test"]},
        "required_pull_request_reviews": {"required_approving_review_count": 1},
        "allow_force_pushes": False,
    }
    evidence = evaluate_branch_protection_evidence(
        default_branch="main",
        classic_protection=classic,
        ruleset_payloads=[],
    )
    assert evidence.verdict == "checked_pass"
    assert evidence.classic_protection_sufficient is True


def test_ruleset_pass_when_classic_missing() -> None:
    evidence = evaluate_branch_protection_evidence(
        default_branch="main",
        classic_protection=None,
        ruleset_payloads=[_ruleset_payload()],
    )
    assert evidence.verdict == "checked_pass"
    assert evidence.ruleset_pass is True
    assert evidence.qualifying_ruleset is not None


def test_ruleset_fail_when_approvals_zero() -> None:
    evidence = evaluate_branch_protection_evidence(
        default_branch="main",
        classic_protection=None,
        ruleset_payloads=[_ruleset_payload(approvals=0)],
    )
    assert evidence.verdict == "checked_fail"
    assert "required_approvals_below_1" in evidence.failure_reasons


def test_ruleset_fail_when_no_status_checks() -> None:
    evidence = evaluate_branch_protection_evidence(
        default_branch="main",
        classic_protection=None,
        ruleset_payloads=[_ruleset_payload(omit_rules=["required_status_checks"])],
    )
    assert evidence.verdict == "checked_fail"


def test_ruleset_inactive_fails_without_classic() -> None:
    evidence = evaluate_branch_protection_evidence(
        default_branch="main",
        classic_protection=None,
        ruleset_payloads=[_ruleset_payload(enforcement="disabled")],
    )
    assert evidence.verdict == "checked_fail"


def test_ruleset_not_on_main_fails() -> None:
    evidence = evaluate_branch_protection_evidence(
        default_branch="main",
        classic_protection=None,
        ruleset_payloads=[_ruleset_payload(include_default=False)],
    )
    assert evidence.verdict == "checked_fail"


def test_parse_ruleset_rejects_non_branch_target() -> None:
    payload = _ruleset_payload()
    payload["target"] = "tag"
    assert parse_ruleset_payload(payload) is None


def test_ruleset_meets_pass_criteria_direct() -> None:
    parsed = parse_ruleset_payload(_ruleset_payload())
    assert parsed is not None
    ok, failures = ruleset_meets_pass_criteria(parsed, default_branch="main")
    assert ok is True
    assert failures == []
