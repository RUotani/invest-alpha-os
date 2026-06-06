# STATE.md — invest-alpha-os 現状スナップショット

版: v0.6 / 最終更新: 2026-06-06（Post #506 / v1.3 trial send）

## 3行サマリー
- **週次主系統**: Weekly Candidate Brief v1.2 UX — `scripts/run_weekly_candidate_brief.sh` + Gmail OAuth send
- **latest verified main**: `756ce5b`（#506 merge）— v1.3 trial send PR pending
- **ユーザー入口**: `reports-private/manual_issue/latest/README_FOR_USER.md`
- **v1.2 sample**: `reports-private/sample_outputs/weekly_report_v1_2_sample.md`
- **v1.3 trial**: `reports-private/trial_send/weekly_v1_2_2026-06-06/README_FOR_USER.md`
- P3 live forward usable は **time-dependent monitoring gate**（`matched_normal=1/10` · need 9）— 短期 KPI から外す
- 旧 Weekly Observation Report v1 は主出力ではなく、過去比較/診断/付録として扱う

## §1. 主要完了状態（main反映済み）

- PR #437 / v85: Portfolio-Aware Weekly Action Checklist
- PR #438 / v83: Cleanup Priority Scoring Pack
- PR #440 / v82: Target Allocation Gap Calculator
- PR #442 / v84: Monthly Decision Sheet Pack
- PR #444 / v84b: Decision Label Neutralization Pack
- PR #445 / v87: Veto Reason Display Clarity Pack
- PR #462 / v104: Scheduled Run Observability + Artifact Status Schema
- PR #463 / v105: Versionless Facade Introduction
- PR #464 / v106: Common Validation Taxonomy Assessment
- PR #465 / v107: Non-Breaking Common Validation Taxonomy Skeleton
- PR #466 / v108: State Refresh After v107 Taxonomy Skeleton
- PR #467 / v109: Portfolio Data Quality Review
- PR #468 / v110: Raw Input Quarantine Design
- PR #469 / v111: Raw Input Quarantine Cross Review Skeleton
- PR #470: Marathon Epoch 1 progress dashboard + sample outputs
- PR #471: Epoch 2 disclaimer + `portfolio-data-quality-review` CLI
- PR #472: Epoch 3 operator dashboard + `sample-output-pack` CLI
- PR #473: Epoch 4 scheduled observation pending + 24h final summary
- PR #474: sample review pack + scheduled observation pending
- PR #475–#481: JSON runner、UX、Ruff 0、regression contracts
- PR #482–#485: monthly integration、language pass、operator guide、next 24h tree
- Post #485 Long-Run: observation contract、`weekly-report-user-summary`、workflow proposals
- PR #503: schedule non-fire RCA / delivery expectation hardening
- PR #504: v1.1 SMTP weekly report email delivery foundation
- PR #505: Gmail OAuth actual weekly report delivery（message id `19e9a26b12d4a2eb` @ 2026-06-06 manual pack）
- PR #506: v1.2 weekly report investment-grade UX（guardrail表・候補比較・深掘りカード）

## §2. Weekly / Monthly 現在機能

### Weekly Candidate Brief（v81-v87 + v1.2 UX #506）

- v1.1 Gmail: OAuth 実送信承認済み（`weekly-report-email-send` · `daily_gmail.env`）
- v1.2 UX: guardrail表・候補比較・深掘りカード・用語定義・email renderer 改善
- v1.3 trial: `reports-private/trial_send/weekly_v1_2_2026-06-06/` · Gmail sent `19e9a953c07c3a4a`
- Agent playbook: `.agent/cursor_knowledge_longrun_playbook_20260606.md`
- 今週の結論
- ポートフォリオ制約
- 行動分類
- 今週の行動チェックリスト
- 整理・監視優先度スコア
- 目標配分ギャップ（v82）
- 候補0件の理由メモ（coverage不足 / score未達 / veto）
- email txt/html preview への短縮理由メモ反映

### Monthly Decision Sheet（v84-v84b）

- 今月の結論
- 判断サマリー
- 中立化済みの意思決定テーブル
- 現金回復ステップ
- 次月への持ち越し
- Safety note（売買指示ではない旨を明示）

## §3. Scheduled Run / Observability 現在地

- v86 scheduled run observation: **partial / schedule-trigger observation miss**
- pre-v86 workflow_dispatch reference artifact:
  - weekly report / copy report / email preview txt/html生成確認済み
  - Gmail未着は仕様どおり（real email send無効）
- v102 temporary cron: v103で削除済み
- normal schedule: `0 22 * * 5`（Saturday 07:00 JST）を維持
- v104 `status.json` schema: trigger metadata / reports / email preview / `gmail_send_attempted=false`を導入済み
- 次のnatural scheduled observation:
  - task: Scheduled Weekly Run Observation / Artifact Review
