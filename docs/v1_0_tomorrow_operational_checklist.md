# v1.0 明日からの運用チェックリスト（2026-06-07）

版: 2026-06-06  
目的: invest-alpha-os を **Candidate Discovery OS** として初日から安全に使う

> 自動売買ボットではない。ブローカー接続・注文実行・actual import は対象外。

## 朝（5分）— 起動確認

```bash
cd /Users/uotani/Projects/invest-alpha-os
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main v1-readiness-check --format markdown
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main progress-dashboard-check --format markdown
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main operator-dashboard-summary --format markdown
```

- [ ] `v1_usable_tomorrow: true`（core 12/12）
- [ ] Hard Gate 項目がすべて未実行のまま
- [ ] `git status` が clean（`handoff/` untracked のみ許容）

## 週次レビュー（10分）

- [ ] `docs/v1_0_weekly_10min_flow.md` に従う
- [ ] `weekly-report-user-summary --source composed` で one-page を取得
- [ ] Weekly copy の結論・guardrail・非売買指示を確認
- [ ] email preview は **確認のみ**（送信しない）

## Scheduled observation（時刻到達後）

**2026-06-06 07:30 JST 以降** に実施:

```bash
gh run list --workflow weekly_candidate_brief.yml --limit 10
```

| 分類 | 次アクション |
| --- | --- |
| SCHEDULE_SUCCESS | `/tmp` に download → `weekly-artifact-local-verify` |
| SCHEDULE_MISS | `scheduled_run_observation_20260606.md` を gap として更新 |
| NOT_YET_OBSERVABLE | 07:30 前は pending のまま（初日運用は fixture/sample で可） |

## 初日にやらないこと（Hard Gate）

- [ ] workflow_dispatch を実行しない
- [ ] `.github/workflows/*` を変更しない
- [ ] live HTTP / cache write / actual import を実行しない
- [ ] broker API / raw Excel を触らない
- [ ] real email send を実行しない
- [ ] secrets / `.env` を表示・コミットしない

## 参照ドキュメント

| 用途 | パス |
| --- | --- |
| v1.0 readiness dashboard | `docs/v1_0_operational_readiness_dashboard.md` |
| 週次10分 | `docs/v1_0_weekly_10min_flow.md` |
| one-page sample | `reports-private/sample_outputs/chatgpt_one_page_summary_sample.md` |
| プロジェクト目的 | `docs/project_goal_candidate_discovery_os.md` |
