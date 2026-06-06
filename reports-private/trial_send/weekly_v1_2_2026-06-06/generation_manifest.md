# Generation Manifest — v1.2 Trial Spot Send

| 項目 | 値 |
| --- | --- |
| schema_version | trial_send_manifest.v1 |
| report_date | 2026-06-06 |
| trial_root | reports-private/trial_send/weekly_v1_2_2026-06-06 |
| generation_mode | local_cli_cache_only |
| ux_version | v1.2 |
| purpose | trial spot Gmail send |

## CLI steps

1. `weekly-candidate-brief --format markdown` → `weekly_candidate_brief_v1_2.md`
2. `weekly-candidate-brief --format copy` → `weekly_candidate_brief_copy.md`
3. `weekly-candidate-brief --format json` → `weekly_candidate_brief.json`
4. `weekly-candidate-brief-email` → `email/email_preview.{txt,html,eml}`
5. `weekly-report-user-summary --source sample` → `weekly_report_user_summary.md`

## Artifacts

| ファイル | 状態 |
| --- | --- |
| README_FOR_USER.md | created |
| weekly_candidate_brief_v1_2.md | generated |
| weekly_candidate_brief_copy.md | generated |
| weekly_report_user_summary.md | generated |
| email/email_preview.txt | generated |
| email/email_preview.html | generated |
| send_result.md | recorded post-send |

## Safety

- no live HTTP
- no cache write
- no broker API
- observation-only weekly report
