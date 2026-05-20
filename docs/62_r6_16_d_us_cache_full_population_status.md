# R6.16-D — US cache full population status（operator manual · docs-only）

**ステータス**: **完了 · `main` 反映済み**（PR **#10** squash merge · branch **`work/r6-16-d-us-cache-full-population-docs`**）。  
**性質**: **運用記録**（手動 / bulk **gated cache ingest** 完了）。watchlist **16 symbols · ok 16 · missing 0**（missing **13 → 0**）。**cache JSON** と **`.env` は local / gitignore · 未コミット**。**コード変更なし** · **ingest plan CLI なし** · **daily / signals 接続は別承認**。  
**関連**: **R6.16-E** freshness 拡張（PR **#11** · **`39304a1`**）は **別物**（population 記録 vs `ok` / `fresh_enough`）。

---

## 1. inventory 結果（2026-05-19 · read-only）

`debug us-daily-bars-cache-inventory --cache-root outputs/market_data/us_daily_bars`

| 指標 | 値 |
|---|---|
| total_symbols | 16 |
| ok | **16** |
| missing | **0** |
| invalid | 0 |
| insufficient | 0 |
| stale_unknown | 0 |

**missing 13 → 0** まで解消（初期 smoke: ok 3 · missing 13 → 最終: ok 16 · missing 0）。

---

## 2. 投入経路

- 既存 **gated single-symbol** path: `debug us-provider-cache-preview`（`stooq_preview`）
- 各銘柄: **live no-write**（`CONFIRM_US_LIVE_HTTP=YES` + `--live`）→ **preview_ok** 確認 → **explicit write**（`CONFIRM_US_CACHE_WRITE=YES` + `--write-cache`）
- 設計参照: [docs/61](./61_r6_16_c_operator_gated_ingest_design.md)（**実装 PR は別承認**）

---

## 3. 銘柄別 bar_count（inventory · ok）

| symbol | bar_count | 備考 |
|---|---|---|
| AAPL | 10504 | bulk 前に投入 |
| NVDA | 6871 | 同上 |
| QQQ | 6839 | 同上 |
| SPY | 5339 | 同上 |
| AMZN | 7291 | bulk 9 |
| META | 3519 | bulk 9 |
| TSLA | 3996 | bulk 9 |
| TLT | 5339 | bulk 9 |
| SLV | 5044 | bulk 9 |
| MSTR | 5339 | bulk 9 |
| COIN | 1280 | bulk 9 |
| MARA | 2969 | bulk 9 |
| TMF | 4298 | bulk 9 |
| MSFT | 72 | 初期 fixture 系 |
| GOOGL | 68 | 同上 |
| GLDM | 60 | 同上 |

---

## 4. 衛生・安全

- **cache JSON**: `outputs/market_data/us_daily_bars/*.json` — **`.gitignore`** · **未 commit**
- **`STOOQ_APIKEY`**: ローカル `.env` のみ — **未 commit**
- **本タスクの PR**: **docs-only**（product code 変更なし）
- **daily / US signals default**: **変更なし**（R6.17 は **別承認**）

---

## 5. `ok` vs `fresh enough`

- 全銘柄 **inventory `status=ok`**（検証通過 + freshness メタデータあり）
- **`fresh enough`（運用鮮度）** は inventory 未判定 — 例: MSFT/GOOGL/GLDM は bar 数が少ない · 長期履歴銘柄は last_date が古くないかは **別レビュー**

---

## 6. 次候補

- **freshness extension**: inventory に `freshness_status` 等（**別タスク**）
- **R6.16-C ingest plan CLI**: [docs/61](./61_r6_16_c_operator_gated_ingest_design.md) — **実装は別承認**
- **R6.17**: daily / signals cache-only 接続判断 — **別承認**
