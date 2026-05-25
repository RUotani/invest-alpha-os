# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-25

## 3行サマリー
- `origin/main` @ `c08cffd`（#251 skip_pattern · peer_sync co-write · post-refresh-smoke）。
- observation_log **74行** · tier-1 gap **0** · forward matched=0 · `skip_pattern=fresh_log` 想定内。
- portfolio **25%** — `config/portfolio_observation_acceptance.yaml`。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 93% | peer_sync co-write · skip_pattern |
| risk/ | 62% | veto-at-t join |
| portfolio/ | 25% | human_accepted YAML |
| data ingest | 68% | AMD + US16 cached |
| reports/ui | 78% | validate post-refresh-smoke |
| operator/ | 80% | 凍結 |

## §2. 残作業

- [x] P10 AMD · weekly write · portfolio 25%
- [ ] forward P3 usable（セッション蓄積）
- [ ] portfolio P1 shadow linkage

## §4. 最新main

```text
origin/main: c08cffd
open PRs: 0
tests: 1062 passed
observation_log: 74 lines
tier-1 missing: (none)
forward: matched=0 · skip_pattern=fresh_log
```

## §7. 次の推奨

1. `validate post-refresh-smoke --format markdown`
2. 次回 weekly は `--write-observation-log --with-peer-sync`（peer_sync 同梱）
3. `--backtest-within-cache` は探索のみ

## §8. 履歴

- 2026-05-25: #251 observation wave2 · #250 post-approval
- 2026-05-25: 承認 A/B/C 実行
- 2026-05-24: #245–#246 observation-health
