# Position-Aware DCA Decision Pack v74

Date: 2026-06-01

## Decision

Add a source-only position-aware DCA decision pack for redacted manual position snapshots, starting with JFE Holdings
`5411.T` and Honda Motor `7267.T`.

## Rationale

Averaging down should not be decided from price decline or dividend yield alone. The pack separates four questions:

- whether price is cheaper
- whether business value is better
- whether the investment thesis remains intact
- whether portfolio allocation and cash buffer permit additional exposure

## Raw Broker Data Boundary

Raw broker data, broker exports, account statements, order history, and credentials remain forbidden. The source pack
only accepts typed redacted/manual position snapshot fields and fixture snapshots for tests.

## ChatGPT Boundary

ChatGPT receives a copy-ready redacted summary for strategy dialogue. The pack does not emit trading instructions, order
placement commands, broker automation, or buy/sell recommendations.

## Starter Profiles

The first static profiles cover:

- JFE: steel cycle, domestic demand flatness, China/export pressure, raw material spread risk, leverage/capital
  intensity, dividend floor vs payout sustainability
- Honda: EV-related losses / strategic reset, US tariff sensitivity, China/Asia competition, auto margin pressure,
  motorcycle segment offset, shareholder return / low PBR thesis

## Explicit Non-Approval

- provider live access: not approved
- live HTTP: not approved
- cache write: not approved
- actual refresh/import: not approved
- manual actual import: not approved
- broker API access: not approved
- raw broker export parsing: not approved
- raw OHLCV/API persistence: not approved
- env/secret display: not approved
- dependency / pyproject changes: not approved
- `.github/workflows` direct changes: not approved
- trading action / order placement / broker automation: not approved

## Next Decision Point

The next step is to replace fixture placeholders with a human-redacted position snapshot if the operator wants
household-specific allocation discussion. Any actual trade decision remains outside this pack.
