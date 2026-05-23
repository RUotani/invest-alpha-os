# Product P5 — US forward-return validation MVP

**Status**: superseded by v2 · see **[docs/145](./145_product_p7_forward_validation_v2.md)** · **cache-only** · observation only

---

## CLI

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --help

.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns \
  --observation-log outputs/observation_log/observation_log.jsonl \
  --cache-dir outputs/market_data/us_daily_bars \
  --horizons 5,20,60 \
  --format markdown
```

## Behavior

- Reads `us_cache_signal observation_only` rows from `observation_log.jsonl`
- Joins `created_at` date to cached US daily bars (last bar on/before event date)
- Computes session-forward returns for horizons (default **5, 20, 60**)
- Aggregates `by_symbol` / `by_signal_label` averages
- **Fail-closed** on invalid JSONL; controlled skip with `skipped_reasons` otherwise

## Safety

- No live HTTP · no cache write · no trading recommendations
- Design reference: [docs/142](./142_product_p3_forward_return_validation_design.md)
