# Product P9/P11 — Observation log usability and veto-at-t join

**Status**: implemented · cache-only · observation only  
**Related**: [docs/150](./150_product_observation_log_weekly_runbook.md), [docs/160](./160_product_weekly_operator_one_pager.md), [docs/161](./161_product_forward_validation_fresh_log_guidance.md), [docs/162](./162_product_p10_tier1_evidence_pack.md), [docs/163](./163_product_forward_validation_post_refresh_smoke.md)

---

## P9 — Forward validation usability

- `sample_quality`: `empty` / `thin` / `usable` with `interpretation`, `needed_more_samples`, `next_commands`
- CLI: `validate us-forward-returns --format markdown`
- Weekly: `weekly-us-observation --write-observation-log` then validate（runbook: [docs/150](./150_product_observation_log_weekly_runbook.md) · one-pager: [docs/160](./160_product_weekly_operator_one_pager.md)）
- Stale cache / fresh log: [docs/161](./161_product_forward_validation_fresh_log_guidance.md)
- Post P10 refresh smoke: [docs/163](./163_product_forward_validation_post_refresh_smoke.md)

## P11 — Veto-at-t in observation_log

- Notes may include `veto_triggered=true|false` and `veto_rules=rule1,rule2`
- `log us-signals-batch` / weekly cycle pass `quality_snapshot` when logging
- Forward report: `veto_at_t` joined or `not_in_observation_log` for legacy rows; `by_veto_status` buckets

## P10 — US 30+ tier-1 (read-only)

```bash
.venv/bin/python -m invis_alpha_os.cli.main us-universe-expansion-plan --tier 1 --missing-only
```

Live HTTP / cache write require explicit approval（[docs/162](./162_product_p10_tier1_evidence_pack.md) · [docs/155](./155_product_p10_tier1_refresh_risk_boundary.md)）。
