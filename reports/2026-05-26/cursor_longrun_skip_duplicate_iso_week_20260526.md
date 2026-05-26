# Cursor longrun wave — skip duplicate ISO week (2026-05-26)

## PR theme

Opt-in `--skip-duplicate-iso-week` for L1 weekly writes + read-only `p3_weekly_write_plan` in forward-p3-status.

## Motivation

L1 without skip logged 16 rows but matched stayed 1/10 — duplicate ISO weeks dominate dead_rows.

## Changes

- `us_signal_iso_week_dedupe.py` — shared keys + write plan
- `us_signals_batch.py` — skip flag (default off)
- `weekly_us_observation` + CLI flag
- `forward_p3_status` — `p3_weekly_write_plan` JSON/markdown

## Tests

24+ product tests PASS
