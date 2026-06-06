# Send Result — v1.2 Trial Spot Send

| 項目 | 値 |
| --- | --- |
| report_date | 2026-06-06 |
| trial_root | reports-private/trial_send/weekly_v1_2_2026-06-06 |
| content_source | email_preview_html |
| email_delivery_status | sent |
| delivery_transport | gmail_oauth |
| message_id | 19e9a953c07c3a4a |
| subject | [invest-alpha-os] Weekly Report 2026-06-06 |
| recipient_redacted | p***@gmail.com |

## Status taxonomy

- generated: yes
- preview_created: yes
- sent: yes (Gmail API)
- delivered: pending human inbox confirmation

## Command

```bash
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main weekly-report-email-send \
  --report-date 2026-06-06 \
  --report-root reports-private/trial_send/weekly_v1_2_2026-06-06 \
  --send \
  --format markdown
```
