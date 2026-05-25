# Product — observation_log 週次運用 runbook

**Status**: operational guide · cache-only · observation only  
**Related**: [docs/141](./141_product_p4_weekly_observation_cycle.md), [docs/147](./147_product_p9_p11_observation_veto_forward_usability.md)

---

## 目的

`observation_log.jsonl` を週次で蓄積し、`validate us-forward-returns` の `sample_quality` を `thin` → `usable` に近づける。

## 前提

- ローカル `outputs/` は git 外（commit しない）
- live HTTP / cache write は本 runbook では **不要**（既存 cache のみ）
- 取引推奨ではない（observation-only ラベル）

## 週次・日常確認（read-only · 1コマンド）

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate ops-smoke --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate ops-smoke --format json --strict
```

**コピペ one-pager**: [docs/160_product_weekly_operator_one_pager.md](./160_product_weekly_operator_one_pager.md)（read-only 既定: `validate ops-smoke --strict`）

**P10 tier-1 evidence pack**: [docs/162_product_p10_tier1_evidence_pack.md](./162_product_p10_tier1_evidence_pack.md) · refresh 後 forward smoke: [docs/163](./163_product_forward_validation_post_refresh_smoke.md)

## 週次コマンド（書込あり · 人間承認）

```bash
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation \
  --manifest-out outputs/signals/weekly_us_manifest.json \
  --write-observation-log \
  --with-peer-sync \
  --format markdown
```

### 各フラグ

| フラグ | 作用 |
| --- | --- |
| `--manifest-out` | バッチ manifest を `outputs/signals/` に保存（observation 書込に必須） |
| `--write-observation-log` | `outputs/observation_log/observation_log.jsonl` に US signal 行を append |
| `--with-peer-sync` | peer 乖離レポート + **`--write-observation-log` 時は peer_sync 行も append**（#251） |
| `--with-daily-report` | 任意: daily US opt-in セクションも生成 |

## 事後検証

```bash
.venv/bin/python -m invis_alpha_os.cli.main log us-signals-summary
.venv/bin/python -m invis_alpha_os.cli.main log peer-sync-summary
.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate peer-sync-forward-returns --format markdown
.venv/bin/python -m invis_alpha_os.cli.main snapshot portfolio-observation-summary --format markdown
```

### peer_sync 行の append

週次で `--write-observation-log --with-peer-sync` を使う場合、US signal に加え **peer_sync 行も同一 run で append** される（markdown に `Peer sync log write (this run)` を表示）。

追加のみ必要なとき:

```bash
.venv/bin/python -m invis_alpha_os.cli.main log peer-sync-snapshot
```

### sample_quality の見方

| status | 意味 | 次アクション |
| --- | --- | --- |
| `empty` | 行なし / マッチなし | 週次 `--write-observation-log` を継続 |
| `thin` | サンプル不足 | あと数週分蓄積 |
| `usable` | 統計参照可能 | forward validation レポートを研究チェックリストへ |

## ドライラン（outputs 非書込）

```bash
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation --dry-run --with-peer-sync
```

## 人間承認が必要な場合

- **tier-1 missing symbols の cache refresh** → [docs/151](./151_product_p10_tier1_refresh_evidence_template.md)
- **Gmail 配信** → 別 runbook / 明示承認

## トラブルシュート

| 症状 | 確認 |
| --- | --- |
| `observation batch failed` | manifest パス・cache ファイル存在 |
| forward validation `empty` | `skip_pattern=fresh_log` · [docs/161](./161_product_forward_validation_fresh_log_guidance.md)（直後ログは future bars 不足で正常） |
| peer_sync 全部 `missing_cache` | US cache 未配置 or peer_map が JP のみ |
