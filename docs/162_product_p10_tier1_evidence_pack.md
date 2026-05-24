# Product P10 — tier-1 evidence pack (read-only · copy-paste)

**Status**: operator pack · **no live HTTP / no cache write in this doc**  
**Related**: [docs/151](./151_product_p10_tier1_refresh_evidence_template.md), [docs/155](./155_product_p10_tier1_refresh_risk_boundary.md), [docs/163](./163_product_forward_validation_post_refresh_smoke.md)

---

## 目的

tier-1 US cache refresh を **人間承認前** に evidence を揃える。Agent/operator は本 doc の read-only 手順のみ実行可。

## 現状ギャップ（2026-05-24 時点 · ローカル）

| 項目 | 値 |
| --- | --- |
| watchlist manifest | 16/16 cached |
| tier-1 missing（weekly レポート） | **AMD**（要確認: expansion plan で再確認） |
| forward validation（通常） | matched=0 · `cache_stale` / `forward_stale_cache` warn |
| observation_log | 38行 · `as_of=` 付き行あり |

---

<<< COPY FROM HERE — READ-ONLY PRE-APPROVAL >>>

## Step A — missing 確認

```bash
cd /path/to/invest-alpha-os
.venv/bin/python -m invis_alpha_os.cli.main us-universe-expansion-plan \
  --tier 1 --missing-only --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate ops-smoke --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate ops-smoke --format json --strict
.venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format markdown
```

**保存先（git 外）**: `outputs/evidence/p10_tier1_pre_YYYYMMDD.md`

## Step B — 人間承認チェックリスト（実行前 · すべて必須）

- [ ] 対象 symbol リスト確定（expansion YAML / watchlist 一致）
- [ ] provider / レート制限方針確認
- [ ] cache 書込先: `outputs/market_data/us_daily_bars/{SYMBOL}.json`
- [ ] ロールバック手順（バックアップ or コピー退避）
- [ ] Longpack / issue 番号で **明示承認** 記録
- [ ] live HTTP / cache write は **本 doc では実行しない**

## Step C — 承認後 evidence 記録テンプレ

`outputs/evidence/p10_tier1_post_YYYYMMDD.md` に記録（git commit 禁止）:

```markdown
# P10 tier-1 refresh evidence — YYYY-MM-DD

## Approved by
- operator:
- approval ref:

## Symbols refreshed
| symbol | bar_count | first_date | last_date | source |
| --- | ---: | --- | --- | --- |
| AMD | | | | |

## Errors / retries
- (none)

## Post-refresh smoke
See docs/163 — all read-only checks pass/fail recorded below.
```

<<< COPY UNTIL HERE >>>

---

## 承認後（read-only · cache 更新**後**のみ）

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate peer-sync --format markdown
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation --dry-run --with-peer-sync --format markdown
```

**Forward matched 確認**: [docs/163](./163_product_forward_validation_post_refresh_smoke.md)

## 禁止事項

- 本 pack 単体での live HTTP / stooq fetch / cache write
- cache JSON / vendor payload の repo commit
- daily/signals default 変更
- Gmail 配信

## 参照

| Doc | 用途 |
| --- | --- |
| [151](./151_product_p10_tier1_refresh_evidence_template.md) | 詳細テンプレ |
| [155](./155_product_p10_tier1_refresh_risk_boundary.md) | リスク境界 |
| [163](./163_product_forward_validation_post_refresh_smoke.md) | refresh 後 forward smoke |
| [160](./160_product_weekly_operator_one_pager.md) | 週次 read-only ops |
