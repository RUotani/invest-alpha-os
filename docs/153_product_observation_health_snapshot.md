# Product — observation health snapshot (Wave B)

**Status**: read-only · observation only

---

## Command

```bash
.venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format markdown
.venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format json
```

Aggregates:

- US signal rows (`us_signals`)
- **`repeat_summary`** (top-level JSON; also under `us_signals.repeat_summary`)
- peer_sync rows (`peer_sync`)
- portfolio linkage counts
- forward validation `sample_quality` (when signal rows exist)
- log integrity (JSON parse errors, unclassified notes)

## When to use

- Weekly ops check before/after `--write-observation-log` (read-only safe anytime)
- Diagnose thin/empty forward validation sample

## Related

- [docs/150](./150_product_observation_log_weekly_runbook.md)
- [docs/152](./152_product_ops_smoke_report_20260524.md)