- scheduled target: 2026-06-06 07:00 JST
- recommended observation: 2026-06-06 07:30 JST以降
- 確認対象:
  - scheduled event 発火
  - run conclusion success
  - weekly candidate brief artifact 生成
  - v81/v85/v83/v82/v87 反映
  - email txt/html preview 崩れなし

## §3.5 Hard Gates / 継続禁止事項

- workflow変更は未承認
- manual workflow_dispatch 未承認
- provider live HTTP 未承認
- market-data live fetch 未承認
- cache write: **NO-GO**
- actual refresh/import / manual actual import: **NO-GO**
- broker API / broker login: **NO-GO**
- raw Excel direct parsing: **NO-GO**
- raw broker export parsing 未承認
- env/secret 表示禁止
- dependency/pyproject/Makefile 変更は別承認
- real email send: **NO-GO**
- trading action / order placement / 自動売買: **NO-GO**

## §3.6 Product / Validation Architecture 現在地

- v105 versionless facades:
  - `product/report_view_model.py`
  - `product/portfolio_input.py`
  - `product/candidate_pipeline.py`
- v106 assessment:
  - v95/v97/v98/v100の40 keyを棚卸し
  - 命名揺れ2組、validator severity揺れ0組
- v107 taxonomy skeleton:
  - severity / category / canonical key / legacy alias mappingを定義
  - 既存validatorには未接続
  - concrete consumerなしの追加拡張・一括移行は停止
- v109 portfolio data quality review:
  - fixture/sanitized inputの構造整合・guardrail・target gap・manual confirmationを横断review
- v110 raw input quarantine contract:
  - declaration-only manifest / stdout-only CLI
  - raw path・raw payload読取なし
  - import/cache readinessは常時NO-GO
- v111 raw input quarantine cross-review skeleton:
  - v109 portfolio data quality reviewとv110 quarantine declarationを接続
  - safe fixtureもmanual review required、raw宣言はblocked
  - import/cache readinessは常時NO-GO

## §4. ローカル

```text
observation_log: 538
portfolio human: 55% P0-P2
peer_forward: usable
us_forward: 1/10 thin (matched_normal=1; rows_matched may differ)
p3_us_forward_summary: need 9 toward usable
```

## §5. 直近ゲート

| ゲート | 状態 |
| --- | --- |
| `will_be_matchable_after_date_rows` | 16（log 内 · cache 経過で mature） |
| `write_now_count` | 0（ISO 週重複 · L1 ブロック） |
| L1 | **消費済み 2/2** · [skip](../reports/2026-05-26/approved_execution_L1_skip_20260526.md) |
| ISO 週 rollover | `validate forward-p3-status` → `iso_week_rollover` |
| horizon timeline | `p3_horizon_timeline`（#289） |
| path to usable | `validate p3-path-to-usable` / weekly dry-run **P3 path preflight**（#299） |
| P3 CLI hints | `p3_monitoring_next_commands()`（#299） |
| horizon export | `validate p3-horizon-timeline --format json`（#296） |
| matched P3 vs raw | `matched_normal`（dedupe）≠ `rows_matched`（#302–#304） |
| P3 display | forward-p3-status: `all_rows_sample_quality` vs `p3_sample_quality`（#302） |
| L1 rollover passed | `rollover_passed_write_still_blocked` wording（#303） |
| 重複週方針 | [decision](../docs/decisions/2026-05-26_observation_log_duplicate_week_policy.md) |
| portfolio 70% / P3 | usable 到達後に L3 再承認 |

## §6. 監視コマンド

```bash
scripts/run_weekly_candidate_brief.sh
.venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief --format copy --report-date "$(date +%F)" | pbcopy
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation --dry-run --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate p3-path-to-usable --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate p3-horizon-timeline --format json --horizon-rows 100
.venv/bin/python -m invis_alpha_os.cli.main validate forward-p3-status --format markdown
```

## §7. Weekly Candidate Brief 生成物ポリシー

以下は生成物であり、原則コミットしない。

- `reports/YYYY-MM-DD/weekly_candidate_brief_v0_1.md`
- `reports/YYYY-MM-DD/weekly_candidate_brief_v0_1.json`
- `reports/YYYY-MM-DD/weekly_candidate_brief_copy.md`
- `reports/YYYY-MM-DD/email/*`
- `outputs/operator/weekly_candidate_brief/**`

## §8. 次工程候補

優先順:

1. v104 `status.json`による次回natural scheduled run観測
2. quarantine reviewとmonthly review packの接続評価
3. raw-input approval boundaryの人間レビュー（actual import承認とは分離）

Actual import / broker access / raw Excel direct parsing / cache writeは、上記設計・reviewを完了しても自動承認されない。
