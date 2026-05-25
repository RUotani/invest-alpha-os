# Codex review — wave21 (post wave6 O/P + product)

**Scope**: `forward_p3_status`, `weekly_us_observation`, `post_p10_refresh_smoke`

| Class | Count |
|---|---:|
| BLOCKER | 0 |
| SHOULD_FIX_BEFORE_MERGE | 0 (addressed in PR) |
| NICE_TO_HAVE | 1 — US matched 3/10 until new ISO weeks accumulate |
| DEFERRED_OPS_FREEZE | 0 |

## Fixed in PR

1. `forward_p3_status` — `recommended_actions`, `observation_log_lines`, markdown section
2. `post_p10` — tier-1 missing copy → Gated + chat approval
3. `weekly` — `observation_log_total_lines` + thin-forward reason cites log depth / docs/161

## Tests

22 passed (forward_p3, post_p10, weekly, trend)
