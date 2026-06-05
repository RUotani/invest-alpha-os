# Progress Dashboard Consistency Checker

Date: 2026-06-05

## Decision

Add `progress-dashboard-check` as a source-only consistency checker for `docs/progress_dashboard.md`.

## Rationale

The dashboard previously mixed table counts, section header counts, checklist counts, and weighted reference wording.
This makes progress reporting drift-prone and can mislead downstream handoffs.

The checker validates:

- domain table weights sum to 100
- each table progress percentage matches completed / fixed item count
- each detail heading count matches the table count
- each detail checklist count matches its heading
- Actual Import Readiness remains 0% with no checked items
- the weighted reference percentage matches the recomputed weighted value

## Source Fixes

The dashboard was normalized to the actual visible checklist counts:

- Report MVP: 14/18
- Weekly / Monthly Ops: 11/14
- Portfolio Data Quality: 12/14
- Raw Input Quarantine: 14/15
- UX / Sample Outputs: 11/11
- weighted reference: approximately 79%

Actual Import Readiness remains 0/10 and 0%.

## Boundary

- source-only markdown consistency check
- no workflow change
- no manual workflow_dispatch
- no live HTTP / market-data live fetch
- no cache write / actual import / manual import
- no broker API / raw Excel direct parsing
- no env/secret display
- no trading action / real email send

## Follow-Up

Add a STATE.md consistency checker separately so STATE snapshots and dashboard progress cannot drift silently.
