# Product P4 — Weekly US observation cycle

**Status**: PR branch `work/product-p3-p4-weekly-observation` · **default off** for all existing commands

---

## One-command weekly flow (US cache-only)

```bash
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation \
  --manifest-out outputs/signals/weekly_us_manifest.json \
  --write-observation-log \
  --with-peer-sync \
  --with-daily-report \
  --format markdown
```

Steps performed:

1. Build watchlist manifest (explicit paths; no directory scan)
2. US signals batch preview (cache-only)
3. Signal quality snapshot (metrics + momentum + veto)
4. Optional `observation_log` append
5. Optional `daily` with US opt-in sections
6. Optional `--with-peer-sync` peer divergence section (cache-only)

Dry-run (no manifest file under `outputs/`):

```bash
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation --dry-run
```

## Observation log validation

```bash
.venv/bin/python -m invis_alpha_os.cli.main log us-signals-summary
```

## P3/US expansion (read-only)

```bash
.venv/bin/python -m invis_alpha_os.cli.main us-cache-expansion-report --limit 25
```

No live HTTP · no cache write in these commands.

## References

- P2b observation: [docs/140](./140_product_p2b_observation_log.md)
- Forward-return design: [docs/142](./142_product_p3_forward_return_validation_design.md)
