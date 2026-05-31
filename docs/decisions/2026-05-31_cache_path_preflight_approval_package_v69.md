# Cache Path Preflight and Cache-Write Pilot Approval Package v69

Date: 2026-05-31

## Decision

The candidate private/local cache path is recorded as a source-only preflight input:

```text
$HOME/.local/share/invest-alpha-os/private-cache/tiingo-ohlcv
```

The path is structurally suitable for a future Tiingo private/local cache-write pilot because it is user-local,
provider-scoped, and outside source Git and reports-private by string-level policy. This decision does not approve or
execute cache write.

## Rationale

v68 made SIGNOFF-16 human-fillable. v69 narrows the next approval package by recording the future cache path candidate
and making the preflight boundary machine-readable. The preflight is intentionally string-level only: it does not expand
`$HOME`, probe the filesystem, create directories, write files, read raw OHLCV, or contact providers.

## Approval Boundary

- Cache write remains not approved.
- Actual refresh/import remains not approved.
- Provider live access remains not approved.
- Raw OHLCV persistence remains not approved.
- Git-tracked raw data remains forbidden.
- reports-private raw data remains forbidden.
- Trading action remains not approved.
- The phrases `cache writeを実行してよい` and `actual refresh/importを実行してよい` remain not issued.

## Required Future Operator Confirmations

- SIGNOFF-16 human review completed.
- Candidate cache path approved by operator.
- Cache path Git-ignore or outside-source status verified at future runtime.
- Retention owner and period recorded.
- Purge dry-run and rollback process accepted.
- Post-purge verification checklist accepted.
- Cache-write approval phrase issued in a separate future runtime context.

## Progression

```text
v67 readiness gate
→ v68 operator signoff sheet
→ v69 cache path preflight / approval package
→ v69B purge/inventory dry-run contract and redacted manifest schema
→ future Cursor/local cache-write pilot runbook
→ future explicit cache-write approval
→ pilot result review
→ actual import readiness
```

## Next Decision Point

Prepare a source-only purge/inventory dry-run contract and redacted manifest schema so that any future cache-write pilot
can be reversible and auditable without exposing raw OHLCV.
