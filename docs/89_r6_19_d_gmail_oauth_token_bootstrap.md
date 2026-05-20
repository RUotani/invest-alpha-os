# R6.19-D — Gmail OAuth Token Bootstrap

**日付**: 2026-05-20 · **性質**: surgical fix · `ensure_gmail_credentials()`

---

## Problem

`daily-email --send` failed with `Gmail credentials/token files not configured` when `gmail_token.json` was missing, even though `gmail_credentials.json` and previews worked.

## Fix

- `ensure_gmail_credentials()` — load · refresh · Desktop OAuth `run_local_server(port=0)` · save token (chmod 600)
- `credentials_configured()` — **credentials file only** (token optional until first send)
- Subject: `Daily Observation Report`（spacing）

## Operator flow

1. Configure `~/.config/invest-alpha-os/daily_gmail.env` + `gmail_credentials.json`
2. `daily-email --dry-run`（no OAuth）
3. `daily-email --send` with `CONFIRM_GMAIL_SEND=YES` — browser opens once
4. `gmail_token.json` created locally — **never commit**
5. launchd 07:00 after self-send smoke

## Optional deps

```bash
pip install -e ".[gmail]"
```

---

## 関連

- [docs/80](./80_r6_19_a_gmail_delivery_and_display_names.md)
- [docs/81](./81_r6_19_b_daily_0700_gmail_delivery_runbook.md)
