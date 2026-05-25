# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-25

## 3行サマリー
- `origin/main` @ `96f13f8`（#256 P1 linkage hints · integration tests）。
- observation_log **74行** · forward P3 未達（fresh_log）· tier-1 clear。
- portfolio **25%** · P1: shadow + evidence ids（docs/165）。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 95% | forward_fresh_log · JP peer hints |
| portfolio/ | 25% | p1_linkage_hint |
| reports/ui | 83% | jp-peer-sync in next_commands |
| data ingest | 68% | tier-1 clear |
| risk/ | 62% | — |
| operator/ | 80% | 凍結 |

## §2. 残作業

- [ ] forward P3 usable
- [ ] portfolio P1 shadow + evidence ids

## §4. 最新main

```text
origin/main: 96f13f8
tests: 1070+ passed (CI)
observation_log: 74 lines
forward: matched=0 · skip_pattern=fresh_log
```

## §7. 次の推奨

1. docs/165 shadow linkage
2. `validate jp-peer-sync-readiness`
3. セッション経過後 forward 再評価

## §8. 履歴

- 2026-05-25: #256 P1 hints · #255 post-refresh ops
- 2026-05-25: #253–#254 · 承認 A/B/C
