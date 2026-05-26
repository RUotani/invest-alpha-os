# Cursor longrun wave 3 — P3 L1 write gate (2026-05-26)

## PR #285

Machine-readable `l1_gate` in `p3_weekly_write_plan`:
- `ready` when write_now_count > 0
- `blocked_duplicate_iso_week` when all planned writes duplicate
- Surfaces in forward-p3-status, post-refresh-smoke, portfolio readiness, observation-health

## Current local gate (post L1 skip)

- write_now_count: 0
- l1_status: blocked_duplicate_iso_week
- matched: 1/10
