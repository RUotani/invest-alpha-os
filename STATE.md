# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-24

## 3行サマリー
- `origin/main` @ `395c146`（#245 peer_sync_forward · #246 docs/160 リンク）。
- observation_log **58行**（US 48 + peer_sync 10 · `peer_sync_forward` 統合済）。
- P10 AMD refresh: **ブロック中**（`STOOQ_APIKEY` 未設定 · 承認リクエスト `reports/2026-05-24/approval_requests_20260524.md`）。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 91% | observation-health · peer_sync_forward join |
| risk/ | 62% | veto-at-t join |
| portfolio/ | [要確認]% | readiness evaluator · % 人間承認待ち |
| data ingest | 64% | tier-1 **AMD** gap（Stooq API key 要） |
| reports/ui | 74% | docs/160 リンク · peer_sync_forward · stale_repeat markdown |
| operator/ | 80% | 凍結 |

## §2. 残作業

- [x] 週次 observation_log #3（2026-05-24 承認実行）
- [ ] P10 AMD refresh 再試行（`STOOQ_APIKEY` 設定後 · docs/162）
- [ ] 週次 observation_log 継続（次回 · 承認）
- [x] docs/81 Gmail runbook
- [ ] portfolio % 確定（人間承認 · `[要確認]` 維持）

## §4. 最新main

```text
origin/main: 395c146
open PRs: 0
tests: 1056 passed
observation_log: 58 lines (local outputs/)
tier-1 missing: AMD (STOOQ_APIKEY blocker)
ops-smoke --strict: exit 2 · taxonomy EXPECTED_BLOCKED (repeat + stale)
```

## §7. 次の推奨

1. `STOOQ_APIKEY` を git 外 env に設定 → AMD refresh 再実行（docs/162/163）
2. 週次 read-only: `docs/160` · `snapshot observation-health`（tier-1 gap 行確認）
3. Gmail dry-run: `docs/81` · `./scripts/run_daily_gmail_report.sh --dry-run`

## §8. 履歴

- 2026-05-24: #245 observation-health peer_sync_forward · #246 docs/160 リンク（Cursor MERGE）
- 2026-05-24: #243 ops-smoke strict stderr · observation repeat_summary JSON（Cursor 承認 A）
- 2026-05-24: #241 ops-smoke taxonomy · evidence manifest · repeat summary（Cursor 承認 A → merge）
- 2026-05-24: #238 tier-1 gap · docs/81; weekly #3 · AMD refresh blocked
- 2026-05-24: #236 portfolio readiness evaluator
