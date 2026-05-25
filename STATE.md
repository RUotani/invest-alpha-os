# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-25

## 3行サマリー
- `origin/main` @ `696da52`（#255 post-refresh-smoke in ops · docs/161）。
- observation_log **74行** · forward P3 未達（fresh_log）· tier-1 clear。
- portfolio **25%** · P1: shadow + `thesis_evidence_ids` 手動（docs/165）。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 95% | forward_fresh_log |
| portfolio/ | 25% | p1_linkage_hint（wave7） |
| reports/ui | 82% | post-refresh-smoke next_commands |
| data ingest | 68% | tier-1 clear |
| risk/ | 62% | — |
| operator/ | 80% | 凍結 |

## §2. 残作業

- [ ] forward P3 usable
- [ ] portfolio P1 shadow + evidence ids

## §4. 最新main

```text
origin/main: 696da52
tests: 1067+ passed (CI)
observation_log: 74 lines
forward: matched=0 · skip_pattern=fresh_log
```

## §7. 次の推奨

1. docs/165 shadow + observation id 紐付け
2. `validate post-refresh-smoke`
3. セッション経過後 forward 再評価

## §8. 履歴

- 2026-05-25: #255 ops/docs/161/STATE
- 2026-05-25: #253–#254 · 承認 A/B/C
