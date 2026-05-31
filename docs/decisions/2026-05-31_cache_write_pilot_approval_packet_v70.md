# Cache-Write Pilot Execution Runbook and Operator Approval Packet v70

Date: 2026-05-31

## Decision

Create a source-only operator approval packet for a future Cursor/local Tiingo private/local cache-write pilot. The
packet consolidates v67 readiness, v68 SIGNOFF-16 operator signoff, v69 cache path preflight, and v69B purge/inventory
dry-run contract into one future execution runbook.

## Rationale

The project now has the required preflight and rollback contract pieces, but a future cache-write pilot still needs an
execution-specific approval packet that is impossible to mistake for execution approval. The packet must list the exact
future pilot scope, required operator fields, stop conditions, output constraints, and approval phrase boundary before a
runtime task can be considered.

## Future Pilot Draft

- provider: Tiingo
- operation: `tiingo_private_local_cache_write_pilot`
- first subset: SPY, QQQ, AAPL, NVDA
- candidate cache path: `$HOME/.local/share/invest-alpha-os/private-cache/tiingo-ohlcv`
- data type: EOD OHLCV with adjusted fields if provider returns them
- storage: private/local only, Git-ignored, outside repo and outside reports-private
- allowed output: redacted summary, metadata, pass/fail, aggregate counts
- forbidden output: raw OHLCV, raw API response, raw CSV/JSON, broker/manual raw data, secret values

## Required Future Human Approval

This packet does not approve cache write. A future runtime/operator context must include the exact phrase:

```text
cache writeを実行してよい
```

That phrase approves only the specific cache-write pilot described in that future approval context. It does not approve
actual refresh/import, trading action, or raw data in reports-private, Git, GitHub artifacts, ChatGPT, Cursor, or public
outputs.

## Explicit Non-Approval

- provider live access: not approved
- cache write: not approved
- actual refresh/import: not approved
- manual actual import: not approved
- raw OHLCV persistence: not approved
- raw API response persistence: not approved
- reports-private raw data: not approved
- Git-tracked raw data: not approved
- env/secret display: not approved
- trading action: not approved

## Next Decision Point

Prepare a source-only cache-write pilot result review gate and data quality acceptance pack. Actual import must remain
separate until a future cache-write pilot is explicitly approved, executed, reviewed, and accepted.
