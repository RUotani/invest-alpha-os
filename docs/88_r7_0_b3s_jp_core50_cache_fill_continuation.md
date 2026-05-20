# R7.0-B3S — JP Core50 Cache Fill Continuation

**日付**: 2026-05-20 · **main 起点**: `defdbb1`（R6.19-D 取り込み後）· **性質**: gated continuation + docs-only evidence

---

## 1. Purpose

R7.0-B3R で確立した安全ポリシー（短い日付範囲 · バッチ ≤3 · 60s 間隔 · 400/429 で即停止）で、残り **31** 銘柄の Core50 cache fill を継続し、**≥40/50** を目標とする。

---

## 2. Starting point (PR #36 / B3R)

| 指標 | 値 |
|---|---|
| Core50 ok（≥80 bars · cache 監査） | **19/50** |
| missing | **31** |
| cache JSON files | 21 |
| 成功ポリシー | `2025-06-01` … `2026-02-17` · batch ≤3 · 60s |

---

## 3. Known-good mitigation（継続）

| 項目 | 値 |
|---|---|
| date range | `2025-06-01` … `2026-02-17` |
| batch size | ≤3 |
| inter-batch delay | 60s |
| stop policy | バッチ JSON に `http_status_400` / `http_status_429` があれば **次バッチへ進まない** |
| gates | `CONFIRM_LIVE_HTTP=YES` · `JQUANTS_ALLOW_LIVE_HTTP=true` · `--live --write-cache` |

コマンド（B3R 同型）:

```bash
CONFIRM_LIVE_HTTP=YES .venv/bin/python scripts/load_jquants_env.py run \
  --env-file .env --set JQUANTS_ALLOW_LIVE_HTTP=true -- \
  .venv/bin/python -m invis_alpha_os.cli.main debug jquants-watchlist-bars-cache \
  --from-date 2025-06-01 --to-date 2026-02-17 \
  --codes "CODE1,CODE2,CODE3" --live --write-cache
```

---

## 4. Execution result

| 項目 | 値 |
|---|---|
| batches planned | **11**（31 銘柄 ÷ 3） |
| batches attempted | **4** |
| batches succeeded（429/400 なし） | **3** |
| symbols ingested（cache write 成功） | **11** |
| stop reason | **`http_status_429`**（batch 4 · code **6594**） |

### バッチ内訳

| batch | codes | result |
|---:|---|---|
| 1 | 8411, 8058, 8001 | 3/3 success |
| 2 | 8031, 6503, 7012 | 3/3 success |
| 3 | 7013, 5401, 4063 | 3/3 success |
| 4 | 4188, 6098, 6594 | 2/3 success · **6594 → 429** → **停止** |

**ingested symbols**: 8411, 8058, 8001, 8031, 6503, 7012, 7013, 5401, 4063, 4188, 6098

ローカル証跡: `outputs/operator/discovery_eval/2026-05-20/r7_0_b3s/`（**未コミット**）

---

## 5. Coverage before / after

**指標**: `load_jquants_daily_bars_cache(code)` かつ **≥80 bars**（B3R/B2 と同じ監査）

| 指標 | before | after | Δ |
|---|---:|---:|---:|
| Core50 ok | 19 | **30** | +11 |
| missing | 31 | **20** | −11 |
| cache JSON files | 21 | **32** | +11 |
| 目標 ≥40/50 | — | **未達** | あと **10** 銘柄 |

**missing after（20）**: 6594, 7269, 6902, 6920, 6146, 6273, 6367, 6645, 7735, 7741, 7751, 7974, 8766, 8725, 8750, 9020, 9022, 9101, 9104, 9503

---

## 6. Discover-jp summary

`discover-jp` は cache がある銘柄のみランキング出力するため、**全 50 銘柄のカバレッジ指標には使わない**（B3R 同様）。

| 指標 | before | after |
|---|---:|---:|
| ranked rows | 20 | 20 |
| `data_quality=ok` | 20 | 20 |

**after ラベル上位**: near_high 6 · rapid_mover_20d 4 · rapid_mover_5d 1 · overheat_caution 1

---

## 7. Safety

- cache JSON · operator outputs · `.env` · credentials/token: **コミットなし**
- live HTTP: **gated** · 残 missing のみ · バッチ ≤3
- trading / allocation / macro / default 変更: **なし**
- Gmail send: **なし**

---

## 8. Recommendation

| 条件 | 推奨 |
|---|---|
| ok **≥40/50**（未達: 30/50） | **B3S2** を継続: 残り 20 銘柄 · 同ポリシー · **429 後は 90–120s 待機**または **1 銘柄/バッチ**で 6594 から再開 |
| ok ≥40 到達後 | **R7.0-B4** 再評価 → その後 **R7.0-C** US MVP |
| 即時 | **R7.0-C は延期**（Core50 カバレッジ不足） |

**tests（ローカル）**: `test_jp_universe_core50_config` · `test_jp_universe_scanner_mvp` · `test_symbol_display_names` — **16 passed**
