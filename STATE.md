# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-25

## 3行サマリー
- `origin/main` @ `54b0579`（#248 ops-smoke taxonomy · 承認実行はローカル outputs）。
- observation_log **74行**（週次書込 2026-05-25 承認 B · US 64 + peer_sync 10）。
- P10 AMD **完了**（tier-1 gap 解消）。forward matched=0 は fresh-log 想定内（docs/161）。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 92% | 週次書込済 · observation-health 統合 |
| risk/ | 62% | veto-at-t join |
| portfolio/ | 25% | 人間承認 C · rubric P0（docs/154） |
| data ingest | 68% | tier-1 AMD cache 済 · US16+1 |
| reports/ui | 76% | evidence manifest · weekly write stats |
| operator/ | 80% | 凍結 |

## §2. 残作業

- [x] P10 AMD refresh（2026-05-25 承認 A 実行）
- [x] 週次 observation_log 蓄積（2026-05-25 承認 B）
- [x] portfolio % 25% 確定（2026-05-25 承認 C · P0 tier）
- [ ] forward validation usable（P3 · 蓄積 + cache 鮮度）
- [ ] 次回週次 observation_log（承認後）

## §4. 最新main

```text
origin/main: 54b0579
open PRs: 0
tests: 1058 passed (pre-PR local)
observation_log: 74 lines (local outputs/)
tier-1 missing: (none)
ops-smoke --strict: exit 2 · EXPECTED_BLOCKED (repeat + forward fresh-log)
forward: matched=0 · insufficient_future_bars dominant
```

## §7. 次の推奨

1. 週次 read-only: `docs/163` post-refresh smoke 継続
2. forward 探索（read-only）: `validate us-forward-returns --backtest-within-cache`
3. portfolio P1+: shadow positions + linkage 蓄積

## §8. 履歴

- 2026-05-25: 承認 A/B/C 実行 · AMD cache · weekly write · portfolio 25%
- 2026-05-25: #248 ops-smoke tier1/peer_sync/stale_repeat taxonomy
- 2026-05-24: #245 observation-health peer_sync_forward · #246 docs/160 リンク
