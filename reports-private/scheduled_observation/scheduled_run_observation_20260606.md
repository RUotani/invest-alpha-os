# Scheduled Run Observation — 2026-06-06

## Observation Summary

| 項目 | 結果 |
| --- | --- |
| observation time | 2026-06-05 19:32 JST（Long-Run Phase 1） |
| workflow | `weekly-candidate-brief` |
| event | **not observed** — `event=schedule` の run は一覧に未出現 |
| conclusion | **not yet fired**（観測ウィンドウ 2026-06-06 07:30 JST 未到達） |
| run id | — |
| branch/head | `main` / `bcac62624b96a64dcc12a7058d52a22c66456fb2` |
| artifact count | — |
| status.json | 未確認（natural run なし） |
| weekly_candidate_brief.md | 未確認 |
| weekly_candidate_brief.json | runner 修正後は生成予定（CI upload は workflow 待ち） |
| copy report | 未確認 |
| email preview txt/html | 未確認 |
| gmail_send_attempted | 設計上 `false`（v104） |
| result | **PENDING — re-observe after 2026-06-06 07:30 JST** |

## Findings

- 現時刻は観測ウィンドウ前。cron `0 22 * * 5`（金曜 22:00 UTC ≒ 土曜 07:00 JST）。
- 直近 runs は **workflow_dispatch のみ**（2026-06-01〜02、すべて success）。
- Phase 2: `weekly_candidate_brief.json` の runner 生成漏れを source-only 修正（`run_weekly_candidate_brief.sh`）。

## Missing / Gaps

- natural scheduled run 未確認
- CI artifact upload に JSON 未含む（workflow 変更は未承認のため docs に記録）
- v86 observation: **partial**

## Next Actions

1. 2026-06-06 07:30 JST 以降に `gh run list --workflow weekly_candidate_brief.yml` を再実行
2. schedule run 成功時: artifact / status.json / email preview を read-only 確認
3. `weekly_artifact_gap_analysis_20260606.md` 参照

## Safety Summary

- workflow_dispatch: **未実行**
- workflow 変更: **なし**
- real email send: **なし**
