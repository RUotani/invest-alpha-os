# Merge Queue — product_massive_longrun_20260524

## Merge order (stacked)

```text
1. #218 → main
2. Rebase #219 base to main → merge
3. Rebase #220 base to main → merge
4. Rebase #221 base to main → merge
```

| PR | Title | Branch | CI | Mergeable | Files | Risk | Depends on | Recommendation |
|---|---|---|---|---|---:|---|---|---|
| #218 | ops smoke + peer_sync observation_log | work/product-ops-smoke-and-continue-20260524 | SUCCESS | yes | ~15 | LOW | — | **MERGE** |
| #219 | observation-health snapshot (Wave B) | work/product-wave-b-observation-health-20260524 | pending | stacked | ~7 | LOW | #218 | **MERGE** (after #218) |
| #220 | portfolio by_symbol/by_tag (Wave C) | work/product-wave-c-portfolio-20260524 | pending | stacked | ~3 | LOW | #219 | **MERGE** (after #219) |
| #221 | P10 boundary + signals inventory docs | TBD | pending | stacked | ~5 | LOW | #220 | **MERGE** (after #220) |

## Human-only (not in queue)

- `--write-observation-log` / `log peer-sync-snapshot` — outputs write · explicit approval
- P10 tier-1 live refresh — **DO_NOT_MERGE** execution; docs only

## ChatGPT prompt

```text
merge_queue: reports/2026-05-24/merge_queue_product_massive_longrun_20260524.md
Merge #218→#221 in order after CI green. Do not run tier-1 refresh or observation_log writes.
```
