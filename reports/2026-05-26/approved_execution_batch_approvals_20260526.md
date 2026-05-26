# Approved execution — バッチ承認（2026-05-26）

**チャット承認**: L1（条件付き）· cache refresh · 重複週方針 · P3/70%（条件付き）· STATE.md

---

## 1. L1 バッチ — **1/2 実行（ゲート通過後）**

| 段階 | `will_be_matchable_after_date_rows` | 操作 |
| --- | --- | --- |
| cache refresh 前 | 0 | L1 保留 |
| cache refresh 後 | 8 | ゲート通過 |
| L1-1 後 | 16 | weekly write 実行 |

| 項目 | 値 |
| --- | --- |
| CLI | `weekly-us-observation --write-observation-log --with-peer-sync` |
| log | **514 → 534** (+20) |
| logged | 16 · skipped 0 |
| matched (normal) | **1/10**（変化なし） |

```text
承認 L1: YES · 回数=2 · 期限=2026-06-30
```
**残り 1 回** — 次回は `will_be_matchable` 再増加時のみ推奨（重複週 preflight 参照）。

---

## 2. cache refresh — **実行済**

| 銘柄 | CLI status |
| --- | --- |
| MSFT | success |
| NVDA | success |
| AAPL | success |
| AMZN | success |
| GOOGL | success |
| META | success |
| TSLA | success |
| GLDM | success |

```bash
env CONFIRM_US_LIVE_HTTP=YES CONFIRM_US_CACHE_WRITE=YES \
  .venv/bin/python -m invis_alpha_os.cli.main debug us-provider-cache-preview \
  --symbol SYMBOL --provider stooq_preview --live --write-cache
```

**注意（docs/161）**: ログ内の **historical stale 行**は matched に戻らない場合あり。新規 weekly 行が fresh cache を参照する。

---

## 3. 重複週整理方針 — **decision 記録**

- [docs/decisions/2026-05-26_observation_log_duplicate_week_policy.md](../../docs/decisions/2026-05-26_observation_log_duplicate_week_policy.md)

---

## 4. portfolio 70% / P3 — **保留（usable 未到達）**

| 指標 | 値 |
| --- | --- |
| matched_normal | 1/10 |
| sample_quality | thin |

usable 到達後に `config/portfolio_observation_acceptance.yaml` を **P0-P3 · 70%** へ更新（別 L3 相当承認）。

---

## 5. STATE.md — **更新済**

- `origin/main` @ `012032f` (#283)
- log **514**
- US forward **1/10** thin · peer usable
