from __future__ import annotations

from invis_alpha_os.security.github_ruleset_operational_risk import assess_ruleset_operational_risk


def test_solo_operation_review_required() -> None:
    risk = assess_ruleset_operational_risk(
        collaborator_count=1,
        bypass_actors=[],
        required_approving_review_count=1,
    )
    assert risk.solo_operation_review_required is True
    assert len(risk.manual_notes) >= 1


def test_not_solo_when_multiple_collaborators() -> None:
    risk = assess_ruleset_operational_risk(
        collaborator_count=2,
        bypass_actors=[],
        required_approving_review_count=1,
    )
    assert risk.solo_operation_review_required is False


def test_bypass_actors_reduce_solo_risk_flag() -> None:
    risk = assess_ruleset_operational_risk(
        collaborator_count=1,
        bypass_actors=[{"actor_type": "User", "actor_id": 1, "bypass_mode": "always"}],
        required_approving_review_count=1,
    )
    assert risk.solo_operation_review_required is False
    assert risk.bypass_actor_count == 1
