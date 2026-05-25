# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-25

## 3行サマリー
- `origin/main` @ `8a5331e` → wave4 PR 待ち（P2 supplemental · post_refresh_hints · shadow seed docs）。
- observation_log **74行** · forward matched=0 · skip_pattern 診断済。
- portfolio **25%** · P1 は `docs/165` + `config/examples/shadow_portfolio_positions.example.jsonl`。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 94% | weekly_trend trailing_7d · calendar_week_caveat |
| risk/ | 62% | veto-at-t join |
| portfolio/ | 25% | shadow_seed_hint · P1 手動 seed |
| data ingest | 68% | tier-1 0 missing |
| reports/ui | 80% | observation-health post_refresh_hints |
| operator/ | 80% | 凍結 |

## §2. 残作業

- [ ] forward P3 usable
- [ ] portfolio P1 linkage（shadow 手動配置）
- [ ] 次回 weekly write（承認後）

## §4. 最新main

```text
origin/main: 8a5331e (pre wave4)
tests: 1065 passed (local wave4)
```

## §7. 次の推奨

1. shadow seed → `docs/165`
2. `validate post-refresh-smoke`
3. `snapshot observation-health` で post_refresh_hints 確認

## §8. 履歴

- 2026-05-25: #251–#252 observation wave2/3
- 2026-05-25: 承認 A/B/C 実行
