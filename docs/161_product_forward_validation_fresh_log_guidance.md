# Product — forward validation fresh-log guidance

**Status**: operational · read-only  
**Related**: [docs/150](./150_product_observation_log_weekly_runbook.md), [docs/158](./158_product_peer_sync_forward_validation_join.md)

---

## 症状

週次 `--write-observation-log` 直後に:

- `validate us-forward-returns` → `sample_quality: empty`
- `skipped_reasons.insufficient_future_bars` が US signal 行数と同程度
- `validate peer-sync-forward-returns` → peer_sync 行はあるが matched=0

## 原因（正常）

イベント日 = `created_at`（ログ当日）。cache に **未来セッション** が無いため forward window が計算できない。

## 次アクション

1. 数セッション経過後に read-only 再実行
2. 週次蓄積を継続（historical rows が増えると matched が増える）
3. P10 tier-1 refresh は **別承認**（live HTTP 禁止）

## CLI

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --format markdown
.venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format markdown
```

`sample_quality.reason` に `too recent for forward windows` が出れば本 doc のケース。
