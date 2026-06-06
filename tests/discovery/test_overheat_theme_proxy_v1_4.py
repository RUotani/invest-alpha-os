from __future__ import annotations

from invis_alpha_os.discovery.candidate_classifier import classify_unified_candidate_fields
from invis_alpha_os.discovery.candidate_roles import CandidateRole
from invis_alpha_os.discovery.early_discovery_score import is_hard_overheat


def test_ret_20d_70_percent_triggers_hard_overheat() -> None:
    assert is_hard_overheat(ret_20d=0.70, ret_60d=None) is True


def test_unified_fields_285a_not_early_discovery() -> None:
    result = classify_unified_candidate_fields(
        instrument_id="285A",
        return_20d=0.732,
        return_60d=1.752,
        categories=("rapid_mover", "overheated_caution"),
        labels=("overheat_caution",),
    )
    assert result.early_discovery is False
    assert result.role in {CandidateRole.THEME_PROXY, CandidateRole.DO_NOT_CHASE}
