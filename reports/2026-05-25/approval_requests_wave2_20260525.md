# 人間承認リクエスト — wave2（2026-05-25）

## 3行サマリー
- **A/B/C は 2026-05-25 実行済み**（AMD P10 · weekly 74行 · portfolio 25%）。
- **現状 BLOCKER**: forward `matched=0` · `skip_pattern=mixed`（stale 16 + fresh 48）→ **E/F** が P3 解消に有効。
- **G** は P1 shadow 配置後。**D** は Gmail 本番（未実行）。

## ローカル read-only スナップショット（承認前）

| 項目 | 値 |
| --- | --- |
| `origin/main` | `d7ee3f7` |
| `post-refresh-smoke` | tier1_missing=0 · matched=0 · skip_pattern=mixed |
| `skipped_reasons` | stale=16 · insufficient_future=48 |
| observation_log | 74 lines |

---

<<< ここからコピペして返信 >>>

## 承認 E — 週次 observation_log 追記書込（推奨）

週次蓄積を継続し `as_of=` 行を増やす（forward fresh_log 側の解消）。

```text
承認 E: weekly --write-observation-log（2回目）
- YES / NO
- 実行日: 2026-05-__（空欄可）
- --with-peer-sync: YES（推奨） / NO
- 実行担当: Cursor / 人間ターミナル
```

**実行コマンド（YES 後のみ）**:

```bash
cd /Users/uotani/Projects/invest-alpha-os
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation \
  --write-observation-log --with-peer-sync --format markdown
```

---

## 承認 F — P10 tier-1 cache refresh（stale_cache 解消 · 推奨）

`cache_stale_event_after_cache_end=16` 向け。tier-1 missing は **0**（AMD 済み）だが、コア銘柄の cache 末尾更新が必要な可能性。

```text
承認 F: P10 tier-1 cache refresh（live + write-cache）
- YES / NO
- STOOQ_APIKEY: 設定済み（値は貼らない）
- 対象 symbol（カンマ区切り · 空欄=MSFT,NVDA,GOOGL,AAPL）: ___________
- 1銘柄ずつ実行: YES（推奨） / 一括
- approval ref: （任意）
```

**1銘柄テンプレ（YES 後 · 例 MSFT）**:

```bash
cd /Users/uotani/Projects/invest-alpha-os
# source .env は git 外 · 値をチャットに貼らない
.venv/bin/python -m invis_alpha_os.cli.main debug us-provider-cache-preview \
  --symbol MSFT --live --write-cache
```

**事後 read-only**:

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate post-refresh-smoke --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --format markdown
```

---

## 承認 G — portfolio 進捗 % 更新（P1 完了後）

`docs/165` で shadow + `thesis_evidence_ids` を配置した後、rubric **P0+P1 → 40%** 候補。

```text
承認 G: portfolio domain %
- YES / NO
- 確定値: 40%（P0+P1） / __% / 要確認維持（25%）
- P1 完了確認: shadow 配置済み YES / NO
```

---

## 承認 D — Gmail 本番（任意 · 従来どおり）

```text
承認 D: Gmail send
- YES / NO
- モード: dry-run のみ / 本番1通
- 実行日: __
```

手順: [docs/81](../docs/81_r6_19_b_daily_0700_gmail_delivery_runbook.md)

---

## 手動タスク H — portfolio P1（承認不要 · 人間作業）

Agent は `outputs/shadow_portfolio/positions.jsonl` を無承認で書き込まない。

1. [docs/165](../../docs/165_product_shadow_portfolio_seed.md) に従い shadow 配置
2. `thesis_evidence_ids` に observation_log の `id` を設定
3. read-only 確認:

```bash
.venv/bin/python -m invis_alpha_os.cli.main snapshot portfolio-observation-summary --format markdown
.venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format markdown
```

完了後 **承認 G** を検討。

<<< ここまでコピペして返信 >>>

---

## 優先順位（Agent 推奨）

1. **E** + **F**（forward P3 向け · データ鮮度 + ログ蓄積）
2. **H**（人間 · P1 linkage）
3. **G**（% 確定）
4. **D**（Gmail · 任意）

前回実行記録: [approved_execution_report_20260525.md](./approved_execution_report_20260525.md)
