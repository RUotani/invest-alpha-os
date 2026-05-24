# Product — validate ops-smoke (consolidated read-only)

**Status**: read-only · observation only

---

## Command

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate ops-smoke --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate ops-smoke --format json --strict
```

Aggregates: watchlist manifest, signal quality, peer_sync, portfolio summary, observation health, peer_map config.

## Related

- [docs/152](./152_product_ops_smoke_report_20260524.md) (manual run log)
- [docs/153](./153_product_observation_health_snapshot.md)
