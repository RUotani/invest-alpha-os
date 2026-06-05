# Weekly / Monthly Golden Snapshot Regression Tests

Date: 2026-06-05

## Decision

Add fixture-only golden snapshot regression tests for the weekly candidate brief and monthly decision sheet.

## Rationale

The weekly and monthly reports are now user-facing decision-support artifacts. Regression tests should catch accidental
removal of the key decision-support structure without freezing every sentence of the UX copy.

The tests therefore lock:

- weekly markdown section order around copy-ready summary, portfolio constraints, score/veto, pipeline trace, action
  checklist, safety note, and legacy candidate sections
- weekly copy paste boundaries and action checklist headings
- weekly JSON schema, section keys, and score/veto pipeline fields
- monthly decision sheet section order, portfolio context numbers, allocation gap markers, and safety wording
- absence of direct trading/action-command wording in weekly/monthly fixture outputs

## Boundary

- source-only / fixture-only
- no workflow change
- no manual workflow_dispatch
- no live HTTP / market-data live fetch
- no cache write / actual import
- no broker API / raw Excel direct parsing
- no env/secret display
- no trading action / order placement / real email send

## Follow-Up

If future report UX changes intentionally rename headings, update these snapshot expectations in the same PR as the UX
change and explain the user-facing rationale.
