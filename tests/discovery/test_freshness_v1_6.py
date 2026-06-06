from __future__ import annotations

from invis_alpha_os.discovery.freshness import (
    FreshnessStatus,
    age_days_from_latest,
    can_promote_candidate_by_freshness,
    classify_data_freshness,
    freshness_info_for_latest_date,
)


def test_freshness_age_boundaries() -> None:
    assert classify_data_freshness(9) == FreshnessStatus.FRESH
    assert classify_data_freshness(19) == FreshnessStatus.STALE_WARNING
    assert classify_data_freshness(109) == FreshnessStatus.EXPIRED
    assert classify_data_freshness(None) == FreshnessStatus.UNKNOWN


def test_age_days_from_latest() -> None:
    assert age_days_from_latest("2026-05-28", "2026-06-06") == 9
    assert age_days_from_latest("2026-02-17", "2026-06-06") == 109


def test_expired_cannot_promote() -> None:
    assert can_promote_candidate_by_freshness(FreshnessStatus.EXPIRED) is False
    assert can_promote_candidate_by_freshness(FreshnessStatus.UNKNOWN) is False
    assert can_promote_candidate_by_freshness(FreshnessStatus.FRESH) is True
    assert can_promote_candidate_by_freshness(FreshnessStatus.STALE_WARNING) is True


def test_freshness_info_fixture_dates() -> None:
    fresh = freshness_info_for_latest_date("2026-05-28", "2026-06-06")
    stale = freshness_info_for_latest_date("2026-05-18", "2026-06-06")
    expired = freshness_info_for_latest_date("2026-02-17", "2026-06-06")
    assert fresh.status == FreshnessStatus.FRESH
    assert stale.status == FreshnessStatus.STALE_WARNING
    assert expired.status == FreshnessStatus.EXPIRED
