# Redacted Position Snapshot Input Pack v75

Date: 2026-06-01

## Decision

Add a source-only redacted position snapshot input pack so the operator can safely hand-create JFE `5411.T` and Honda
`7267.T` position summaries for ChatGPT strategy review.

## Rationale

v74 proved the position-aware DCA matrix, but it used fixture placeholders. A useful strategy discussion requires a
human-redacted snapshot with allocation, cash buffer, thesis status, and must-not-buy conditions. The input contract must
make the safe path easy without adding broker integrations.

## Scope

The pack adds:

- a JSON/Markdown redacted snapshot template
- a validator for human-created redacted JSON snapshots
- numerical consistency checks for market value, unrealized P/L, and unrealized P/L percent
- forbidden field/value detection for broker identifiers, secrets, raw exports, and order language
- a ChatGPT strategy pack that compares v74 placeholder labels with redacted position-aware labels
- a human input checklist for the next safe JFE/Honda household inputs

## Raw Data Boundary

This pack may read only a human-created redacted JSON object. It is not a raw broker export parser and does not support
broker statements, CSV exports, screenshots, login data, order history, or credentials.

## ChatGPT Boundary

The output is a redacted strategy dialogue pack. It does not emit trading recommendations, order placement commands,
broker automation, or execution instructions.

## Explicit Non-Approval

- provider live access: not approved
- live HTTP: not approved
- cache write: not approved
- actual refresh/import: not approved
- manual actual import: not approved
- broker API access: not approved
- broker login: not approved
- raw broker export parsing: not approved
- raw broker data persistence: not approved
- raw OHLCV/API persistence: not approved
- reports-private raw data write: not approved
- Git-tracked raw data write: not approved
- env/secret display: not approved
- dependency / pyproject changes: not approved
- `.github/workflows` direct changes: not approved
- trading action / order placement: not approved

## Next Decision Point

The next human step is to fill the redacted snapshot template with safe manual values. Any live data pull, broker access,
raw export parsing, or trade decision remains outside this source-only pack.
