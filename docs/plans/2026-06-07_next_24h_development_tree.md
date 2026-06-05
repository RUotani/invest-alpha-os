# Next 24h Development Tree — 2026-06-07

## Branch A — Schedule success path

1. 2026-06-06 07:30 JST 以降 read-only 観測
2. artifact download → `weekly-artifact-local-verify`
3. `real_or_pending_weekly_report_review` を実レポート版に更新
4. Report MVP 80–85% へ（scheduled 観測 pass）

## Branch B — Schedule miss path

1. `OBSERVABILITY_MISS` として観測 MD 追記
2. cron / concurrency / GitHub schedule 遅延を docs に記録
3. workflow patch proposal の承認催促（dispatch はしない）

## Branch C — Workflow approval path

1. `docs/proposals/2026-06-06_workflow_approval_boundary_pack.md` 承認
2. JSON upload path 1行追加 PR
3. 次 run で artifact schema 再検証

## Branch D — Report MVP 85% path

1. 実レポート確認後の sample 同期
2. weekly/monthly UX 微調整（golden snapshot 更新）
3. operator dashboard 実データ footnote

## Branch E — Actual import NO-GO path

- Actual Import Readiness **0% 維持**
- broker/raw Excel/cache write/live HTTP は承認パッケージまで停止

## Recommended PR order

1. Post-#485 observation + contract（本 PR）
2. Scheduled observation follow-up（観測後）
3. Workflow upload patch（承認後のみ）

## Stop conditions

workflow_dispatch、unapproved workflow edit、import/cache/broker/live data、pytest 同一原因2回失敗
