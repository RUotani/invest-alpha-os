# Cache-Write Operator Signoff Sheet v68

Date: 2026-05-30

## Decision

SIGNOFF-16 is represented as a human-fillable operator signoff sheet before any Tiingo private/local cache-write pilot
can be approved. The sheet is source-only and records required operator fields, cache location checks, forbidden raw
data locations, retention/inventory obligations, purge/rollback checks, data quality preconditions, and explicit
approval phrase boundaries.

## Rationale

v67 created the cache-write readiness gate, but the gate remained abstract. Cache write must not depend on implicit
interpretation of a source decision or placeholder approval phrase. A human operator needs a deterministic checklist
that makes unresolved items visible before raw provider data can be written anywhere.

## Boundaries

- Cache write remains not approved.
- Actual refresh/import remains not approved and separate from cache write.
- Provider live access remains not approved.
- Raw OHLCV persistence remains not approved.
- Trading action remains not approved.
- Source Git, reports-private, GitHub artifacts, ChatGPT/Cursor pasted content, public outputs, and broker/manual raw
  data mixing remain forbidden raw-data locations.

## Progression

```text
v67 readiness gate
→ v68 operator signoff sheet
→ future human path selection and approval package
→ future Cursor/local cache-write pilot
→ result review
→ actual import readiness
```

## Future Cache-Write Pilot Requirements

A future Cursor/local cache-write pilot requires all of the following before execution:

- SIGNOFF-16 completed by a human.
- Private/local cache path selected and recorded.
- Cache path verified as Git-ignored, private/local, and outside reports-private.
- Retention owner, raw inventory rule, purge dry-run, rollback, and post-purge verification accepted.
- Cache-write approval phrase issued in a separate future runtime/operator context.
- No actual import or trading action included in the cache-write pilot.

## Explicit Non-Approval

- provider live access: not approved
- cache write: not approved
- actual refresh/import: not approved
- manual actual import: not approved
- raw OHLCV persistence: not approved
- reports-private raw data: not approved
- env/secret display: not approved
- trading action: not approved

## Next Decision Point

After the operator completes SIGNOFF-16 and selects a private/local cache path, decide whether to prepare a future
cache-write pilot approval package. That future package must still be execution-specific and must not imply actual
refresh/import readiness.
