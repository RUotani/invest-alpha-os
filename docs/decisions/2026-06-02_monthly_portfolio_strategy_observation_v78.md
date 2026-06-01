# Monthly Portfolio Strategy Observation v78

Date: 2026-06-02

## Decision

Add a source-only monthly portfolio strategy observation pack for human-redacted month-end portfolio summaries.

The pack supports:

- monthly portfolio snapshot template and validator
- core/satellite allocation guardrail report
- generic cleanup candidate observation matrix
- monthly ChatGPT portfolio review pack
- ChatGPT context pack / main-development handoff status

## Rationale

The user now provides a monthly portfolio Excel near month-end, but this milestone must not parse raw Excel, broker
exports, broker APIs, live prices, or order history. A redacted/manual monthly snapshot contract gives ChatGPT enough
context to review allocation drift, cash buffer pressure, individual-stock exposure, and cleanup candidates without
crossing data or trading gates.

## 2026-05 Corrected Example

The 2026-05 month-end example uses the human-confirmed correction that OLC is `22.4万円`, not `224.0万円`.

Corrected approximate values:

- total assets: `4,327.9万円`
- mortgage balance: `3,432.0万円`
- net worth: `895.9万円`
- cash: `508.2万円`
- INDEX: `2,088.2万円`
- individual stocks: `846.3万円`
- bonds: `582.7万円`
- GOLD: `234.5万円`
- crypto/high-beta proxy: `57.5万円`
- leveraged: `10.5万円`

## Core/Satellite Direction

Core should be mutual funds, broad ETFs, and index exposure. Individual stocks should be treated as a learning and
verification satellite, not the main battlefield. The pack reports individual-stock overweight as an observation-only
review pressure, not as a trade instruction.

## Raw Data Boundary

This pack may read only a human-created redacted JSON snapshot. It is not a broker export parser, raw Excel parser,
live price fetcher, cache writer, actual import, or broker automation tool.

## Explicit Non-Approval

- provider live access: not approved
- live HTTP: not approved
- cache write: not approved
- cache directory creation: not approved
- actual refresh/import: not approved
- manual actual import: not approved
- broker API access: not approved
- broker login: not approved
- raw broker export parsing: not approved
- raw Excel direct parsing: not approved
- raw broker data persistence: not approved
- raw OHLCV/API persistence: not approved
- reports-private raw data write: not approved
- Git-tracked raw data write: not approved
- env/secret display: not approved
- dependency / pyproject changes: not approved
- `.github/workflows` direct changes: not approved
- trading action / order placement: not approved

## Main Development Handoff

v78 keeps DCA/nanpin work as a thin sub-tool after v76. The next main line remains:

1. observe the 2026-06-06 weekly scheduled run
2. decide cache-write pilot execution only after explicit approval
3. continue actual import readiness only after cache-write acceptance
4. expand portfolio strategy reporting without trading wording
