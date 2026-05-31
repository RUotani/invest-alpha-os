# Weekly Report Recovery Runbook and Manual Backfill Approval Pack v70F

Date: 2026-05-31

## Decision

Add a source-only Weekly Candidate Brief recovery runbook so a missed weekly report has a safe manual response path
without provider live access, cache write, actual import, Gmail send, workflow edits, or trading action.

## Rationale

v70D diagnosed the missing Saturday JST report incident and v70E added a metadata-only sentinel. v70F defines what an
operator may consider next when the sentinel reports a missing weekly report, while keeping execution and approval
boundaries explicit.

## Safe Recovery Paths

- Re-run schedule diagnostic and sentinel checks.
- Optionally regenerate local Weekly Candidate Brief markdown/copy/email preview artifacts after human operator choice.
- Repair local launchd or approve a GitHub Actions workflow only through a separate human approval boundary.

## Manual Backfill Approval Boundary

- This pack does not approve backfill execution by itself.
- Manual backfill is a human operator choice.
- Backfill candidates may write generated report artifacts under `reports/YYYY-MM-DD/`.
- Gmail send is not approved.
- Workflow changes are not approved.
- Provider live access, cache write, actual refresh/import, manual actual import, raw persistence, and trading action are
  not approved.

## Explicit Non-Approval

- provider live access: not approved
- live HTTP: not approved
- Tiingo API call: not approved
- Stooq / Yahoo / Polygon live fetch: not approved
- cache write: not approved
- actual refresh/import: not approved
- manual actual import: not approved
- raw OHLCV persistence: not approved
- raw API response persistence: not approved
- reports-private raw data write: not approved
- Git-tracked raw data write: not approved
- env/secret display: not approved
- Gmail send: not approved
- workflow changes: not applied
- trading action: not approved

## Next Confidence Check

After any manual backfill or scheduler repair, run the v70E sentinel and confirm `expected_report_present`.
