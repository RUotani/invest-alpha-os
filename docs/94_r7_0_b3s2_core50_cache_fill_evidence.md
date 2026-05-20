# R7.0-B3S2 — JP Core50 Cache Fill Evidence

**作成日**: 2026-05-20

---

## 1. Purpose

R7.0-B3S（バッチ≤3・60s で 429 停止後）からの継続。残り Core50 に対し **1 銘柄/バッチ**・**120s 間隔**で gated ingest を行い、キャッシュ検証 **≥80 bars** 基準で **≥40/50** を達成した記録。

---

## 2. State Capsule

```text
phase: R7.0-B3S2 JP Core50 cache fill
mode: gated live HTTP + cache write
universe: config/jp_universe_core50.yaml
date_range: 2025-06-01 … 2026-02-17
batch_size: 1
delay_seconds: 120
start_ok: 30/50
end_ok: 40/50
target: >=40/50
stop_reason: target_reached
http_status_400: none
http_status_429: none
evidence_dir: outputs/operator/discovery_eval/2026-05-20/r7_0_b3s2/
```

---

## 3. Checkpoint summary

ローカル `checkpoint.json`: `stop_reason` = **target_reached** · ingest 済み銘柄 **10**（各 `written: 1`）。

---

## 4. Ingest batches（記録のみ）

CLI: `CONFIRM_LIVE_HTTP=YES` · `scripts/load_jquants_env.py` · `debug jquants-watchlist-bars-cache` · `--live --write-cache`

| # | code | cache_written_count | HTTP |
|---:|---|:---:|:---|
| 1 | 6594 | 1 | ok |
| 2 | 7269 | 1 | ok |
| 3 | 6902 | 1 | ok |
| 4 | 6920 | 1 | ok |
| 5 | 6146 | 1 | ok |
| 6 | 6273 | 1 | ok |
| 7 | 6367 | 1 | ok |
| 8 | 6645 | 1 | ok |
| 9 | 7735 | 1 | ok |
| 10 | 7741 | 1 | ok |

リスト上の残銘柄（7741 以降）は **目標 40 到達により未実行**。

---

## 5. Verification（監査）

- Core50 OK 数: **`load_jquants_daily_bars_cache(code)` + len(bars) ≥ 80**
- **30 → 40/50**

---

## 6. Safety

| 項目 | 結果 |
|---|---|
| live HTTP | gated（`CONFIRM_LIVE_HTTP` · `JQUANTS_ALLOW_LIVE_HTTP`） |
| cache JSON | **local only · git 未コミット** |
| secrets / `.env` / token | doc に含めず |
| trading recommendation | なし |
| daily/signals **default** | 変更なし |

---

## 7. Recommendation

**R7.0-B4** 再評価 · その後 **R7.0-C** US Universe Scanner MVP の可否を判断。

---

## 関連

- [docs/88](./88_r7_0_b3s_jp_core50_cache_fill_continuation.md)（B3S）
- [docs/87](./87_r7_0_b3r_jp_core50_cache_retry_diagnostics.md)（B3R）
