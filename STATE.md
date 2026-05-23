# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-24

このファイルはプロジェクトの現状を AI ツールに素早く伝えるためのスナップショット。
週次で人間が更新するか、AIが更新案を作成し、ユーザー承認後にコミットする。

## 3行サマリー
- `origin/main` は `3601554`（#216 peer_sync + portfolio summary）、open PR は 0（weekly/runbook PR 作成予定）。
- US cache-only signals、forward validation、peer_sync、portfolio snapshot CLI は稼働。
- 次: observation_log 週次蓄積（人間運用）、tier-1 refresh（明示承認）、peer_sync observation_log 連携は未実装。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 75% | momentum + peer_sync MVP + weekly `--with-peer-sync` opt-in。 |
| risk/ | 55% | veto-at-t observation note + forward validation join。 |
| portfolio/ | [要確認]% | shadow JSONL + `snapshot portfolio-observation-summary`。 |
| data ingest | 60% | US16稼働、US30+ readiness。tier-1 refresh evidence template 追加。 |
| reports/ui | 42% | weekly runbook docs/150、forward sample_quality 導線。 |
| operator/ | 80% | 拡張凍結。 |

## §2. 投資ロジック稼働までの残作業

- [ ] observation_logを週次運用で蓄積（runbook: docs/150）
- [x] veto-at-t observation note + forward validation join
- [ ] US 30+ tier-1 gated refresh（evidence template: docs/151、実行は人間承認）
- [x] peer_sync cache-only MVP + weekly opt-in
- [x] portfolio observation-only 設計 + read-only summary CLI
- [ ] peer_sync 行の observation_log 構造化（別 PR 候補）

## §3. 直近の重要決定

- 2026-05-24: peer_sync weekly `--with-peer-sync` opt-in（default off）
- 2026-05-24: PR #216 merged — peer_sync MVP + portfolio summary
- 2026-05-23: P9/P11 (#215), SSoT, Ops 凍結

## §4. 最新main / PR状態

```text
repo: RUotani/invest-alpha-os
latest confirmed origin/main: 3601554
latest merged PR: #216 product peer_sync cache-only MVP and portfolio observation design
open PRs: 0
```

## §5. main反映済みの主なProduct work

- P1–P2: US cache-only signals, observation_log path
- P5–P8: forward validation v2, report usefulness, daily `--us-observation-summary`
- P9/P11: sample_quality, veto-at-t join
- P12 (informal): peer_sync MVP, portfolio observation summary (#216)

## §6. 既知の課題

- observation_log 薄い間は forward validation 有用性が限定的
- tier-1 refresh は live HTTP/cache write — 明示承認必須
- peer_sync JP peers は US cache ローダーでは missing_cache
- portfolio 進捗 `[要確認]%`

## §7. 次の推奨作業

1. observation_log 週次蓄積（人間運用 · docs/150）
2. P10 tier-1 refresh（人間承認 · docs/151）
3. peer_sync observation_log note（Agent · 別 PR）

## §8. このファイルへの追加履歴

- 2026-05-23: 初版
- 2026-05-24: #216 / peer_sync / portfolio
- 2026-05-24: weekly peer_sync + runbooks
