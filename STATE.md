# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-25

## 3行サマリー
- `origin/main` @ `d7ee3f7`（#257 JP peer hints）。
- forward P3 未達: `matched=0` · `skip_pattern=mixed`（stale 16 / fresh 48）。
- **承認待ち wave2**: E weekly · F P10 refresh · G portfolio % · H shadow 手動。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 95% | mixed skip · wave2 E/F 待ち |
| portfolio/ | 25% | P1 手動（docs/165） |
| reports/ui | 84% | forward_p3 recommended_actions（wave9） |
| data ingest | 72% | tier-1 missing=0 |
| risk/ | 62% | — |
| operator/ | 80% | 凍結 |

## §2. 残作業

- [ ] 承認 E/F 実行（forward P3）
- [ ] portfolio P1 shadow（手動 H）
- [ ] 承認 G（% 40% 候補）

## §4. 最新main

```text
origin/main: d7ee3f7
observation_log: 74 lines
post-refresh: tier1_ok · matched=0 · skip_pattern=mixed
```

## §7. 次の推奨

1. [approval_requests_wave2_20260525.md](../reports/2026-05-25/approval_requests_wave2_20260525.md) に E/F YES
2. 手動 H（shadow linkage）
3. `validate post-refresh-smoke` 再実行

## §8. 履歴

- 2026-05-25: #255–#257 · wave1 A/B/C 実行
- 2026-05-25: wave2 承認リクエスト掲出
