# Common Validation Taxonomy Assessment v106

Date: 2026-06-04

## Decision

Inventory v95/v97/v98/v100 before introducing common validation taxonomy. The assessment finds enough repeated meanings
and two concrete naming-drift pairs to justify a non-breaking v107 skeleton, but not a validator refactor.

## Evidence

- 40 real source keys: v95 12, v97 9, v98 14, v100 5.
- Naming drift: `amount_unit_contract` / `invalid_amount_unit`.
- Naming drift: `allocation_ratio_total_mismatch` / `ratio_total_mismatch`.
- No severity drift among validator issues sharing a normalized meaning.
- v100 keys are review projections and must remain separate from validator issue keys.

## Canonical Candidate

Treat v98 sanitized/manual input as the upstream canonical-input candidate, v97 as projection/context, v95 as a
downstream validator, and v100 as a user-facing reviewer. This is an assessment, not a behavior or contract migration.

## v107 Boundary

Proceed only with a standalone taxonomy skeleton containing severity/category/canonical-key vocabulary and legacy alias
mapping. Do not connect it to existing validators yet. Do not change issue keys, severities, return contracts, execution
order, thresholds, or rendering.

## Counterargument

A shared taxonomy can become architecture overhead if it merely duplicates strings. The skeleton is justified only
because two real aliases and several repeated meanings already exist. Further abstraction requires a concrete consumer.

## Explicit Non-Approval

- workflow change or manual workflow_dispatch: not approved / not executed
- live HTTP, cache write, actual import, broker API, raw Excel parsing: not approved / not executed
- env/secret display, dependency, pyproject, or Makefile change: not approved / not executed
- trading action or real email send: not approved / not executed
