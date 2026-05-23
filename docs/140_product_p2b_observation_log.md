# Product P2b — US signals observation_log (opt-in)

**Status**: PR **#207** · default **off** · observation only

---

## Commands

```bash
# Standalone (requires valid batch manifest)
.venv/bin/python -m invis_alpha_os.cli.main log us-signals-batch \
  --manifest outputs/signals/p1_us_16_cache_manifest.json

# With daily report (manifest required)
.venv/bin/python -m invis_alpha_os.cli.main daily \
  --us-signals-dry-run-manifest outputs/signals/p1_us_16_cache_manifest.json \
  --write-observation-log
```

## Behavior

- One `observation_log.jsonl` row per manifest entry (symbol + status note).
- Notes include `observation_only` and `not buy/sell advice` — no buy/sell wording.
- Invalid manifest → **exit 2**; daily report file is **not** written when `--write-observation-log` fails.
- No live HTTP · no cache write · manifest paths resolved from repo root.

## AAPL fixture

`tests/fixtures/us_daily_bars/AAPL.json` is a **bars array** for `debug us-daily-bars-cache-import` only (not envelope JSON for signals preview).

## References

- P1 smoke: [docs/137](./137_product_p1_us_signals_cache_smoke.md)
- P2 evidence: [docs/139](./139_product_p2_msft_aapl_evidence_pack.md)
