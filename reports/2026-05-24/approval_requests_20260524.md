# 人間承認リクエスト — 2026-05-24

## 3行サマリー
- **#245 / #246 は Cursor 判断で MERGE 済**（`origin/main` @ `395c146`）。
- **承認 A（必須）**: P10 tier-1 **AMD** cache refresh — `STOOQ_APIKEY` 未設定のため現状 BLOCKED。
- **承認 B（任意）**: 週次 `weekly-us-observation --write-observation-log`（outputs 書込）。

---

## Cursor merge 判断（完了）

| PR | 判定 | 根拠 |
|---|---|---|
| #245 | **MERGE** | CI SUCCESS · read-only product · 失敗系テストあり · 5 files LOW risk |
| #246 | **MERGE** | CI SUCCESS（rebase 後）· markdown リンクのみ · 3 files LOW risk |

---

## 承認リクエスト A — P10 tier-1 AMD refresh（BLOCKED）

**種別**: live HTTP + cache write + secrets（git 外 env）  
**現状ブロッカー**: `STOOQ_APIKEY` = **missing**（シェル確認 2026-05-24）  
**対象 symbol**: **AMD**（tier-1 missing · docs/162）  
**参照**: [docs/162](docs/162_product_p10_tier1_evidence_pack.md) · [docs/163](docs/163_product_forward_validation_post_refresh_smoke.md) · [docs/155](docs/155_product_p10_tier1_refresh_risk_boundary.md)

### 承認いただく内容

1. git 外に `STOOQ_APIKEY` を設定（`.env` commit 禁止）
2. **AMD のみ** Stooq live fetch → `outputs/market_data/us_daily_bars/AMD.json` 書込
3. 事後 read-only smoke（docs/163）と `outputs/evidence/p10_tier1_post_YYYYMMDD.md` 記録

### 承認しない場合

- tier-1 gap は継続 · forward validation は `cache_stale` / thin のまま想定内

### 承認テンプレ（コピペ返信可）

```text
承認 A: P10 AMD refresh
- YES / NO
- STOOQ_APIKEY: 設定済み（値は貼らない）
- 対象: AMD のみ
- 実行担当: 人間ターミナル / Cursor（YES の場合のみ Agent 実行可）
- approval ref: （issue / Longpack 番号任意）
```

### Agent が YES 後に実行するコマンド（参考 · 値は出さない）

docs/162 Step B チェックリスト完了後、承認記録付きで gated ingest を実行（具体コマンドは runbook / CLI help に従う）。**承認なしでは実行しない。**

---

## 承認リクエスト B — 週次 observation_log 蓄積（任意）

**種別**: outputs 書込（`observation_log.jsonl`）  
**参照**: [docs/150](docs/150_product_observation_log_weekly_runbook.md) · [docs/160](docs/160_product_weekly_operator_one_pager.md)

### 承認いただく内容

```bash
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation \
  --manifest-out outputs/signals/weekly_us_manifest.json \
  --write-observation-log \
  --with-peer-sync \
  --format markdown
```

### 承認テンプレ

```text
承認 B: weekly --write-observation-log
- YES / NO
- 実行日: YYYY-MM-DD
```

---

## 承認リクエスト C — portfolio 進捗 %（任意 · 数値確定）

**種別**: STATE.md 人間判断  
**参照**: [docs/154](docs/154_product_portfolio_progress_proposal.md)  
**現状**: `[要確認]%` 維持（rubric P0–P3 は CLI で参照可）

### 承認テンプレ

```text
承認 C: portfolio domain %
- 確定値: __% または 要確認維持
- 根拠: docs/154 milestone __
```

---

## 承認リクエスト D — Gmail 本番送信（任意 · 別 runbook）

**種別**: Gmail 送信  
**参照**: [docs/81](docs/81_gmail_daily_report_runbook.md)  
**現状**: dry-run のみ推奨。本番 send は未リクエスト実行。

### 承認テンプレ

```text
承認 D: Gmail send
- YES / NO（dry-run のみ / 本番）
```

---

## 実行済み（承認不要 · read-only）

- #245 · #246 squash merge
- main 上 pytest: **1056 passed**
- `snapshot observation-health`（read-only）— `peer_sync_forward` ブロック確認可能（#245 反映後）

---

## 次の Cursor アクション（あなたの返信待ち）

| 承認 | YES 時に Agent が行うこと |
|---|---|
| A | preflight 再確認 → gated AMD refresh（live HTTP + cache write）→ docs/163 smoke → evidence MD |
| B | 上記 weekly コマンド実行 → read-only サマリ報告 |
| C | STATE.md 更新案 PR |
| D | docs/81 に従い dry-run または送信（承認範囲内） |
