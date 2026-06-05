from __future__ import annotations

from datetime import date

from invis_alpha_os.reports.jquants_date_range import (
    contract_dates_from_env,
    is_effective_refresh_range,
    parse_contract_date,
    resolve_refresh_date_range,
)


def test_parse_contract_date_accepts_iso_and_compact() -> None:
    assert parse_contract_date("20260306") == date(2026, 3, 6)
    assert parse_contract_date("2026-03-06") == date(2026, 3, 6)


def test_resolve_refresh_date_range_clamps_when_allowed() -> None:
    env = {"JQUANTS_DATA_AVAILABLE_TO": "20260306"}
    resolution = resolve_refresh_date_range(
        env,
        requested_to=date(2026, 5, 29),
        allow_date_clamp=True,
    )
    assert resolution.validation_status == "ok"
    assert resolution.requested_to_date == "2026-05-29"
    assert resolution.clamped_to_date == "2026-03-06"
    assert resolution.date_range_clamped is True
    assert resolution.date_range_clamp_required is True


def test_resolve_refresh_date_range_rejects_without_allow_clamp() -> None:
    env = {"JQUANTS_DATA_AVAILABLE_TO": "20260306"}
    resolution = resolve_refresh_date_range(
        env,
        requested_to=date(2026, 5, 29),
        allow_date_clamp=False,
    )
    assert resolution.validation_status == "date_range_out_of_contract"
    assert resolution.http_prevented_by_date_validation is True


def test_is_effective_refresh_range() -> None:
    assert is_effective_refresh_range("2026-03-06", "2026-02-17") is True
    assert is_effective_refresh_range("2026-03-06", "2026-03-06") is False


def test_resolve_refresh_date_range_no_effective_range() -> None:
    env = {"JQUANTS_DATA_AVAILABLE_TO": "20260306"}
    resolution = resolve_refresh_date_range(
        env,
        requested_to=date(2026, 5, 29),
        allow_date_clamp=True,
        latest_bar_dates={"5802": "2026-03-06", "6645": "2026-03-06"},
        check_effective_range=True,
    )
    assert resolution.validation_status == "no_effective_refresh_range"


def test_contract_dates_from_env() -> None:
    diag = contract_dates_from_env({"JQUANTS_DATA_AVAILABLE_TO": "20260306"})
    assert diag["data_available_to_present"] is True
    assert diag["data_available_to"] == "2026-03-06"
