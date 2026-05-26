# Approved execution — L1 skip duplicate ISO week（2026-05-26）

**承認**: L1 残 1 回 · `--skip-duplicate-iso-week` 付き · **消費 2/2 完了**

## 事前

| 指標 | 値 |
| --- | --- |
| log lines | 534 |
| matched (normal) | 1/10 |
| `p3_weekly_write_plan.write_now_count` | **0** |
| `skip_duplicate_count` | 16 |
| `will_be_matchable_after_date` | 16 |

## 実行

```bash
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation \
  --write-observation-log --with-peer-sync --skip-duplicate-iso-week
```

| 項目 | 結果 |
| --- | --- |
| US signals logged | **0** |
| skipped_duplicate_iso_week | **16**（全 watchlist 銘柄が同一 ISO 週済み） |
| peer_sync logged | **4** |
| log lines | **534 → 538** (+4) |

## 事後

| 指標 | 値 |
| --- | --- |
| matched (normal) | **1/10**（変化なし · 想定内） |
| samples_needed | 9 |
| 効果 | 重複 US 行 **0 追加**（P3 dead_rows 増加を回避） |

## 次アクション（read-only）

- 新 ISO 週（カレンダー週替わり）後に `write_now_count > 0` を確認してから L1 再承認
- `validate forward-p3-status` で `will_be_matchable_after_date` 経過を監視
