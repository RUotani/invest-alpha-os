from __future__ import annotations

from pathlib import Path

from invis_alpha_os.product import portfolio_input
from invis_alpha_os.product.validation_issue_taxonomy import (
    CANONICAL_VALIDATION_ISSUE_KEYS,
    LEGACY_VALIDATION_ISSUE_ALIASES,
    VALIDATION_SEVERITIES,
    ValidationIssueCategory,
    get_validation_issue_category,
    is_known_validation_issue_key,
    normalize_validation_issue_key,
)
from invis_alpha_os.product.validation_taxonomy_assessment_v106 import find_validation_naming_drift_v106


def test_v107_severity_and_category_vocabulary_is_complete() -> None:
    assert VALIDATION_SEVERITIES == ("ERROR", "WARN", "INFO")
    assert {category.value for category in ValidationIssueCategory} == {
        "date",
        "unit",
        "amount",
        "ratio",
        "equity",
        "guardrail",
        "schema",
    }


def test_v107_aliases_are_limited_to_v106_real_naming_drift() -> None:
    drift = find_validation_naming_drift_v106()
    assert LEGACY_VALIDATION_ISSUE_ALIASES == {
        "allocation_ratio_total_mismatch": "ratio_total_mismatch",
        "amount_unit_contract": "invalid_amount_unit",
    }
    for legacy, canonical in LEGACY_VALIDATION_ISSUE_ALIASES.items():
        assert legacy in drift[canonical]
        assert canonical in drift[canonical]
        assert canonical in CANONICAL_VALIDATION_ISSUE_KEYS


def test_v107_normalizes_legacy_aliases_without_changing_unknown_keys() -> None:
    assert normalize_validation_issue_key("allocation_ratio_total_mismatch") == "ratio_total_mismatch"
    assert normalize_validation_issue_key("amount_unit_contract") == "invalid_amount_unit"
    assert normalize_validation_issue_key("future_extension_key") == "future_extension_key"


def test_v107_resolves_categories_for_canonical_and_legacy_keys() -> None:
    assert get_validation_issue_category("ratio_total_mismatch") is ValidationIssueCategory.RATIO
    assert get_validation_issue_category("allocation_ratio_total_mismatch") is ValidationIssueCategory.RATIO
    assert get_validation_issue_category("amount_unit_contract") is ValidationIssueCategory.UNIT
    assert get_validation_issue_category("cash_below_minimum_guardrail") is ValidationIssueCategory.GUARDRAIL
    assert get_validation_issue_category("future_extension_key") is None


def test_v107_known_key_check_handles_canonical_legacy_and_unknown() -> None:
    assert is_known_validation_issue_key("net_worth_mismatch")
    assert is_known_validation_issue_key("amount_unit_contract")
    assert not is_known_validation_issue_key("future_extension_key")


def test_v107_existing_portfolio_validation_behavior_is_unchanged() -> None:
    fixture = portfolio_input.build_redacted_sanitized_manual_input_fixture()
    result = portfolio_input.validate_sanitized_manual_input(fixture, current_month=fixture.as_of_month)
    assert {issue.code for issue in result.issues} == {
        "cash_below_minimum_guardrail",
        "single_stock_above_target_band",
    }


def test_v107_taxonomy_has_no_forbidden_execution_paths() -> None:
    text = Path("src/invis_alpha_os/product/validation_issue_taxonomy.py").read_text(encoding="utf-8").lower()
    forbidden = ("requests.", "urllib", "workflow_dispatch", "cache_write", "actual_import", "broker_api", "raw_excel", "send_gmail")
    assert all(term not in text for term in forbidden)
