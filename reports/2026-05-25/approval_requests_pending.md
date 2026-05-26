# 承認 — 最新（バッチ方式 · 2026-05-26）

| バッチ | 状態 |
| --- | --- |
| **L1** 回数=2 · 期限=2026-06-30 | **消費済み 2/2** · [skip L1](../2026-05-26/approved_execution_L1_skip_20260526.md) |
| **L2** dry-run+send-test-1回 | **消費済み** · [L2](../2026-05-26/approved_execution_L2_gmail_20260526.md) |
| **L3** tier=P0-P2 · percent=55 | **消費済み** · [L3](../2026-05-26/approved_execution_L3_portfolio_20260526.md) |
| **cache refresh** stale/missing | **実行済**（8銘柄 P10）· 同上 batch |
| **重複週方針** | **approved** · [decision](../../docs/decisions/2026-05-26_observation_log_duplicate_week_policy.md) |
| **L3 P0-P3 · 70%** | **保留**（US forward usable 後） |

## 待ち（任意）

```text
承認 L1: YES · 回数=2 · 期限=YYYY-MM-DD
```

（L1 **消費済み** · 次回は新 ISO 週で `write_now_count>0` 確認後 · L2 再送 · L3 再承認は tier/percent 変更時のみ）

## Agent 自律

product PR · read-only validate · pytest · merge（オプション B）· Gmail dry-run のみ
