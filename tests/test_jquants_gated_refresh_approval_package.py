from __future__ import annotations

from invis_alpha_os.reports.jquants_gated_refresh_approval_package import (
    APPROVAL_PHRASE,
    build_jquants_gated_refresh_approval_package,
)


def test_approval_package_ready_when_preflight_recommends() -> None:
    result = build_jquants_gated_refresh_approval_package(
        report_date="2026-05-29",
        env_discovery={"required_keys_present": True, "missing_required_keys": []},
        preflight={
            "credentials_available": True,
            "refresh_recommended": True,
            "contract_limited_risk": "low",
            "max_gap_days": 90,
            "expected_new_rows": "likely",
            "per_ticker": [{"ticker": "285A", "cache_latest_date": "2026-02-17"}],
        },
    )
    assert result.json_payload["package_status"] == "ready_for_refresh_approval"
    assert result.json_payload["required_approval_phrase"] == APPROVAL_PHRASE
    assert result.json_payload["safety_checklist"]["jquants_live_http"] is False
