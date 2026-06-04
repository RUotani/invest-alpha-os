# Common Validation Taxonomy Skeleton v107

Date: 2026-06-04

## Decision

Add a standalone, versionless validation taxonomy skeleton based on the v106 source-backed assessment. Existing
v95/v97/v98/v100 validators and reviewers do not import or depend on the skeleton.

## Scope

- Severity vocabulary: `ERROR`, `WARN`, `INFO`.
- Categories: date, unit, amount, ratio, equity, guardrail, schema.
- Canonical keys limited to existing validator meanings.
- Legacy aliases limited to two real v106 naming-drift pairs.
- Unknown keys remain unchanged and have no category.

## Legacy Alias Mapping

- `amount_unit_contract` -> `invalid_amount_unit`
- `allocation_ratio_total_mismatch` -> `ratio_total_mismatch`

The aliases are descriptive only. Existing validators continue returning their current legacy keys.

## Non-Breaking Boundary

- No existing issue key, severity, return contract, threshold, execution order, or rendering changes.
- No bulk migration or validator integration.
- A future consumer must demonstrate concrete value before existing validators reference this module.
- v100 review-item keys remain outside the validator taxonomy.

## Counterargument

The skeleton duplicates existing vocabulary and adds maintenance cost. Its value is currently limited to making two real
aliases and shared categories explicit. Do not add more layers or speculative aliases without a concrete consumer.

## Explicit Non-Approval

- workflow change or manual workflow_dispatch: not approved / not executed
- live HTTP, cache write, actual import, broker API, raw Excel parsing: not approved / not executed
- env/secret display, dependency, pyproject, or Makefile change: not approved / not executed
- trading action or real email send: not approved / not executed
