# Progress Dashboard — invest-alpha-os（固定分母）

版: v0.1 / 最終更新: 2026-06-04  
基準 commit: `3a5349eb3d7329eaac424805bc8df683af906bf9`（main）

## 使い方

- 進捗率の**分母は固定**（本ファイルの「満たした項目数 / 固定項目数」）。
- **MVP進捗**と**完全自動化（actual import 等）**は分離する。
- actual import / cache write / broker は NO-GO のままでも、Report MVP の完成度を不当に下げない。

## ドメイン別進捗（固定分母）

| Domain | 重み | 完了 | 固定項目数 | 進捗 |
| --- | ---: | ---: | ---: | ---: |
| Safety / Hard Gates | 15 | 15 | 15 | 100% |
| Report MVP | 20 | 14 | 20 | 70% |
| Weekly / Monthly Ops | 15 | 11 | 15 | 73% |
| Portfolio Data Quality | 15 | 12 | 15 | 80% |
| Raw Input Quarantine | 15 | 13 | 15 | 87% |
| Actual Import Readiness | 10 | 0 | 10 | 0% |
| UX / Sample Outputs | 10 | 8 | 10 | 80% |

**加重参考（単一総合%は運用禁止・参考のみ）:** 約 **76%**

## カテゴリ詳細チェックリスト

### Safety / Hard Gates（15/15）

- [x] live HTTP 未実行方針
- [x] cache write NO-GO
- [x] actual import NO-GO
- [x] broker API NO-GO
- [x] raw Excel direct parsing NO-GO
- [x] real email send NO-GO
- [x] trading action 禁止
- [x] env/secret 非表示
- [x] workflow 変更なし（v102 一時 cron 削除済み）
- [x] v104 `gmail_send_attempted=false` 記録
- [x] v110 declaration-only（raw 読取なし）
- [x] v111 cross-review import/cache NO-GO
- [x] v107 taxonomy 既存 validator 未接続（破壊なし）
- [x] scheduled observation partial 記録（platform 制約）
- [x] Hard Gates を STATE / decisions に明文化

### Report MVP（14/20）

- [x] Weekly Candidate Brief copy-ready
- [x] Weekly email preview txt/html
- [x] Monthly Decision Sheet v84
- [x] v95 monthly input consistency
- [x] v96 shared view model
- [x] v98/v99 sanitized manual path
- [x] v104 status.json schema
- [x] v109 portfolio data quality review
- [x] v110 quarantine review
- [x] v111 cross-review
- [ ] scheduled natural run 観測完了（2026-06-06 待ち）
- [ ] weekly JSON artifact CI 生成（optional）
- [ ] operator dashboard 本番 CLI 統合
- [ ] monthly + weekly 統合 index ページ
- [ ] v86 observation **pass**
- [x] sample weekly output（fixture）
- [x] sample monthly output（fixture）

### Weekly / Monthly Ops（11/15）

- [x] `run_weekly_candidate_brief.sh`
- [x] v104 status paths（reports + email preview）
- [x] normal cron `0 22 * * 5`
- [x] v102 temporary cron 削除（#461）
- [ ] 2026-06-06 scheduled run success 確認
- [x] email dry-run 既定
- [x] pipeline trace / score veto 統合
- [x] target allocation gap v82
- [x] monthly decision sheet 中立ラベル v84b
- [x] portfolio constraints 週次表示
- [ ] Gmail test-send 経路の運用ドキュメント一本化
- [ ] scheduled artifact v101 checklist 全項目 CI 一致
- [x] pre-v86 dispatch 参考 artifact 検証
- [x] v105 facades 導入

### Portfolio Data Quality（12/15）

- [x] v109 review module
- [x] guardrail 横断
- [x] target gap 表示
- [x] manual confirmation 項目
- [x] fixture-only 入力
- [x] tests
- [x] decision doc
- [x] v111 との taxonomy key 接続
- [ ] CLI `portfolio-data-quality-review` 公開
- [ ] sample を weekly copy に短縮要約接続
- [ ] STATE と dashboard 自動同期スクリプト
- [x] import readiness NO-GO 明示
- [x] 売買指示でない safety wording
- [x] sample markdown 生成

### Raw Input Quarantine（13/15）

- [x] v110 manifest contract
- [x] v110 CLI `raw-input-quarantine-review`
- [x] blocked_by_hard_gate シナリオ
- [x] safe fixture accepted + import NO-GO
- [x] v111 cross-review module
- [x] v111 CLI `portfolio-quarantine-cross-review`
- [x] v109 接続
- [x] tests v110/v111
- [x] decision docs
- [ ] quarantine → weekly report 1行サマリ接続
- [x] raw path 読取なしテスト
- [x] stdout-only / declaration-only
- [x] sample quarantine markdown
- [x] sample cross-review markdown
- [ ] operator runbook 日本語1枚

### Actual Import Readiness（0/10）

- [ ] human approval package
- [ ] broker export 設計
- [ ] cache write 承認
- [ ] raw Excel パーサー
- [ ] import dry-run
- [ ] data freshness SLA
- [ ] rollback 手順
- [ ] audit trail
- [ ] v110→import ゲート自動化（意図的に未接続）
- [ ] production import 実行

### UX / Sample Outputs（8/10）

- [x] progress_dashboard.md（本ファイル）
- [x] MILESTONE_REPORT.md
- [x] weekly sample（完成）
- [x] monthly sample（完成）
- [x] portfolio quality sample（完成）
- [x] quarantine sample（完成）
- [x] cross-review sample（完成）
- [x] operator_dashboard_sample（完成）
- [x] reports-private index README
- [ ] ChatGPT 貼り付け用 1ページサマリ

## 投資ロジック稼働までの残作業（参考カウンタ）

- signals 本番観察3ファイル未完了: **3件**（`momentum.py` / `peer_sync.py` / `veto_rules.py` 運用観察）

## 次の6時間（Epoch 1）

1. `reports-private/sample_outputs/` 全6種 + README
2. `operator_dashboard_sample.md` 統合
3. focused pytest（v109–v111 + sample 生成スモーク）
4. UX wording 微修正（必要最小）
5. PR 作成・CI（sample/docs のみ）
