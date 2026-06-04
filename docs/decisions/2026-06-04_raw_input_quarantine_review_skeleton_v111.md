# Raw Input Quarantine Review Skeleton v111

Date: 2026-06-04

## Decision

Connect v109 portfolio data-quality review and v110 declaration-only quarantine review through a source-only
cross-review skeleton. Safe fixture declarations still require human review because the portfolio fixture has WARN
guardrails. Raw Excel declarations remain blocked without reading a file.

## Contract

- Cross-review states: `manual_review_required` or `blocked_by_hard_gate`.
- v107 taxonomy normalizes shared validation keys.
- CLI supports only built-in `safe_fixture` and `raw_excel_declared` declaration scenarios.
- Import and cache-write readiness are always `NO-GO`.

## Boundary

The cross-review is not an ingestion pipeline, raw parser, approval engine, or execution gate. It cannot promote any
input to actual import or cache write. It does not contain personal or account raw-data fixtures.

## Counterargument

Cross-reporting adds another presentation layer and does not validate the truth of a manifest. Keep it limited to
review-state consistency; do not add automated promotion or speculative workflow.

## Explicit Non-Approval

- raw Excel / broker export parsing, broker API, live HTTP: not approved / not executed
- cache write / actual import / manual import: not approved / not executed
- env/secret display, workflow, dependency, pyproject, or Makefile change: not approved / not executed
- trading action or real email send: not approved / not executed
