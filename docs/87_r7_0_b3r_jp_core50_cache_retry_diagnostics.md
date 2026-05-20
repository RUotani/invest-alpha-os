# R7.0-B3R — JP Core50 Cache Retry Diagnostics

**日付**: 2026-05-20 · **main**: `fe8b8c7`+ · **性質**: gated diagnosis + small-batch retry

---

## 1. Purpose

R7.0-B3 の batch 1（10 銘柄）が HTTP 400/429 で全滅した原因を切り分け、安全な小バッチで cache fill を再試行する。

---

## 2. Starting point (PR #35)

| 指標 | 値 |
|---|---|
| Core50 ok | 9/50 |
| missing | 41 |
| B3 batch 1 | 10/10 `http_error`（400×5, 429×5） |
| cache files | 11 |
| date range (B3) | `2024-02-18` … `2026-02-17` |

---

## 3. Diagnosis

### 400 / 429 の解釈

| code | 意味 | 本件 |
|---|---|---|
| 429 | レート制限 | B3 の 10 銘柄一括で混在 |
| 400 | リクエスト不正 | **広い日付範囲 + バッチ負荷**の可能性 |

### One-symbol diagnostic（6758）

| 項目 | 値 |
|---|---|
| date range | `2025-06-01` … `2026-02-17`（契約ウィンドウ内） |
| `--live`（no `--write-cache`） | **success** · row_count **175** |
| B3 同等範囲（2024-02-18 起） | `http_status_400`（再現） |

**結論**: ゲート・コマンドは有効。**日付範囲を短縮**し、**バッチ ≤3 + 60s 間隔**で ingest 可能。

---

## 4. Retry policy

- diagnostic: 1 銘柄 · no write
- write test: 1 銘柄
- retry: **≤3 銘柄/バッチ** · **60s** 間隔 · 最大 **3 バッチ**（本 run）
- stop on 400/429: 遵守（バッチ 1–3 は clean）

---

## 5. Execution result

| step | result |
|---|---|
| diagnostic code | **6758** |
| one-symbol write | **pass**（175 bars → cache） |
| batch 1 (6861,8035,6857) | 3/3 success |
| batch 2 (9984,9432,9433) | 3/3 success |
| batch 3 (9983,8306,8316) | 3/3 success |
| batches attempted | **3**（+ diag write） |
| symbols filled this run | **10** |

**Date range used**: `2025-06-01` … `2026-02-17`

---

## 6. Coverage before / after

| 指標 | before | after |
|---|---:|---:|
| cache JSON files | 11 | **21** |
| Core50 ok (≥80 bars) | 9 | **19** |
| missing | 41 | **31** |
| ranked ok | 9 | **19** |

**Top labels（after）**: near_high 3 · rapid_mover_20d 4 · rapid_mover_5d 1 · overheat_caution 1

---

## 7. Remaining failures

- **31/50** 銘柄は依然 cache 未整備（本 run は 10 銘柄のみ ingest）
- 目標 ≥40/50 には **追加 B3R バッチ**（同ポリシー）が必要

---

## 8. Recommendation

1. **Continue B3R**: 残り 31 銘柄を 3×3 バッチ + 60s · 日付 `2025-06-01`–`2026-02-17`
2. **Avoid** B3 の 10 銘柄一括 + `2024-02-18` 起点の広範囲
3. **R7.0-C US MVP**: Core50 ok **≥40** まで延期（現状 19/50）

---

## 9. Safety

- cache JSON **not committed**
- secrets / `.env` **not printed**
- gates: `CONFIRM_LIVE_HTTP=YES` + `load_jquants_env --set JQUANTS_ALLOW_LIVE_HTTP=true`
- no trading recommendations · no default enablement

---

## ローカル証跡

`outputs/operator/discovery_eval/2026-05-20/r7_0_b3r/`
