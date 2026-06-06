"""Data freshness classification for weekly report candidate promotion (cache/fixture-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class FreshnessStatus(Enum):
    FRESH = "fresh"
    STALE_WARNING = "stale_warning"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


FRESHNESS_DAYS_DEFAULT = 14
STALE_DAYS_DEFAULT = 30


@dataclass(frozen=True)
class FreshnessInfo:
    status: FreshnessStatus
    age_days: int | None
    latest_date: str | None

    @property
    def can_promote(self) -> bool:
        return can_promote_candidate_by_freshness(self.status)


def age_days_from_latest(latest_date: str | None, report_date: str) -> int | None:
    if not latest_date or not latest_date.strip():
        return None
    try:
        d_latest = date.fromisoformat(latest_date.strip())
        d_report = date.fromisoformat(report_date.strip())
    except ValueError:
        return None
    return max((d_report - d_latest).days, 0)


def classify_data_freshness(
    age_days: int | None,
    *,
    fresh_days: int = FRESHNESS_DAYS_DEFAULT,
    stale_days: int = STALE_DAYS_DEFAULT,
) -> FreshnessStatus:
    if age_days is None:
        return FreshnessStatus.UNKNOWN
    if age_days <= fresh_days:
        return FreshnessStatus.FRESH
    if age_days <= stale_days:
        return FreshnessStatus.STALE_WARNING
    return FreshnessStatus.EXPIRED


def can_promote_candidate_by_freshness(status: FreshnessStatus) -> bool:
    return status in (FreshnessStatus.FRESH, FreshnessStatus.STALE_WARNING)


def freshness_info_for_latest_date(latest_date: str | None, report_date: str) -> FreshnessInfo:
    age = age_days_from_latest(latest_date, report_date)
    status = classify_data_freshness(age)
    return FreshnessInfo(status=status, age_days=age, latest_date=latest_date or None)


def freshness_display_label(info: FreshnessInfo) -> str:
    if info.status == FreshnessStatus.FRESH:
        suffix = f"（{info.age_days}日前）" if info.age_days is not None else ""
        return f"🟢新しい{suffix}"
    if info.status == FreshnessStatus.STALE_WARNING:
        suffix = f"（{info.age_days}日前）" if info.age_days is not None else ""
        return f"🟡要更新{suffix}"
    if info.status == FreshnessStatus.EXPIRED:
        suffix = f"（{info.age_days}日前）" if info.age_days is not None else ""
        return f"🔴期限切れ{suffix}"
    return "⚪不明"
