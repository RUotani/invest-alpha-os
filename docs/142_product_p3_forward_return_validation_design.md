# Product P3 — Forward-return validation (design)

**Status**: design only · **no live labels** · observation only

---

## Goal

Measure whether cache-only **momentum_label** / veto state at time T aligns with **subsequent** cache-derived returns (T+5, T+20 trading days) — without trading advice.

## Inputs (read-only)

- `outputs/market_data/us_daily_bars/{SYMBOL}.json` (local; not committed)
- `observation_log.jsonl` rows with `us_cache_signal observation_only`
- `compute_us_daily_bars_basic_metrics` / `calculate_returns` on cached bars

## Proposed metrics (per observation row)

| Field | Definition |
|-------|------------|
| `symbol` | From observation_log |
| `observation_date` | `created_at` (JST date slice) |
| `momentum_label_at_t` | Parsed from note |
| `return_5d_forward` | Close return from observation bar date + 5 sessions |
| `return_20d_forward` | Same for 20 sessions |
| `veto_at_t` | From parallel quality snapshot or note extension |

## Non-goals

- No order / allocation language
- No automatic retraining
- No live HTTP backfill for missing forward windows

## Implementation PR (future)

1. `product forward-return-report --from-observation-log` (read-only)
2. Join observation rows to cache bars by symbol + date
3. Markdown summary: hit-rate buckets by label (not investment advice)

## JP Core50

Separate track under P3 JP — J-Quants gated ingest per [docs/136](./136_r7_0_product_pivot_signals_pack.md); not mixed with US forward-return v1.
