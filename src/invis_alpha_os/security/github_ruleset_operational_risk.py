"""Read-only operational risk notes for Repository Rulesets (no settings changes)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RulesetOperationalRisk:
    solo_operation_review_required: bool
    collaborator_count: int | None
    bypass_actor_count: int
    required_approving_review_count: int
    bypass_actors_redacted: tuple[str, ...]
    manual_notes: tuple[str, ...]
    recommendations: tuple[str, ...]


def assess_ruleset_operational_risk(
    *,
    collaborator_count: int | None,
    bypass_actors: list[dict[str, Any]],
    required_approving_review_count: int,
) -> RulesetOperationalRisk:
    bypass_count = len(bypass_actors)
    bypass_labels: list[str] = []
    for actor in bypass_actors:
        actor_id = actor.get("actor_id")
        actor_type = actor.get("actor_type")
        bypass_mode = actor.get("bypass_mode")
        bypass_labels.append(f"{actor_type}:{actor_id}:{bypass_mode}")

    solo_review = (
        collaborator_count == 1
        and required_approving_review_count >= 1
        and bypass_count == 0
    )

    manual_notes: list[str] = []
    recommendations: list[str] = []

    if solo_review:
        manual_notes.append(
            "Single collaborator with required PR approvals>=1 and no ruleset bypass actors; "
            "merge may require self-approval or alternate account — confirm GitHub plan/policy."
        )
        recommendations.extend(
            [
                "Confirm whether solo maintainer can approve own PR on this repo (GitHub policy).",
                "If blocked, consider documented bypass actor or second reviewer — settings change needs approval.",
            ]
        )
    elif required_approving_review_count >= 1 and bypass_count == 0:
        manual_notes.append("PR approvals required with no ruleset bypass actors configured.")
    if bypass_count > 0:
        manual_notes.append(f"Ruleset has {bypass_count} bypass actor(s); review in GitHub UI.")

    return RulesetOperationalRisk(
        solo_operation_review_required=solo_review,
        collaborator_count=collaborator_count,
        bypass_actor_count=bypass_count,
        required_approving_review_count=required_approving_review_count,
        bypass_actors_redacted=tuple(bypass_labels),
        manual_notes=tuple(manual_notes),
        recommendations=tuple(recommendations),
    )


def ruleset_operational_risk_to_dict(risk: RulesetOperationalRisk) -> dict[str, Any]:
    return {
        "solo_operation_review_required": risk.solo_operation_review_required,
        "collaborator_count": risk.collaborator_count,
        "bypass_actor_count": risk.bypass_actor_count,
        "required_approving_review_count": risk.required_approving_review_count,
        "bypass_actors_redacted": list(risk.bypass_actors_redacted),
        "manual_notes": list(risk.manual_notes),
        "recommendations": list(risk.recommendations),
    }
