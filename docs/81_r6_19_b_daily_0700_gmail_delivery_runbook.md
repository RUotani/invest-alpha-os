# R6.19-B — Daily 07:00 Gmail delivery runbook

**Status**: operator copy-paste · **send requires explicit gates**  
**Related**: [docs/80](./80_r6_19_a_gmail_delivery_and_display_names.md), [docs/89](./89_r6_19_d_gmail_oauth_token_bootstrap.md), [docs/90](./90_r6_19_f_launchd_0700_gmail_setup.md), [docs/91](./91_r6_19_e_japanese_gmail_report.md), [docs/118](./118_ops_i_gmail_no_attachment.md)

---

## 目的

毎朝 **07:00 JST（Mac ローカル）** に日次観測 Gmail を送る。取引推奨ではない（observation-only）。

## 前提（ローカル · git 外）

| ファイル | 用途 |
| --- | --- |
| `~/.config/invest-alpha-os/daily_gmail.env` | `CONFIRM_GMAIL_SEND`, `GMAIL_REPORT_TO` 等 |
| `~/.config/invest-alpha-os/gmail_credentials.json` | OAuth client |
| `~/.config/invest-alpha-os/gmail_token.json` | OAuth token（初回 send で生成） |

**commit 禁止**: credentials / token / `.env`

---

<<< COPY FROM HERE — DRY-RUN（既定） >>>

```bash
cd /path/to/invest-alpha-os
./scripts/run_daily_gmail_report.sh --dry-run
```

生成物（git 外）:

```text
outputs/operator/daily_usage/YYYY-MM-DD/
  daily_us_cache_preview.md
  signals_us_cache_preview.md
  operator_summary.md
  email/email_preview.{eml,txt,html}
  run_0700.log
  status.json
```

プレビュー確認:

```bash
.venv/bin/python -m invis_alpha_os.cli.main daily-email \
  --bundle-dir outputs/operator/daily_usage/$(.venv/bin/python -c "from invis_alpha_os.utils.date_utils import today_jst_iso; print(today_jst_iso())") \
  --dry-run
```

<<< COPY UNTIL HERE >>>

---

## 手動 gated send（人間承認 · 本番送信）

```bash
CONFIRM_GMAIL_SEND=YES \
GMAIL_REPORT_TO="your.address@gmail.com" \
GMAIL_REPORT_ALLOWLIST="your.address@gmail.com" \
GMAIL_CREDENTIALS_FILE="$HOME/.config/invest-alpha-os/gmail_credentials.json" \
GMAIL_TOKEN_FILE="$HOME/.config/invest-alpha-os/gmail_token.json" \
./scripts/run_daily_gmail_report.sh --send
```

初回 `--send` でブラウザ OAuth が開く（[docs/89](./89_r6_19_d_gmail_oauth_token_bootstrap.md)）。

---

## launchd 07:00 セットアップ

テンプレ: `ops/launchd/com.invest-alpha-os.daily-gmail-report.plist.template`  
詳細: [docs/90](./90_r6_19_f_launchd_0700_gmail_setup.md)

```bash
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs/invest-alpha-os"
sed -e "s#__REPO_ROOT__#$(pwd)#g" \
    -e "s#__LOG_DIR__#$HOME/Library/Logs/invest-alpha-os#g" \
  ops/launchd/com.invest-alpha-os.daily-gmail-report.plist.template \
  > "$HOME/Library/LaunchAgents/com.invest-alpha-os.daily-gmail-report.plist"
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.invest-alpha-os.daily-gmail-report.plist" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.invest-alpha-os.daily-gmail-report.plist"
launchctl enable "gui/$(id -u)/com.invest-alpha-os.daily-gmail-report"
```

---

## 安全ゲート

| Gate | 必須 |
| --- | --- |
| `CONFIRM_GMAIL_SEND=YES` | `--send` 時 |
| `GMAIL_REPORT_TO` / allowlist | 送信先 |
| `daily_gmail.env` | launchd / スクリプト |
| 重複送信防止 | `email_sent.json` 存在時 skip（`FORCE_DAILY_GMAIL_SEND=YES` で上書き） |

## 禁止事項

- Gmail credentials / token の repo commit
- 本 runbook だけでの無ゲート `--send`
- 取引推奨文言の追加

## トラブルシュート

| 症状 | 確認 |
| --- | --- |
| `credentials not configured` | [docs/89](./89_r6_19_d_gmail_oauth_token_bootstrap.md) |
| 07:00 未送信 | `launchctl print gui/$(id -u)/com.invest-alpha-os.daily-gmail-report` |
| プレビューのみ欲しい | `--dry-run`（既定） |
| 日本語本文 | [docs/91](./91_r6_19_e_japanese_gmail_report.md) |

## Product 週次との境界

- 週次 Product ops: [docs/160](./160_product_weekly_operator_one_pager.md)（Gmail とは独立）
- Gmail は **operator daily bundle** 専用 — `outputs/operator/daily_usage/` のみ
