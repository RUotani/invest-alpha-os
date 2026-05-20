# R6.17-D — Stale refresh status（MSFT / GOOGL / GLDM · operator）

**日付**: 2026-05-20 · **main 起点**: `ee8dda6`  
**性質**: gated **live HTTP** + **cache write**（3 symbols のみ）· **cache JSON 未コミット**

---

## 1. Codex pre-execution review

- **Verdict**: `APPROVED_WITH_MINOR_NOTES`（blocker なし）
- **Minor note**: docs/70 · docs/01 の R6.17-C「ブランチのみ」表記 → 本 PR / docs microfix で **main 反映済み**に更新

---

## 2. Inventory before / after

| 指標 | Before | After |
|---|---:|---:|
| total_symbols | 16 | 16 |
| ok | 16 | 16 |
| missing | 0 | 0 |
| invalid | 0 | 0 |
| insufficient | 0 | 0 |
| stale_unknown | 0 | 0 |
| fresh_enough | 13 | **16** |
| stale | 3 | **0** |
| freshness_unknown | 0 | 0 |

**Before stale**: MSFT · GOOGL · GLDM  
**After stale**: （なし）

---

## 3. Per-symbol execution

| Symbol | Live preview | Cache write | Before | After | latest_date (after) |
|---|---|---|---|---|---|
| MSFT | `preview_ok` · write=false | `success` · write=true | stale | fresh_enough | 2026-05-19 |
| GOOGL | `preview_ok` · write=false | `success` · write=true | stale | fresh_enough | 2026-05-19 |
| GLDM | `preview_ok` · write=false | `success` · write=true | stale | fresh_enough | 2026-05-19 |

**Provider**: `stooq_preview` · gates: `CONFIRM_US_LIVE_HTTP=YES` · `CONFIRM_US_CACHE_WRITE=YES`  
**Non-target symbols**: **not written**

---

## 4. Daily smoke（post-refresh · read-only）

| Check | Result |
|---|---|
| default daily | **no** US cache preview section |
| `daily --us-cache-preview` | preview section **yes** |
| stale notes (MSFT/GOOGL/GLDM) | **0**（post-refresh） |
| forbidden terms in preview | **none** detected |

---

## 5. Safety

- cache JSON: **local/gitignore only** · **not committed**
- `.env` / API keys: **not printed**
- product code / workflow / Makefile / pyproject: **unchanged**
- daily/signals **default**: **unchanged**
- default enablement: **not performed**

---

## 6. 関連

- [docs/71_r6_17_c_stale_refresh_approval_package.md](./71_r6_17_c_stale_refresh_approval_package.md)
- [docs/69_r6_17_b_opt_in_us_cache_preview_runbook.md](./69_r6_17_b_opt_in_us_cache_preview_runbook.md)
