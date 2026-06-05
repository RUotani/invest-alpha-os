# Scheduled Run Observation — 2026-06-06

## Observation Summary

| 項目 | 結果 |
| --- | --- |
| observation time | 2026-06-05 19:18 JST（観測実施） |
| workflow | `weekly-candidate-brief`（`.github/workflows/weekly_candidate_brief.yml`） |
| event | **not observed** — `event=schedule` の run は一覧に存在せず |
| conclusion | **not yet fired**（観測ウィンドウ未到達） |
| run id | — |
| artifact status | 未確認（natural run なし） |
| status.json | 未確認 |
| weekly candidate brief | 未確認 |
| copy report | 未確認 |
| email preview | 未確認 |
| gmail_send_attempted | 設計上 `false`（v104）— artifact 未取得 |
| result | **PENDING — re-observe after 2026-06-06 07:30 JST** |

## Findings

- 現時刻（2026-06-05 19:18 JST）は、指示の観測ウィンドウ **2026-06-06 07:30 JST 以降** に未到達。
- `gh run list --workflow weekly_candidate_brief.yml --limit 15` の直近は **workflow_dispatch のみ**（2026-06-01〜02、すべて success）。
- workflow cron: `0 22 * * 5`（金曜 22:00 UTC ≒ **土曜 07:00 JST**）。次の natural run は **2026-06-06（土）07:00 JST 前後** が想定される。

## Gaps

- `event=schedule` の natural run 未確認
- v101 checklist 項目（`weekly_candidate_brief.json` 等）の CI 一致は未検証
- v86 scheduled observation は **partial** のまま

## Next Actions

1. **2026-06-06 07:30 JST 以降** に再度 read-only 観測:
   ```bash
   gh run list --repo RUotani/invest-alpha-os --workflow weekly_candidate_brief.yml --limit 10
   ```
2. `event=schedule` かつ success の run があれば:
   ```bash
   gh run view <RUN_ID>
   gh run download <RUN_ID> --dir /tmp/invest-alpha-os-run-artifacts
   ```
   （一時ディレクトリのみ。repo へ artifact コミットしない）
3. `status.json` / email preview / weekly 出力の有無を本ファイルに追記

## Safety Summary

- workflow_dispatch: **未実行**
- workflow 変更: **なし**
- real email send: **なし**
- live market-data / broker / import: **なし**
