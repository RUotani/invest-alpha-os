# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-25

## 3行サマリー
- `origin/main` @ `c09c340`（#260 p3_progress · peer_sync 診断）。
- US forward **3/10** thin · peer_sync_forward **6/10** thin · portfolio **40%**。
- wave12: stale_skip_by_symbol 診断（PR 予定）。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 97% | stale symbol breakdown |
| portfolio/ | 40% | P0+P1 |
| reports/ui | 87% | — |
| data ingest | 75% | — |
| operator/ | 82% | — |
| risk/ | 62% | — |

## §2. 残作業

- [ ] forward P3 usable（10 matched）
- [ ] P10 refresh for stale_skip_symbols（要承認）

## §4. 最新ローカル観測

```text
origin/main: c09c340
observation_log: 94 lines
us_forward: 3/10 thin
peer_sync_forward: 6/10 thin
```

## §8. 履歴

- 2026-05-25: #260 P3 progress
- 2026-05-25: wave2 全承認 · #259
