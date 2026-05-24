# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-24

## 3行サマリー
- `origin/main` @ `d3bd10d`（#225–#230 マージ済 · fix plan PR1–5 完了）。
- observation_log **38行**（US 32 + peer_sync 6 · 週次蓄積 2回目完了）。
- forward: 通常 matched=0（cache stale）· `--backtest-within-cache` で usable（探索のみ）。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 88% | as_of notes · peer_sync × forward |
| risk/ | 62% | veto-at-t join |
| portfolio/ | [要確認]% | rubric docs/154 · 人間承認待ち |
| data ingest | 64% | US16 cache; tier-1 AMD gap |
| reports/ui | 60% | runbooks 150–161 · ops-smoke strict |
| operator/ | 80% | 凍結 |

## §2. 残作業

- [x] observation_log 週次蓄積 ×2（2026-05-24 承認済）
- [ ] 週次 observation_log 継続（次回 · 承認）
- [ ] US tier-1 refresh（実行禁止 · P10 別承認）
- [x] program review fix plan PR1–5
- [ ] portfolio % 確定（docs/154 · 人間承認）

## §4. 最新main

```text
origin/main: d3bd10d
open PRs: 0
tests: 1031 passed
ruff: clean
observation_log: 38 lines (local outputs/)
```

## §7. 次の推奨

1. `validate ops-smoke --strict` + `snapshot observation-health`
2. 次回週次: docs/160 承認後 `--write-observation-log`
3. P10 tier-1 cache refresh（別承認）→ forward matched 本番化

## §8. 履歴

- 2026-05-24: fix plan #228–#230; 週次蓄積 38行; #227 as_of/backtest
