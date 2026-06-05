# v1.0 Operator Start Here — Candidate Discovery OS

版: 2026-06-07（初日運用安定化）  
目的: **明日から迷わず始める** 1ページ索引（自動売買ではない）

## 今日読むファイル（1つに固定）

```text
reports-private/manual_issue/latest/README_FOR_USER.md
```

週次の結論・深掘り候補（285A / AAPL / QQQ）・guardrail・ブロッカーはすべてここから辿れます。

## 明日まず実行する2コマンド（agent / 任意確認用）

```bash
cd /Users/uotani/Projects/invest-alpha-os
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main v1-readiness-check --format markdown
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main weekly-report-user-summary --format markdown --source composed
```

期待: `v1_usable_tomorrow: **true**` + 1ページ要約が読めること。

## 導線

| 用途 | パス |
| --- | --- |
| **今日読む週次レポート** | [latest/README_FOR_USER.md](../reports-private/manual_issue/latest/README_FOR_USER.md) |
| manual issue 索引 | [manual_issue/README.md](../reports-private/manual_issue/README.md) |
| 初日チェックリスト | [v1_0_tomorrow_operational_checklist.md](./v1_0_tomorrow_operational_checklist.md) |
| 週次10分フロー | [v1_0_weekly_10min_flow.md](./v1_0_weekly_10min_flow.md) |
| v1.0 readiness dashboard | [v1_0_operational_readiness_dashboard.md](./v1_0_operational_readiness_dashboard.md) |
| scheduled observation | [scheduled_run_observation_20260606.md](../reports-private/scheduled_observation/scheduled_run_observation_20260606.md) |
| artifact verify（natural） | [weekly_artifact_local_verify_20260606_natural.md](../reports-private/scheduled_observation/weekly_artifact_local_verify_20260606_natural.md) |
| ChatGPT one-page sample | [chatgpt_one_page_summary_sample.md](../reports-private/sample_outputs/chatgpt_one_page_summary_sample.md) |
| プロジェクト目的 | [project_goal_candidate_discovery_os.md](./project_goal_candidate_discovery_os.md) |

## v1.1 Gmail 自動送信（承認済み）

| 項目 | 説明 |
| --- | --- |
| 機能 | `weekly-report-email-send`（SMTP / stdlib） |
| セットアップ | [v1_1_gmail_auto_send_setup.md](./v1_1_gmail_auto_send_setup.md) |
| 動作 | secrets 設定済みなら workflow 後に自動送信 |
| fallback | 送信失敗時も latest README で閲覧可 |

## 別ブロッカー（初日運用は止めない）

| ブロッカー | 状態 | 初日運用 |
| --- | --- | --- |
| GitHub scheduled run | `OBSERVATION_PENDING_SCHEDULED_RUN_NOT_VISIBLE` | **継続可**（manual pack 代替済み） |
| Gmail 配信 | v1.1: secrets 未設定時は `blocked`、設定後は自動送信 | README が fallback |
| v1.0 core | **12/12** | **開始可** |

実体パック: `reports-private/manual_issue/weekly_20260606/`（#501）

## NO-GO 一覧（実行しない）

- workflow_dispatch / workflow 変更
- live HTTP / cache write / actual import
- broker API / raw Excel parsing
- real email send / trading action
- env / secret 表示・コミット

## 人間判断が必要なもの（proposal のみ）

- CI `weekly_candidate_brief.json` upload — [workflow patch proposal](./proposals/2026-06-06_weekly_workflow_artifact_patch_proposal.md)

## 週次の流れ（要約）

1. `v1-readiness-check`
2. `gh run list`（read-only）で schedule 分類
3. artifact あれば `weekly-artifact-local-verify`
4. `weekly-report-user-summary --source composed`
5. copy の結論・guardrail を目視（売買指示ではない）

詳細は [v1_0_weekly_10min_flow.md](./v1_0_weekly_10min_flow.md)。
