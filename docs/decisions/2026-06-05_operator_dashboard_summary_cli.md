# Operator Dashboard Summary CLI

Date: 2026-06-05

## Decision

Add `operator-dashboard-summary` as a source-only stdout CLI for the post-#475 main development queue.

## Rationale

The operator needs a compact view of the current primary queue without running workflows, fetching live data, writing
cache, importing actual data, parsing raw inputs, displaying secrets, or sending email.

The CLI summarizes:

- P1 scheduled natural run observation status
- P2 weekly artifact/status local verification readiness
- P3 weekly/monthly golden snapshot regression readiness
- P4 operator dashboard CLI readiness
- hard-gate status for live HTTP, cache/import, broker/raw/secret/email/trading, workflow change, and dispatch
- recommended next actions for the 2026-06-06 natural run observation

## Boundary

- stdout-only
- source-only / fixture-only
- no workflow change
- no manual workflow_dispatch
- no live HTTP / market-data live fetch
- no cache write / actual import / manual import
- no broker API / raw Excel direct parsing
- no env/secret display
- no trading action / order placement / real email send

## Follow-Up

Connect the dashboard summary with the Secondary Queue consistency checkers so `docs/progress_dashboard.md` and
`STATE.md` drift can be detected without changing source behavior.
