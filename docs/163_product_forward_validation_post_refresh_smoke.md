# Product — forward validation post-refresh smoke (read-only)

**Status**: operator procedure · cache-only · observation only  
**Related**: [docs/161](./161_product_forward_validation_fresh_log_guidance.md), [docs/162](./162_product_p10_tier1_evidence_pack.md), [docs/158](./158_product_peer_sync_forward_validation_join.md)

---

## いつ使うか

P10 tier-1 **cache refresh 承認・実行後**（live HTTP は別ゲート）。  
目的: `validate us-forward-returns` の **通常モード**（`--backtest-within-cache` なし）で `matched > 0` に近づくか確認する。

## 前提

- `observation_log.jsonl` に `as_of=` 付き US signal 行があること（週次 `--write-observation-log` 済み）
- refresh 後の cache `last_date` が observation の `as_of` **以降に future sessions がある**こと
- 取引推奨ではない（exploratory diagnostics のみ）

---

<<< COPY FROM HERE — POST-REFRESH READ-ONLY >>>

```bash
cd /path/to/invest-alpha-os

# 0) cache 鮮度（manifest / expansion）
.venv/bin/python -m invis_alpha_os.cli.main us-universe-expansion-plan \
  --tier 1 --missing-only --format markdown

# 1) ops 全体
.venv/bin/python -m invis_alpha_os.cli.main validate ops-smoke --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate ops-smoke --format json --strict

# 2) forward validation — 通常（本番確認）
.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate peer-sync-forward-returns --format markdown

# 3) 統合 health
.venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format markdown
.venv/bin/python -m invis_alpha_os.cli.main log us-signals-summary
.venv/bin/python -m invis_alpha_os.cli.main log peer-sync-summary
```

<<< COPY UNTIL HERE >>>

---

## 合格基準（observation only）

| チェック | 期待 |
| --- | --- |
| `us-universe-expansion-plan --missing-only` | tier-1 missing **減少 or 0** |
| `validate us-forward-returns` | `rows_matched > 0` |
| `sample_quality.status` | `thin` 以上（`empty` でない） |
| `skipped_reasons.cache_stale_event_after_cache_end` | **0 に近づく** |
| `validate ops-smoke --strict` | `forward_stale_cache` warn **解消**（repeat warn は別途） |
| `peer-sync-forward-returns` | peer_sync 行があれば matched ≥ 1（cache 依存） |

## まだ matched=0 のとき

| 原因 | 確認 | 次アクション |
| --- | --- | --- |
| cache `last_date` ≈ `as_of` で future 不足 | cache JSON の末尾日 vs note の `as_of=` | さらにセッション経過 or 週次蓄積 |
| refresh 対象 symbol 不足 | expansion missing リスト | 追加 symbol refresh（承認後） |
| 古い行に `as_of` 無し | observation_log 先頭行 | 新規週次行のみで再評価 |
| 探索のみ必要 | — | `--backtest-within-cache`（**本番判断不可** · [161](./161_product_forward_validation_fresh_log_guidance.md)） |

## 探索モード（比較用 · opt-in）

refresh 前後の差分確認用。**合格判定には使わない。**

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns \
  --backtest-within-cache --format markdown
```

## evidence 記録

`outputs/evidence/p10_tier1_post_YYYYMMDD.md` に追記:

```markdown
## Forward post-refresh smoke
- us-forward-returns matched: __
- sample_quality: __
- top skipped_reason: __
- peer-sync-forward matched: __
- ops-smoke strict exit: __
```

## 禁止事項

- 本 doc だけでは cache refresh を実行しない
- `--backtest-within-cache` を合格判定に使わない
- matched 数から取引判断しない
