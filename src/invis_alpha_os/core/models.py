from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class DataConfidence(str, Enum):
    low = "low"
    mid = "mid"
    high = "high"


class WatchlistTier(str, Enum):
    tier_1 = "tier_1"
    tier_2 = "tier_2"
    tier_3 = "tier_3"


class VetoLevel(str, Enum):
    hard_veto = "hard_veto"
    soft_veto = "soft_veto"


@dataclass(frozen=True)
class Evidence:
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)

    source: str = "manual"
    data_confidence: DataConfidence = DataConfidence.mid

    symbol: str | None = None
    title: str | None = None
    note: str | None = None

    external_url: str | None = None
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ObservationLogEntry:
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)

    symbol: str | None = None
    note: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ShadowPosition:
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)

    symbol: str = ""
    quantity: float = 0.0
    entry_price: float | None = None
    entry_date: date | None = None
    thesis_evidence_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OutcomeRecord:
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)

    symbol: str = ""
    decision_date: date | None = None
    outcome_date: date | None = None
    result: str = "unknown"
    note: str | None = None

    related_observation_id: str | None = None
    related_shadow_position_id: str | None = None
    evidence_ids: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VetoResult:
    level: VetoLevel
    rule_id: str
    message: str
    evidence_ids: list[str] = field(default_factory=list)

