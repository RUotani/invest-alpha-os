# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-24

## 3行サマリー
- `origin/main` は `4402dae`（#217 weekly peer_sync + runbooks）、ops smoke docs/152 実施済み。
- read-only CLI 3本（weekly/validate/snapshot）はローカルで exit 0 確認。
- 次: `log peer-sync-snapshot` / `--write-observation-log` は明示 opt-in のみ。tier-1 refresh 禁止。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 78% | peer_sync + weekly opt-in + observation note（PR 予定） |
| risk/ | 55% | veto-at-t join |
| portfolio/ | [要確認]% | snapshot portfolio-observation-summary |
| data ingest | 60% | US16 cache ローカル確認。tier-1 AMD gap |
| reports/ui | 45% | docs/150-152 runbook + ops smoke |
| operator/ | 80% | 凍結 |

## §2. 残作業

- [ ] observation_log 週次 `--write-observation-log`（人間・明示承認）
- [ ] US tier-1 refresh（禁止中 · docs/151）
- [x] ops smoke 3 CLI
- [ ] peer_sync observation_log CLI — **実装済み・PR 待ち**

## §4. 最新main

```text
latest origin/main: 4402dae (#217 merged)
pending PR: peer_sync observation_log + ops report + next_commands fix
```

## §7. 次の推奨

1. PR マージ（peer_sync log + docs/152）
2. 人間: `--write-observation-log` 週次運用
3. forward validation sample_quality 追跡

## §8. 履歴

- 2026-05-24: ops smoke + peer_sync observation_log CLI
