# v1.0 週次10分フロー — Weekly Candidate Brief

版: 2026-06-06  
対象: Global Multi-Asset Candidate Discovery OS（自動売買ではない）

## 前提

- read-only / fixture-first が既定
- workflow_dispatch・live HTTP・cache write・actual import・real email send は **実行しない**
- 売買指示ではなく、候補・guardrail・反証のレビュー用

## 10分フロー

| 分 | ステップ | コマンド / 操作 |
| ---: | --- | --- |
| 1 | v1.0 readiness 確認 | `env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main v1-readiness-check --format markdown` |
| 2 | scheduled run 分類（read-only） | `gh run list --workflow weekly_candidate_brief.yml --limit 10`（schedule なし → pending 記録で終了） |
| 3 | artifact download（success 時のみ） | `gh run download <RUN_ID> --dir /tmp/invest-alpha-os-weekly-<RUN_ID>` |
| 4 | artifact verify | `weekly-artifact-local-verify --report-date <date> --report-dir /tmp/.../reports/<date> --status-file /tmp/.../outputs/operator/weekly_candidate_brief/<date>/status.json --json-report-optional` |
| 5 | one-page summary | `weekly-report-user-summary --format markdown --source composed --report-date <date>` |
| 6 | 結論・guardrail 確認 | copy の `## 今週の結論` / `## ポートフォリオ制約` を目視 |
| 7 | email preview 確認 | `email_preview.txt` または sample を開く（送信しない） |
| 8 | 記録 | `reports-private/scheduled_observation/` に分類メモ（artifact 本体はコミットしない） |

## 候補0件 / 候補ありの見方

| 状態 | 確認ポイント |
| --- | --- |
| 候補0件 | `今週は新規買いを急がない` + coverage 理由（日本語）+ fixture 名が出ていないこと |
| 候補あり | `今週は候補あり` + 第1/深掘り/監視/見送り + `これは売買指示ではありません` |

## 週次でやらないこと

- workflow 変更 / workflow_dispatch
- broker API / raw Excel / actual import
- Gmail 本番送信（preview のみ）
- trading action 文言の追加

## 関連

- `docs/v1_0_tomorrow_operational_checklist.md`
- `docs/operator_user_guide.md`
- `docs/project_goal_candidate_discovery_os.md`
