# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-25

## 3行サマリー
- `origin/main` @ `010a5f4`（#259 portfolio 40% · thin hints）。
- forward matched=**3** thin · peer_sync_forward matched=**6** thin（P3 あと4件）。
- wave2 E/F/G/H/D 実行済み · 次は read-only 診断強化（#260 予定）。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 97% | p3_progress 表示 · peer_sync 6/10 |
| portfolio/ | 40% | P0+P1 |
| reports/ui | 86% | observation-health peer_sync section |
| data ingest | 75% | — |
| operator/ | 82% | Gmail sent |
| risk/ | 62% | — |

## §2. 残作業

- [ ] forward P3 usable（US 3/10 · peer 6/10）
- [ ] stale_cache skips 削減

## §4. 最新ローカル観測

```text
origin/main: 010a5f4
observation_log: 94 lines
us_forward: matched=3 thin
peer_sync_forward: matched=6 thin
```

## §8. 履歴

- 2026-05-25: wave2 全承認実行 · #259
- 2026-05-25: #258 forward P3 actions
