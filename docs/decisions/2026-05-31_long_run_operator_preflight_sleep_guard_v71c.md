# Long-Run Operator Preflight Sleep-Guard Pack v71C

Date: 2026-05-31

## Decision

Standardize a source-only Long-Run operator preflight block for MacBook sleep prevention and invest-alpha-os hard-gate
reminders.

Future Long-Run Max instructions, Cursor handoffs, and operator runbooks should include the following operator command
before starting a long unattended run:

```bash
caffeinate -dimsu -t 43200
```

This is an operator preflight instruction only. It does not approve macOS settings changes from the coding agent and does
not approve any repository workflow change.

## Rationale

The weekly report missing incident showed that long unattended development and scheduled-report recovery work need a
repeatable operator preflight. Display sleep settings alone are not sufficient. The preflight must be explicit, reusable,
and paired with the same hard-gate reminders used for source-only weekly-report and provider/cache work.

## Standard Block Requirements

- run `caffeinate -dimsu -t 43200` in a separate Terminal window
- keep MacBook connected to AC power
- keep the lid open
- keep the caffeinate Terminal window running until the Codex/Cursor run is finished
- do not rely on display sleep settings alone
- do not change macOS system settings from the coding agent
- repeat invest-alpha-os hard gates, including live HTTP, provider access, cache write, actual import, raw data,
  `.github/workflows`, dependency/pyproject, and trading boundaries

## Explicit Non-Approval

- macOS system settings change: not approved
- `.github/workflows` direct change: not approved
- provider live access: not approved
- live HTTP: not approved
- cache write: not approved
- actual refresh/import: not approved
- raw OHLCV/API persistence: not approved
- trading action: not approved

## Next Decision Point

Create a scheduled-report assurance snapshot that combines v70D-v71C into a next-run readiness matrix.
