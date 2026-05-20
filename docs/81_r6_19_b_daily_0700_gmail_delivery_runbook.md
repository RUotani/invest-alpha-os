# R6.19-B — Daily 07:00 JST Gmail delivery runbook

**日付**: 2026-05-20 · **前提**: R6.19-A merged（`daily-email` · 表示名）

---

## 1. Purpose

毎朝 **07:00（ローカル時刻 · launchd）** に observation-only 日次レポートを Gmail へ送る（**gated**）。

---

## 2. Current status

| 項目 | 状態 |
|---|---|
| バンドル生成 | `scripts/run_daily_gmail_report.sh` |
| メール | `daily-email` CLI（R6.19-A） |
| スケジュール | `ops/launchd/*.plist.template` |
| 重複送信防止 | `email/email_sent.json`（`FORCE_DAILY_GMAIL_SEND=YES` で上書き可） |

---

## 3. Preconditions

- `origin/main` に R6.19-A 反映済み
- US cache ローカル（gitignore）
- Gmail OAuth: credentials + token（**コミット禁止**）
- `~/.config/invest-alpha-os/daily_gmail.env`（`ops/daily_gmail.env.example` 参照）

---

## 4. Gmail OAuth setup

1. Google Cloud で Gmail API 有効化 · OAuth client（Desktop）
2. `gmail_credentials.json` → `~/.config/invest-alpha-os/`
3. 初回トークン取得（R6.19-A docs/80 参照）
4. scope: `https://www.googleapis.com/auth/gmail.send`

---

## 5. Dry-run command

```bash
./scripts/run_daily_gmail_report.sh --dry-run
```

出力: `outputs/operator/daily_usage/YYYY-MM-DD/` · `email/` プレビュー · `run_0700.log`

---

## 6. One-time gated send smoke

```bash
cp ops/daily_gmail.env.example ~/.config/invest-alpha-os/daily_gmail.env
# edit addresses (do not commit)

CONFIRM_GMAIL_SEND=YES ./scripts/run_daily_gmail_report.sh --send
```

---

## 7. Install launchd job

```bash
mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$HOME/Library/Logs/invest-alpha-os"

sed \
  -e "s#__REPO_ROOT__#$(pwd)#g" \
  -e "s#__LOG_DIR__#$HOME/Library/Logs/invest-alpha-os#g" \
  ops/launchd/com.invest-alpha-os.daily-gmail-report.plist.template \
  > "$HOME/Library/LaunchAgents/com.invest-alpha-os.daily-gmail-report.plist"

launchctl unload "$HOME/Library/LaunchAgents/com.invest-alpha-os.daily-gmail-report.plist" 2>/dev/null || true
launchctl load "$HOME/Library/LaunchAgents/com.invest-alpha-os.daily-gmail-report.plist"
launchctl list | grep invest-alpha-os || true
```

**注意**: Mac がスリープ中は **07:00 厳密配信は保証されない**。起床後にログ確認。

---

## 8. Verify job

```bash
launchctl print "gui/$(id -u)/com.invest-alpha-os.daily-gmail-report" 2>/dev/null | head -20
tail -50 "$HOME/Library/Logs/invest-alpha-os/launchd_daily_gmail_report.out.log"
```

---

## 9. Disable / uninstall

```bash
launchctl unload "$HOME/Library/LaunchAgents/com.invest-alpha-os.daily-gmail-report.plist"
rm "$HOME/Library/LaunchAgents/com.invest-alpha-os.daily-gmail-report.plist"
```

---

## 10. Logs and troubleshooting

| ログ | パス |
|---|---|
| スクリプト | `outputs/operator/daily_usage/YYYY-MM-DD/run_0700.log` |
| launchd stdout | `~/Library/Logs/invest-alpha-os/launchd_daily_gmail_report.out.log` |
| launchd stderr | `~/Library/Logs/invest-alpha-os/launchd_daily_gmail_report.err.log` |

| 症状 | 対処 |
|---|---|
| 重複スキップ | `email/email_sent.json` あり · 再送は `FORCE_DAILY_GMAIL_SEND=YES` |
| send 失敗 | `CONFIRM_GMAIL_SEND` · allowlist · token |
| `daily-email` なし | main を R6.19-A 以降に更新 |

---

## 11. Safety boundaries

- observation-only · **売買推奨なし**
- default daily/signals preview **有効化しない**
- 受信者 allowlist / self のみ
- 市場 live HTTP / cache write **なし**（バンドル生成は既存 CLI read-only）

---

## 12. Relation to R7 discovery engine

本 runbook は **named watchlist 観測の日次配信**。横断 discovery は [docs/82](./82_r7_0_a_discovery_engine_planning.md)。
