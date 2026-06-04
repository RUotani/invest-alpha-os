from __future__ import annotations

import ast
from pathlib import Path

from invis_alpha_os.product import portfolio_input
from invis_alpha_os.product.validation_taxonomy_assessment_v106 import (
    build_validation_issue_inventory_v106,
    find_validation_naming_drift_v106,
    find_validation_severity_drift_v106,
    group_validation_issue_inventory_by_meaning_v106,
    render_validation_taxonomy_assessment_markdown_v106,
)


SOURCE_PATHS = {
    "v95": Path("src/invis_alpha_os/product/monthly_input_consistency_v95.py"),
    "v97": Path("src/invis_alpha_os/product/portfolio_context_input_v97.py"),
    "v98": Path("src/invis_alpha_os/product/sanitized_manual_input_v98.py"),
    "v100": Path("src/invis_alpha_os/product/sanitized_manual_input_user_review_v100.py"),
}


def _declared_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg in {"code", "key"} and isinstance(keyword.value, ast.Constant):
                if isinstance(keyword.value.value, str):
                    keys.add(keyword.value.value)
    return keys


def test_v106_inventory_matches_real_source_keys() -> None:
    inventory = build_validation_issue_inventory_v106()
    assert len(inventory) == 40
    for source, path in SOURCE_PATHS.items():
        expected = {entry.key for entry in inventory if entry.source == source}
        assert _declared_keys(path) == expected


def test_v106_inventory_groups_duplicate_meanings() -> None:
    grouped = group_validation_issue_inventory_by_meaning_v106()
    assert {entry.source for entry in grouped["net_worth_mismatch"]} == {"v95", "v97", "v98"}
    assert {entry.source for entry in grouped["cash_below_minimum_guardrail"]} == {"v95", "v97", "v98"}


def test_v106_detects_real_naming_drift_and_no_validation_severity_drift() -> None:
    drift = find_validation_naming_drift_v106()
    assert drift["ratio_total_mismatch"] == ("allocation_ratio_total_mismatch", "ratio_total_mismatch")
    assert drift["invalid_amount_unit"] == ("amount_unit_contract", "invalid_amount_unit")
    assert find_validation_severity_drift_v106() == {}


def test_v106_review_keys_remain_separate_from_validator_issue_meanings() -> None:
    inventory = build_validation_issue_inventory_v106()
    review = tuple(entry for entry in inventory if entry.source == "v100")
    assert len(review) == 5
    assert all(entry.domain == "review" for entry in review)
    assert all(entry.normalized_meaning.endswith("_review") for entry in review)


def test_v106_assessment_renders_source_backed_summary() -> None:
    markdown = render_validation_taxonomy_assessment_markdown_v106()
    assert "inventory entries: 40" in markdown
    assert "naming drift groups: 2" in markdown
    assert "severity drift groups: 0" in markdown
    assert "v98 input -> v97 projection/context -> v95 downstream validator -> v100 reviewer" in markdown


def test_v106_existing_portfolio_facade_behavior_is_unchanged() -> None:
    fixture = portfolio_input.build_redacted_sanitized_manual_input_fixture()
    result = portfolio_input.validate_sanitized_manual_input(fixture, current_month=fixture.as_of_month)
    assert {issue.code for issue in result.issues} == {
        "cash_below_minimum_guardrail",
        "single_stock_above_target_band",
    }


def test_v106_assessment_has_no_forbidden_execution_paths() -> None:
    text = Path("src/invis_alpha_os/product/validation_taxonomy_assessment_v106.py").read_text(encoding="utf-8").lower()
    forbidden = ("requests.", "urllib", "workflow_dispatch", "cache_write", "actual_import", "broker_api", "raw_excel", "send_gmail")
    assert all(term not in text for term in forbidden)
