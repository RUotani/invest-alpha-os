from __future__ import annotations

from invis_alpha_os.reports.data_contract_limit import assess_data_contract_limit


def test_assess_data_contract_limit_when_at_contract_end_but_stale() -> None:
    diag = assess_data_contract_limit(
        latest_bar_date="2026-03-06",
        report_date="2026-05-27",
        contract_to="2026-03-06",
        freshness_classification="data_update_required",
    )
    assert diag["data_contract_limited"] is True
    assert diag["provider_plan_upgrade_required"] is True
    assert diag["alternative_provider_required"] is True


def test_assess_data_contract_limit_false_when_latest_after_contract_end() -> None:
    diag = assess_data_contract_limit(
        latest_bar_date="2026-05-18",
        report_date="2026-05-27",
        contract_to="2026-03-06",
        freshness_classification="stale",
    )
    assert diag["data_contract_limited"] is False


def test_assess_data_contract_limit_false_when_fresh() -> None:
    diag = assess_data_contract_limit(
        latest_bar_date="2026-03-06",
        report_date="2026-05-27",
        contract_to="2026-03-06",
        freshness_classification="fresh",
    )
    assert diag["data_contract_limited"] is False
