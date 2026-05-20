# R6.17-A — Opt-in US cache preview smoke（read-only · operator）

**ステータス**: **完了 · `main` 反映予定**（docs-only PR）。  
**実装（`main`）**: **`879fe47`** · PR **#16** squash merge。

---

## 1. 実行条件

| 項目 | 値 |
|---|---|
| 日付（JST daily ラベル） | 2026-05-19 実施記録（inventory）/ 2026-05-20（daily 出力ファイル名） |
| cache_root | `outputs/market_data/us_daily_bars`（local · gitignore） |
| CLI | `daily --us-cache-preview`（**opt-in**） |
| live HTTP | **なし** |
| cache write | **なし** |
| secrets / `.env` | **未出力 · 未コミット** |

---

## 2. Inventory smoke（read-only）

`debug us-daily-bars-cache-inventory --cache-root outputs/market_data/us_daily_bars --format json`

| 指標 | 値 |
|---|---:|
| total_symbols | 16 |
| ok | 16 |
| missing | 0 |
| invalid | 0 |
| insufficient | 0 |
| stale_unknown | 0 |
| fresh_enough | 13 |
| stale | 3 |
| freshness_unknown | 0 |
| newest_latest_date | 2026-05-18 |
| freshness_cutoff_date | 2026-05-13 |

**stale symbols（参考）**: MSFT · GOOGL · GLDM（fixture / 古い bar 由来 · プレビューでは note 明示）

---

## 3. Daily smoke

### Default（`--us-cache-preview` なし）

- **`### US Cache Preview (opt-in)` 節なし** · exit 0
- J-Quants 行は clean env（`JQUANTS_*` unset）で既知の stub/disabled 表示

### Opt-in（`daily --us-cache-preview`）

- preview 節 **あり** · Markdown 表（許可列のみ）
- **stale note**: `stale — returns not used` ×3（MSFT/GOOGL/GLDM 行）
- **aggregate score**: 算出なし（節内 disclaimer: “No aggregate score.”）
- **forbidden terms**（preview 節のみ）: buy/sell/recommendation/allocation/portfolio/veto/macro/production — **検出なし**
- **live_http**: false

---

## 4. 運用境界

- **default enable なし** · `market_data.yaml` の US momentum gate は変更していない
- 本 smoke は **read-only 確認** · 定期運用は operator 判断
- production decision / R6.17+ daily 接続は **別承認**

---

## 5. 関連

- [docs/69_r6_17_b_opt_in_us_cache_preview_runbook.md](./69_r6_17_b_opt_in_us_cache_preview_runbook.md) — operator runbook（R6.17-B）
- [docs/65_r6_17_opt_in_us_cache_preview_plan.md](./65_r6_17_opt_in_us_cache_preview_plan.md)
- [docs/67_r6_17_opt_in_us_cache_preview_implementation.md](./67_r6_17_opt_in_us_cache_preview_implementation.md)
