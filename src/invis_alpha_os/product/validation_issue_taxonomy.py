"""Non-breaking common vocabulary for validation issues.

Existing validators do not depend on this module. It records a stable vocabulary
for future consumers without changing legacy keys, severities, or behavior.
"""

from __future__ import annotations

from enum import Enum


class ValidationIssueSeverity(str, Enum):
    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"


class ValidationIssueCategory(str, Enum):
    DATE = "date"
    UNIT = "unit"
    AMOUNT = "amount"
    RATIO = "ratio"
    EQUITY = "equity"
    GUARDRAIL = "guardrail"
    SCHEMA = "schema"


LEGACY_VALIDATION_ISSUE_ALIASES: dict[str, str] = {
    "allocation_ratio_total_mismatch": "ratio_total_mismatch",
    "amount_unit_contract": "invalid_amount_unit",
}

VALIDATION_ISSUE_CATEGORIES: dict[str, ValidationIssueCategory] = {
    "asset_total_mismatch": ValidationIssueCategory.AMOUNT,
    "cash_below_minimum_guardrail": ValidationIssueCategory.GUARDRAIL,
    "cash_below_preferred_recovery_zone": ValidationIssueCategory.GUARDRAIL,
    "duplicate_asset_key": ValidationIssueCategory.SCHEMA,
    "equity_total_mismatch": ValidationIssueCategory.EQUITY,
    "future_as_of_month": ValidationIssueCategory.DATE,
    "invalid_amount_unit": ValidationIssueCategory.UNIT,
    "invalid_currency": ValidationIssueCategory.UNIT,
    "missing_as_of_month": ValidationIssueCategory.DATE,
    "missing_required_asset_class": ValidationIssueCategory.SCHEMA,
    "negative_amount": ValidationIssueCategory.AMOUNT,
    "net_worth_mismatch": ValidationIssueCategory.AMOUNT,
    "ratio_total_mismatch": ValidationIssueCategory.RATIO,
    "single_stock_above_target_band": ValidationIssueCategory.GUARDRAIL,
    "stale_as_of_month": ValidationIssueCategory.DATE,
    "unknown_asset_key": ValidationIssueCategory.SCHEMA,
}

CANONICAL_VALIDATION_ISSUE_KEYS: tuple[str, ...] = tuple(sorted(VALIDATION_ISSUE_CATEGORIES))
VALIDATION_SEVERITIES: tuple[str, ...] = tuple(severity.value for severity in ValidationIssueSeverity)


def normalize_validation_issue_key(key: str) -> str:
    """Return a canonical key for a known legacy alias; leave unknown keys unchanged."""

    return LEGACY_VALIDATION_ISSUE_ALIASES.get(key, key)


def get_validation_issue_category(key: str) -> ValidationIssueCategory | None:
    """Return the category for a canonical or legacy key."""

    return VALIDATION_ISSUE_CATEGORIES.get(normalize_validation_issue_key(key))


def is_known_validation_issue_key(key: str) -> bool:
    """Return whether a canonical or legacy validation issue key is known."""

    return get_validation_issue_category(key) is not None


__all__ = [
    "CANONICAL_VALIDATION_ISSUE_KEYS",
    "LEGACY_VALIDATION_ISSUE_ALIASES",
    "VALIDATION_ISSUE_CATEGORIES",
    "VALIDATION_SEVERITIES",
    "ValidationIssueCategory",
    "ValidationIssueSeverity",
    "get_validation_issue_category",
    "is_known_validation_issue_key",
    "normalize_validation_issue_key",
]
