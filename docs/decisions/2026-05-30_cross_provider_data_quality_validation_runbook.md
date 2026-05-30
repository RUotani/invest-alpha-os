# Cross-Provider Data Quality Validation Runbook

Date: 2026-05-30

## Decision

After v63B/v64 Tiingo live-fetch viability, the next execution package must be a no-write cross-provider data-quality
validation runbook. It prepares comparison across Tiingo, Stooq, Yahoo Finance/yfinance, and optional Polygon, but it
does not execute provider access, write cache, import data, or store raw OHLCV.

## Rationale

Tiingo v63B proved that the pilot universe can be fetched and that base/adjusted fields are present. It did not prove
price accuracy, adjusted-price calculation correctness, cross-provider consistency, split/dividend handling quality,
long-history completeness, delisted coverage, rate-limit stability, or cache/database legal suitability.

The tolerance policy is intentionally conservative. A 0.5% close/adjusted-close relative tolerance and 5% volume
tolerance are red-flag thresholds, not proof of correctness. Any unexplained major provider disagreement blocks cache
write and actual import.

No-write discipline remains because the next task is validation, not durable state mutation. Raw OHLCV rows, raw API
responses, individual daily prices, CSV price series, and JSON raw market data must not be persisted to source or
reports-private.

Cache write remains a separate decision because it adds storage, retention, purge/rollback, provider terms, and
SIGNOFF-16 legal/storage obligations that a no-write comparison cannot satisfy alone.

## Provider Positioning

- Tiingo: v63B live-fetch-only provider viability passed, but data quality still needs cross-provider review.
- Stooq: free fallback and comparison provider.
- Yahoo Finance/yfinance: convenient comparison-only provider, not the production primary source.
- Polygon: optional and cost-sensitive production-quality comparison, only if token/account access is separately
  approved later.

## Operating Boundary

- future approval phrase may be documented but is not issued by this decision
- provider live access remains unapproved in this source-only pack
- cache write remains unapproved
- actual import remains unapproved
- reports-private must receive redacted summaries only if a separate approved sync is performed later

## Next Decision Point

The next approval decision is whether to execute the no-write cross-provider validation pilot with the explicit public
OHLCV live-fetch approval phrase. Cache-write readiness must wait until that validation result is reviewed.
