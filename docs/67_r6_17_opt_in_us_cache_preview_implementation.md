# R6.17 — Opt-in US cache-only preview (implementation)

**ステータス**: **ブランチ作業のみ**（PR 未 merge）。ブランチ: **`work/r6-17-opt-in-us-cache-preview-implementation`**。

## 実装概要

- **CLI**: `daily --us-cache-preview`（**default off**）
- **Module**: `reports/us_cache_preview_opt_in.py` — inventory + metrics table
- **Metrics**: `return_1d` · `volume_status` in `us_daily_bars_metrics.py`

## Contracts

- **volume_status**: prior-25 average (latest excluded); high ≥2.0 · low &lt;0.5 · normal otherwise · unknown if &lt;5 prior bars
- **return_1d**: horizons `[1, 5, 20]`
- **stale note**: `stale — returns not used` (no aggregate score)
- **benchmarks**: SPY/QQQ/TLT/GLDM warn when stale; preview does not stop

## Non-goals

- No live HTTP · no cache write
- No daily/signals default enable
- No Veto / portfolio / macro · no trading recommendation

## Tests

- `tests/test_us_daily_bars_metrics.py`
- `tests/test_us_cache_preview_opt_in.py`
