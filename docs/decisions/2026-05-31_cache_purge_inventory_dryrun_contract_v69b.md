# Cache Purge / Inventory Dry-Run Contract and Redacted Manifest Schema v69B

Date: 2026-05-31

## Decision

Define a source-only purge/inventory dry-run contract and redacted manifest schema before any future Tiingo private/local
cache-write pilot. The contract prepares reversibility and auditability without reading raw OHLCV, scanning the
filesystem, deleting files, writing cache, or contacting providers.

## Rationale

v69 recorded the candidate cache path and future pilot approval package. A future cache-write pilot also needs a
predefined inventory and purge contract so that raw cache files can be accounted for and removed after an approved pilot.
The contract must be designed before execution, but it must not itself become an execution tool.

## Redacted Manifest Policy

Allowed fields are metadata-only aggregate labels such as provider name, asset scope, symbol count, file count, coarse
date range label, schema version, hash presence boolean, optional aggregate raw row count, and an explicit
`no_raw_rows_embedded_boolean`.

Forbidden fields include open, high, low, close, adjusted close, volume rows, raw API responses, per-row OHLCV data,
secret values, and broker/manual raw data.

## Boundaries

- No file deletion is executed.
- No raw OHLCV is read.
- No provider API call is executed.
- No cache write is executed.
- No actual refresh/import is executed.
- The candidate cache path remains candidate-only.
- Destructive purge requires future explicit approval.
- Redacted manifest contains metadata categories only, not raw OHLCV rows.

## Explicit Non-Approval

- provider live access: not approved
- cache write: not approved
- actual refresh/import: not approved
- manual actual import: not approved
- raw OHLCV read or persistence: not approved
- raw API response persistence: not approved
- reports-private raw data: not approved
- Git-tracked raw data: not approved
- destructive purge / file deletion: not approved
- env/secret display: not approved
- trading action: not approved

## Next Decision Point

Prepare a v70 Cursor/local Tiingo private local cache-write pilot runbook as source-only. The v70 runbook must still not
execute provider access or cache write unless a future explicit cache-write approval phrase is issued in that runtime
context.
