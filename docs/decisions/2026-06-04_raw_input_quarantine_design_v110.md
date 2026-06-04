# Raw Input Quarantine Design v110

Date: 2026-06-04

## Decision

Add a declaration-only raw-input quarantine contract and stdout-only CLI. The contract classifies safe manifests,
review-required declarations, and hard-gate-blocked declarations without receiving a raw path or reading raw payloads.

## Boundary

- Safe fixture/sanitized/redacted declarations may be accepted for review.
- Missing metadata and quality warnings require manual review.
- Raw Excel, broker export, sensitive identifiers, actual import, cache write, broker API, and secrets are blocked.
- `import_allowed` and `cache_write_allowed` are always `False`.

## Integration

The contract uses v107 taxonomy only to normalize declared validation keys. It does not change existing validators,
v109 data-quality review, or actual-import behavior. CLI `raw-input-quarantine-review` accepts declaration fields only
and writes nothing.

## Counterargument

A manifest can be false or incomplete. An accepted fixture/sanitized declaration proves only that the declaration is
safe to review; it does not prove the underlying data is accurate, current, or approved for import.

## Explicit Non-Approval

- raw Excel / broker export parsing, broker API, live HTTP: not approved / not executed
- cache write / actual import / manual import: not approved / not executed
- env/secret display, workflow, dependency, pyproject, or Makefile change: not approved / not executed
- trading action or real email send: not approved / not executed
