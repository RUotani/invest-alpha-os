# STATE.md Consistency Checker

Date: 2026-06-05

## Decision

Add `state-consistency-check` as a read-only checker for STATE.md safety and snapshot markers.

## Rationale

STATE.md can drift from main during long-running development. Direct STATE.md updates remain approval-sensitive, so the
safe source-only step is to detect drift without modifying STATE.md.

The checker validates:

- latest verified main marker exists
- optional expected main comparison
- hard gate markers for workflow change, manual dispatch, live HTTP, cache write, actual import, broker API, raw Excel,
  env/secret display, real email send, and trading action
- weekly primary system and scheduled observation markers
- generated artifact policy marker

Latest-main mismatch is a warning by default and becomes an error only with `--strict-latest-main`.

## Boundary

- read-only STATE.md check
- no STATE.md update by this pack
- no workflow change
- no manual workflow_dispatch
- no live HTTP / market-data live fetch
- no cache write / actual import / manual import
- no broker API / raw Excel direct parsing
- no env/secret display
- no trading action / real email send

## Follow-Up

Prepare an explicit STATE.md refresh proposal after scheduled natural-run observation and after the user approves STATE
snapshot updates.
