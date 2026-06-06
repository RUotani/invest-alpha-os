"""Candidate phase and role taxonomy for v1.4 Early Discovery pivot."""

from __future__ import annotations

from enum import Enum


class CandidatePhase(str, Enum):
    EARLY = "early"
    ACCEL = "accel"
    OVERHEAT = "overheat"
    REVERSAL = "reversal"
    UNKNOWN = "unknown"


class CandidateRole(str, Enum):
    EARLY_DISCOVERY = "early_discovery"
    DEEP_DIVE = "deep_dive"
    WATCH = "watch"
    THEME_PROXY = "theme_proxy"
    DO_NOT_CHASE = "do_not_chase"
    AVOID = "avoid"


ROLE_LABEL_JA: dict[CandidateRole, str] = {
    CandidateRole.EARLY_DISCOVERY: "初動候補",
    CandidateRole.DEEP_DIVE: "深掘り候補",
    CandidateRole.WATCH: "監視候補",
    CandidateRole.THEME_PROXY: "テーマ代表",
    CandidateRole.DO_NOT_CHASE: "追いかけ禁止",
    CandidateRole.AVOID: "見送り",
}

PHASE_LABEL_JA: dict[CandidatePhase, str] = {
    CandidatePhase.EARLY: "初動",
    CandidatePhase.ACCEL: "加速",
    CandidatePhase.OVERHEAT: "過熱",
    CandidatePhase.REVERSAL: "反落",
    CandidatePhase.UNKNOWN: "判定不能",
}

EARLY_DISCOVERY_ROLES: frozenset[CandidateRole] = frozenset({CandidateRole.EARLY_DISCOVERY})
THEME_PROXY_ROLES: frozenset[CandidateRole] = frozenset(
    {CandidateRole.THEME_PROXY, CandidateRole.DO_NOT_CHASE}
)


def is_early_discovery_role(role: CandidateRole) -> bool:
    return role in EARLY_DISCOVERY_ROLES


def role_label_ja(role: CandidateRole) -> str:
    return ROLE_LABEL_JA.get(role, role.value)


def phase_label_ja(phase: CandidatePhase) -> str:
    return PHASE_LABEL_JA.get(phase, phase.value)
