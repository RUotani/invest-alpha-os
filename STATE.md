# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-24

## 3行サマリー
- `origin/main` @ `b5ee55e`（#225–#229 マージ済 · ops-smoke 実質化 + ruff clean）。
- read-only ops: `validate ops-smoke`, `snapshot observation-health`, forward `--backtest-within-cache`（探索のみ）。
- observation_log **18行** 蓄積済（人間承認済）· P10 tier-1 / live HTTP **禁止継続**。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 88% | peer_sync + forward join + as_of notes |
| risk/ | 62% | veto-at-t join |
| portfolio/ | [要確認]% | rubric docs/154 · 人間承認待ち |
| data ingest | 64% | US16 cache; tier-1 AMD gap |
| reports/ui | 58% | runbooks 150–161, ops-smoke strict |
| operator/ | 80% | 凍結 |

## §2. 残作業

- [x] observation_log 初回 `--write-observation-log`（2026-05-24 承認済）
- [ ] 週次 observation_log 継続（来週 · 承認）
- [ ] US tier-1 refresh（実行禁止）
- [x] #225–#229 Product/fix stack merged
- [ ] portfolio % 確定（docs/154 rubric · 人間承認）

## §4. 最新main

```text
origin/main: b5ee55e
open PRs: 0
tests: 1029 passed
```

## §7. 次の推奨

1. 週次: `validate ops-smoke --strict` + `snapshot observation-health`
2. forward: cache refresh 後 or `--backtest-within-cache`（探索）
3. portfolio rubric 承認 → STATE % 更新

## §8. 履歴

- 2026-05-24: #228 ops-smoke fail/warn; #229 ruff clean; #227 as_of/backtest
