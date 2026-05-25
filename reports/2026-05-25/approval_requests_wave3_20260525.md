# 人間承認リクエスト — wave3（2026-05-25）

## 3行サマリー
- **I/J 実行済み（2026-05-25 YES）** · log **114** · peer **8/10** · US **3/10**。
- stale_skips=16 は履歴行に残存 · 新規行は fresh cache 参照。
- 次: wave4 **M/N** — [approval_requests_wave4_20260525.md](./approval_requests_wave4_20260525.md)

実行記録: [approved_execution_report_wave3_ij_20260525.md](./approved_execution_report_wave3_ij_20260525.md)

## スナップショット（承認前 · read-only）

| 項目 | 値 |
| --- | --- |
| observation_log | 94 lines |
| us_forward | matched=3 · skip_pattern=mixed · stale_skips=16 |
| peer_sync_forward | matched=6 · thin |
| portfolio rubric | P0+P1 pass · P2 declining · P3 thin |
| docs_163_hard_pass | True |

---

<<< ここからコピペして返信 >>>

## 承認 I — 週次 observation_log 追記（3回目 · 推奨）

```text
承認 I: weekly --write-observation-log（3回目）
- YES / NO
- --with-peer-sync: YES（推奨） / NO
- 実行日: 2026-05-__
```

**YES 後コマンド**:

```bash
cd /Users/uotani/Projects/invest-alpha-os
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation \
  --write-observation-log --with-peer-sync --format markdown
```

---

## 承認 J — P10 cache refresh（stale_skip 銘柄 · 推奨）

read-only `stale_skip_by_symbol` 上位（各1件）+ 不足分は expansion plan で補完可。

```text
承認 J: P10 cache refresh（live + write-cache）
- YES / NO
- STOOQ_APIKEY: 設定済み（値は貼らない）
- 対象 symbol: MSFT,NVDA,AAPL,AMZN,GOOGL,META,AMD,GLDM
  （空欄=上記 · カンマ編集可）
- 1銘柄ずつ: YES（推奨） / 一括
```

**1銘柄テンプレ**:

```bash
cd /Users/uotani/Projects/invest-alpha-os
env CONFIRM_US_LIVE_HTTP=YES CONFIRM_US_CACHE_WRITE=YES \
  .venv/bin/python -m invis_alpha_os.cli.main debug us-provider-cache-preview \
  --symbol SYMBOL --provider stooq_preview --live --write-cache
```

**事後 read-only**:

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate post-refresh-smoke --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate peer-sync-forward-returns --format markdown
```

---

## 承認 K — portfolio % 更新（milestone 達成後 · 任意）

| rubric tier | suggested % |
| --- | ---: |
| P0+P1（現状） | 40 |
| P0–P2 | 55 |
| P0–P3 | 70 |

```text
承認 K: portfolio domain %
- YES / NO
- 確定値: 55% / 70% / 40%維持 / 要確認
- 根拠: P2 pass / P3 usable 達成後のみ推奨
```

---

## 承認 L — Gmail 再送（任意 · 当日済みなら SKIP 可）

当日 `email_sent.json` がある場合は `FORCE_DAILY_GMAIL_SEND=YES` が必要。

```text
承認 L: Gmail send（再送）
- YES / NO
- モード: dry-run のみ / 本番1通 / SKIP（本日送信済み）
```

<<< ここまでコピペして返信 >>>

---

## 優先順位（Agent 推奨）

1. **I** + **J**（forward / peer P3 向け）
2. **K**（I/J 後に rubric 再評価してから）
3. **L**（任意）

wave2 記録: [approved_execution_report_wave2_ef_20260525.md](./approved_execution_report_wave2_ef_20260525.md) · [approved_execution_report_wave2_ghd_20260525.md](./approved_execution_report_wave2_ghd_20260525.md)
