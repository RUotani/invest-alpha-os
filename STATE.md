# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-23

このファイルはプロジェクトの現状を AI ツールに素早く伝えるためのスナップショット。
週次で人間が更新するか、AIが更新案を作成し、ユーザー承認後にコミットする。

## 3行サマリー
- `origin/main` は `9ea1f93`、open PR は 0、SSoT Phase 1 まで main 反映済み。
- US cache-only signals、forward-return validation v2、weekly/daily observation summary は observation-only で稼働可能。
- 次の優先課題は observation_log 蓄積、veto-at-t structured observation、US 30+ tier-1 gated refresh準備。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 65% | US cache-only signals と forward validation v2 は稼働。peer_sync / veto-at-t join は未完成。 |
| risk/ | 45% | veto snapshot は週次qualityで扱えるが、observation_logへの構造化保存とvalidation joinは未完成。 |
| portfolio/ | [要確認]% | position sizing / allocation接続は未完成。現状はobservation-only。 |
| data ingest | 60% | US16は稼働、US30+はconfig/readinessあり。tier-1 missing refreshは別承認。 |
| reports/ui | 35% | weekly/daily report usefulnessは改善済み。dashboard/運用UIは未完成。 |
| operator/ | 80% | 既存自動化は十分。追加拡張は原則凍結。 |

## §2. 投資ロジック稼働までの残作業

- [ ] observation_logを週次運用で蓄積し、forward validationのsample_qualityをusableへ近づける。
- [ ] veto-at-tをobservation_logに構造化保存し、forward validationとjoinできるようにする。
- [ ] US 30+ tier-1 missing symbolsのgated refresh手順とevidenceを整える。
- [ ] peer_sync系シグナル検出の現状を確認し、未実装なら実装計画を作る。
- [ ] portfolio / position sizing接続方針をobservation-only前提で設計する。

## §3. 直近の重要決定

- 2026-05-23: SSoT導入を決定。`RULES.md` / `AGENTS.md` / `CLAUDE.md` / `STATE.md` / `.cursor/rules/main.mdc` / `docs/decisions/` を共通参照点にする。
- 2026-05-23: Cursor Agent単独Longpack方式は短距離PRで早期終了しやすいため、Terminal-first supervised run方式へ切替。
- 2026-05-23: Ops増築は凍結し、投資ロジック・risk・portfolio・data・report usefulnessを優先。
- 2026-05-23: PR #211 により P7/P8 forward validation v2 / report usefulness upgrade を main 反映。

## §4. 最新main / PR状態

```text
repo: RUotani/invest-alpha-os
latest confirmed origin/main: 9ea1f93
latest merged PR: #213 docs: add SSoT phase1 agent guidance files
open PRs: 0
```

## §5. main反映済みの主なProduct work

- Product P1: US cache-only signals smoke and daily `--us-momentum-section` opt-in
- Product P2: AAPL/MSFT cache refresh evidence and observation_log path
- Product P5/P6: forward-return validation MVP and US 30+ expansion plan
- Product P7/P8: forward validation v2, hit-rate buckets, sample guard, report usefulness upgrade, daily `--us-observation-summary` opt-in

## §6. 既知の課題

- LongpackをCursor Agentへ渡すだけでは、AgentがPR作成時点で早期終了しやすい。
- Terminal-first supervised run用のrepo内実行パッケージを標準化する必要がある。
- US 30+ tier-1 refreshはlive HTTP/cache writeを伴うため、明示承認なしに実行不可。
- observation_logが薄い間は、forward validationの統計的有用性が限定的。
- veto-at-tは現状structured observationとして未接続。

## §7. 次の推奨作業

1. P9: observation_log実蓄積とforward validation usable化
2. P10: tier-1 missing cache refresh readinessのread-only整備
3. P11: veto-at-t structured observation設計/実装
4. peer_sync現状棚卸し
5. portfolio接続設計

## §8. このファイルへの追加履歴

- 2026-05-23: 初版作成
