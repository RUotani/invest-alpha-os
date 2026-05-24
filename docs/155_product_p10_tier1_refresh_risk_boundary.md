# Product P10 — tier-1 refresh risk boundary (Wave D)

**Status**: read-only · **execution forbidden without approval**

---

## Allowed (Agent / operator read-only)

- `us-universe-expansion-plan --tier 1 --missing-only`
- `validate peer-sync`, `weekly-us-observation --dry-run`
- `snapshot observation-health`
- Evidence template: [docs/151](./151_product_p10_tier1_refresh_evidence_template.md)

## Forbidden without explicit Longpack approval

- live HTTP / stooq fetch
- cache write to `outputs/market_data/us_daily_bars/`
- committing cache JSON or vendor payloads
- changing daily/signals defaults

## Stop conditions

- Rate limit / HTML response from vendor
- Symbol slug mismatch unresolved
- Missing rollback path for cache files

## Post-approval validation (read-only)

```bash
.venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format markdown
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation --dry-run --with-peer-sync
.venv/bin/python -m pytest -q
```

## Human sign-off fields

- approver name / date
- symbol list approved
- max symbols per batch
