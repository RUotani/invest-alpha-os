# R7.0-B3 — JP Core50 Gated Cache Fill

**日付**: 2026-05-20 · **main**: `9d6df7d`+ · **性質**: gated ingest attempt + coverage re-audit

---

## 1. Purpose

R7.0-B2 で Core50（50 銘柄）を定義したが cache カバレッジは **9/50**。既存 gated J-Quants bulk コマンドで missing 41 銘柄の cache fill を試行し、再評価する。

---

## 2. Starting point

| 指標 | 値 |
|---|---|
| Core50 symbols | 50 |
| JP cache files | 11 |
| cache ok (≥80 bars) | **9/50** |
| missing | **41** |
| ranked ok | 9 |

---

## 3. Command / gate confirmation

| 項目 | 値 |
|---|---|
| Bulk command | `debug jquants-watchlist-bars-cache` |
| Per-code command | `debug jquants-daily-bars-cache --code …` |
| Live HTTP gate | `CONFIRM_LIVE_HTTP=YES` + `JQUANTS_ALLOW_LIVE_HTTP=true`（`load_jquants_env.py run --set`） |
| Cache write | `--write-cache`（`--live` 必須） |
| Date range used | `2024-02-18` … `2026-02-17`（契約ウィンドウ内） |
| Wrapper | `scripts/load_jquants_env.py run --env-file .env` |

---

## 4. Batch plan

- Missing symbols: **41**
- Batch size: **≤10**
- Planned batches: **5**
- Executed: **1**（Longpack: バッチ失敗時は停止）

---

## 5. Execution result

### Batch 1（10 symbols）

| 項目 | 値 |
|---|---|
| exit | 1 |
| `cache_written_count` | **0** |
| `success_count` | 0 |
| `error_count` | 10 |
| Failure reasons | `http_status_400`（5）· `http_status_429`（5） |

**Batches 2–5**: **not run**（batch 1 全件失敗のため停止）

### Symbols in batch 1

6758, 6861, 8035, 6857, 9984, 9432, 9433, 9983, 8306, 8316

---

## 6. Cache coverage after

| 指標 | before | after |
|---|---:|---:|
| cache JSON files | 11 | 11 |
| Core50 ok (≥80 bars) | 9 | **9** |
| missing | 41 | **41** |
| ranked ok | 9 | **9** |

**No cache files added** — ingest did not succeed.

---

## 7. Discover-jp summary

変化なし。top ranked は B2 と同様（5802 score 3 等）。**41 銘柄は insufficient** のまま。

---

## 8. Safety

- cache JSON **not committed**
- secrets / `.env` **not printed**
- no trading recommendations · no default enablement
- batch size ≤10 enforced
- live HTTP only via explicit gates

---

## 9. Next recommendation

1. **Provider / rate-limit**: HTTP 429 → バッチ間スリープ・日次クォータ確認。400 → 日付範囲・銘柄コード・API プランを確認。
2. **Retry B3** with smaller batches (e.g. 3 symbols) + delay between batches after 429 clears.
3. **9984** 等 all-alpha wire は cache 書き込み時に別途 wire 制約あり（docs/85）。
4. Coverage が **≥40/50** になるまで **R7.0-C US MVP は延期**。
5. ローカル証跡: `outputs/operator/discovery_eval/2026-05-20/r7_0_b3/`

---

## 関連

- [docs/85](./85_r7_0_b2_jp_universe_cache_expansion.md)
- [docs/84](./84_r7_0_b1_jp_discovery_scanner_evaluation.md)
