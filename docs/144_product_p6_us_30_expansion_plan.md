# Product P6 — US 30+ expansion plan (config-first)

**Status**: implemented · **read-only** · no gated refresh in this PR

---

## Config

[`config/us_universe_expansion_30.yaml`](../config/us_universe_expansion_30.yaml) — ~38 observation targets with `tier`, `theme`, `reason`.

## CLI

```bash
.venv/bin/python -m invis_alpha_os.cli.main us-universe-expansion-plan --format markdown
.venv/bin/python -m invis_alpha_os.cli.main us-universe-expansion-plan --format json
```

## Output

- existing cache symbols vs configured targets
- `missing_symbols` · `parse_ok_symbols` · `parse_fail_symbols`
- `next_gated_refresh_order` (tier-sorted, cache missing only)

## Safety

- No live HTTP · no cache write in this command
- Complements P3 `us-cache-expansion-report` (watchlist + discovery)
