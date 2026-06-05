# v1.0 Operator Start Here — Candidate Discovery OS

版: 2026-06-06  
目的: **明日から迷わず始める** 1ページ索引（自動売買ではない）

## 明日まず実行する2コマンド

```bash
cd /Users/uotani/Projects/invest-alpha-os
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main v1-readiness-check --format markdown
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main weekly-report-user-summary --format markdown --source composed
```

期待: `v1_usable_tomorrow: **true**` + 1ページ要約が読めること。

## 導線

| 用途 | パス |
| --- | --- |
| 初日チェックリスト | [v1_0_tomorrow_operational_checklist.md](./v1_0_tomorrow_operational_checklist.md) |
| 週次10分フロー | [v1_0_weekly_10min_flow.md](./v1_0_weekly_10min_flow.md) |
| v1.0 readiness dashboard | [v1_0_operational_readiness_dashboard.md](./v1_0_operational_readiness_dashboard.md) |
| scheduled observation | [scheduled_run_observation_20260606.md](../reports-private/scheduled_observation/scheduled_run_observation_20260606.md) |
| artifact verify（natural） | [weekly_artifact_local_verify_20260606_natural.md](../reports-private/scheduled_observation/weekly_artifact_local_verify_20260606_natural.md) |
| ChatGPT one-page sample | [chatgpt_one_page_summary_sample.md](../reports-private/sample_outputs/chatgpt_one_page_summary_sample.md) |
| プロジェクト目的 | [project_goal_candidate_discovery_os.md](./project_goal_candidate_discovery_os.md) |

## Scheduled Observation 現状（2026-06-06 07:58 JST）

| 項目 | 状態 |
| --- | --- |
| natural `event=schedule` | **未出現** — `OBSERVATION_PENDING_SCHEDULED_RUN_NOT_VISIBLE` |
| natural artifact verify | **未実施** — `OBSERVATION_PENDING_ARTIFACT_NOT_FOUND` |
| v1.0 core（明日実用） | **12/12** — 初日運用は fixture/sample で可 |

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
