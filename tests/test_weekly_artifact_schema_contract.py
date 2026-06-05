from __future__ import annotations

from invis_alpha_os.product.scheduled_run_observation_readiness_v101 import (
    build_fixture_artifact_texts_for_scheduled_observation_v101,
)
from invis_alpha_os.product.weekly_artifact_schema_contract import (
    validate_weekly_artifact_schema_contract,
)


def test_schema_contract_passes_complete_fixture() -> None:
    texts = build_fixture_artifact_texts_for_scheduled_observation_v101(report_date="2026-06-06")
    result = validate_weekly_artifact_schema_contract(texts)
    assert result.ready is True
    assert result.v104_valid is True
    assert result.v101_ready is True


def test_schema_contract_fails_without_status_json() -> None:
    texts = build_fixture_artifact_texts_for_scheduled_observation_v101(report_date="2026-06-06")
    del texts["status.json"]
    result = validate_weekly_artifact_schema_contract(texts)
    assert result.ready is False
    assert "status.json:missing" in result.v104_issues
