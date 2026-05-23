# Product P9/P11 — Observation log usability and veto-at-t join

**Status**: implemented · cache-only · observation only

---

## P9 — Forward validation usability

- `sample_quality`: `empty` / `thin` / `usable` with `interpretation`, `needed_more_samples`, `next_commands`
- CLI: `validate us-forward-returns --format markdown`
- Weekly: `weekly-us-observation --write-observation-log` then validate

## P11 — Veto-at-t in observation_log

- Notes may include `veto_triggered=true|false` and `veto_rules=rule1,rule2`
- `log us-signals-batch` / weekly cycle pass `quality_snapshot` when logging
- Forward report: `veto_at_t` joined or `not_in_observation_log` for legacy rows; `by_veto_status` buckets

## P10 — US 30+ tier-1 (read-only)

```bash
.venv/bin/python -m invis_alpha_os.cli.main us-universe-expansion-plan --tier 1 --missing-only
```

Live HTTP / cache write require explicit approval.
