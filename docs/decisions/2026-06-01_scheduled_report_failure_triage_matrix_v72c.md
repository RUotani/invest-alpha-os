# Scheduled Report Failure Triage Matrix v72C

Date: 2026-06-01

## Decision

Add a source-only triage matrix for future weekly report non-delivery incidents.

The matrix separates scheduler failure, CLI failure, report generation failure, delivery/export failure, timezone
mismatch, missing secret, permission failure, and silent failure while preserving source-only boundaries.

## Evidence Boundary

- secret values are never displayed
- raw market data is not read or written
- live HTTP and provider access are not used
- `.github/workflows` files are not modified
- cache write and actual refresh/import remain forbidden

## Triage Order

1. scheduler failure
2. timezone mismatch
3. permission failure
4. missing secret
5. CLI failure
6. report generation failure
7. delivery/export failure
8. silent failure

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

Create a long-run development progress snapshot that summarizes v63B through the latest milestone by domain without
using a single overall percentage.
