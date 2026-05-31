# Long-Run Development Progress Snapshot v72D

Date: 2026-06-01

## Decision

Add a source-only long-run development progress snapshot for v63B through the latest weekly-report milestones.

The snapshot reports progress by domain only: cache-write, weekly-report, actual-import, and operator-runbook. It does
not emit a single overall percentage because `RULES.md` section 16 forbids single overall progress percentages.

## Domain Progress Policy

- cache-write progress is tracked separately from actual import
- weekly-report progress is blocked primarily by human approval of the workflow patch
- actual-import remains quarantined and not approved
- operator-runbook progress includes sleep guard and recovery contracts, but does not imply execution approval

## Explicit Non-Approval

- provider live access: not approved
- live HTTP: not approved
- cache write: not approved
- actual refresh/import: not approved
- raw OHLCV/API persistence: not approved
- reports-private raw data: not approved
- env/secret display: not approved
- `.github/workflows` direct change: not approved
- trading action: not approved

## Next Decision Point

The next human decision is whether to approve the weekly candidate brief workflow patch. Cache-write and actual-import
execution remain separate approval tracks.
