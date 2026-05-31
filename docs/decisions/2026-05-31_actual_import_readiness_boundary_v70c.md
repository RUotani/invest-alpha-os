# Actual Import Separation, Quarantine Boundary, and Readiness Matrix v70C

Date: 2026-05-31

## Decision

Add a source-only actual import readiness boundary so cache-write pilot approval, cache-write pilot result review, actual
refresh/import, manual actual import, and trading action cannot be confused.

## Rationale

v70 created the future cache-write pilot approval packet, and v70B created the future result review gate. Neither one
approves actual refresh/import. v70C records that separation as an explicit matrix and quarantine boundary before any
future cache-write pilot result can be interpreted as import readiness.

## Boundaries

- Cache-write pilot approval does not imply actual refresh/import approval.
- A passing cache-write pilot result review is required before actual import can be discussed, but it is not sufficient.
- Pilot cache data remains quarantined from production/import paths.
- Automatic promotion from pilot cache to actual import is not allowed.
- Raw provider data remains private/local only and is not allowed in Git, reports-private, ChatGPT/Cursor pasted text, or
  public outputs.
- Trading action remains separate and not approved.

## Required Future Human Approval

- Future cache-write pilot execution still requires the exact cache-write approval phrase in that future runtime context.
- Actual refresh/import requires a separate approval package and the exact actual refresh/import approval phrase in a
  separate future context.
- Manual actual import and trading action require separate approvals and are outside this package.

## Current Readiness Matrix

| Area | Current Status |
|---|---|
| cache write pilot | future approval required |
| cache write pilot result review | not run |
| actual import | not ready |
| manual actual import | not ready |
| trading action | not approved |

## Explicit Non-Approval

- provider live access: not approved
- live HTTP: not approved
- Tiingo API call: not approved
- cache write: not approved
- actual refresh/import: not approved
- manual actual import: not approved
- raw OHLCV persistence: not approved
- raw API response persistence: not approved
- reports-private raw data write: not approved
- Git-tracked raw data write: not approved
- env/secret display: not approved
- broker/manual raw data handling: not approved
- trading action: not approved

## Next Decision Point

Stop at v70C unless a new human instruction is issued. The next safe choices are either explicit cache-write pilot
approval in a future runtime context, or a separate source-only actual import approval package draft.
