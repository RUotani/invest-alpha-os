# Product P10 — tier-1 US cache refresh evidence template

**Status**: read-only template · **no live HTTP in this doc**  
**Related**: `us-universe-expansion-plan`, [docs/148](./148_product_peer_sync_inventory_and_mvp.md), [docs/155](./155_product_p10_tier1_refresh_risk_boundary.md), [docs/162](./162_product_p10_tier1_evidence_pack.md), [docs/163](./163_product_forward_validation_post_refresh_smoke.md)

---

## いつ使うか

`us-universe-expansion-plan --tier 1 --missing-only` で missing が出たあと、**人間が live HTTP / cache write を承認する前**に evidence を揃える。

## Step 0 — read-only 現状確認

```bash
.venv/bin/python -m invis_alpha_os.cli.main us-universe-expansion-plan \
  --tier 1 --missing-only --format markdown
```

出力を `outputs/evidence/` に保存（git 外推奨）:

```text
outputs/evidence/p10_tier1_missing_YYYYMMDD.md
```

## Step 1 — 承認チェックリスト（人間）

- [ ] 対象 symbol リストを確認（watchlist / expansion YAML と一致）
- [ ] レート制限・provider 方針を確認
- [ ] cache write 先: `outputs/market_data/us_daily_bars/{SYMBOL}.json`
- [ ] ロールバック: バックアップ or git 外コピー方針
- [ ] 本番実行は operator + 明示 Longpack 承認

## Step 2 — 実行後 evidence（人間が記録）

テンプレ:

```markdown
# P10 tier-1 refresh evidence — YYYY-MM-DD

## Approved by
- operator:
- approval ref (Longpack / issue):

## Symbols refreshed
| symbol | cache path | bar_count | first_date | last_date | source |
| --- | --- | ---: | --- | --- | --- |
| NVDA | outputs/market_data/us_daily_bars/NVDA.json | | | | stooq |

## Post-refresh smoke
- [ ] validate peer-sync — diverged/missing 減少
- [ ] weekly-us-observation --dry-run — manifest entries 増加
- [ ] forward validation — 通常モードで matched > 0 → [docs/163](./163_product_forward_validation_post_refresh_smoke.md)
- [ ] pytest -q（repo; cache は git 外）

## Notes
- errors / retries:
```

## Step 3 — Product 再検証（cache-only CLI）

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate peer-sync --format markdown
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation \
  --dry-run --with-peer-sync --format markdown
```

## 禁止事項

- 本テンプレートだけでは live HTTP を実行しない
- evidence を repo に commit しない（cache JSON / vendor payload）
- daily/signals default の変更

## 参照

- **Evidence pack（read-only 一冊）**: [docs/162](./162_product_p10_tier1_evidence_pack.md)
- refresh 後 forward smoke: [docs/163](./163_product_forward_validation_post_refresh_smoke.md)
- リスク境界: [docs/155](./155_product_p10_tier1_refresh_risk_boundary.md)
- 週次 one-pager: [docs/160](./160_product_weekly_operator_one_pager.md)
