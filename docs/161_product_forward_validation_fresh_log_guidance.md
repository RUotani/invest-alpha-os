# Product — forward validation fresh-log guidance

**Status**: operational · read-only  
**Related**: [docs/150](./150_product_observation_log_weekly_runbook.md), [docs/158](./158_product_peer_sync_forward_validation_join.md), [docs/163](./163_product_forward_validation_post_refresh_smoke.md)

---

## 症状

週次 `--write-observation-log` 直後に:

- `validate us-forward-returns` → `sample_quality: empty`
- `skipped_reasons.insufficient_future_bars` または `cache_stale_event_after_cache_end`
- `validate peer-sync-forward-returns` → peer_sync 行はあるが matched=0

## 原因

| パターン | イベント日 | 説明 |
| --- | --- | --- |
| fresh log | `created_at` = 当日 | cache 末尾に未来バーなし |
| stale cache | `created_at` > cache 最終日 | fixture/古い cache · note に `as_of=` 無し |
| 改善後 | note の `as_of=` | cache preview の `last_date` を週次ログに保存 |

## 探索用 CLI（opt-in · 本番判断不可）

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns \
  --backtest-within-cache --format markdown
```

cache 内で forward 可能な最終位置へシフトする **read-only 探索**。

## 本番向け

1. 週次 `--write-observation-log`（新規行に `as_of=` 自動付与）
2. 週次蓄積を継続
3. P10 tier-1 US cache refresh（**別承認** · live HTTP 禁止）
4. refresh **後** read-only smoke: [docs/163](./163_product_forward_validation_post_refresh_smoke.md)（`matched > 0` 確認）

## 通常 CLI

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --format markdown
.venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format markdown
```
