# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-25

## 3行サマリー
- `origin/main` @ `de767e2`（#250 weekly write stats · 承認 A/B/C 実行済）。
- observation_log **74行** · tier-1 **AMD cache 済** · forward matched=0（fresh_log · skip_pattern 診断追加予定 #251）。
- portfolio **25%** — `config/portfolio_observation_acceptance.yaml`（承認 C）。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 93% | weekly+peer_sync co-write · skip_pattern |
| risk/ | 62% | veto-at-t join |
| portfolio/ | 25% | human_accepted · config YAML |
| data ingest | 68% | tier-1 0 missing |
| reports/ui | 78% | post-refresh-smoke CLI · docs/163 |
| operator/ | 80% | 凍結 |

## §2. 残作業

- [x] P10 AMD refresh（2026-05-25）
- [x] 週次 observation_log 書込（2026-05-25）
- [x] portfolio % 25%（config 承認 C）
- [ ] forward P3 usable（fresh_log 蓄積 · セッション経過）
- [ ] portfolio P1+ shadow linkage

## §4. 最新main

```text
origin/main: de767e2
open PRs: 0 (wave2 pending)
tests: 1062 passed (CI target)
observation_log: 74 lines (local)
tier-1 missing: (none)
forward: matched=0 · skip_pattern=fresh_log (expected)
```

## §7. 次の推奨

1. `validate post-refresh-smoke`（#251 マージ後）
2. `validate us-forward-returns --backtest-within-cache`（探索のみ）
3. shadow positions 追加 → P1 評価

## §8. 履歴

- 2026-05-25: 承認 A/B/C 実行 · #250 merged
- 2026-05-25: #248 ops-smoke taxonomy
- 2026-05-24: #245–#246 observation-health / docs/160
