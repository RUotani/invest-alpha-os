# Cross-Provider Validation Result Review and Stooq Policy

Date: 2026-05-30

## Decision

v65 cross-provider validation is recorded as `warn_manual_review_required`, not as a Tiingo failure. The warning is
reclassified as a provider-pair policy warning because Stooq does not provide an adjusted close series in the v65
result and should not be used as an adjusted-series oracle.

## Rationale

v65 succeeded across the required providers and 14-symbol universe with consistent row counts and date range. The
large close/volume deviations concentrated in Stooq-vs-Tiingo/Yahoo pairs, especially split-sensitive symbols such as
NVDA and AVGO. The likely root cause is a series-definition mismatch: Stooq non-adjusted/base close compared with
adjusted or differently adjusted Tiingo/Yahoo series.

Tiingo/Yahoo adjusted-close agreement matters more for adjusted-series sanity because both providers exposed adjusted
series and their maximum adjusted-close deviation was approximately 0.009% in the redacted v65 summary.

## Stooq Policy

- Stooq is a coverage, base-close, and fallback provider.
- Stooq is not an adjusted-series oracle unless an explicit adjusted series is available.
- Stooq adjusted comparison should be disabled when Stooq lacks adjusted close.
- Split-sensitive Stooq breaches require manual review, not automatic Tiingo failure classification.

## Cache-Write Boundary

Tiingo remains viable as the first private/local cache candidate after provider-pair policy refinement. Cache write is
still not ready because SIGNOFF-16, cache location design, retention policy, purge/rollback policy, terms/cache
acknowledgement, and explicit cache-write approval are unresolved.

## Explicit Non-Approval

- provider live access: not approved by this source-only review
- cache write: not approved
- actual refresh/import: not approved
- manual actual import: not approved
- raw OHLCV persistence: not approved
- reports-private raw data: not approved
- trading action: not approved

## Next Decision Point

Prepare a cache-write readiness gate draft focused on SIGNOFF-16, private/local cache location, retention, purge and
rollback, terms acknowledgement, and approval phrase status.
