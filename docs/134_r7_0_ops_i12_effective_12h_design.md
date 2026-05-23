# R7.0-Ops-I12 — Effective 12h productive longrun design

**Problem (I11)**: `max_prs=15` + `allow_early_completion` → ~18m run, 15/84 tasks, stacked PRs.

## Design pillars

| Mode | Purpose |
|---|---|
| **productive_waves** | Wave 1 primary (create PRs) → post-run-integrate → Wave 2 reserve if wall budget remains |
| **post-run-integrate** | `operator-runner post-run-integrate` audit/merge/consolidate (#185–#199 style batches) |
| **consolidation** | Stacked PRs → single squash PR vs `main` (I11 #200 pattern) |
| **reserve_continuation** | After integrate, new run with `skip-existing` + reserve/stretch tiers only |
| **durability_mode** | Separate profile: `no_early_completion`, min_runtime 720m, heartbeat allowed |

## Profile proposal: `true_longrun_12h_productive_v4`

- `max_prs_per_wave`: 12–15 (reviewable)
- `max_tasks_per_wave`: 24–30
- `waves`: 2–3 per 12h window with **integrate between waves** (human gate or `post-run-integrate --integrate`)
- `early_completion`: after **wave** completes, not after first pr_cap within wave
- `min_wall_minutes`: optional floor (e.g. 120m) before early exit on pr_cap

## CLI (J delivered)

```bash
operator-runner post-run-integrate --run-id <id> --pr-range 185-199 --dry-run
CONFIRM_PRODUCTIVE_PR_MERGE=YES operator-runner post-run-integrate --run-id <id> --execute --integrate
```

## I12 implementation slices

1. `productive_wave` field in evidence + runner script loop.
2. `post-run-integrate` consolidation auto-push PR (still no auto-merge).
3. Queue v4 with fresh task_ids per wave.
