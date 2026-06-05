# Progress Dashboard — invest-alpha-os（固定分母）

版: v0.3 / 最終更新: 2026-06-05  
基準 commit: `a88f4d15a5172a0affc5e508fd4c7bae5572c69c`（main, #473）  
直近: Post #473 — sample review pack + scheduled observation **pending**（2026-06-06 07:30 JST 以降）  
#471–#473 merged / Actual Import Readiness **0% 維持**

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
| Portfolio Data Quality | 15 | 13 | 15 | 87% |
| Raw Input Quarantine | 15 | 13 | 15 | 87% |
| Actual Import Readiness | 10 | 0 | 10 | 0% |
| UX / Sample Outputs | 10 | 10 | 10 | 100% |

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
- [x] CLI `portfolio-data-quality-review` 公開（Epoch 2）
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
- [x] sample 再生成手順（`docs/sample_output_regeneration.md`）

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

### UX / Sample Outputs（10/10）

- [x] progress_dashboard.md（本ファイル）
- [x] MILESTONE_REPORT.md
- [x] weekly sample（完成）
- [x] monthly sample（完成）
- [x] portfolio quality sample（完成）
- [x] quarantine sample（完成）
- [x] cross-review sample（完成）
- [x] operator_dashboard_sample（完成）
- [x] reports-private index README
- [x] ChatGPT 貼り付け用 1ページサマリ（`chatgpt_one_page_summary_sample.md`）
- [x] 全 sample 先頭 disclaimer 統一（blockquote）

## 24h Marathon 見える成果（#470 + Epoch 2）

| PR | 内容 |
| --- | --- |
| #470 | progress dashboard + 6 sample outputs |
| #471 | disclaimer + UX wording + portfolio-data-quality-review CLI |
| #472 | operator dashboard + sample-output-pack + full pytest |
| #473 | scheduled observation pending + final summary |
| #474（予定） | sample review for user + scheduled observation 2026-06-06 |

進捗率が過去にブレた理由: 分母未定義・MVPと自動化の混同。本ダッシュボードは**固定項目数**で再計算する。

## 投資ロジック稼働までの残作業（参考カウンタ）

- signals 本番観察3ファイル未完了: **3件**（`momentum.py` / `peer_sync.py` / `veto_rules.py` 運用観察）

## 次（Epoch 3–4）

1. operator dashboard カード風 polish
2. full pytest + ruff
3. 2026-06-06 07:30 JST scheduled run read-only 観測（Epoch 4）
4. `cursor_auto_24h_final_summary.md`
