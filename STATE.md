# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-24

このファイルはプロジェクトの現状を AI ツールに素早く伝えるためのスナップショット。
週次で人間が更新するか、AIが更新案を作成し、ユーザー承認後にコミットする。

## 3行サマリー
- `origin/main` は `cb87dcc`（#215 P9/P11）、open PR は 0（peer_sync PR 作成予定）。
- US cache-only signals、forward validation v2、observation summary、veto-at-t join は稼働。
- 次の優先課題は observation_log 実蓄積（usable化）、tier-1 gated refresh（人間承認）、portfolio read-only summary。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 72% | momentum + **peer_sync cache-only MVP**（validate peer-sync）。weekly 未統合。 |
| risk/ | 55% | veto-at-t observation note + forward validation `by_veto_status`。 |
| portfolio/ | [要確認]% | shadow JSONL のみ。observation-only 接続設計 doc 149 追加。 |
| data ingest | 60% | US16稼働、US30+ config/readiness。tier-1 refresh は別承認。 |
| reports/ui | 38% | sample_quality/next_commands 導線。peer_sync report CLI 追加。 |
| operator/ | 80% | 既存自動化十分。拡張凍結。 |

## §2. 投資ロジック稼働までの残作業

- [ ] observation_logを週次運用で蓄積し、forward validationのsample_qualityをusableへ近づける（導線は整備済み）。
- [x] veto-at-tをobservation_log noteに構造化保存し、forward validationとjoin（legacy行は not_in_observation_log）。
- [ ] US 30+ tier-1 missing symbolsのgated refresh手順とevidenceを整える（read-only report 整備済み）。
- [x] peer_sync系シグナル検出の現状を確認し、未実装なら実装計画を作る（→ cache-only MVP + docs/148）。
- [x] portfolio / position sizing接続方針をobservation-only前提で設計する（docs/149）。
- [x] portfolio read-only summary CLI（`snapshot portfolio-observation-summary`）

## §3. 直近の重要決定

- 2026-05-24: peer_sync cache-only MVP を approved（`docs/decisions/2026-05-24_peer_sync_cache_only_mvp.md`）。
- 2026-05-23: SSoT導入。Terminal-first supervised run へ切替。
- 2026-05-23: Ops増築凍結。投資ロジック・risk・portfolio・data を優先。
- 2026-05-23: PR #215 P9/P11 sample-quality + veto-at-t join を main 反映。

## §4. 最新main / PR状態

```text
repo: RUotani/invest-alpha-os
latest confirmed origin/main: cb87dcc
latest merged PR: #215 product P9/P11 observation veto forward usability
open PRs: 0
pending: peer_sync + portfolio design PR (this branch)
```

## §5. main反映済みの主なProduct work

- Product P1: US cache-only signals smoke and daily `--us-momentum-section` opt-in
- Product P2: AAPL/MSFT cache refresh evidence and observation_log path
- Product P5/P6: forward-return validation MVP and US 30+ expansion plan
- Product P7/P8: forward validation v2, hit-rate buckets, sample guard, daily `--us-observation-summary`
- Product P9/P11: sample_quality/next_commands, veto-at-t note join, `by_veto_status`

## §6. 既知の課題

- observation_logが薄い間は forward validation の統計的有用性が限定的。
- US 30+ tier-1 refreshは live HTTP/cache write を伴うため明示承認必須。
- peer_sync は US cache のみ; JP peer_map 行は missing_cache になる。
- RULES.md §5 の paths と実装（veto under risk/）に軽い drift あり。
- portfolio 進捗 % は人間確認待ち（`[要確認]%`）。

## §7. 次の推奨作業

1. P9 運用: weekly `--write-observation-log` で observation_log 蓄積
2. P10: tier-1 gated cache refresh（明示承認後・operator）
3. peer_sync weekly opt-in section（別 PR）
4. peer_sync weekly opt-in section（別 PR）

## §8. このファイルへの追加履歴

- 2026-05-23: 初版作成
- 2026-05-24: cb87dcc / P9/P11 / peer_sync MVP / portfolio design 反映
