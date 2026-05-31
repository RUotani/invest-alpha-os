# Weekly Report Manual Backfill Command Pack v72B

Date: 2026-06-01

## Decision

Add a source-only manual backfill command pack for missed weekly candidate brief reports.

The pack defines command contracts and expected generated output paths for a human-approved backfill, but it does not
execute backfill, provider access, cache write, actual refresh/import, Gmail send, or workflow changes.

## Scope

- report date and missed report date are explicit
- timezone defaults to `Asia/Tokyo`
- generated outputs are constrained to weekly report markdown/json/copy artifacts, email preview directory, and operator
  status JSON
- raw data outputs are forbidden
- commands are shown as copy-ready contracts and marked `execution_approved_by_this_pack=false`

## Explicit Non-Approval

- manual backfill execution: not approved
- provider live access: not approved
- live HTTP: not approved
- cache write: not approved
- actual refresh/import: not approved
- raw OHLCV/API persistence: not approved
- reports-private raw data: not approved
- Gmail send: not approved
- `.github/workflows` direct change: not approved
- trading action: not approved

## Next Decision Point

Build a scheduled report failure triage matrix that separates scheduler, CLI, report generation, delivery/export,
timezone, secret, permission, and silent failures.
