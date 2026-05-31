# Weekly Report Local Dry-Run and Backfill Verification Contract v71B

Date: 2026-05-31

## Decision

Add a source-only local dry-run and backfill verification contract before any weekly report recovery execution.

The contract defines safe command inventory, allowed generated/redacted output locations, forbidden raw-data locations,
and failure modes for local recovery validation. It does not approve local dry-run execution, manual backfill execution,
Gmail send, workflow modification, cache write, provider access, actual refresh/import, or raw data persistence.

## Rationale

v70D-v70F made the missed Saturday morning JST weekly report diagnosable and recoverable, and v71 produced a copy-ready
workflow approval patch package. The next risk is operational ambiguity: an operator may need to validate a missed report
without accidentally crossing live-data, raw-data, cache-write, Gmail-send, or workflow-change boundaries.

v71B therefore separates a verification contract from execution. Generated weekly report artifacts and redacted summaries
are acceptable outputs only after the operator makes a separate recovery choice. Raw OHLCV files, raw API responses,
reports-private raw market data, provider cache persistence, and broker/manual raw data are forbidden locations.

## Contract Scope

- safe command inventory for markdown report, copy report, email preview, schedule diagnostic, and sentinel rendering
- explicit execution boundary: local dry-run and manual backfill are not approved by this pack
- output contract for generated/redacted artifacts
- failure-mode matrix for CLI missing, date mismatch, timezone mismatch, output missing, empty report,
  notification/export missing, and workflow not approved
- context pack integration via `weekly_report_local_dryrun_backfill_contract_status`

## Explicit Non-Approval

- provider live access: not approved
- live HTTP: not approved
- cache write: not approved
- actual refresh/import: not approved
- manual actual import: not approved
- raw OHLCV persistence: not approved
- raw API response persistence: not approved
- reports-private raw market data: not approved
- Git-tracked raw data: not approved
- Gmail send: not approved
- `.github/workflows` direct change: not approved
- trading action: not approved

## Next Decision Point

Standardize Long-Run operator preflight and Mac sleep-prevention guidance as a reusable source-only handoff/runbook block.
