# Generic Position-Aware Guard v76

Date: 2026-06-01

## Decision

Position-aware DCA support is limited to a thin, source-only generic guard that can be used for arbitrary symbols.
JFE `5411.T` and Honda `7267.T` remain starter examples and fixtures only. They must not drive symbol-specific
decision logic, fixed labels, or fixed ChatGPT prompts.

## Rationale

v74 and v75 proved that redacted position snapshots can support an observation-only average-down review, but the first
implementation was anchored to JFE/Honda examples. Keeping the feature in that shape would overfit a side use case and
pull development away from the main roadmap.

The v76 guard separates the minimum reusable conditions:

- cheap_price
- improved_business_value
- intact_thesis
- portfolio_permission
- cash_permission
- entry_trigger
- must_not_buy_blocker

The output labels are generic:

- `monitor_only`
- `wait_for_capitulation`
- `small_tranche_allowed`
- `dca_blocked_by_portfolio_risk`
- `dca_blocked_by_thesis_damage`
- `dca_blocked_by_cash_buffer`
- `requires_latest_market_review`

## Scope Boundary

This is not a deeper DCA engine. It does not perform live market review, provider access, broker access, trading
recommendations, order placement, portfolio automation, or actual import.

## JFE/Honda Handling

- JFE/Honda example profiles are retained only for v74/v75 continuity and starter fixtures.
- Default CLI symbol sets now include multiple JP and US examples.
- Redacted snapshot templates, validator output, strategy pack tables, and ChatGPT prompts use generic wording.

## Return To Main Development

After v76, stop deepening the DCA side feature unless a later roadmap explicitly reprioritizes it. The recommended
return line is:

1. weekly report observation and scheduled-report assurance
2. cache-write readiness and purge/inventory dry-run follow-through
3. actual import separation and quarantine boundary
4. portfolio strategy reporting that remains observation-only

## Explicit Non-Approval

- provider live access: not approved
- live HTTP: not approved
- cache write: not approved
- actual refresh/import: not approved
- manual actual import: not approved
- broker API access: not approved
- raw broker export parsing: not approved
- raw OHLCV/API persistence: not approved
- env secret display: not approved
- trading action or order placement: not approved
