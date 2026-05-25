# Codex review — wave22 (post wave7 Q/R)

| Class | Count |
|---|---:|
| BLOCKER | 0 |
| SHOULD_FIX | 2 (fixed in PR) |
| NICE_TO_HAVE | 1 — US matched 3/10 until fresh weeks |
| DEFERRED_OPS_FREEZE | 0 |

## Fixed

1. `post-refresh-smoke` JSON — top-level `us_forward` / `peer_sync_forward` aliases (scripts no longer see `None`)
2. `forward_p3_recommended_actions` — peer ≥10 shows `usable (N matched)` not `16/10`

## Tests

post_p10 + forward_p3 + weekly targeted pytest
