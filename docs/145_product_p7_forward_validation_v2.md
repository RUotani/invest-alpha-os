# Product P7 — Forward-return validation v2

**Status**: implemented · cache-only · observation only

---

## CLI

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns \
  --horizons 5,20,60 \
  --format markdown
```

## v2 additions

| Feature | Behavior |
|---------|----------|
| Positive horizons | `--horizons` must be positive integers; `0`/negative/malformed → exit 2 |
| Quality buckets | Per horizon: count, avg, median, hit rates, best/worst |
| Sample guard | `empty` / `thin` (<10 matched) / `usable` |
| veto-at-t | Not in observation_log; deferred to P5 v3 (weekly quality snapshot) |

## Interpretation

- **thin/empty**: do not draw signal-quality conclusions from buckets.
- Buckets are exploratory; not investment advice.

## References

- MVP design: [docs/142](./142_product_p3_forward_return_validation_design.md)
- MVP runbook: [docs/143](./143_product_p5_us_forward_return_validation_mvp.md)
