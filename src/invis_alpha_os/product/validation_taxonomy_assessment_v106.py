"""Static assessment of the existing v95/v97/v98/v100 validation vocabulary."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationIssueInventoryEntryV106:
    source: str
    key: str
    severity: str
    normalized_meaning: str
    domain: str
    recommended_action: str
    notes_ja: str


def _entry(
    source: str,
    key: str,
    severity: str,
    meaning: str,
    domain: str,
    action: str = "keep",
    notes: str = "",
) -> ValidationIssueInventoryEntryV106:
    return ValidationIssueInventoryEntryV106(source, key, severity, meaning, domain, action, notes)


def build_validation_issue_inventory_v106() -> tuple[ValidationIssueInventoryEntryV106, ...]:
    """Return the source-reviewed issue and review-item inventory without executing validators."""

    return (
        _entry("v95", "missing_as_of_month", "ERROR", "invalid_as_of_month", "date"),
        _entry("v95", "future_as_of_month", "ERROR", "future_as_of_month", "date"),
        _entry("v95", "stale_as_of_month", "WARN", "stale_as_of_month", "date"),
        _entry("v95", "amount_unit_contract", "ERROR", "invalid_amount_unit", "unit", "alias"),
        _entry("v95", "net_worth_mismatch", "ERROR", "net_worth_mismatch", "amount"),
        _entry("v95", "asset_total_mismatch", "ERROR", "asset_total_mismatch", "amount"),
        _entry("v95", "allocation_ratio_total_mismatch", "ERROR", "ratio_total_mismatch", "ratio", "alias"),
        _entry("v95", "equity_total_mismatch", "ERROR", "equity_total_mismatch", "equity"),
        _entry("v95", "cash_below_minimum_guardrail", "WARN", "cash_below_minimum_guardrail", "guardrail"),
        _entry(
            "v95",
            "cash_below_preferred_recovery_zone",
            "INFO",
            "cash_below_preferred_recovery_zone",
            "guardrail",
        ),
        _entry("v95", "single_stock_above_target_band", "WARN", "single_stock_above_target_band", "guardrail"),
        _entry("v95", "negative_amount", "ERROR", "negative_amount", "amount"),
        _entry("v97", "missing_required_asset_class", "ERROR", "missing_required_asset_class", "schema"),
        _entry("v97", "amount_unit_contract", "ERROR", "invalid_amount_unit", "unit", "alias"),
        _entry("v97", "net_worth_mismatch", "ERROR", "net_worth_mismatch", "amount"),
        _entry("v97", "asset_total_mismatch", "ERROR", "asset_total_mismatch", "amount"),
        _entry("v97", "allocation_ratio_total_mismatch", "ERROR", "ratio_total_mismatch", "ratio", "alias"),
        _entry("v97", "equity_total_mismatch", "ERROR", "equity_total_mismatch", "equity"),
        _entry("v97", "cash_below_minimum_guardrail", "WARN", "cash_below_minimum_guardrail", "guardrail"),
        _entry(
            "v97",
            "cash_below_preferred_recovery_zone",
            "INFO",
            "cash_below_preferred_recovery_zone",
            "guardrail",
        ),
        _entry("v97", "single_stock_above_target_band", "WARN", "single_stock_above_target_band", "guardrail"),
        _entry("v98", "missing_as_of_month", "ERROR", "invalid_as_of_month", "date"),
        _entry("v98", "future_as_of_month", "ERROR", "future_as_of_month", "date"),
        _entry("v98", "invalid_currency", "ERROR", "invalid_currency", "unit"),
        _entry("v98", "invalid_amount_unit", "ERROR", "invalid_amount_unit", "unit"),
        _entry("v98", "duplicate_asset_key", "ERROR", "duplicate_asset_key", "schema"),
        _entry("v98", "unknown_asset_key", "ERROR", "unknown_asset_key", "schema"),
        _entry("v98", "missing_required_asset_class", "ERROR", "missing_required_asset_class", "schema"),
        _entry("v98", "net_worth_mismatch", "ERROR", "net_worth_mismatch", "amount"),
        _entry("v98", "asset_total_mismatch", "ERROR", "asset_total_mismatch", "amount"),
        _entry("v98", "ratio_total_mismatch", "ERROR", "ratio_total_mismatch", "ratio"),
        _entry("v98", "equity_total_mismatch", "ERROR", "equity_total_mismatch", "equity"),
        _entry("v98", "negative_amount", "ERROR", "negative_amount", "amount"),
        _entry("v98", "cash_below_minimum_guardrail", "WARN", "cash_below_minimum_guardrail", "guardrail"),
        _entry("v98", "single_stock_above_target_band", "WARN", "single_stock_above_target_band", "guardrail"),
        _entry("v100", "cash_guardrail", "WARN|INFO", "cash_guardrail_review", "review", "keep", "review item"),
        _entry(
            "v100",
            "individual_stock_band",
            "WARN|INFO",
            "individual_stock_band_review",
            "review",
            "keep",
            "review item",
        ),
        _entry("v100", "target_allocation_gap", "WARN", "target_allocation_gap_review", "review", "keep", "review item"),
        _entry("v100", "contract_parity", "ERROR|WARN|INFO", "contract_parity_review", "review", "keep", "review item"),
        _entry("v100", "raw_data_boundary", "INFO", "raw_data_boundary_review", "review", "keep", "review item"),
    )


def group_validation_issue_inventory_by_meaning_v106(
    inventory: tuple[ValidationIssueInventoryEntryV106, ...] | None = None,
) -> dict[str, tuple[ValidationIssueInventoryEntryV106, ...]]:
    grouped: defaultdict[str, list[ValidationIssueInventoryEntryV106]] = defaultdict(list)
    for entry in inventory or build_validation_issue_inventory_v106():
        grouped[entry.normalized_meaning].append(entry)
    return {meaning: tuple(entries) for meaning, entries in sorted(grouped.items())}


def find_validation_naming_drift_v106(
    inventory: tuple[ValidationIssueInventoryEntryV106, ...] | None = None,
) -> dict[str, tuple[str, ...]]:
    drift: dict[str, tuple[str, ...]] = {}
    for meaning, entries in group_validation_issue_inventory_by_meaning_v106(inventory).items():
        keys = tuple(sorted({entry.key for entry in entries}))
        if len(keys) > 1:
            drift[meaning] = keys
    return drift


def find_validation_severity_drift_v106(
    inventory: tuple[ValidationIssueInventoryEntryV106, ...] | None = None,
) -> dict[str, tuple[str, ...]]:
    drift: dict[str, tuple[str, ...]] = {}
    for meaning, entries in group_validation_issue_inventory_by_meaning_v106(inventory).items():
        severities = tuple(sorted({entry.severity for entry in entries}))
        if len(severities) > 1:
            drift[meaning] = severities
    return drift


def render_validation_taxonomy_assessment_markdown_v106(
    inventory: tuple[ValidationIssueInventoryEntryV106, ...] | None = None,
) -> str:
    entries = inventory or build_validation_issue_inventory_v106()
    naming_drift = find_validation_naming_drift_v106(entries)
    severity_drift = find_validation_severity_drift_v106(entries)
    lines = [
        "# Common Validation Taxonomy Assessment v106",
        "",
        f"- inventory entries: {len(entries)}",
        f"- naming drift groups: {len(naming_drift)}",
        f"- severity drift groups: {len(severity_drift)}",
        "- canonical candidate: v98 input -> v97 projection/context -> v95 downstream validator -> v100 reviewer",
        "",
        "## Naming Drift",
    ]
    lines.extend(f"- `{meaning}`: {', '.join(keys)}" for meaning, keys in naming_drift.items())
    lines.extend(["", "## Inventory", "", "| source | key | severity | meaning | domain | action |", "| --- | --- | --- | --- | --- | --- |"])
    lines.extend(
        f"| {entry.source} | {entry.key} | {entry.severity} | {entry.normalized_meaning} | {entry.domain} | {entry.recommended_action} |"
        for entry in entries
    )
    return "\n".join(lines) + "\n"
