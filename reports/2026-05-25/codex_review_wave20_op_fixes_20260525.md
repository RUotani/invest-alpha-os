# Codex review — wave20 (post O/P + product longrun)

**Scope**: `forward_p3_*`, `portfolio_readiness`, `weekly_us_observation` checklist, `post_p10_refresh_smoke`, `ops_smoke_report`  
**Reviewer**: Cursor Agent (Codex-style per `RULES.md` §2)

## Summary

| Class | Count |
|---|---:|
| BLOCKER | 0 |
| SHOULD_FIX_BEFORE_MERGE | 4 (addressed in #269) |
| NICE_TO_HAVE | 2 |
| DEFERRED_OPS_FREEZE | 0 |

## SHOULD_FIX_BEFORE_MERGE (fixed)

1. **Stale approval copy** — `forward_p3_recommended_actions` referenced obsolete wave2 IDs (E/F). → Generic **Gated + chat approval** wording.
2. **P3 progress label** — `12/10 toward usable` when matched > threshold. → `usable (N matched)` when `matched >= 10`.
3. **Rubric alignment** — `state_percent_matches_rubric` ignored YAML `accepted_tier`. → Compare `human_accepted_tier` to computed `tier`.
4. **Research checklist** — peer partial next_action still said "when approved". → **gated … chat approval**.

## NICE_TO_HAVE (deferred)

1. `build_ops_smoke_report` calls full `evaluate_portfolio_readiness` (heavy); cache or split light reader later.
2. US forward `matched=3` with 16 historical stale skips — product limitation; document only (not code bug).

## Tests

```bash
env -u STOOQ_APIKEY .venv/bin/python -m pytest -q \
  tests/test_post_p10_refresh_smoke.py \
  tests/test_portfolio_readiness.py \
  tests/test_weekly_trend_p2_supplemental.py \
  tests/test_forward_p3_status.py
```

## Safety

- No trading recommendation wording added.
- No default behavior change on daily/signals.
- 285A coverage exists elsewhere (`tests/test_momentum_signals.py`).
