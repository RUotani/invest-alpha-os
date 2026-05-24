# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-24

## 3行サマリー
- `origin/main` @ `4402dae` (#217)。open PR stack: **#218 → #219 → #220 → #221**（merge 順序依存）。
- ops smoke 完了（docs/152）。Wave B `snapshot observation-health` 追加済み（#219）。
- 人間: PR マージ、`--write-observation-log` 明示承認、P10 refresh 禁止継続。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 82% | momentum + peer_sync + weekly opt-in + observation notes |
| risk/ | 62% | veto-at-t join; RULES path drift documented |
| portfolio/ | [要確認]% | by_symbol/by_tag exposure (#220); rubric docs/154 |
| data ingest | 64% | US16 local cache; tier-1 AMD gap; P10 docs/155 |
| reports/ui | 48% | observation-health, runbooks 150-156 |
| operator/ | 80% | 凍結 |

## §2. 残作業

- [ ] observation_log 週次 `--write-observation-log`（人間・明示承認）
- [ ] US tier-1 refresh（実行禁止 · docs/151/155）
- [x] ops smoke read-only CLI 群
- [x] peer_sync observation_log tooling (#218)
- [x] observation-health snapshot (#219)

## §4. 最新main / PR

```text
origin/main: 4402dae (#217)
open: #218 #219 #220 #221 (stacked merge order)
```

## §7. 次の推奨

1. 人間: merge queue 順に PR マージ
2. 週次 ops: docs/150 + snapshot observation-health
3. portfolio % 確定（docs/154 rubric）

## §8. 履歴

- 2026-05-24: massive longrun waves A–E
