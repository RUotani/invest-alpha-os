# Scheduled Report Assurance Snapshot v71D

Date: 2026-05-31

## Decision

Add a source-only scheduled-report assurance snapshot that combines v70D-v71C into a next-run readiness matrix.

The snapshot reports the next Saturday morning JST target, workflow patch requirement, local dry-run/backfill contract
availability, missing-report sentinel availability, recovery runbook availability, sleep-prevention instruction presence,
and remaining manual approvals.

## Rationale

The weekly report missing incident now has diagnostic, observability, recovery, workflow approval, local dry-run contract,
and sleep-prevention packs. Operators need a single source-side readiness view before relying on the next scheduled
Saturday morning JST report.

v71D keeps the assessment source-only and explicitly records that scheduled delivery is not ready until the workflow
patch is explicitly approved and applied by a human.

## Readiness Boundary

- next scheduled target: next Saturday 07:00 JST, represented as GitHub Actions cron `0 22 * * 5`
- workflow patch: still requires explicit human approval when missing from tracked workflows
- local dry-run/backfill: contract exists, execution is not approved by this snapshot
- recovery/backfill: requires explicit operator choice
- Gmail send: not approved
- sleep guard: standardized by v71C

## Explicit Non-Approval

- `.github/workflows` direct change: not approved
- provider live access: not approved
- live HTTP: not approved
- cache write: not approved
- actual refresh/import: not approved
- manual actual import: not approved
- raw OHLCV/API persistence: not approved
- Gmail send: not approved
- trading action: not approved

## Next Decision Point

After human approval of the workflow patch, re-run the assurance snapshot and observe the next scheduled Saturday morning
JST report.
