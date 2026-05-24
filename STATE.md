# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-24

## 3行サマリー
- `origin/main` @ `a328e29`（#218–#222 マージ済 · Option B Agent merge 稼働）。
- read-only ops: `validate ops-smoke`, `snapshot observation-health`, weekly `--with-peer-sync`。
- 次: observation_log 週次蓄積（人間承認）、P10 refresh 禁止継続。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 84% | momentum + peer_sync + observation notes + ops-smoke |
| risk/ | 62% | veto-at-t join |
| portfolio/ | [要確認]% | by_symbol/by_tag · docs/154 |
| data ingest | 64% | US16 cache; tier-1 AMD gap |
| reports/ui | 52% | runbooks 150–156, consolidated ops-smoke |
| operator/ | 80% | 凍結 |

## §2. 残作業

- [ ] observation_log 週次 `--write-observation-log`（人間・明示承認）
- [ ] US tier-1 refresh（実行禁止）
- [x] #218–#221 Product stack merged
- [ ] RULES §5 path reconciliation decision（optional）

## §4. 最新main

```text
origin/main: a328e29
open PRs: 0
```

## §7. 次の推奨

1. 週次: `validate ops-smoke` + `snapshot observation-health`
2. 人間: `--write-observation-log` 開始判断
3. portfolio % 確定（docs/154）

## §8. 履歴

- 2026-05-24: Option B merge; waves B–E on main
