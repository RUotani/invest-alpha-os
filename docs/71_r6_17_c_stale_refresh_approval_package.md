# R6.17-C — Stale refresh approval package（MSFT / GOOGL / GLDM）

**ステータス**: **承認パッケージのみ** · **実行なし**。実行は **`.agent/r6_17_stale_refresh_longpack_draft.md`**（別ユーザー承認後）。

---

## 1. Purpose

- **MSFT** · **GOOGL** · **GLDM** の stale を解消する **gated ingest** の事前承認文書
- **live HTTP** と **cache write** を伴うため **本パッケージ承認 ≠ 自動実行**

---

## 2. Targets

| Symbol | 理由 |
|---|---|
| MSFT | `freshness_status=stale`（fixture / 古い bar） |
| GOOGL | 同上 |
| GLDM | 同上 |

**Expected inventory shift**:

| 指標 | 前 | 後（目標） |
|---|---:|---:|
| fresh_enough | 13 | **16** |
| stale | 3 | **0** |
| ok | 16 | **16** |
| missing | 0 | **0** |

---

## 3. Required approvals

| Gate | 内容 |
|---|---|
| Live HTTP | **`CONFIRM_US_LIVE_HTTP=YES`**（operator · 明示） |
| Cache write | **`CONFIRM_US_CACHE_WRITE=YES`**（operator · 明示） |
| Symbol list | **MSFT, GOOGL, GLDM のみ**（追加は別承認） |
| Operator | ChatGPT / ユーザーが実行 Longpack を **別途承認** |
| Bundling | **default enablement と同時に実施しない** |

**Local**: **`STOOQ_APIKEY`** が `.env` にあること（値は **出力・コミット禁止**）。

---

## 4. Execution constraints

- **per-symbol** gated path（[docs/61](./61_r6_16_c_operator_gated_ingest_design.md)）
- **live no-write** → `preview_ok` / success 確認 → **write**
- **after inventory**（read-only）必須
- `validation_error` / parse failure で **停止**
- **batch write** は本パッケージでは **明示リスト 3 銘柄のみ**
- **code / workflow / Makefile / pyproject 変更なし**

---

## 5. Rollback / quarantine

- cache JSON は **local / gitignore**
- 不良ファイルは対象 `{SYMBOL}.json` を **手動 quarantine**（削除または退避）
- after inventory で `status` / `freshness_status` を再確認
- **cache JSON を git commit しない**

---

## 6. Decision checklist（実行前）

- [ ] `STOOQ_APIKEY` が local `.env` にある（値は見せない）
- [ ] 対象は **MSFT / GOOGL / GLDM のみ**
- [ ] stale refresh がまだ必要（inventory で stale 3 確認）
- [ ] default enablement を **同梱しない**
- [ ] live HTTP / cache write 承認を **明示**
- [ ] 実行は **専用 Longpack**（draft は実行しない）

---

## 7. 関連

- [docs/69_r6_17_b_opt_in_us_cache_preview_runbook.md](./69_r6_17_b_opt_in_us_cache_preview_runbook.md) §6
- `.agent/r6_17_stale_refresh_longpack_draft.md`
