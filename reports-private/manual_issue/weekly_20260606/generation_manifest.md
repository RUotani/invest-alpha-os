# Generation Manifest — weekly_20260606 manual issue

| 項目 | 値 |
| --- | --- |
| report_date | 2026-06-06 |
| generated_at | 2026-06-06 JST（ローカル CLI） |
| main_at_generation | fce211a15a5ea06ff1e196152278ed4cb505cff3 |
| mode | cache-only / no live HTTP / no workflow_dispatch |
| gmail_send | **false**（dry-run preview only） |
| v1_usable_tomorrow | true |

## Commands executed

```bash
export JQUANTS_API_KEY= JQUANTS_ENABLED= JQUANTS_ALLOW_LIVE_HTTP= CONFIRM_US_LIVE_HTTP=
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main v1-readiness-check --format markdown
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main weekly-report-user-summary --format markdown --source composed --report-date 2026-06-06
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief --format markdown --report-date 2026-06-06 --out .../weekly_candidate_brief_v0_1.md
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief --format copy --report-date 2026-06-06 --out .../weekly_candidate_brief_copy.md
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief --format json --report-date 2026-06-06 --out .../weekly_candidate_brief.json
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief-email --report-date 2026-06-06 --report-dir ... --copy-file .../weekly_candidate_brief_copy.md --full-md .../weekly_candidate_brief_v0_1.md
```

## Artifacts in this directory

| file | description |
| --- | --- |
| README_FOR_USER.md | ユーザー向け要約（**まずここ**） |
| weekly_candidate_brief_copy.md | copy-ready 週次本文 |
| weekly_candidate_brief_v0_1.md | フル markdown |
| weekly_candidate_brief.json | 機械可読 JSON |
| weekly_report_user_summary.md | one-page user summary |
| v1_readiness_check.md | v1.0 readiness snapshot |
| email/email_preview.txt | メール text preview（**.gitignore · ローカルのみ**） |
| email/email_preview.html | メール html preview（**.gitignore · ローカルのみ**） |
| email/email_preview.eml | MIME preview（**.gitignore · ローカルのみ**） |

## Safety

- workflow_dispatch: not executed
- workflow change: none
- real email: not sent
- cache write / actual import / broker: not executed
