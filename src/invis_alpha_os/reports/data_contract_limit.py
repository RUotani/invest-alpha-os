"""Classify provider contract data limits after refresh."""

from __future__ import annotations

from typing import Any

from invis_alpha_os.reports.jquants_date_range import parse_contract_date

_STALE_FRESHNESS = frozenset({"data_update_required", "stale", "partial_history"})


def assess_data_contract_limit(
    *,
    latest_bar_date: str | None,
    report_date: str,
    contract_to: str | None,
    freshness_classification: str,
) -> dict[str, Any]:
    limited = False
    parsed_latest = parse_contract_date(latest_bar_date)
    parsed_report = parse_contract_date(report_date)
    parsed_contract_to = parse_contract_date(contract_to)
    if (
        parsed_latest is not None
        and parsed_report is not None
        and parsed_contract_to is not None
        and parsed_latest == parsed_contract_to
        and parsed_report > parsed_contract_to
        and freshness_classification in _STALE_FRESHNESS
    ):
        limited = True
    return {
        "data_contract_limited": limited,
        "provider_plan_upgrade_required": limited,
        "alternative_provider_required": limited,
        "data_contract_limit_reason": (
            "latest_bar_date reached provider contract end but report_date remains stale"
            if limited
            else None
        ),
    }
