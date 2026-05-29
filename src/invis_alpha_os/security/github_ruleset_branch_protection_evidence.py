"""Repository Ruleset-aware branch protection evidence (read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from invis_alpha_os.security.github_gh_client import gh_api_json, gh_api_list, owner_repo

BranchProtectionVerdict = Literal["checked_pass", "checked_fail", "not_checked"]


@dataclass(frozen=True)
class ParsedRuleset:
    ruleset_id: int
    name: str
    enforcement: str
    target: str
    applies_to_default_branch: bool
    rule_types: frozenset[str]
    required_approving_review_count: int
    required_status_check_contexts: tuple[str, ...]
    strict_required_status_checks_policy: bool


@dataclass(frozen=True)
class BranchProtectionEvidence:
    default_branch: str
    classic_protection_present: bool
    classic_protection_sufficient: bool
    active_rulesets: tuple[ParsedRuleset, ...]
    qualifying_ruleset: ParsedRuleset | None
    ruleset_pass: bool
    verdict: BranchProtectionVerdict
    failure_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    notes_redacted: str


def ruleset_applies_to_default_branch(conditions: dict[str, Any] | None) -> bool:
    if not conditions:
        return False
    ref_name = conditions.get("ref_name")
    if not isinstance(ref_name, dict):
        return False
    includes = ref_name.get("include")
    if not isinstance(includes, list):
        return False
    for item in includes:
        if item in ("~DEFAULT_BRANCH", "refs/heads/main"):
            return True
    return False


def parse_ruleset_payload(ruleset: dict[str, Any]) -> ParsedRuleset | None:
    target = str(ruleset.get("target", ""))
    if target != "branch":
        return None
    ruleset_id = int(ruleset.get("id", 0))
    name = str(ruleset.get("name", ""))
    enforcement = str(ruleset.get("enforcement", "")).lower()
    conditions = ruleset.get("conditions") if isinstance(ruleset.get("conditions"), dict) else {}
    applies = ruleset_applies_to_default_branch(conditions)

    rule_types: set[str] = set()
    approvals = 0
    contexts: list[str] = []
    strict = False
    rules = ruleset.get("rules")
    if isinstance(rules, list):
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            rtype = str(rule.get("type", ""))
            rule_types.add(rtype)
            params = rule.get("parameters")
            if not isinstance(params, dict):
                continue
            if rtype == "pull_request":
                approvals = int(params.get("required_approving_review_count", 0))
            elif rtype == "required_status_checks":
                strict = bool(params.get("strict_required_status_checks_policy"))
                checks = params.get("required_status_checks")
                if isinstance(checks, list):
                    for chk in checks:
                        if isinstance(chk, dict) and chk.get("context"):
                            contexts.append(str(chk["context"]))
    return ParsedRuleset(
        ruleset_id=ruleset_id,
        name=name,
        enforcement=enforcement,
        target=target,
        applies_to_default_branch=applies,
        rule_types=frozenset(rule_types),
        required_approving_review_count=approvals,
        required_status_check_contexts=tuple(contexts),
        strict_required_status_checks_policy=strict,
    )


def ruleset_meets_pass_criteria(ruleset: ParsedRuleset, *, default_branch: str) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if default_branch != "main":
        failures.append("default_branch_not_main")
    if ruleset.enforcement != "active":
        failures.append("ruleset_not_active")
    if not ruleset.applies_to_default_branch:
        failures.append("ruleset_not_on_default_branch")
    if "pull_request" not in ruleset.rule_types:
        failures.append("missing_pull_request_rule")
    if ruleset.required_approving_review_count < 1:
        failures.append("required_approvals_below_1")
    if "required_status_checks" not in ruleset.rule_types:
        failures.append("missing_required_status_checks")
    if not ruleset.required_status_check_contexts:
        failures.append("no_status_check_contexts")
    if not ruleset.strict_required_status_checks_policy:
        failures.append("strict_status_checks_disabled")
    if "non_fast_forward" not in ruleset.rule_types:
        failures.append("missing_non_fast_forward")
    if "deletion" not in ruleset.rule_types:
        failures.append("missing_deletion_rule")
    return len(failures) == 0, failures


def classic_protection_sufficient(protection: dict[str, Any] | None) -> bool:
    if not protection:
        return False
    status_checks = protection.get("required_status_checks")
    has_checks = False
    if isinstance(status_checks, dict):
        contexts = status_checks.get("contexts") or status_checks.get("checks")
        has_checks = bool(contexts)
    has_pr = protection.get("required_pull_request_reviews") is not None
    blocks_force = protection.get("allow_force_pushes") is False or protection.get("allow_force_pushes") is None
    return bool(has_checks and has_pr and blocks_force)


def evaluate_branch_protection_evidence(
    *,
    default_branch: str,
    classic_protection: dict[str, Any] | None,
    ruleset_payloads: list[dict[str, Any]],
) -> BranchProtectionEvidence:
    classic_present = classic_protection is not None
    classic_ok = classic_protection_sufficient(classic_protection)

    parsed: list[ParsedRuleset] = []
    for payload in ruleset_payloads:
        item = parse_ruleset_payload(payload)
        if item is not None:
            parsed.append(item)

    branch_target_rulesets = [r for r in parsed if r.target == "branch"]
    active_on_main = [
        r
        for r in branch_target_rulesets
        if r.enforcement == "active" and r.applies_to_default_branch
    ]
    qualifying: ParsedRuleset | None = None
    ruleset_pass = False
    all_failures: list[str] = []
    for candidate in active_on_main:
        ok, failures = ruleset_meets_pass_criteria(candidate, default_branch=default_branch)
        if ok:
            qualifying = candidate
            ruleset_pass = True
            break
        all_failures = failures

    warnings: list[str] = []
    if classic_present and ruleset_pass and qualifying is not None:
        warnings.append("classic_and_ruleset_both_present")
    if classic_present and not classic_ok and ruleset_pass:
        warnings.append("classic_insufficient_ruleset_qualifies")
    if classic_ok and not ruleset_pass and active_on_main:
        warnings.append("classic_sufficient_ruleset_does_not_qualify")

    if classic_ok or ruleset_pass:
        verdict: BranchProtectionVerdict = "checked_pass"
    elif not classic_present and not branch_target_rulesets:
        verdict = "not_checked"
    else:
        verdict = "checked_fail"

    note_parts: list[str] = []
    if classic_present:
        note_parts.append(f"classic_protection={'sufficient' if classic_ok else 'present_not_sufficient'}")
    if qualifying is not None:
        note_parts.append(
            f"ruleset={qualifying.name}(id={qualifying.ruleset_id}) "
            f"approvals={qualifying.required_approving_review_count} "
            f"checks={','.join(qualifying.required_status_check_contexts)}"
        )
    elif active_on_main:
        note_parts.append(f"active_rulesets_on_main={len(active_on_main)} none_met_criteria")
    else:
        note_parts.append("no_active_ruleset_on_default_branch")
    if warnings:
        note_parts.append(f"warnings={','.join(warnings)}")

    return BranchProtectionEvidence(
        default_branch=default_branch,
        classic_protection_present=classic_present,
        classic_protection_sufficient=classic_ok,
        active_rulesets=tuple(active_on_main),
        qualifying_ruleset=qualifying,
        ruleset_pass=ruleset_pass,
        verdict=verdict,
        failure_reasons=tuple(all_failures),
        warnings=tuple(warnings),
        notes_redacted="; ".join(note_parts),
    )


def fetch_ruleset_payloads(repo: str) -> list[dict[str, Any]]:
    owner, name = owner_repo(repo)
    summaries = gh_api_list(f"repos/{owner}/{name}/rulesets")
    payloads: list[dict[str, Any]] = []
    for summary in summaries:
        ruleset_id = summary.get("id")
        if ruleset_id is None:
            continue
        detail = gh_api_json(f"repos/{owner}/{name}/rulesets/{ruleset_id}")
        if detail is not None:
            payloads.append(detail)
    return payloads


def branch_protection_evidence_to_dict(evidence: BranchProtectionEvidence) -> dict[str, Any]:
    qualifying = evidence.qualifying_ruleset
    return {
        "default_branch": evidence.default_branch,
        "classic_protection_present": evidence.classic_protection_present,
        "classic_protection_sufficient": evidence.classic_protection_sufficient,
        "ruleset_pass": evidence.ruleset_pass,
        "verdict": evidence.verdict,
        "failure_reasons": list(evidence.failure_reasons),
        "warnings": list(evidence.warnings),
        "notes_redacted": evidence.notes_redacted,
        "qualifying_ruleset": (
            {
                "id": qualifying.ruleset_id,
                "name": qualifying.name,
                "required_approving_review_count": qualifying.required_approving_review_count,
                "required_status_check_contexts": list(qualifying.required_status_check_contexts),
                "strict_required_status_checks_policy": qualifying.strict_required_status_checks_policy,
            }
            if qualifying is not None
            else None
        ),
        "active_ruleset_count_on_main": len(evidence.active_rulesets),
    }
