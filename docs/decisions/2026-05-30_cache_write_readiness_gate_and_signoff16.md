# Cache-Write Readiness Gate and SIGNOFF-16

Date: 2026-05-30

## Decision

Cache write is the next major gate after Tiingo provider viability and cross-provider validation review. It remains not
approved. v67 records the requirements for a future private/local Tiingo cache-write pilot without executing any live
fetch, cache write, actual import, or raw data persistence.

## Rationale

Tiingo is viable as the first private/local cache candidate after v63B, v65, and v66. That does not approve durable
storage. Cache/database writes introduce provider terms, raw data handling, retention, purge, rollback, and Git/report
contamination risks that must be governed separately.

Future cache/database capability is not ruled out. It is explicitly preserved behind SIGNOFF-16, a private/local cache
location policy, retention and purge rules, and a separate cache-write approval phrase.

## Raw Data Boundary

Raw OHLCV and raw provider responses cannot go to:

- source Git
- reports-private
- GitHub Actions artifacts
- ChatGPT or Cursor pasted prompts
- public outputs
- mixed broker/manual raw data areas

Only a future explicitly approved private/local cache location may hold raw data, and that location must be Git-ignored,
outside reports-private, inventoried, purgeable, and covered by a retention policy.

## Required Before Cache Write

- SIGNOFF-16 terms/cache suitability acknowledgement
- private/internal use and no redistribution acknowledgement
- approved private/local cache path
- Git-ignore and outside-reports-private verification
- retention period and owner
- purge/rollback procedure
- redacted summary output policy
- separate cache-write approval phrase

## Actual Import Boundary

Actual refresh/import remains a later and separate approval. A cache-write pilot cannot imply actual import approval.

## Next Decision Point

After SIGNOFF-16 and private/local storage policy are reviewed, decide whether to issue a separate cache-write pilot
approval for a small Tiingo subset such as SPY, QQQ, AAPL, and NVDA.
