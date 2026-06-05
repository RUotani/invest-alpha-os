# v1.1 Gmail Auto-Send Setup

版: 2026-06-06  
週次レポートの **SMTP 自動送信**（v1.1 承認済み）。App password はコミットしない。

## 前提

- **方式A (SMTP)**: Gmail 2段階認証 + アプリパスワード → GitHub secrets
- **方式B (OAuth, ローカル推奨)**: 既存 `~/.config/invest-alpha-os/daily_gmail.env` + OAuth token があれば SMTP 未設定でも自動送信
- 送信は `weekly-report-email-send` CLI、`run_weekly_candidate_brief.sh`、または scheduled workflow

## 1回だけ: GitHub secrets / variables

```bash
cd /Users/uotani/Projects/invest-alpha-os

gh secret set SMTP_HOST --body "smtp.gmail.com"
gh secret set SMTP_PORT --body "587"
gh secret set SMTP_USERNAME --body "<your gmail address>"
gh secret set SMTP_PASSWORD --body "<gmail app password>"
gh secret set WEEKLY_REPORT_EMAIL_FROM --body "<your gmail address>"
gh secret set WEEKLY_REPORT_EMAIL_TO --body "<recipient gmail address>"
gh variable set WEEKLY_REPORT_EMAIL_ENABLED --body "true"
```

`WEEKLY_REPORT_EMAIL_ENABLED=true` のとき、scheduled workflow がレポート生成後に自動送信を試行します。

## ローカル即時送信（latest pack · OAuth）

`daily_gmail.env` が設定済みなら SMTP 不要。`--auto-env-file` が既定で env を読み込みます。

```bash
cd /Users/uotani/Projects/invest-alpha-os

env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main weekly-report-email-send \
  --report-date 2026-06-06 \
  --report-root reports-private/manual_issue/weekly_20260606 \
  --send \
  --format markdown
```

## ローカル即時送信（SMTP）

```bash
export WEEKLY_REPORT_EMAIL_ENABLED=true
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USERNAME='<your gmail address>'
export SMTP_PASSWORD='<gmail app password>'
export WEEKLY_REPORT_EMAIL_FROM='<your gmail address>'
export WEEKLY_REPORT_EMAIL_TO='<recipient gmail address>'

env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main weekly-report-email-send \
  --report-date 2026-06-06 \
  --report-root reports-private/manual_issue/weekly_20260606 \
  --send \
  --no-auto-env-file \
  --format markdown
```

`email/` プレビューが無い場合は `README_FOR_USER.md` にフォールバックします。

## ドライラン（送信なし）

```bash
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main weekly-report-email-send \
  --report-date 2026-06-06 \
  --report-root reports-private/manual_issue/latest \
  --format markdown
```

期待: `email_delivery_status: dry_run`

## 失敗時の fallback

送信失敗時も `reports-private/manual_issue/latest/README_FOR_USER.md` が閲覧用正本です。

## 安全

- secret 値をログ出力しない
- 宛先は redacted 表示（例: `r***@gmail.com`）
- 売買指示ではない週次観測レポートのみ
