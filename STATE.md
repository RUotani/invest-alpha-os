# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-24

## 3行サマリー
- `origin/main` @ `0b78da0`（#233 P10 evidence pack / post-refresh smoke docs マージ済）。
- observation_log **38行**（US 32 + peer_sync 6 · 週次蓄積 2回目完了）。
- forward: 通常 matched=0（cache stale · 想定内）· `--backtest-within-cache` で usable（探索のみ）。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 88% | as_of notes · peer_sync × forward |
| risk/ | 62% | veto-at-t join |
| portfolio/ | [要確認]% | rubric docs/154 · 人間承認待ち |
| data ingest | 64% | US16 cache; tier-1 AMD gap |
| reports/ui | 62% | runbooks 150–163 · ops-smoke strict 既定 |
| operator/ | 80% | 凍結 |

## §2. 残作業

- [x] observation_log 週次蓄積 ×2（2026-05-24 承認済）
- [ ] 週次 observation_log 継続（次回 · 承認）
- [ ] US tier-1 refresh（実行禁止 · P10 別承認 · docs/162）
- [x] program review fix plan PR1–5
- [x] P10 evidence pack docs（#233 · docs/162–163）
- [ ] portfolio % 確定（docs/154 · 人間承認）

## §4. 最新main

```text
origin/main: 0b78da0
open PRs: 0
tests: 1033 passed
ruff: clean
observation_log: 38 lines (local outputs/)
ops-smoke --strict: exit 2 (repeat_signals=16, forward_stale_cache=1 · 想定内)
tier-1 missing: AMD
```

## §7. 次の推奨

1. 週次 read-only: `docs/160` · `validate ops-smoke --strict` + `snapshot observation-health`
2. 次回週次蓄積: 人間承認後 `--write-observation-log`
3. P10 tier-1 cache refresh（別承認 · docs/162）→ post smoke `docs/163`

## §8. 履歴

- 2026-05-24: #233 docs/162–163; ops-smoke strict 週次既定; fix plan #228–#232 完了
- 2026-05-24: 週次蓄積 38行; #227 as_of/backtest
